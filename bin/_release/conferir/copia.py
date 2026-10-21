"""copia — `release conferir copia`: toda materialização viva tem declaração (card #3763).

arq:0022 §6.3 manda uma classe própria de `release conferir`, por substrato (balde, banco, índice), que confere que
toda materialização viva é cópia declarada. A declaração nomeia a fonte, a chave, os atributos copiados, o ato que repõe
a cópia, o modo (materializada ou sob demanda; §6.2) e, desde a arq:0130 D4, se a regeneração é reproduzível, com
método e insumos. Materialização sem declaração é fóssil (§6.5).

Onde a declaração mora (decisão do dono de 21/10/2026, comentário #3480): no schema, por COMMENT na tabela, onde a cópia é
tabela. Uma linha só, depois do comentário que a tabela já tinha, começando por `copia-de:` e com os campos separados
por « | » (migrações 131 do rag e 019 do motor; a spec entidade-raiz-da-casa guarda o formato):

    copia-de: familia=… | fonte=… | chave=<coluna> | atributos=a,b | repoe=… | modo=materializada|sob-demanda |
              reproduzivel=sim|nao | metodo=… | insumos=a,b | migracao=NNN

Três substratos, um coletor cada:

  banco   as tabelas do schema `acervo` do banco rag.
  indice  as tabelas do schema `motor` do banco do motor (os índices vetoriais, seus vetores e trechos).
  balde   os espelhos de leitura do balde (`espelho/<sha do arquivo>/<digest do método>/`). O espelho é o texto da
          família impressão: o endereço dele já carrega a chave da fonte e o método, e declarado é o que uma impressão
          reclama. O que nenhuma impressão reclama sai como não declarado (o mesmo critério e a mesma lista de
          `acervo apagar biblioteca espelho`, em plano seco). A ficha do espelho com a ligação copia-de espera a ficha do
          arquivo da obra (comentário #3488 do #3763).

Partição de tabela particionada não conta: a declaração fica na tabela-mãe. Visão não conta: não guarda nada.
Tabela que o catálogo da raiz nomeia como substrato golden (`acervo.entidade_classe.substrato_golden`) é fonte, não cópia,
e sai à parte. O que não é uma coisa nem outra sai como não declarado, com o prefixo de fóssil assinalado (_backup_,
_mig_, _fusao_, _osint). Nada se expurga aqui: o expurgo é ato próprio, reversível, e a remoção definitiva vai ao dono.

Fora da classe, e contado na primeira linha como «sem coletor»: o modelo formal gerado, a unit gerada pelo bot, o
CLAUDE.md da fita, as instruções de Project e as preferências do claude.ai, e a projeção de card.

Exit: 0 tudo declarado · 1 há materialização sem declaração ou declaração com defeito · 2 uso · 5 substrato que não se
conseguiu olhar. Só olha: nenhuma escrita.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import predicados_acervo as pa
import resultado

Indeterminavel = pa.Indeterminavel

SUBSTRATOS = ("balde", "banco", "indice")

# substrato → (banco do `psql_json`, schema que o coletor percorre)
ONDE = {"banco": ("rag", "acervo"), "indice": ("motor", "motor")}
NOMES = {"banco": "banco: tabelas do schema acervo (rag)", "indice": "indice: tabelas do schema motor",
         "balde": "balde: espelhos de leitura"}

PREFIXO = "copia-de:"
SEPARADOR = " | "
CAMPOS = ("familia", "fonte", "chave", "atributos", "repoe", "modo", "reproduzivel", "metodo", "insumos", "migracao")
SO_SE_REPRODUZIVEL = ("metodo", "insumos")
MODOS = ("materializada", "sob-demanda")
SIM_NAO = ("sim", "nao")
PREFIXOS_DE_FOSSIL = ("_backup_", "_mig_", "_fusao_", "_osint")
MOSTRAR = 5

# o espelho é o texto da família impressão (arq:0117 §1.4): declarada a família com `texto`, o espelho é declarado
FAMILIA_DO_ESPELHO = ("impressao", "texto")

SEM_COLETOR = (
    ("modelo formal gerado", "arquivo versionado que o gerador emite das shapes; o conferir não lê o repositório"),
    ("unit gerada pelo bot", "mora no host, como ficha do serviço na forma host; fora dos três substratos"),
    ("CLAUDE.md da fita", "arquivo da pasta de trabalho, reposto por bin/chat; fora dos três substratos"),
    ("instruções de Project e preferências do claude.ai",
     "cópias da persona e da conduta em superfície de terceiro; fora dos três substratos"),
    ("projeção de card", "mora no rastreador, que o conferir não lê; falta o ato que a refaz (carta ao produto)"),
)

_ESPELHO_DIR = re.compile(r"espelho/([0-9a-f]{64})/([0-9a-f]{64})/(?:espelho\.md|mapa\.json)$")
_SOB_ESPELHO = re.compile(r"(?:^|/)espelho/")
_NOME_NO_GOLDEN = re.compile(r"\b([a-z_]+)\.([a-z_][a-z0-9_]*)")

SQL_TABELAS = """
select coalesce(json_agg(json_build_object(
         'schema', n.nspname, 'tabela', c.relname,
         'comentario', obj_description(c.oid, 'pg_class'),
         'colunas', (select coalesce(json_agg(a.attname order by a.attnum), '[]'::json)
                       from pg_attribute a
                      where a.attrelid = c.oid and a.attnum > 0 and not a.attisdropped))
       order by c.relname), '[]'::json)
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = '{schema}' and c.relkind in ('r', 'p', 'm') and not c.relispartition
"""

# o que o catálogo da raiz diz ser substrato golden: texto livre que cita tabelas (`acervo.obra`, `motor.indice`…)
SQL_GOLDEN = """
select coalesce(json_agg(substrato_golden), '[]'::json)
  from acervo.entidade_classe where substrato_golden is not null
