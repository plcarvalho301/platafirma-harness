#!/usr/bin/env python3
"""sessao_orfa — `release conferir sessao-orfa`: contagem de sessao_id órfãos (card #3375).

Mede, por tabela do acervo e da fita, os sessao_id gravados sem sessão correspondente
em sessao.sessao (legado de fontes recicláveis e gravações ocorridas com o banco de sessão fora).

Regra de negócio:
  - Antes de gravar um sessao_id no acervo, o gravador consulta sessao.sessao por chave primária.
  - Existe: grava. Não existe: grava sessao_id nulo e conta em campos_invalidos (migração 088).
  - Banco de sessão fora: grava como veio — log não se perde — e a linha fica para a contagem.
  - `release conferir sessao-orfa` conta, por tabela, os sessao_id gravados sem sessão.
  - Sai 0 sem órfão novo (contra a linha de base do legado).
  - Sai 1 com órfão novo.
  - Sai 5 se um banco não responde.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Callable

import resultado

BANCOS = {
    "rag": ("rag-extractor-pg", "rag", "rag_extractor"),
    "sessao": ("harness-sessao-db", "sessao", "sessao"),
}

# Linha de base do legado de sessao_id órfãos anterior à trava do card #3375.
# Cada entrada é o teto tolerado. Qualquer acréscimo é divergência (exit 1).
# Medida em 10/10/2026: 13:02 e 13:14 BRT, contagem igual nas duas leituras, com a
# trava no ar (conhecimento 86efd11) e o extrator parado entre elas (incidente #3401).
# Legado não se corrige nem se apaga: só se conta (trava do card).
LINHA_DE_BASE: dict[str, int] = {
    "acervo.evento_recuperacao": 2,
    "acervo.voto_humano": 0,
    "acervo.registro": 0,
    "acervo.log(sessao_id)": 64,
    "acervo.log(origem_sessao)": 0,
    "sessao.fita": 1,
}


class Indeterminavel(Exception):
    """Banco ou fonte que não respondeu."""


def psql_json(banco: str, sql: str, env_docker: dict[str, str] | None = None) -> Any:
    """Executa SQL no container do banco e decodifica retorno JSON."""
    if banco not in BANCOS:
        raise Indeterminavel(f"banco desconhecido: {banco}")
    ctr, usr, base = BANCOS[banco]
    env = dict(env_docker) if env_docker else dict(os.environ)
    env.setdefault("DOCKER_HOST", f"unix:///run/user/{os.getuid()}/docker.sock")
    try:
        p = subprocess.run(
            ["docker", "exec", "-i", ctr, "psql", "-U", usr, "-d", base, "-tA",
             "-v", "ON_ERROR_STOP=1", "-c", sql],
            capture_output=True, text=True, env=env, timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Indeterminavel(f"{ctr}: {e}") from None

    if p.returncode != 0:
        msg = (p.stderr or p.stdout or f"psql saiu {p.returncode}").strip().splitlines()
        raise Indeterminavel(f"{ctr}: {msg[0] if msg else p.returncode}")

    texto = p.stdout.strip()
    if not texto:
        return None
    try:
        return json.loads(texto)
    except ValueError:
        raise Indeterminavel(f"{ctr}: resposta não é json: {texto[:80]!r}") from None


# Definição das tabelas e colunas inspecionadas
# (nome_tabela, banco, sql_grupos_sid)
TABELAS_A_CONFERIR: list[tuple[str, str, str]] = [
    (
        "acervo.evento_recuperacao",
        "rag",
        """
        SELECT json_agg(json_build_object('sid', sessao_id::text, 'qtd', c))
        FROM (
            SELECT sessao_id, count(*) as c
            FROM acervo.evento_recuperacao
            WHERE sessao_id IS NOT NULL AND sessao_id::text != ''
            GROUP BY sessao_id
        ) sub;
        """,
    ),
    (
        "acervo.voto_humano",
        "rag",
        """
        SELECT json_agg(json_build_object('sid', sessao_id::text, 'qtd', c))
        FROM (
            SELECT sessao_id, count(*) as c
            FROM acervo.voto_humano
            WHERE sessao_id IS NOT NULL AND sessao_id::text != ''
            GROUP BY sessao_id
        ) sub;
        """,
    ),
    (
        "acervo.registro",
        "rag",
        """
        SELECT json_agg(json_build_object('sid', sessao_id::text, 'qtd', c))
        FROM (
            SELECT sessao_id, count(*) as c
            FROM acervo.registro
            WHERE sessao_id IS NOT NULL
            GROUP BY sessao_id
        ) sub;
        """,
    ),
    (
        "acervo.log(sessao_id)",
        "rag",
        """
        SELECT json_agg(json_build_object('sid', sessao_id::text, 'qtd', c))
        FROM (
            SELECT sessao_id, count(*) as c
            FROM acervo.log
            WHERE sessao_id IS NOT NULL
            GROUP BY sessao_id
        ) sub;
        """,
    ),
    (
        "acervo.log(origem_sessao)",
        "rag",
        """
        SELECT json_agg(json_build_object('sid', origem_sessao::text, 'qtd', c))
        FROM (
            SELECT origem_sessao, count(*) as c
            FROM acervo.log
            WHERE origem_sessao IS NOT NULL
            GROUP BY origem_sessao
        ) sub;
        """,
    ),
    (
        "sessao.fita",
        "sessao",
        """
        SELECT json_agg(json_build_object('sid', sessao_id::text, 'qtd', c))
        FROM (
            SELECT sessao_id, count(*) as c
            FROM sessao.fita
            WHERE sessao_id IS NOT NULL AND sessao_id != ''
            GROUP BY sessao_id
        ) sub;
        """,
    ),
]


def carregar_sessoes_validas(fn_psql: Callable[[str, str], Any] = psql_json) -> set[str]:
    sql = "SELECT json_agg(sessao_id::text) FROM sessao.sessao WHERE sessao_id IS NOT NULL;"
    dados = fn_psql("sessao", sql)
    if not dados:
        return set()
    return set(dados)


def contar_orfaos_tabela(
    banco: str,
    sql_grupos: str,
    sessoes_validas: set[str],
    fn_psql: Callable[[str, str], Any] = psql_json,
) -> tuple[int, int]:
    """Retorna (total_linhas_com_sessao, total_linhas_orfas)."""
    grupos = fn_psql(banco, sql_grupos)
    if not grupos:
        return 0, 0

    total_com_sessao = 0
    total_orfaos = 0
    for g in grupos:
        sid = (g.get("sid") or "").strip()
        qtd = int(g.get("qtd") or 0)
        total_com_sessao += qtd
        if sid not in sessoes_validas:
            total_orfaos += qtd

    return total_com_sessao, total_orfaos


def conferir(
    alvo: str | None = None,
    como_json: bool = False,
    sha_release: str = "desconhecido",
    fn_psql: Callable[[str, str], Any] = psql_json,
) -> int:
    """Compara contagem de sessao_id órfãos por tabela contra a linha de base."""
    itens: list[tuple[str, resultado.Veredito]] = []

    # 1. Carregar sessões válidas de sessao.sessao
    try:
        sessoes_validas = carregar_sessoes_validas(fn_psql)
    except Indeterminavel as e:
        itens.append(("(banco de sessao)", resultado.indeterminavel(str(e))))
        return resultado.relatorio("sessao-orfa", alvo, itens, sha_release, como_json=como_json)

    # 2. Filtrar tabelas se alvo fornecido
    tabelas = TABELAS_A_CONFERIR
    if alvo:
        alvo_norm = alvo.strip().lower()
        tabelas = [t for t in TABELAS_A_CONFERIR if alvo_norm in t[0].lower()]
        if not tabelas:
            msg = f"nenhuma tabela corresponde ao alvo {alvo!r}"
            if como_json:
                print(json.dumps({"erro": msg}))
            else:
                print(msg, file=sys.stderr)
            return 1

    # 3. Conferir cada tabela
    for nome, banco, sql_grupos in tabelas:
        base = LINHA_DE_BASE.get(nome, 0)
        try:
            total_com_sessao, total_orfaos = contar_orfaos_tabela(
                banco, sql_grupos, sessoes_validas, fn_psql=fn_psql
            )
        except Indeterminavel as e:
            itens.append((nome, resultado.indeterminavel(str(e))))
            continue

        if total_orfaos > base:
            novos = total_orfaos - base
            motivo = (f"{total_orfaos} órfãos ({novos} novo(s) acima da linha de base de {base}; "
                      f"{total_com_sessao} total com chave)")
            itens.append((nome, resultado.divergente(motivo)))
        else:
            itens.append((nome, resultado.conforme()))

    return resultado.relatorio("sessao-orfa", alvo, itens, sha_release, como_json=como_json)
