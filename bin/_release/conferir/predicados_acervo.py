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
import sys

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
NOME_INVARIANTES = "I1 a I13: invariantes do ciclo de vida do dado (guia ciclo-de-vida-do-dado-do-acervo §6)"
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


# --- invariantes I1 a I13 (#3323, #3324) --------------------------------------------------------
#
# Uma função por invariante (`i1` … `i13`), para o relato citar «I2». Cada uma recebe os dados
# coletados (`coletar`) e devolve a lista das CHAVES que violam, no formato `<tipo>:<id>`
# (obra, impressao, indice, geracao, casa_impressao, espelho-orfao…), ou None quando o lado que a
# mede não respondeu (nunca zero: não conseguir olhar não é conforme). A chave é o que o retrato
# guarda e o gate compara: violação NOVA é chave que o retrato anterior não tinha.
# A classe (bloqueante ou aviso) é a do guia ciclo-de-vida-do-dado-do-acervo §6 e da arq:0121 §5.2.

INVARIANTES = {
    "I1": ("uma servindo", "bloqueante"),
    "I2": ("cobertura no índice", "bloqueante"),
    "I3": ("retirada não serve", "bloqueante"),
    "I4": ("vetor com alvo", "bloqueante"),
    "I5": ("índice da servindo", "bloqueante"),
    "I6": ("espelho presente", "aviso"),
    "I7": ("ficha confere", "aviso"),
    "I8": ("uma geração", "bloqueante"),
    "I9": ("régua vigente", "aviso"),
    "I10": ("retirada com autoria", "aviso"),
    "I11": ("sobra", "bloqueante"),
    "I12": ("sombra reclamada", "aviso"),
    "I13": ("nenhum anterior", "bloqueante"),
}
# a exposição da arq:0119 §6 pelos valores que o banco ainda guarda em acervo.obra.marcacao
EXPOSICAO = {"inteira": "arquivo", "transcrita": "texto", "transcrita e indexada": "trecho"}
BIBLIOTECA = "biblioteca"
POR_ARQUIVO = "balde: não medido (listagem do balde fora do ar); I6 e I7 só pelo catálogo"
HARNESS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_HEX = "0123456789abcdef"
TETO_LISTAGEM = 1000    # curadoria/lotes.py `listar_objetos_bucket(limite=1000)`, sem aviso de corte
FAIXAS_BALDE = [f"espelho/{c}" for c in _HEX] + [a + b for a in _HEX for b in _HEX]
_ESPELHO_NO_BALDE = re.compile(r"espelho/([0-9a-f]{64})/([0-9a-f]{64})/espelho\.md$")
_OBJETO_NO_BALDE = re.compile(r"^(?:acervo|pessoal)/[0-9a-f]{64}$")

# rag: as obras com o que os invariantes leem delas; as impressões servindo e em construção com o
# espelho (digest, veredito) e se um lote aberto as reclama; as aposentadas de obra viva (I13), com
# a obra, para o retrato atribuir. Agregado no Postgres: um json, nunca uma linha por vez no verbo.
SQL_COLETA_RAG = """
select json_build_object(
  'obras', (select coalesce(json_agg(json_build_object(
        'id', o.id::text, 'titulo', o.titulo, 'retirada', o.retirada_em is not null,
        'tem_autoria', (o.retirada_motivo is not null and o.retirada_por is not null),
        'marcacao', o.marcacao, 'objeto', o.objeto, 'objeto_id', o.objeto_id,
        'ficha_ok', (o.objeto_id is not null and exists (select 1 from acervo.ficha_arquivo f
                      where f.sha256 = o.objeto_id and f.erro_leitura is null))) order by o.titulo),
        '[]'::json) from acervo.obra o),
  'impressoes', (select coalesce(json_agg(json_build_object(
        'id', i.id::text, 'obra', i.obra_id::text, 'estado', i.estado, 'metodo', i.metodo_digest,
        'espelho', i.espelho is not null, 'digest', i.espelho ->> 'digest',
        'regua', i.espelho -> 'veredito' ->> 'regua',
        'servivel', (i.espelho -> 'veredito' ->> 'servivel')::boolean,
        'imperfeita', (i.espelho -> 'veredito' ->> 'imperfeita')::boolean,
        'reclamada', exists (select 1 from acervo.lote_reextracao_obra l
                               join acervo.lote_reextracao r on r.id = l.lote_id
                              where l.impressao_id = i.id and r.estado = 'aplicando'))), '[]'::json)
        from acervo.impressao i where i.estado in ('servindo', 'em_construcao')),
  'aposentadas', (select coalesce(json_agg(json_build_object('id', i.id::text, 'obra', i.obra_id::text)),
        '[]'::json) from acervo.impressao i join acervo.obra o on o.id = i.obra_id
        where i.estado = 'aposentada' and o.retirada_em is null),
  'total', (select count(*) from acervo.obra))
"""

