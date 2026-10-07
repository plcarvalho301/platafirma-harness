"""predicados_acervo — `release conferir acervo`: os predicados de §11 da spec espelho-de-leitura.

Pedido da engenharia sob o card #3193, passo 14 (carta 20261001T165146-engenharia). Esta
classe mede, por enquanto, dois predicados de §11 e aponta uma pendência:

  §11 predicado 7 — toda impressão `servindo` tem `sinais.fidelidade`, e nenhuma de classe A
                    com `perda`, `insercao` ou `duplicacao` em papel de corpo (§4.5).
  §11 predicado 9 — toda impressão `servindo` com espelho tem `veredito` da régua vigente; a
                    julgada por régua anterior é divergência até o rejulgar (§9, caso 8).
  §4.2 item 6     — a selada de obra marcada «transcrita e indexada» sem índice aprovado no
                    motor (o gate do `motor indexar`, #3203, pela contagem). NÃO é divergência: sai à parte, como pendência dirigida à ia, e não
                    mexe no exit.

Recorte do predicado 7 (decisão de ti, 01/10): mede as impressões `servindo` COM espelho. A
`servindo` sem espelho é matéria do predicado 1 de §11, que a própria spec põe em regime de
aviso até o lote inicial (#3194). Medir o 7 ao pé da letra antes do lote faria as ~1.000
impressões sem espelho divergirem por um motivo que a spec já classifica como aviso, e o exit
1 permanente esconderia a divergência real. A contagem das sem espelho sai como aviso,
nunca omitida. Quando o lote fechar, o predicado 1 entra nesta classe e as cobra.

Classe A: a de `sinais.fidelidade.classe`; a medida antiga (anterior ao #3193) não grava a
classe, e então vale a classe do tipo real (`metodo.conversao.tipo`), pela mesma tabela do
conversor (`contrato.CLASSE_A_TIPOS`).

Fonte única: a régua vigente (`VERSAO_REGUA`), os papéis de corpo (`PAPEL_DE_CORPO`) e os tipos
de classe A NÃO se copiam para cá. Lêem-se, por AST e sem importar nada, do código SERVIDO de
platafirma-conhecimento (`<PF_RELEASE_RAIZ>/platafirma-conhecimento/current/conversor/conversor/`).
Régua ilegível é "não consegui olhar", nunca conforme.

Os dados vêm de dois Postgres da casa por `docker exec … psql` (o mesmo caminho de `acervo
psql`): `rag-extractor-pg` (catálogo, schema `acervo`) e `motor-pg` (schema `motor`). Fora do ar:
indeterminável, exit 5 (§11, cabeçalho). Só olha: nenhuma escrita.

Fora desta classe ainda (§11): os predicados 1 a 6 e 8 (balde, órfão, unicidade, prazo, fatia).
A saída declara a ausência; não a omite.
"""
import ast
import json
import os
import re
import subprocess

import resultado

PROD_RAIZ = os.environ.get("PF_RELEASE_RAIZ", "/opt/platafirma")
SERVIDO_CONVERSOR = os.environ.get(
    "PF_CONVERSOR_SERVIDO",
    os.path.join(PROD_RAIZ, "platafirma-conhecimento", "current", "conversor", "conversor"))

BANCOS = {
    "rag": ("rag-extractor-pg", "rag", "rag_extractor"),
    "motor": ("motor-pg", "motor", "motor"),
}

METRICAS_BLOQUEANTES = ("perda", "insercao", "duplicacao")
MARCACAO_INDEXADA = "transcrita e indexada"   # motor_acervo.curadoria.obras.MARCACAO_INDEXADA
TIPO_PDF = "application/pdf"
MOSTRAR = 5                                     # ids citados por motivo
FORA_DA_CLASSE = "§11 predicados 1 a 6 e 8 ainda fora desta classe"

_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


class Indeterminavel(Exception):
    """Fonte que não respondeu: o item sai indeterminável com esta mensagem."""


# --- leitura -----------------------------------------------------------------------------

