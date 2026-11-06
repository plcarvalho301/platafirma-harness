"""Páginas de dados e projeções com posse e vencimento conferidos antes."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .publicacao import Catalogo
from . import exigir


def ler(
    cat: Catalogo, id: str, tabela: dict, linhas: str, projecao: str, destino: Path
) -> dict:
    if id.startswith("ex-"):
        return {
            "execucao_id": id,
            "estado": "pronta",
            "manifesto": cat.execucao(id)["manifesto"],
        }
    obj = cat.objeto(id)
    if not tabela and not projecao:
        return {
            "estado": "pronta",
            "manifesto": obj["manifesto"],
            "expires_at": obj["expires_at"],
        }
    if projecao:
        from . import nome_seguro

        nome_seguro(projecao)
        row = cat.conn.execute(
            "SELECT conteudo FROM analise.projecao WHERE objeto_id=%s AND nome=%s",
            (id, projecao),
        ).fetchone()
        exigir(row, "projecao-desconhecida")
        # A cópia fica dentro do diretório protegido da própria execução.
        p = destino / "analise" / obj["execucao_id"] / "projecoes" / (projecao + ".png")
        p.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        p.write_bytes(bytes(row[0]))
        p.chmod(0o400)
        return {"estado": "pronta", "caminho": str(p)}
    import re

    m = re.fullmatch(r"(\d+)-(\d+)", linhas)
    exigir(
        m and 1 <= int(m[1]) <= int(m[2]) and int(m[2]) - int(m[1]) < 500,
        "pagina-invalida",
    )
    from psycopg import sql

    row = cat.conn.execute(
        "SELECT fisica,colunas,ordem FROM analise.tabela WHERE objeto_id=%s AND nome=%s",
        (id, tabela),
    ).fetchone()
    exigir(row, "tabela-desconhecida")
    fisica, colunas, ordem = row
    with cat.conn.cursor() as cur:
        cur.execute(
            sql.SQL("SELECT {} FROM analise.{} ORDER BY {} OFFSET %s LIMIT %s").format(
                sql.SQL(",").join(sql.Identifier(c["nome"]) for c in colunas),
                sql.Identifier(fisica),
                sql.SQL(",").join(sql.Identifier(c) for c in ordem),
            ),
            (int(m[1]) - 1, int(m[2]) - int(m[1]) + 1),
        )
        rows = cur.fetchall()
    return {
        "estado": "pronta",
        "colunas": [c["nome"] for c in colunas],
        "linhas": rows,
        "expires_at": obj["expires_at"],
    }