# rag: por impressão servindo, os trechos elegíveis e o resumo dos ids (a mesma conta do motor, lado a
# lado, para o I4 ver o alvo que não existe). Agregado: cada impressão devolve uma linha.
SQL_COLETA_TRECHOS = """
select coalesce(json_agg(json_build_object('imp', x.imp, 'n', x.n, 'h', x.h)), '[]'::json)
  from (select i.id::text as imp, count(t.id) filter (where t.elegivel) as n,
               md5(coalesce(string_agg(t.id::text, ',' order by t.id::text) filter (where t.elegivel), '')) as h
          from acervo.impressao i left join acervo.trecho t on t.impressao_id = i.id
         where i.estado = 'servindo' group by i.id) x
"""

# motor: as gerações vivas; os índices em construção e servindo com a contagem e o resumo dos alvos
# (agregado por índice, arq:0045 Morada: nunca vetor a vetor); as facetas cujo vetor aponta para
# outra impressão que a do índice (I4).
SQL_COLETA_MOTOR = """
select json_build_object(
  'geracoes', (select coalesce(json_agg(json_build_object('id', g.id::text, 'particao', g.particao::text,
        'estado', g.estado::text, 'numero', g.numero, 'embedder', g.parametros ->> 'embedder',
        'dimensao_trecho', g.parametros ->> 'dimensao_trecho', 'dimensao_faceta', g.parametros ->> 'dimensao_faceta')),
        '[]'::json) from motor.geracao g where g.estado::text <> 'expurgada'),
  'indices', (select coalesce(json_agg(json_build_object('id', x.id, 'imp', x.imp, 'obra', x.obra,
        'estado', x.estado, 'gran', x.gran, 'part', x.part, 'geracao_servindo', x.gserv, 'n', x.n, 'h', x.h)),
        '[]'::json)
        from (select i.id::text as id, coalesce(i.impressao_id, i.alvo_impressao_id)::text as imp,
                     i.obra_id::text as obra, i.estado, i.granularidade as gran, i.particao::text as part,
                     (g.estado::text = 'servindo') as gserv, count(v.alvo_id) as n,
                     md5(coalesce(string_agg(v.alvo_id::text, ',' order by v.alvo_id::text), '')) as h
                from motor.indice i join motor.geracao g on g.id = i.geracao_id
                left join motor.vetor v on v.indice_id = i.id and v.geracao_id = i.geracao_id
               where i.estado in ('em_construcao', 'servindo')
               group by i.id, g.estado) x),
  'faceta_alvo_errado', (select coalesce(json_agg(i.id::text), '[]'::json) from motor.indice i
        where i.granularidade = 'impressao' and exists (select 1 from motor.vetor v
              where v.indice_id = i.id and v.geracao_id = i.geracao_id
                and v.alvo_id <> coalesce(i.impressao_id, i.alvo_impressao_id))))
"""

# rag: o último retrato guardado da base, com as chaves violadas de cada invariante (o gate compara)
SQL_ULTIMO_RETRATO = """
select (select json_build_object('id', r.id::text, 'total', r.total,
               'tirado_em', to_char(r.tirado_em at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
               'invariantes', r.rodape -> 'invariantes')
          from acervo.retrato r where r.base = 'biblioteca' order by r.tirado_em desc limit 1)
"""


def listagem_do_balde(colecao, prefixo):
    """Os itens que `GET /acervo/baldes/<coleção>/objetos?prefixo=` devolve, pelo adaptador REST do motor."""
    if HARNESS not in sys.path:
        sys.path.insert(0, HARNESS)
    from recuperacao.adaptadores import motor_acervo_rest
    from recuperacao.adaptadores.base import FonteIndisponivel
    try:
        return motor_acervo_rest.baldes_objetos(colecao, prefixo).get("itens") or []
    except FonteIndisponivel as e:
        raise Indeterminavel(f"balde {colecao}: {e}") from None