def psql_json(banco, sql):
    """Roda `sql` (um SELECT que devolve UMA linha com um json) no banco da allowlist e devolve o
    valor decodificado. Qualquer falha levanta Indeterminavel."""
    ctr, usr, base = BANCOS[banco]
    env = dict(os.environ)
    env.setdefault("DOCKER_HOST", f"unix:///run/user/{os.getuid()}/docker.sock")
    try:
        p = subprocess.run(
            ["docker", "exec", "-i", ctr, "psql", "-U", usr, "-d", base, "-tA",
             "-v", "ON_ERROR_STOP=1", "-c", sql],
            capture_output=True, text=True, env=env, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Indeterminavel(f"{ctr}: {e}") from None
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or f"psql saiu {p.returncode}").strip().splitlines()
        raise Indeterminavel(f"{ctr}: {msg[0] if msg else p.returncode}")
    texto = p.stdout.strip()
    try:
        return json.loads(texto) if texto else None
    except ValueError:
        raise Indeterminavel(f"{ctr}: resposta que não é json: {texto[:80]!r}") from None


def _constantes(caminho):
    """{nome: valor} das atribuições de topo de um módulo: int, str e frozenset/set de str ou de
    nome já visto. Sem importar o módulo."""
    with open(caminho, encoding="utf-8") as f:
        arvore = ast.parse(f.read(), filename=caminho)
    vistos = {}

    def valor(no):
        if isinstance(no, ast.Constant) and isinstance(no.value, (int, str)):
            return no.value
        if isinstance(no, ast.Name) and no.id in vistos:
            return vistos[no.id]
        if isinstance(no, ast.Call) and getattr(no.func, "id", None) in ("frozenset", "set") \
                and len(no.args) == 1:
            no = no.args[0]
        if isinstance(no, (ast.Set, ast.Tuple, ast.List)):
            itens = [valor(e) for e in no.elts]
            if all(isinstance(i, str) for i in itens):
                return frozenset(itens)
        return None

    for no in arvore.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1 and isinstance(no.targets[0], ast.Name):
            alvo, expr = no.targets[0].id, no.value
        elif isinstance(no, ast.AnnAssign) and isinstance(no.target, ast.Name) and no.value is not None:
            alvo, expr = no.target.id, no.value
        else:
            continue
        v = valor(expr)
        if v is not None:
            vistos[alvo] = v
    return vistos


def regua_servida(raiz=None):
    """(versao_regua, papel_de_corpo, classe_a_tipos) do conversor servido. Indeterminavel se faltar."""
    raiz = raiz or SERVIDO_CONVERSOR
    try:
        regua = _constantes(os.path.join(raiz, "regua.py"))
        contrato = _constantes(os.path.join(raiz, "contrato.py"))
    except (OSError, SyntaxError) as e:
        raise Indeterminavel(f"não li a régua servida em {raiz}: {e}") from None
    versao, corpo, classe_a = regua.get("VERSAO_REGUA"), regua.get("PAPEL_DE_CORPO"), \
        contrato.get("CLASSE_A_TIPOS")
    if not isinstance(versao, int) or not corpo or not classe_a:
        raise Indeterminavel(f"régua servida em {raiz} sem VERSAO_REGUA, PAPEL_DE_CORPO ou "
                             "CLASSE_A_TIPOS legíveis")
    return versao, corpo, classe_a


SQL_SERVINDO = """
select coalesce(json_agg(json_build_object(
         'id', i.id::text,
         'tipo', i.metodo -> 'conversao' ->> 'tipo',
         'espelho', i.espelho is not null,
         'fidelidade', i.espelho -> 'sinais' -> 'fidelidade',
         'tem_fidelidade', coalesce((i.espelho -> 'sinais') ? 'fidelidade', false),
         'regua', i.espelho -> 'veredito' ->> 'regua')), '[]'::json)
  from acervo.impressao i where i.estado = 'servindo'
"""

SQL_TEM_MARCACAO = """
select json_build_object('tem', exists (select 1 from information_schema.columns
 where table_schema = 'acervo' and table_name = 'obra' and column_name = 'marcacao'))
"""

