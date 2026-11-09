"""Admissão do cabeçalho e do SQL antes de abrir uma conexão."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from . import Falha, exigir, nome_seguro, relativo

TIPOS = {"texto", "inteiro", "real", "decimal", "booleano", "instante", "data", "uuid"}
METODOS = {"linear", "agrupamento-hierarquico"}


def carregar(pasta: Path, ato: str | None = None) -> dict:
    try:
        import yaml

        r = yaml.safe_load((pasta / "receita.yaml").read_text())
    except ImportError:
        raise Falha(3, "biblioteca-yaml-ausente") from None
    except (OSError, ValueError):
        raise Falha(2, "cabecalho-ausente-ou-invalido") from None
    exigir(isinstance(r, dict), "cabecalho-invalido")
    for chave in (
        "tipo",
        "pergunta",
        "populacao",
        "metodo",
        "saidas",
        "serializacao",
        "codigo",
        "pilha",
    ):
        exigir(r.get(chave), "campo-ausente:" + chave)
    exigir(r["tipo"] in {"preparacao", "analise"}, "tipo-invalido")
    if ato:
        exigir(
            r["tipo"] == {"preparar": "preparacao", "montar": "analise"}[ato],
            "tipo-trocado",
        )
    exigir(r["metodo"] in METODOS, "metodo-invalido")
    exigir(r.get("entrega", "todos") in {"todos", "privada"}, "entrega-invalida")
    exigir(
        isinstance(r["populacao"], dict) and r["populacao"].get("objeto"),
        "populacao-invalida",
    )
    if r["tipo"] == "preparacao":
        exigir(
            type(r["populacao"].get("n")) is int and r["populacao"]["n"] >= 0,
            "populacao-n-invalido",
        )
        for chave in ("tabelas_de_origem", "consultas", "corte"):
            exigir(r.get(chave), "campo-ausente:" + chave)
        registrados = bancos_registrados()
        declaradas = {}
        for t in r["tabelas_de_origem"]:
            exigir(
                re.fullmatch(r"[a-z_][a-z0-9_]*\.[a-z_][a-z0-9_]*", t["tabela"]),
                "origem-invalida",
            )
            # #4185: toda tabela mora num banco do registro; sem banco, é o do acervo.
            t.setdefault("banco", "rag")
            exigir(t["banco"] in registrados, "banco-fora-do-registro:" + str(t["banco"]))
            exigir(
                t.get("colunas")
                and all(re.fullmatch(r"[a-z_][a-z0-9_]*", c) for c in t["colunas"]),
                "colunas-invalidas",
            )
            exigir(origem_id(t) not in declaradas, "origem-duplicada")
            declaradas[origem_id(t)] = t
        r["corte"] = normalizar_corte(r["corte"], declaradas)
        exigir(set(r["corte"]) == set(declaradas), "corte-por-origem-ausente")
        for oid, corte in r["corte"].items():
            t = declaradas[oid]
            if corte.get("por") == "snapshot":
                # Tabela sem coluna de tempo: vale o snapshot da transação, sem recorte.
                corte.setdefault("garantia", "snapshot")
                corte.setdefault("margem_estimada", False)
                exigir(corte["garantia"] == "snapshot", "corte-invalido")
                continue
            if "." not in corte.get("coluna", ""):
                corte["coluna"] = t["tabela"] + "." + corte.get("coluna", "")
            exigir(
                set(("por", "coluna", "margem", "margem_estimada", "garantia"))
                <= corte.keys(),
                "corte-incompleto",
            )
            # A coluna do corte pode ser de outra tabela do mesmo banco (o giro se corta
            # pelo ts do log a que se liga), nunca de outro banco.
            todas = {
                o["tabela"] + "." + c
                for o in declaradas.values()
                if o["banco"] == t["banco"]
                for c in o["colunas"]
            }
            exigir(corte["coluna"] in todas, "coluna-corte-nao-declarada")
            exigir(
                corte["por"] in {"instante", "chave"}
                and corte["garantia"] in {"fechado", "detectavel"}
                and type(corte["margem_estimada"]) is bool,
                "corte-invalido",
            )
        nomes = set()
        for q in r["consultas"]:
            nome_seguro(q["nome"])
            exigir(q["nome"] not in nomes, "consulta-duplicada")
            nomes.add(q["nome"])
            sql = relativo(pasta, q["arquivo"]).read_text()
            q["banco"] = banco_da_consulta(q, sql, r)
            validar_sql(sql, r, q["banco"])
        if r["populacao"]["objeto"] == "turno":
            chave = r.get("chave_do_turno", {})
            exigir(
                chave.get("chave") == "ordem_id"
                or (chave.get("chave") and chave.get("equivalencia"))
                or (
                    isinstance(chave.get("reconstruido"), dict)
                    and chave["reconstruido"].get("metodo")
                    and chave["reconstruido"].get("chave")
                ),
                "chave-do-turno-ausente",
            )
            if chave.get("equivalencia"):
                exigir(
                    relativo(pasta, chave["equivalencia"]).is_file(),
                    "equivalencia-ausente",
                )
    else:
        exigir(
            r.get("base", {}).get("receitas") and r["base"].get("tabelas"),
            "base-aceita-ausente",
        )
        for t in r["base"]["tabelas"]:
            nome_seguro(t)
    saidas = r["saidas"]
    nomes = set()
    for t in saidas.get("tabelas", []):
        nome_seguro(t["nome"])
        exigir(t["nome"] not in nomes, "saida-duplicada")
        nomes.add(t["nome"])
        cols = t.get("colunas", [])
        exigir(
            cols and all(c.get("tipo") in TIPOS for c in cols), "tipo-coluna-invalido"
        )
        for c in cols:
            nome_seguro(c["nome"])
        exigir(len({c["nome"] for c in cols}) == len(cols), "coluna-duplicada")
        exigir(
            t.get("ordem") and set(t["ordem"]) <= {c["nome"] for c in cols},
            "ordem-total-ausente",
        )
    for p in saidas.get("projecoes", []):
        nome = p if isinstance(p, str) else p["nome"]
        nome_seguro(nome)
        exigir(nome not in nomes, "saida-duplicada")
        nomes.add(nome)
    exigir(nomes, "saidas-ausentes")
    ser = r["serializacao"]
    exigir(
        set(("datas", "nulo", "nan", "decimais")) <= ser.keys()
        and ser["datas"] == "utc"
        and ser["nulo"] != ser["nan"]
        and type(ser["decimais"]) is int
        and 0 <= ser["decimais"] <= 15,
        "serializacao-invalida",
    )
    guarda = r.get("guarda", {"dias": 7})
    exigir(
        isinstance(guarda, dict)
        and (
            (
                set(guarda) == {"dias"}
                and type(guarda["dias"]) is int
                and guarda["dias"] > 0
            )
            or (set(guarda) == {"ate_descarte"} and bool(guarda["ate_descarte"]))
        ),
        "guarda-invalida",
    )
    exigir(relativo(pasta, r["codigo"]).is_file(), "codigo-ausente")
    exigir(r["pilha"] == "uv.lock", "pilha-invalida")
    return r


# SQL deliberadamente restrito a SELECT simples. A fronteira não tenta reconhecer
# linguagem arbitrária com expressões regulares: recusa subconsultas, funções,
# operadores de escape, literais de identificador e comandos compostos.
_TOKEN = re.compile(
    r"\s+|--[^\n]*|/\*[\s\S]*?\*/|'(?:''|[^'])*'|:corte\b|[a-zA-Z_][a-zA-Z_0-9]*|[0-9]+|[.,;()<>=*+-]"
)
_PALAVRAS = set(
    [
        "select",
        "from",
        "join",
        "inner",
        "left",
        "right",
        "full",
        "outer",
        "on",
        "using",
        "where",
        "and",
        "order",
        "by",
        "asc",
        "desc",
        "nulls",
        "first",
        "last",
        "is",
        "not",
        "null",
        "true",
        "false",
        "as",
        "distinct",
    ]
)


def bancos_registrados() -> dict:
    """Os Postgres da casa, de registro/bancos.json do harness (#4185)."""
    import json

    import os

    # PF_ANALISE_BANCOS só aponta outro registro no ensaio; a porta não o repassa.
    arq = Path(
        os.getenv("PF_ANALISE_BANCOS")
        or Path(__file__).resolve().parents[2] / "registro/bancos.json"
    )
    try:
        return json.loads(arq.read_text())
    except (OSError, ValueError):
        raise Falha(3, "registro-de-bancos-ausente") from None


def origem_id(t: dict) -> str:
    return t.get("banco", "rag") + "/" + t["tabela"]


def normalizar_corte(corte: dict, declaradas: dict) -> dict:
    """Chave do corte: `banco/schema.tabela`, ou só `schema.tabela` quando única."""
    exigir(isinstance(corte, dict), "corte-invalido")
    saida = {}
    for chave, valor in corte.items():
        if chave in declaradas:
            oid = chave
        else:
            achadas = [o for o, t in declaradas.items() if t["tabela"] == chave]
            exigir(achadas, "corte-de-origem-nao-declarada")
            exigir(len(achadas) == 1, "corte-ambiguo:" + chave)
            oid = achadas[0]
        exigir(oid not in saida, "corte-duplicado")
        exigir(isinstance(valor, dict), "corte-invalido")
        saida[oid] = valor
    return saida


def _tokens(sql: str) -> list[str]:
    tokens, fim = [], 0
    for m in _TOKEN.finditer(sql):
        exigir(m.start() == fim, "sql-fora-do-contrato", 4)
        fim = m.end()
        s = m.group()
        if not s.isspace() and not s.startswith(("--", "/*")):
            tokens.append(s.lower())
    exigir(fim == len(sql), "sql-fora-do-contrato", 4)
    if tokens and tokens[-1] == ";":
        tokens.pop()
    return tokens


def _tabelas_usadas(tokens: list[str]) -> set[str]:
    usadas = set()
    for i, t in enumerate(tokens):
        if t in {"from", "join"}:
            exigir(
                i + 3 < len(tokens) and tokens[i + 2] == ".", "origem-nao-declarada", 4
            )
            usadas.add(tokens[i + 1] + "." + tokens[i + 3])
    return usadas


def banco_da_consulta(q: dict, sql: str, receita: dict) -> str:
    """Uma consulta lê um banco; o cruzamento entre bancos se faz no código da receita."""
    usadas = _tabelas_usadas(_tokens(sql))
    exigir(usadas, "origem-ausente")
    origens = receita["tabelas_de_origem"]
    if q.get("banco"):
        exigir(
            any(t.get("banco", "rag") == q["banco"] for t in origens),
            "banco-da-consulta-sem-origem",
        )
        return q["banco"]
    comuns = None
    for tabela in usadas:
        tem = {t.get("banco", "rag") for t in origens if t["tabela"] == tabela}
        exigir(tem, "origem-nao-declarada", 4)
        comuns = tem if comuns is None else comuns & tem
    exigir(comuns, "consulta-cruza-bancos")
    exigir(len(comuns) == 1, "banco-da-consulta-ambiguo")
    return next(iter(comuns))


def validar_sql(sql: str, receita: dict, banco: str | None = None) -> list[str]:
    if banco is None:
        banco = banco_da_consulta({}, sql, receita)
    origens = [t for t in receita["tabelas_de_origem"] if t.get("banco", "rag") == banco]
    cortes = {
        t["tabela"]: receita["corte"].get(origem_id(t), receita["corte"].get(t["tabela"], {}))
        for t in origens
    }
    return _validar_sql(sql, origens, cortes)


def _validar_sql(sql: str, origens: list[dict], cortes: dict) -> list[str]:
    tokens, fim = [], 0
    for m in _TOKEN.finditer(sql):
        exigir(m.start() == fim, "sql-fora-do-contrato", 4)
        fim = m.end()
        s = m.group()
        if not s.isspace() and not s.startswith(("--", "/*")):
            tokens.append(s.lower())
    exigir(fim == len(sql), "sql-fora-do-contrato", 4)
    if tokens and tokens[-1] == ";":
        tokens.pop()
    exigir(
        tokens
        and tokens[0] == "select"
        and tokens.count("select") == 1
        and ";" not in tokens,
        "sql-somente-select",
        4,
    )
    declaradas = {t["tabela"]: set(t["colunas"]) for t in origens}
    usadas_aqui = _tabelas_usadas(tokens)
    recortadas = {
        tab: c for tab, c in cortes.items()
        if tab in usadas_aqui and c.get("por") != "snapshot"
    }
    if recortadas:
        exigir(":corte" in tokens, "consulta-sem-corte")
    aliases, usados = {}, set()
    for i, t in enumerate(tokens):
        if t in {"from", "join"}:
            exigir(
                i + 3 < len(tokens) and tokens[i + 2] == ".", "origem-nao-declarada", 4
            )
            tabela = tokens[i + 1] + "." + tokens[i + 3]
            exigir(tabela in declaradas, "origem-nao-declarada", 4)
            usados.add(tabela)
            j = i + 4
            if j < len(tokens) and tokens[j] == "as":
                j += 1
            alias = (
                tokens[j]
                if j < len(tokens)
                and re.fullmatch(r"[a-z_][a-z_0-9]*", tokens[j])
                and tokens[j] not in _PALAVRAS
                else tabela.split(".")[1]
            )
            aliases[alias] = tabela
    exigir(usados, "origem-ausente")
    permitidas = _PALAVRAS | {":corte"} | set(aliases)
    for tabela, cols in declaradas.items():
        permitidas.update(tabela.split("."))
        permitidas.update(cols)
    for i, t in enumerate(tokens):
        if re.fullmatch(r"[a-z_][a-z_0-9]*", t):
            exigir(t in permitidas, "coluna-ou-funcao-nao-declarada", 4)
            if i + 1 < len(tokens) and tokens[i + 1] == "(":
                exigir(t == "using", "funcao-nao-declarada", 4)
        if t == "." and i and i + 1 < len(tokens) and tokens[i - 1] in aliases:
            exigir(
                tokens[i + 1] in declaradas[aliases[tokens[i - 1]]],
                "coluna-nao-declarada",
                4,
            )
    if not recortadas:
        return tokens
    exigir("where" in tokens, "consulta-sem-recorte", 4)
    wi = tokens.index("where")
    corte_colunas = {v["coluna"] for v in recortadas.values()}
    for coluna in corte_colunas:
        tab, col = coluna.rsplit(".", 1)
        achou = any(
            tokens[i : i + 5] == [alias, ".", col, "<", ":corte"]
            and tokens[i - 1] in {"where", "and"}
            and (i + 5 == len(tokens) or tokens[i + 5] in {"and", "order"})
            for alias, t in aliases.items()
            if t == tab
            for i in range(wi + 1, len(tokens) - 4)
        )
        exigir(achou, "recorte-nao-imposto", 4)
    return tokens


def parametros(receita: dict, entradas: list[str]) -> dict:
    declarados = {p["nome"]: p["tipo"] for p in receita.get("parametros", [])}
    saida = {}
    for item in entradas:
        nome, sep, valor = item.partition("=")
        exigir(
            sep and nome in declarados and nome not in saida, "parametro-desconhecido"
        )
        tipo = declarados[nome]
        try:
            if tipo == "inteiro":
                valor = int(valor)
            elif tipo in {"real", "decimal"}:
                valor = float(valor)
                import math

                exigir(math.isfinite(valor), "parametro-invalido")
            elif tipo == "booleano":
                exigir(valor in {"true", "false"}, "parametro-invalido")
                valor = valor == "true"
            elif tipo == "instante":
                dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
                exigir(dt.tzinfo is not None, "parametro-sem-fuso")
                valor = dt.isoformat()
            else:
                exigir(tipo == "texto", "tipo-parametro-invalido")
        except ValueError:
            raise Falha(2, "parametro-mal-tipado") from None
        saida[nome] = valor
    return saida


def pre_voo(receita: dict, n: int | None = None) -> int:
    n = receita["populacao"]["n"] if n is None else n
    estimativa = (
        n * (n - 1) // 2 * 8 if receita["metodo"] == "agrupamento-hierarquico" else 0
    )
    exigir(estimativa <= 1024**3, "pre-voo-memoria:" + str(estimativa), 5)
    return estimativa