def _itens_da_colecao(listagem, colecao):
    """Todos os itens da coleção. A rota corta em 1000 e responde `proximo: null` mesmo cortada: a listagem
    inteira só vale abaixo do teto; no teto ou acima, lista-se por faixa de prefixo (os espelhos por
    `espelho/<hex>`, os objetos pelos dois primeiros dígitos do sha), e faixa que chega ao teto é
    Indeterminavel: balde cortado acusaria falta que não há."""
    inteiro = listagem(colecao, None)
    if len(inteiro) < TETO_LISTAGEM:
        return inteiro
    itens = []
    for faixa in FAIXAS_BALDE:
        parte = listagem(colecao, faixa)
        if len(parte) >= TETO_LISTAGEM:
            raise Indeterminavel(f"balde {colecao}: a faixa {faixa!r} chegou a {len(parte)} itens, o teto da "
                                 f"rota ({TETO_LISTAGEM}); a listagem pode estar cortada")
        itens += parte
    return itens


def listar_balde(listagem=None):
    """O que o balde guarda nas duas coleções: os espelhos (objeto_id, digest) com espelho.md e as chaves
    dos objetos originais. `listagem(coleção, prefixo)` é a porta, trocável no teste."""
    listagem = listagem or listagem_do_balde
    espelhos, objetos = set(), set()
    for colecao in ("firma", "pessoal"):
        for item in _itens_da_colecao(listagem, colecao):
            chave = item.get("objeto") or ""
            m = _ESPELHO_NO_BALDE.search(chave)
            if m:
                espelhos.add((m.group(1), m.group(2)))
            elif _OBJETO_NO_BALDE.match(chave):
                objetos.add(chave)
    return {"espelhos": espelhos, "objetos": objetos}


def coletar(ler=psql_json, balde=None, orfaos=None, regua_raiz=None):
    """Os dados que os invariantes leem, dos dois bancos e do balde. Banco fora levanta
    Indeterminavel; o balde e a régua que não respondem entram como None (I6, I7, I9 e a face dos
    espelhos do I13 saem «não medido», sem derrubar os outros)."""
    rag = ler("rag", SQL_COLETA_RAG) or {}
    motor = ler("motor", SQL_COLETA_MOTOR) or {}
    trechos = {x["imp"]: x for x in (ler("rag", SQL_COLETA_TRECHOS) or [])}
    try:
        versao = regua_servida(regua_raiz)[0]
    except Indeterminavel:
        versao = None
    try:
        bal = (balde or listar_balde)()
    except Indeterminavel:
        bal = None
    try:
        n_espelhos = (orfaos or espelhos_orfaos)()
    except Indeterminavel:
        n_espelhos = None
    d = {
        "obras": rag.get("obras") or [], "impressoes": rag.get("impressoes") or [],
        "aposentadas": rag.get("aposentadas") or [], "total": rag.get("total"),
        "trechos": trechos, "motor": motor,
        "i13": ler("rag", SQL_I13_RAG) or {}, "i13_motor": ler("motor", SQL_I13_MOTOR) or [],
        "versao": versao, "balde": bal, "espelhos_orfaos": n_espelhos,
    }
    return completar(d)


def completar(d):
    """Acrescenta a `d` os mapas que atribuem uma chave a uma obra (impressão → obra, índice → obra)."""
    d["imp_obra"] = {i["id"]: i["obra"] for i in d["impressoes"] + d["aposentadas"]}
    d["indice_obra"] = {x["id"]: x.get("obra") for x in (d["motor"].get("indices") or [])}
    return d


def _vivas(d):
    return [o for o in d["obras"] if not o["retirada"]]


def _servindo_por_obra(d):
    por = {}
    for i in d["impressoes"]:
        if i["estado"] == "servindo":
            por.setdefault(i["obra"], []).append(i)
    return por


def _indices(d, estado="servindo", gran=None):
    """Os índices da biblioteca no estado dado (a casa e o log têm a máquina deles)."""
    return [x for x in (d["motor"].get("indices") or [])
            if x["part"] == BIBLIOTECA and x["estado"] == estado and (gran is None or x["gran"] == gran)]


def i1(d):
    """Obra viva exposta em texto ou trecho ⇒ exatamente uma impressão servindo."""
    por = _servindo_por_obra(d)
    return [f"obra:{o['id']}" for o in _vivas(d)
            if EXPOSICAO.get(o["marcacao"]) in ("texto", "trecho") and len(por.get(o["id"], [])) != 1]


