"""Entrega somente as tabelas declaradas, com conferência do publicado."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .publicacao import Catalogo
import csv

from . import exigir
from .serializacao import canonizar, conferir_sha


def materializar(catalogo: Catalogo, base: dict, receita: dict, entrada: Path) -> dict:
    from psycopg import sql

    exigir(base["receita"] in receita["base"]["receitas"], "base-nao-aceita")
    metadados = {}
    for nome in receita["base"]["tabelas"]:
        linha = catalogo.conn.execute(
            "SELECT fisica,colunas,ordem,sha256 FROM analise.tabela WHERE objeto_id=%s AND nome=%s",
            (base["id"], nome),
        ).fetchone()
        exigir(linha, "tabela-base-nao-declarada", 4)
        fisica, colunas, ordem, sha = linha
        arquivo = entrada / (nome + ".csv")
        with (
            catalogo.conn.transaction(),
            catalogo.conn.cursor(name="m_" + nome) as cur,
            arquivo.open("w", newline="") as f,
        ):
            cur.execute(
                sql.SQL("SELECT {} FROM analise.{} ORDER BY {}").format(
                    sql.SQL(",").join(sql.Identifier(c["nome"]) for c in colunas),
                    sql.Identifier(fisica),
                    sql.SQL(",").join(
                        sql.SQL("{} NULLS FIRST").format(sql.Identifier(c))
                        for c in ordem
                    ),
                )
            )
            w = csv.writer(f, lineterminator="\n")
            w.writerow([c["nome"] for c in colunas])
            for row in cur:
                w.writerow(
                    [v.isoformat() if isinstance(v, datetime) else v for v in row]
                )
        tab = {"nome": nome, "colunas": colunas, "ordem": ordem}
        c = canonizar(arquivo, tab, base["manifesto"]["serializacao"])
        conferir_sha(c["conteudo"], sha)
        arquivo.write_bytes(c["conteudo"])
        arquivo.chmod(0o400)
        metadados[nome] = {k: v for k, v in c.items() if k != "conteudo"}
    return metadados