# A selada (arq:0119 §5; leitura_atos.selada_existente): em_construcao, com espelho e trechos.
# Marcação: a coluna, quando existir (#3202); sem ela, a regra do estoque
# (obras.marcacao_de_uso): obra com impressão servindo é «transcrita e indexada».
SQL_SELADAS = """
select coalesce(json_agg(json_build_object(
         'id', i.id::text, 'obra', i.obra_id::text, 'titulo', o.titulo,
         'elegiveis', (select count(*) from acervo.trecho t where t.impressao_id = i.id and t.elegivel),
         'indexada', {indexada})), '[]'::json)
  from acervo.impressao i join acervo.obra o on o.id = i.obra_id
 where i.estado = 'em_construcao' and i.espelho is not null
   and exists (select 1 from acervo.trecho t where t.impressao_id = i.id)
"""
INDEXADA_POR_COLUNA = "(o.marcacao = '" + MARCACAO_INDEXADA + "')"
INDEXADA_POR_ESTOQUE = ("exists (select 1 from acervo.impressao s where s.obra_id = i.obra_id "
                        "and s.estado = 'servindo')")

# O gate do motor (escrita_nova.gate_indice, #3203): um vetor por trecho elegível no índice de trecho e
# o vetor de faceta da impressão. Aqui pela contagem, que não pede o método (modelo e backend) do rag; o
# gate exato, trecho a trecho, roda no `acervo promover`, contra a selada inteira (arq:0046).
SQL_INDICES = """
select coalesce(json_agg(json_build_object('impressao', x.imp, 'vetores', x.vetores,
                                           'faceta', x.faceta)), '[]'::json)
  from (select i.impressao_id::text as imp,
               max(case when i.granularidade = 'trecho'
                        then (select count(*) from motor.vetor v where v.indice_id = i.id)
                        else 0 end) as vetores,
               bool_or(i.remissao = 'faceta'
                       and exists (select 1 from motor.vetor v where v.indice_id = i.id)) as faceta
          from motor.indice i
         where i.impressao_id = any(array[{ids}]::uuid[])
           and i.estado in ('em_construcao', 'servindo')
         group by i.impressao_id) x
"""


# I13 (#3323, bloqueante; a cura é a #3332): nenhum derivado anterior existe depois da promoção.
# Três faces: impressão aposentada de obra ou casa viva (a de obra/casa retirada é a volta da
# retirada e fica); índice no motor cuja impressão não existe mais; espelho no balde sem
# impressão que o reclame. O motor e o acervo não se juntam no SQL: cada um devolve a sua lista.
SQL_I13_RAG = """
select json_build_object(
  'obra', (select coalesce(json_agg(i.id::text), '[]'::json) from acervo.impressao i
            join acervo.obra o on o.id = i.obra_id
           where i.estado = 'aposentada' and o.retirada_em is null),
  'casa', (select coalesce(json_agg(ci.id::text), '[]'::json) from acervo.casa_impressao ci
            join acervo.casa c on c.id = ci.casa_id
           where ci.estado = 'aposentada' and c.retirada_em is null),
  'existentes', (select coalesce(json_agg(x.id), '[]'::json) from (
                   select id::text from acervo.impressao
                   union all select id::text from acervo.casa_impressao) x(id)))
"""
SQL_I13_MOTOR = """
select coalesce(json_agg(distinct coalesce(i.impressao_id, i.alvo_impressao_id)::text), '[]'::json)
  from motor.indice i
"""
NOME_I13 = "I13: nenhum derivado anterior depois da promoção (impressão, índice, espelho)"
ACERVO_BIN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "acervo")