def i2(d):
    """Impressão servindo de obra exposta em trecho ⇒ todo trecho elegível tem vetor no índice de trecho
    servindo da geração servindo."""
    por = _servindo_por_obra(d)
    indice = {x["imp"]: x for x in _indices(d, gran="trecho")}
    out = []
    for o in _vivas(d):
        if EXPOSICAO.get(o["marcacao"]) != "trecho":
            continue
        for imp in por.get(o["id"], []):
            ix, elegiveis = indice.get(imp["id"]), (d["trechos"].get(imp["id"]) or {}).get("n", 0)
            if ix is None or not ix["geracao_servindo"] or ix["n"] != elegiveis:
                out.append(f"obra:{o['id']}")
                break
    return out


def i3(d):
    """Obra retirada ⇒ nenhuma impressão e nenhum índice servindo."""
    retiradas = {o["id"] for o in d["obras"] if o["retirada"]}
    por = _servindo_por_obra(d)
    chaves = {f"obra:{o}" for o in retiradas if por.get(o)}
    chaves |= {f"obra:{x['obra']}" for x in _indices(d) if x["obra"] in retiradas}
    return sorted(chaves)


def i4(d):
    """Vetor ⇒ índice existente (a chave estrangeira garante) e alvo existente: o índice de trecho
    que tem a contagem certa mas os alvos errados, e a faceta cujo vetor aponta para outra impressão."""
    out = set()
    for ix in _indices(d, gran="trecho"):
        tr = d["trechos"].get(ix["imp"])
        if tr and ix["n"] == tr["n"] and ix["h"] != tr["h"]:
            out.add(f"indice:{ix['id']}")
    out |= {f"indice:{i}" for i in d["motor"].get("faceta_alvo_errado") or []}
    return sorted(out)


def i5(d):
    """Índice servindo ⇒ a impressão dele está servindo."""
    servindo = {i["id"] for i in d["impressoes"] if i["estado"] == "servindo"}
    return sorted(f"indice:{x['id']}" for x in _indices(d) if x["imp"] not in servindo)


def i6(d):
    """Impressão servindo ⇒ espelho declarado e presente no balde. Sem a listagem do balde, só o
    lado do catálogo."""
    bal = d["balde"]
    objeto = {o["id"]: o.get("objeto_id") for o in d["obras"]}
    out = []
    for i in d["impressoes"]:
        if i["estado"] != "servindo":
            continue
        if not i["espelho"] or (bal is not None and (objeto.get(i["obra"]), i["digest"]) not in bal["espelhos"]):
            out.append(f"impressao:{i['id']}")
    return sorted(out)


def i7(d):
    """Obra com objeto ⇒ ficha com o sha do objeto, sem erro de leitura, e o objeto no balde."""
    bal = d["balde"]
    return [f"obra:{o['id']}" for o in d["obras"]
            if o["objeto"] and (not o["ficha_ok"] or (bal is not None and o["objeto"] not in bal["objetos"]))]


def i8(d):
    """A partição tem exatamente uma geração servindo e nenhum índice servindo fora dela."""
    geracoes = d["motor"].get("geracoes") or []
    servindo = {}
    for g in geracoes:
        servindo.setdefault(g["particao"], 0)
        servindo[g["particao"]] += g["estado"] == "servindo"
    out = [f"geracao:{p}" for p, n in sorted(servindo.items()) if n != 1]
    out += [f"indice:{x['id']}" for x in (d["motor"].get("indices") or [])
            if x["estado"] == "servindo" and not x["geracao_servindo"]]
    return out


def i9(d):
    """Impressão servindo com espelho ⇒ veredito da régua vigente (o predicado 9 da spec espelho-de-leitura)."""
    if d["versao"] is None:
        return None
    out = []
    for i in d["impressoes"]:
        if i["estado"] != "servindo" or not i["espelho"]:
            continue
        try:
            velha = i["regua"] in (None, "") or int(i["regua"]) < d["versao"]
        except (TypeError, ValueError):
            velha = True
        if velha:
            out.append(f"impressao:{i['id']}")
    return sorted(out)


def i10(d):
    """Obra retirada ⇒ motivo, autor e data."""
    return [f"obra:{o['id']}" for o in d["obras"] if o["retirada"] and not o["tem_autoria"]]


def i11(d):
    """Sobra: exposição arquivo ⇒ nenhuma impressão servindo; exposição texto ⇒ nenhum índice servindo."""
    por = _servindo_por_obra(d)
    texto = {o["id"] for o in _vivas(d) if EXPOSICAO.get(o["marcacao"]) == "texto"}
    chaves = {f"obra:{o['id']}" for o in _vivas(d)
              if EXPOSICAO.get(o["marcacao"]) == "arquivo" and por.get(o["id"])}
    chaves |= {f"obra:{x['obra']}" for x in _indices(d) if x["obra"] in texto}
    return sorted(chaves)


