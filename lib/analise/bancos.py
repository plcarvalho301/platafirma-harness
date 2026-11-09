"""`analise bancos`: o que cada Postgres da casa guarda, lido pela role de leitura (#4185).

Sem banco, uma linha por banco de registro/bancos.json: se a leitura alcança e quantas
tabelas há. Com banco, uma linha por tabela, com a estimativa de linhas e as colunas com o
tipo, que é o que a receita declara em tabelas_de_origem.
"""

from __future__ import annotations

import subprocess

from . import Falha, exigir
from .extrator import _causa, _comando
from .receita import bancos_registrados

_CATALOGO = """\\pset fieldsep '\\t'
SELECT n.nspname || '.' || c.relname,
       greatest(c.reltuples, 0)::bigint,
       string_agg(a.attname || ' ' || format_type(a.atttypid, a.atttypmod), ', ' ORDER BY a.attnum)
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
 WHERE c.relkind IN ('r', 'p', 'v', 'm', 'f')
   AND NOT c.relispartition
   AND n.nspname NOT IN ('pg_catalog', 'information_schema')
   AND n.nspname NOT LIKE 'pg\\_toast%'
 GROUP BY 1, 2
 ORDER BY 1;
"""


def _ler(slug: str, banco: dict) -> list[tuple[str, int, str]]:
    try:
        p = subprocess.run(
            _comando(banco),
            input=_CATALOGO,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except OSError:
        raise Falha(3, "docker-ausente") from None
    except subprocess.TimeoutExpired:
        raise Falha(5, "extracao-estourou-prazo:" + slug) from None
    if p.returncode:
        raise _causa(slug, p.returncode, p.stderr)
    linhas = []
    for linha in p.stdout.splitlines():
        partes = linha.split("\t")
        if len(partes) == 3:
            linhas.append((partes[0], int(partes[1] or 0), partes[2]))
    return linhas


def listar(slug: str | None = None) -> tuple[int, dict]:
    registro = bancos_registrados()
    if slug:
        exigir(slug in registro, "banco-fora-do-registro:" + slug)
        tabelas = _ler(slug, registro[slug])
        return 0, {
            "estado": "pronta",
            "banco": slug,
            "itens": [
                {"tabela": t, "linhas_estimadas": n, "colunas": c} for t, n, c in tabelas
            ],
        }
    itens = []
    pior = 0
    for s, b in registro.items():
        try:
            n = len(_ler(s, b))
            itens.append({"banco": s, "le": True, "tabelas": n, "guarda": b.get("o_que_guarda")})
        except Falha as e:
            pior = max(pior, e.exit)
            itens.append(
                {"banco": s, "le": False, "causa": e.causa, "correcao": e.correcao}
            )
    return (0 if not pior else pior), {"estado": "pronta" if not pior else "incompleta", "itens": itens}