def espelhos_orfaos(bin_acervo=ACERVO_BIN):
    """Quantos espelhos o balde tem sem impressão que os reclame: o plano seco de `acervo apagar
    biblioteca espelho --json` (o mesmo critério que apaga). Falha é Indeterminavel."""
    try:
        p = subprocess.run([bin_acervo, "apagar", "biblioteca", "espelho", "--json"],
                           capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Indeterminavel(f"balde: {e}") from None
    try:
        data = json.loads(p.stdout) if p.returncode == 0 else None
    except ValueError:
        data = None
    if not isinstance(data, dict) or "n" not in data:
        msg = (p.stderr or p.stdout or f"saiu {p.returncode}").strip().splitlines()
        raise Indeterminavel(f"balde: {msg[0] if msg else p.returncode}")
    return int(data["n"])


# --- predicados (puros) --------------------------------------------------------------------

def predicado_13(rag, indexadas_no_motor, espelhos_sem_dono):
    """Veredito do I13: `rag` = {obra, casa, existentes} de SQL_I13_RAG; `indexadas_no_motor` = as
    impressões que algum índice do motor aponta; `espelhos_sem_dono` = contagem do balde."""
    existentes = set(rag.get("existentes") or [])
    obra, casa = rag.get("obra") or [], rag.get("casa") or []
    orfaos = sorted(i for i in (indexadas_no_motor or []) if i and i not in existentes)
    partes = []
    if obra:
        partes.append(f"{len(obra)} impressão(ões) aposentada(s) de obra viva ({_lista(obra)})")
    if casa:
        partes.append(f"{len(casa)} impressão(ões) aposentada(s) de casa viva ({_lista(casa)})")
    if orfaos:
        partes.append(f"{len(orfaos)} índice(s) do motor de impressão que não existe ({_lista(orfaos)})")
    if espelhos_sem_dono:
        partes.append(f"{espelhos_sem_dono} espelho(s) no balde sem impressão que o reclame")
    if partes:
        return resultado.divergente(" · ".join(partes) + " — cura: a promoção apaga no ato (#3332); "
                                    "o espelho, `acervo apagar biblioteca espelho --apply`")
    return resultado.conforme()



def _classe(linha, classe_a):
    fid = linha.get("fidelidade") if isinstance(linha.get("fidelidade"), dict) else {}
    if fid.get("classe") in ("A", "B", "C"):
        return fid["classe"]
    tipo = linha.get("tipo")
    if tipo in classe_a:
        return "A"
    return "B" if tipo == TIPO_PDF else None


def _bloqueio_classe_a(fid, corpo):
    """(metrica, papel, valor) do primeiro bloqueante de classe A, ou None."""
    for metrica in METRICAS_BLOQUEANTES:
        por_papel = fid.get(metrica)
        if not isinstance(por_papel, dict):
            continue
        for papel, valor in sorted(por_papel.items()):
            if papel in corpo and isinstance(valor, (int, float)) and valor > 0:
                return metrica, papel, valor
    return None


def _lista(ids):
    mostra = ", ".join(i[:8] for i in ids[:MOSTRAR])
    return mostra + (f" +{len(ids) - MOSTRAR}" if len(ids) > MOSTRAR else "")


def predicado_7(servindo, corpo, classe_a):
    """Veredito do predicado 7 sobre as `servindo` com espelho."""
    com = [l for l in servindo if l.get("espelho")]
    sem_fid = [l["id"] for l in com if not l.get("tem_fidelidade")]
    bloqueadas = []
    for l in com:
        fid = l.get("fidelidade")
        if not isinstance(fid, dict) or _classe(l, classe_a) != "A":
            continue
        achado = _bloqueio_classe_a(fid, corpo)
        if achado:
            bloqueadas.append((l["id"], achado))
    partes = []
    if sem_fid:
        partes.append(f"{len(sem_fid)} sem sinais.fidelidade ({_lista(sem_fid)})")
    if bloqueadas:
        exemplo = "; ".join(f"{i[:8]} {m}={v} em {p}" for i, (m, p, v) in bloqueadas[:MOSTRAR])
        partes.append(f"{len(bloqueadas)} de classe A com perda, inserção ou duplicação em papel "
                      f"de corpo ({exemplo}{' …' if len(bloqueadas) > MOSTRAR else ''})")
    if partes:
        return resultado.divergente(f"de {len(com)} servindo com espelho: " + " · ".join(partes)
                                    + " — cura: reextrair (§9)")
    return resultado.conforme()


def predicado_9(servindo, versao):
    """Veredito do predicado 9: veredito ausente ou de régua menor que a vigente diverge."""
    com = [l for l in servindo if l.get("espelho")]
    sem, velhas = [], []
    for l in com:
        r = l.get("regua")
        if r in (None, ""):
            sem.append(l["id"])
            continue
        try:
            if int(r) < versao:
                velhas.append(l["id"])
        except (TypeError, ValueError):
            sem.append(l["id"])
    partes = []
    if sem:
        partes.append(f"{len(sem)} sem veredito ({_lista(sem)})")
    if velhas:
        partes.append(f"{len(velhas)} julgadas por régua anterior à {versao} ({_lista(velhas)})")
    if partes:
        return resultado.divergente(f"de {len(com)} servindo com espelho: " + " · ".join(partes)
                                    + " — cura: acervo curar biblioteca --rejulgar --lote --apply")
    return resultado.conforme()


def pendencia_motor(seladas, indices):
    """As seladas de obra marcada para indexar sem índice aprovado (§4.2 item 6): sem um vetor por
    trecho elegível no índice de trecho, ou sem o vetor de faceta (o gate do motor, pela contagem)."""
    por_impressao = {x.get("impressao"): x for x in (indices or []) if isinstance(x, dict)}

    def pronta(s):
        x = por_impressao.get(s["id"]) or {}
        n = s.get("elegiveis") or 0
        return n > 0 and x.get("vetores") == n and bool(x.get("faceta"))

    return [s for s in seladas if s.get("indexada") and not pronta(s)]


# --- a classe ------------------------------------------------------------------------------

def medir(regua_raiz=None, ler=psql_json, orfaos_do_balde=espelhos_orfaos):
    """(itens, avisos, pendencias): o que `conferir_acervo` imprime. `ler(banco, sql)` é a porta
    para o banco e `orfaos_do_balde()` a do balde, trocáveis no teste."""
    itens, avisos, pendencias = [], [FORA_DA_CLASSE], []
    nome7 = "§11 predicado 7: fidelidade medida, sem bloqueante de classe A em papel de corpo"
    nome9 = "§11 predicado 9: veredito da régua vigente"

    try:
        versao, corpo, classe_a = regua_servida(regua_raiz)
        regua_erro = None
    except Indeterminavel as e:
        regua_erro = str(e)
    try:
        servindo = ler("rag", SQL_SERVINDO) or []
        servindo_erro = None
    except Indeterminavel as e:
        servindo_erro = f"catálogo não respondeu: {e}"

    erro = servindo_erro or regua_erro
    if erro:
        itens.append((nome7, resultado.indeterminavel(erro)))
        itens.append((nome9, resultado.indeterminavel(erro)))
    else:
        itens.append((nome7, predicado_7(servindo, corpo, classe_a)))
        itens.append((nome9, predicado_9(servindo, versao)))
        sem_espelho = sum(1 for l in servindo if not l.get("espelho"))
        if sem_espelho:
            avisos.append(f"aviso: {sem_espelho} de {len(servindo)} servindo sem espelho (§11 "
                          "predicado 1: aviso até o lote inicial, #3194); fora do recorte do 7")

    try:
        tem_coluna = (ler("rag", SQL_TEM_MARCACAO) or {}).get("tem")
        sql = SQL_SELADAS.format(indexada=INDEXADA_POR_COLUNA if tem_coluna else INDEXADA_POR_ESTOQUE)
        seladas = ler("rag", sql) or []
        ids = [s["id"] for s in seladas if s.get("indexada") and _UUID.match(s.get("id", ""))]
        indices = ler("motor", SQL_INDICES.format(
            ids=", ".join(f"'{i}'" for i in ids))) if ids else []
        pend = pendencia_motor(seladas, indices)
        regra = "coluna acervo.obra.marcacao" if tem_coluna else "regra do estoque (servindo = indexada)"
        if pend:
            pendencias.append({
                "para": "ia",
                "o_que": "selada de obra marcada «transcrita e indexada» sem índice aprovado no motor",
                "ancora": "spec espelho-de-leitura §4.2 item 6",
                "marcacao_por": regra,
                "impressoes": [{"impressao": s["id"], "obra": s["obra"], "titulo": s.get("titulo")}
                               for s in pend],
            })
        avisos.append(f"pendência do motor (→ ia): {len(pend)} selada(s) de {len(seladas)} "
                      f"sem índice aprovado; marcação pela {regra}")
    except Indeterminavel as e:
        avisos.append(f"pendência do motor: não consegui olhar ({e})")
        pendencias.append({"para": "ia", "indeterminavel": str(e)})
    # a pendência não é item: não pesa no exit (§4.2 item 6: «não é divergência»)

    try:
        itens.append((NOME_I13, predicado_13(ler("rag", SQL_I13_RAG) or {}, ler("motor", SQL_I13_MOTOR) or [],
                                             orfaos_do_balde())))
    except Indeterminavel as e:
        itens.append((NOME_I13, resultado.indeterminavel(str(e))))
    return itens, avisos, pendencias


def conferir_acervo(alvo, sha_release, como_json=False):
    itens, avisos, pendencias = medir()
    return resultado.relatorio("acervo", alvo, itens, sha_release, como_json=como_json,
                               extra={"avisos": avisos, "pendencias": pendencias})