def i12(d):
    """Impressão, índice ou geração em construção ⇒ lote aberto que a reclame. O lote de indexação vive
    na memória da rag-api e não se consulta daqui: todo índice em construção entra como não reclamado."""
    out = [f"impressao:{i['id']}" for i in d["impressoes"]
           if i["estado"] == "em_construcao" and not i["reclamada"]]
    out += [f"indice:{x['id']}" for x in _indices(d, estado="em_construcao")]
    out += [f"geracao:{g['id']}" for g in d["motor"].get("geracoes") or [] if g["estado"] == "em_construcao"]
    return sorted(out)


def i13(d):
    """Nenhum derivado anterior depois da promoção: aposentada em obra ou casa viva, índice de impressão
    que não existe mais e espelho no balde sem impressão que o reclame. Mede-se depois do lote."""
    if d["espelhos_orfaos"] is None:
        return None
    existentes = set(d["i13"].get("existentes") or [])
    out = [f"impressao:{a['id']}" for a in d["aposentadas"]]
    out += [f"casa_impressao:{x}" for x in d["i13"].get("casa") or []]
    out += [f"indice-orfao:{x}" for x in sorted(set(d["i13_motor"] or [])) if x and x not in existentes]
    out += [f"espelho-orfao:{n}" for n in range(d["espelhos_orfaos"])]
    return out


FUNCOES = {"I1": i1, "I2": i2, "I3": i3, "I4": i4, "I5": i5, "I6": i6, "I7": i7, "I8": i8, "I9": i9,
           "I10": i10, "I11": i11, "I12": i12, "I13": i13}


def avaliar_invariantes(d):
    """{código: [chaves que violam] | None (não medido)} dos treze, nesta ordem."""
    return {codigo: FUNCOES[codigo](d) for codigo in INVARIANTES}


def obra_da_chave(chave, d):
    """A obra a que a chave pertence, ou None (geração, espelho órfão, índice sem obra)."""
    tipo, _, ident = chave.partition(":")
    if tipo == "obra":
        return ident
    if tipo == "impressao":
        return d["imp_obra"].get(ident)
    if tipo in ("indice", "indice-orfao"):
        return d["indice_obra"].get(ident)
    return None


def resumo(atual, d):
    """{código: {nome, classe, n, obras, chaves}} — a contagem e as obras de cada invariante (n None =
    não medido)."""
    saida = {}
    for codigo, (nome, classe) in INVARIANTES.items():
        chaves = atual.get(codigo)
        obras = None if chaves is None else sorted({o for o in (obra_da_chave(c, d) for c in chaves) if o})
        saida[codigo] = {"nome": nome, "classe": classe, "n": None if chaves is None else len(chaves),
                         "obras": obras, "chaves": chaves}
    return saida


def contra_o_retrato(atual, anterior):
    """(novas, herdadas) por código bloqueante, contra as chaves que o último retrato guardou: nova é
    a chave que ele não tinha; herdada é a que já tinha e segue. Invariante que o retrato não mediu
    (n nulo) não herda nada: o que a medida de agora acusa é novo."""
    novas, herdadas = {}, {}
    for codigo, (_, classe) in INVARIANTES.items():
        chaves = atual.get(codigo)
        if classe != "bloqueante" or chaves is None:
            continue
        antes = set(((anterior.get("invariantes") or {}).get(codigo) or {}).get("chaves") or [])
        novas[codigo] = sorted(set(chaves) - antes)
        herdadas[codigo] = sorted(set(chaves) & antes)
    return novas, herdadas


def _linha_invariante(codigo, r):
    cabeca = f"{codigo} {r['nome']} [{r['classe']}]"
    if r["n"] is None:
        return f"{cabeca}: não medido"
    if not r["n"]:
        return f"{cabeca}: 0"
    obras = r["obras"] or []
    return f"{cabeca}: {r['n']}" + (f" — obras {_lista(obras)}" if obras else "")


def _do_retrato(nome):
    """Os itens de hoje que o retrato guardado passa a governar: o 9 e o I13 são invariantes, e o 7
    (fidelidade) deixa de pesar no exit com retrato, porque o gate só barra violação bloqueante nova."""
    return nome.startswith(("§11 predicado 7", "§11 predicado 9", "I13"))