"""


@dataclass
class Portas:
    """O que a classe lê de fora, trocável no teste: `ler(banco, sql)`, `listagem(coleção, prefixo)` do balde e
    `plano()` dos espelhos órfãos. Sem `listagem` e sem `plano`, valem os de produção."""

    ler: Callable[[str, str], Any] = pa.psql_json
    listagem: Callable[[str, str | None], list] | None = None
    plano: Callable[[], list[str]] | None = None


@dataclass
class Medida:
    itens: list[tuple[str, resultado.Veredito]] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
    contagem: dict[str, int] = field(default_factory=lambda: {"total": 0, "declaradas": 0, "nao_declaradas": 0,
                                                              "fontes": 0})
    detalhe: dict[str, Any] = field(default_factory=dict)
    familias: dict[str, set[str | None]] = field(default_factory=dict)


# --- a declaração ----------------------------------------------------------------------------

def linha_de_declaracao(comentario: str | None) -> str | None:
    """A linha `copia-de: …` do COMMENT da tabela, ou None."""
    for linha in (comentario or "").splitlines():
        if linha.startswith(PREFIXO):
            return linha
    return None


def ler_declaracao(linha: str) -> tuple[dict[str, str], list[str]]:
    """({campo: valor}, defeitos de forma) da linha de declaração. Campo sem `=`, repetido ou desconhecido é defeito."""
    campos: dict[str, str] = {}
    defeitos: list[str] = []
    for parte in linha[len(PREFIXO):].strip().split(SEPARADOR):
        nome, igual, valor = parte.partition("=")
        nome, valor = nome.strip(), valor.strip()
        if not igual or not nome:
            defeitos.append(f"campo mal formado ({parte.strip()[:40]!r})")
        elif nome not in CAMPOS:
            defeitos.append(f"campo desconhecido ({nome})")
        elif nome in campos:
            defeitos.append(f"campo repetido ({nome})")
        else:
            campos[nome] = valor
    return campos, defeitos


def lista_do_campo(valor: str | None) -> list[str]:
    return [x.strip() for x in (valor or "").split(",") if x.strip()]


def defeitos_da_declaracao(decl: dict[str, str], colunas: list[str] | None) -> list[str]:
    """O que falta ou está fora da forma numa declaração lida. Declaração sem defeito devolve lista vazia."""
    out = []
    reproduzivel = decl.get("reproduzivel")
    for campo in CAMPOS:
        if campo in SO_SE_REPRODUZIVEL and reproduzivel != "sim":
            continue
        if not decl.get(campo):
            out.append(f"sem {campo}")
    if decl.get("modo") and decl["modo"] not in MODOS:
        out.append(f"modo fora da lista ({decl['modo']})")
    if reproduzivel and reproduzivel not in SIM_NAO:
        out.append(f"reproduzivel fora da lista ({reproduzivel})")
    chave = decl.get("chave")
    if chave and colunas is not None and chave not in colunas:
        out.append(f"a coluna da chave ({chave}) não existe na tabela")
    return out


def _lista(nomes: list[str]) -> str:
    mostra = ", ".join(nomes[:MOSTRAR])
    return mostra + (f" +{len(nomes) - MOSTRAR}" if len(nomes) > MOSTRAR else "")


def _eh_fossil(nome: str) -> bool:
    return nome.split(".", 1)[-1].startswith(PREFIXOS_DE_FOSSIL)


# --- banco e índice: as tabelas ----------------------------------------------------------------

def golden_nomeado(textos: list[str] | None) -> set[str]:
    """Os `schema.tabela` que o catálogo cita nos substratos golden."""
    nomeados: set[str] = set()
    for texto in textos or []:
        for m in _NOME_NO_GOLDEN.finditer(texto or ""):
            nomeados.add(f"{m.group(1)}.{m.group(2)}")
    return nomeados


def classificar(tabelas: list[dict[str, Any]], golden: set[str]) -> dict[str, Any]:
    """Cada tabela em declarada, com defeito, fonte nomeada no catálogo ou não declarada."""
    declaradas, defeituosas, fontes, nao, conflitos = [], [], [], [], []
    for t in tabelas:
        nome = f"{t['schema']}.{t['tabela']}"
        linha = linha_de_declaracao(t.get("comentario"))
        if linha is None:
            (fontes if nome in golden else nao).append(nome)
            continue
        decl, forma = ler_declaracao(linha)
        falhas = forma + defeitos_da_declaracao(decl, t.get("colunas"))
        if falhas:
            defeituosas.append((nome, falhas))
            continue
        declaradas.append((nome, decl))
        if nome in golden:
            conflitos.append(nome)
    return {"declaradas": declaradas, "defeituosas": defeituosas, "fontes": fontes, "nao": nao,
            "conflitos": conflitos}


def _veredito_das_tabelas(c: dict[str, Any]) -> resultado.Veredito:
    partes = []
    if c["defeituosas"]:
        casos = [f"{n} ({'; '.join(f)})" for n, f in c["defeituosas"]]
        partes.append(f"{len(casos)} declaração(ões) com defeito: {_lista(casos)}")
    if c["nao"]:
        fosseis = [n for n in c["nao"] if _eh_fossil(n)]
        partes.append(f"{len(c['nao'])} sem declaração: {_lista(c['nao'])}"
                      + (f" — {len(fosseis)} com prefixo de fóssil" if fosseis else ""))
    if not partes:
        return resultado.conforme()
    return resultado.divergente(" · ".join(partes) + " — cura: a cadeira dona declara a tabela (COMMENT `copia-de:`) "
                                "ou o catálogo a nomeia como fonte; expurgo é ato próprio, com a lista ao dono")


def _classificar_substrato(ler: Callable[[str, str], Any], substrato: str, golden: set[str] | None,
                           golden_erro: str | None) -> dict[str, Any]:
    """A classificação das tabelas do substrato, ou {"erro": …} se o banco ou o catálogo não responderam."""
    try:
        if golden is None:
            raise Indeterminavel(golden_erro or "catálogo da raiz sem leitura")
        banco, schema = ONDE[substrato]
        return classificar(ler(banco, SQL_TABELAS.format(schema=schema)) or [], golden)
    except Indeterminavel as e:
        return {"erro": str(e)}


def _relatar_tabelas(m: Medida, substrato: str, c: dict[str, Any]) -> None:
    if "erro" in c:
        m.itens.append((NOMES[substrato], resultado.indeterminavel(c["erro"])))
        return
    m.itens.append((NOMES[substrato], _veredito_das_tabelas(c)))
    nao = len(c["nao"]) + len(c["defeituosas"])
    m.contagem["total"] += len(c["declaradas"]) + nao
    m.contagem["declaradas"] += len(c["declaradas"])
    m.contagem["nao_declaradas"] += nao
    m.contagem["fontes"] += len(c["fontes"])
    m.detalhe[substrato] = {
        "declaradas": [n for n, _ in c["declaradas"]], "nao_declaradas": c["nao"],
        "com_defeito": [{"tabela": n, "defeitos": f} for n, f in c["defeituosas"]], "fontes": c["fontes"]}
    m.avisos.append(f"{substrato}: {len(c['declaradas'])} declarada(s) · {len(c['fontes'])} fonte(s) nomeada(s) no "
                    f"catálogo · {nao} sem declaração válida")
    for nome, decl in c["declaradas"]:
        m.avisos.append(_linha_declarada(nome, decl))
        m.familias.setdefault(decl.get("familia", "?"), set()).add(decl.get("reproduzivel"))
    m.avisos += [f"conflito: o catálogo nomeia {n} como substrato golden e a tabela está declarada como cópia "
                 "(as duas leituras não fecham, #3057)" for n in c["conflitos"]]


def _linha_declarada(nome: str, decl: dict[str, str]) -> str:
    repro = "reproduzível" if decl.get("reproduzivel") == "sim" else "NÃO reproduzível"
    return f"declarada: {nome} — família {decl.get('familia')}, modo {decl.get('modo')}, {repro} (chave {decl.get('chave')})"


# --- balde: os espelhos ----------------------------------------------------------------------------

def inventario_do_balde(listagem: Callable[[str, str | None], list] | None = None) -> dict[str, Any]:
    """O que o balde guarda: os espelhos com o endereço que carrega a chave (sha do arquivo e digest do método), o que
    está sob `espelho/` sem essa forma, e quantos objetos originais há. `listagem(coleção, prefixo)` é a porta."""
    listagem = listagem or pa.listagem_do_balde
    espelhos: set[tuple[str, str]] = set()
    sem_chave: list[str] = []
    originais = 0
    for colecao in ("firma", "pessoal"):
        for item in pa._itens_da_colecao(listagem, colecao):
            chave = item.get("objeto") or ""
            achou = _ESPELHO_DIR.search(chave)
            if achou:
                espelhos.add((achou.group(1), achou.group(2)))
            elif _SOB_ESPELHO.search(chave):
                sem_chave.append(chave)
            elif pa._OBJETO_NO_BALDE.match(chave):
                originais += 1
    return {"espelhos": espelhos, "sem_chave": sorted(set(sem_chave)), "originais": originais}


def plano_de_orfaos(bin_acervo: str = pa.ACERVO_BIN) -> list[str]:
    """Os espelhos que nenhuma impressão reclama, na forma `<sha do arquivo>/<digest>`: o plano seco de
    `acervo apagar biblioteca espelho --json`, o mesmo critério que apaga. Falha é Indeterminavel."""
    comando = [bin_acervo, "apagar", "biblioteca", "espelho", "--json"]
    try:
        saida = subprocess.run(comando, capture_output=True, text=True, timeout=300, check=False)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Indeterminavel(f"balde: {e}") from None
    if saida.returncode != 0:
        msg = (saida.stderr or saida.stdout or f"saiu {saida.returncode}").strip().splitlines()
        raise Indeterminavel(f"balde: {msg[0] if msg else saida.returncode}")
    try:
        plano = json.loads(saida.stdout)
    except ValueError:
        raise Indeterminavel(f"balde: resposta que não é json: {saida.stdout[:80]!r}") from None
    if not isinstance(plano, dict) or "n" not in plano:
        raise Indeterminavel("balde: o plano seco veio sem a contagem (n)")
    listados = [f"{it.get('hex')}/{it.get('digest')}" for it in plano.get("itens") or []]
    # o plano pode contar mais do que lista; o que sobra entra como endereço desconhecido, nunca some
    return listados + [f"(endereço não listado #{i + 1})" for i in range(max(0, int(plano["n"]) - len(listados)))]


def familia_declara_o_espelho(declaradas: list[tuple[str, dict[str, str]]]) -> bool:
    familia, atributo = FAMILIA_DO_ESPELHO
    return any(d.get("familia") == familia and atributo in lista_do_campo(d.get("atributos")) for _, d in declaradas)


def coletar_balde(portas: Portas, declaradas_do_banco: list[tuple[str, dict[str, str]]]) -> dict[str, Any]:
    inv = inventario_do_balde(portas.listagem)
    orfaos = (portas.plano or plano_de_orfaos)()
    familia_ok = familia_declara_o_espelho(declaradas_do_banco)
    total = len(inv["espelhos"])
    return {"total": total, "orfaos": orfaos, "sem_chave": inv["sem_chave"], "originais": inv["originais"],
            "familia_declarada": familia_ok, "declarados": (max(0, total - len(orfaos)) if familia_ok else 0)}


def _veredito_do_balde(b: dict[str, Any]) -> resultado.Veredito:
    partes = []
    if not b["familia_declarada"]:
        familia, atributo = FAMILIA_DO_ESPELHO
        partes.append(f"nenhuma tabela do rag declara a família {familia} com o atributo {atributo}: "
                      f"os {b['total']} espelho(s) ficam sem declaração")
    if b["orfaos"]:
        partes.append(f"{len(b['orfaos'])} espelho(s) que nenhuma impressão reclama: {_lista(b['orfaos'])}")
    if b["sem_chave"]:
        partes.append(f"{len(b['sem_chave'])} objeto(s) sob espelho/ sem o sha do arquivo e o digest no endereço: "
                      f"{_lista(b['sem_chave'])}")
    if not partes:
        return resultado.conforme()
    return resultado.divergente(" · ".join(partes) + " — cura: `acervo apagar biblioteca espelho` (plano seco, sem volta, "
                                "vai ao dono antes do --apply); expurgo não é desta classe")


def _relatar_balde(m: Medida, portas: Portas, banco: dict[str, Any]) -> None:
    try:
        if "erro" in banco:
            raise Indeterminavel(f"a declaração da família está no rag: {banco['erro']}")
        b = coletar_balde(portas, banco["declaradas"])
    except Indeterminavel as e:
        m.itens.append((NOMES["balde"], resultado.indeterminavel(str(e))))
        return
    m.itens.append((NOMES["balde"], _veredito_do_balde(b)))
    sem_declaracao = (b["total"] - b["declarados"]) + len(b["sem_chave"])
    m.contagem["total"] += b["total"] + len(b["sem_chave"])
    m.contagem["declaradas"] += b["declarados"]
    m.contagem["nao_declaradas"] += sem_declaracao
    m.detalhe["balde"] = {"espelhos": b["total"], "declarados": b["declarados"], "orfaos": b["orfaos"],
                          "sem_chave": b["sem_chave"], "objetos_originais": b["originais"]}
    m.avisos.append(f"balde: {b['total']} espelho(s), {b['declarados']} declarado(s) pela família "
                    f"{FAMILIA_DO_ESPELHO[0]}, {len(b['orfaos'])} sem impressão que reclame; "
                    f"{b['originais']} objeto(s) original(is) são o arquivo da obra (fonte, não cópia)")


# --- a classe ----------------------------------------------------------------------------------------

def medir(alvo: str | None, portas: Portas) -> Medida:
    """Os itens, os avisos e a contagem. Banco, índice e balde, na ordem, ou só o do alvo."""
    pedidos = [alvo] if alvo else list(SUBSTRATOS)
    m = Medida()

    # o balde também precisa do catálogo: a declaração da família do espelho está nas tabelas do rag
    golden, golden_erro = None, None
    try:
        golden = golden_nomeado(portas.ler("rag", SQL_GOLDEN))
    except Indeterminavel as e:
        golden_erro = f"catálogo da raiz não respondeu: {e}"

    classificado = {sub: _classificar_substrato(portas.ler, sub, golden, golden_erro)
                    for sub in ("banco", "indice") if sub in pedidos or (sub == "banco" and "balde" in pedidos)}
    for sub in ("banco", "indice"):
        if sub in pedidos:
            _relatar_tabelas(m, sub, classificado[sub])
    if "balde" in pedidos:
        _relatar_balde(m, portas, classificado["banco"])

    m.avisos.append(f"sem coletor ({len(SEM_COLETOR)}): " + "; ".join(f"{n} ({p})" for n, p in SEM_COLETOR))
    nao_repro = sorted(f for f, valores in m.familias.items() if "nao" in valores)
    m.avisos.append("famílias declaradas não reproduzíveis, que a régua de bootstrap trata como fonte (arq:0130 D4): "
                    + (", ".join(nao_repro) if nao_repro else "nenhuma"))
    m.contagem["sem_coletor"] = len(SEM_COLETOR)
    return m


def _ancora(alvo: str | None, itens: list[tuple[str, resultado.Veredito]], sha_release: str,
            cont: dict[str, int]) -> tuple[str, int]:
    base, exit_code = resultado.linha_ancora("copia", alvo, itens, sha_release)
    return (f"{base} · materializações: {cont['total']} · declaradas {cont['declaradas']} · "
            f"não declaradas {cont['nao_declaradas']} · sem coletor {cont['sem_coletor']}"), exit_code


def conferir_copia(alvo: str | None, sha_release: str, *, como_json: bool = False,
                   portas: Portas | None = None) -> int:
    if alvo is not None and alvo not in SUBSTRATOS:
        msg = f"substrato desconhecido: {alvo!r} (esperado: {', '.join(SUBSTRATOS)})"
        if como_json:
            print(json.dumps({"erro": msg}, ensure_ascii=False))
        else:
            print(msg, file=sys.stderr)
        return 2
    m = medir(alvo, portas or Portas())
    linha, exit_code = _ancora(alvo, m.itens, sha_release, m.contagem)
    if como_json:
        print(json.dumps({
            "ancora": linha, "classe": "copia", "alvo": alvo, "release": sha_release,
            "itens": [{"nome": n, **v.dict()} for n, v in m.itens],
            "contagem": m.contagem, "substratos": m.detalhe,
            "sem_coletor": [{"familia": n, "porque": p} for n, p in SEM_COLETOR],
            "avisos": m.avisos,
        }, ensure_ascii=False))
        return exit_code
    print(linha)
    for nome, v in m.itens:
        marca = {"conforme": "ok ", "divergente": "NAO", "indeterminavel": "?? "}[v.estado]
        print(f"    {marca} {nome}")
        if v.motivo:
            print(f"        {v.motivo}")
    for aviso in m.avisos:
        print(f"    --  {aviso}")
    return exit_code