def aplicar_gate(itens, avisos, atual, anterior, d):
    """(itens, avisos, resumo): os itens de `medir` com os invariantes por cima.

    Sem retrato guardado, o exit segue nos predicados de hoje (arq:0121, Consequências) e os
    invariantes só informam, em avisos. Com retrato, o exit é o do gate: um item por invariante
    bloqueante, divergente só com violação nova (e a lista das obras que pioraram), e as herdadas
    vão ao relato sem travar; os de classe aviso informam."""
    res = resumo(atual, d)
    avisos = list(avisos)
    if anterior is None:
        avisos.append("sem retrato guardado: o exit segue nos predicados de hoje (arq:0121, Consequências); "
                      "`acervo listar biblioteca obra --situacao --retrato --guardar` guarda a linha de base")
        avisos += [_linha_invariante(c, res[c]) for c in INVARIANTES]
        return list(itens), avisos, res
    ficam = [(n, v) for n, v in itens if not _do_retrato(n)]
    avisos += [f"herdado — {n}: {v.motivo}" for n, v in itens if _do_retrato(n) and v.estado == "divergente"]
    novas, herdadas = contra_o_retrato(atual, anterior)
    avisos.append(f"gate contra o retrato de {anterior['tirado_em']} ({anterior['id'][:8]}): "
                  "só violação bloqueante nova barra")
    for codigo, (nome, classe) in INVARIANTES.items():
        r, rotulo = res[codigo], f"{codigo}: {nome}"
        if classe != "bloqueante":
            avisos.append(_linha_invariante(codigo, r))
            continue
        if r["n"] is None:
            ficam.append((rotulo, resultado.indeterminavel("não consegui medir (o balde ou o banco não respondeu)")))
            continue
        if novas[codigo]:
            obras = sorted({o for o in (obra_da_chave(c, d) for c in novas[codigo]) if o})
            onde = f"obras {_lista(obras)}" if obras else f"chaves {_lista(novas[codigo])}"
            ficam.append((rotulo, resultado.divergente(
                f"{len(novas[codigo])} violação(ões) nova(s) desde o retrato de {anterior['tirado_em']}: {onde}"
                + (f"; {len(herdadas[codigo])} herdada(s)" if herdadas[codigo] else ""))))
        else:
            ficam.append((rotulo, resultado.conforme()))
            if herdadas[codigo]:
                avisos.append(f"{codigo} herdada do retrato: {len(herdadas[codigo])} (não trava)")
    return ficam, avisos, res


# --- a classe ------------------------------------------------------------------------------

def medir(regua_raiz=None, ler=psql_json, orfaos_do_balde=None):
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
                                             (orfaos_do_balde or espelhos_orfaos)())))
    except Indeterminavel as e:
        itens.append((NOME_I13, resultado.indeterminavel(str(e))))
    return itens, avisos, pendencias


def ultimo_retrato(ler=psql_json):
    """O último retrato guardado da biblioteca ({id, tirado_em, total, invariantes}) ou None, se não há."""
    return ler("rag", SQL_ULTIMO_RETRATO)


def conferir_invariantes(itens, avisos, ler=psql_json, balde=None, orfaos=None, regua_raiz=None):
    """(itens, avisos, resumo) com os treze invariantes avaliados e o gate contra o último retrato.
    Banco fora: o item sai indeterminável e o exit 5 (não conseguir olhar não é conforme)."""
    try:
        d = coletar(ler, balde=balde, orfaos=orfaos, regua_raiz=regua_raiz)
        anterior = ultimo_retrato(ler)
    except Indeterminavel as e:
        return (list(itens) + [(NOME_INVARIANTES, resultado.indeterminavel(str(e)))], list(avisos), None)
    itens, avisos, res = aplicar_gate(itens, avisos, avaliar_invariantes(d), anterior, d)
    if d["balde"] is None:
        avisos.append(POR_ARQUIVO)
    return itens, avisos, res


def conferir_acervo(alvo, sha_release, como_json=False, ler=psql_json, balde=None, orfaos=None):
    itens, avisos, pendencias = medir()
    itens, avisos, res = conferir_invariantes(itens, avisos, ler, balde=balde, orfaos=orfaos)
    extra = {"avisos": avisos, "pendencias": pendencias}
    if res is not None:
        extra["invariantes"] = {c: {k: v for k, v in r.items() if k != "chaves"} for c, r in res.items()}
    return resultado.relatorio("acervo", alvo, itens, sha_release, como_json=como_json, extra=extra)
