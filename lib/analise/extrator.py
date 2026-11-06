"""Uma transação REPEATABLE READ, fechada antes de calcular."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg import Connection

import csv
import os
import re
from datetime import timedelta

from . import Falha, agora, exigir, hash_arquivo, relativo
from .receita import validar_sql
from .supervisor import prazo_extracao


def configuracao(parte: str) -> dict:
    # Cada conexão lê somente sua senha. Nunca carrega POSTGRES_PASSWORD.
    from raizes import instancia

    prefixo = "ANALISE_ORIGEM_" if parte == "origem" else "ANALISE_DESTINO_"
    role = "analise_extracao" if parte == "origem" else "analise_publicacao"
    cofre = instancia() / "segredos/rag"
    arq = cofre / (prefixo + "PASSWORD")
    exigir(arq.is_file(), "credencial-ausente:" + arq.name, 3)
    return dict(
        host=os.getenv(prefixo + "HOST", "127.0.0.1"),
        port=int(os.getenv(prefixo + "PORT", "5432")),
        dbname=os.getenv(prefixo + "DB", "rag_extractor"),
        user=role,
        password=arq.read_text().strip(),
        connect_timeout=5,
    )


def conectar(parte: str) -> Connection:
    try:
        import psycopg

        return psycopg.connect(**configuracao(parte))
    except Falha:
        raise
    except ImportError:
        raise Falha(3, "driver-ausente") from None
    except Exception:
        raise Falha(5, "banco-indisponivel") from None


def resolver_corte(receita: dict, valor: object) -> datetime:
    if valor:
        try:
            dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
            exigir(dt.tzinfo is not None, "corte-sem-fuso")
            return dt
        except ValueError:
            raise Falha(2, "corte-invalido") from None
    margens = []
    for c in receita["corte"].values():
        exigir(c["por"] == "instante", "corte-chave-exige-valor")
        m = re.fullmatch(r"(\d+)(s|min|h|d)", str(c["margem"]))
        exigir(m, "margem-invalida")
        margens.append(int(m[1]) * {"s": 1, "min": 60, "h": 3600, "d": 86400}[m[2]])
    return agora() - timedelta(seconds=max(margens))


def extrair(
    conn: Connection,
    receita: dict,
    pasta: Path,
    entrada: Path,
    corte: datetime,
    prazo: float = 120,
) -> dict:
    consultas = []
    for q in receita["consultas"]:
        sql = relativo(pasta, q["arquivo"]).read_text()
        validar_sql(sql, receita)
        # O token foi validado fora de literais/comentários. Este replace atua
        # só no token conhecido; não usa interpolação de valor.
        consultas.append((q, re.sub(r":corte\b", "%(corte)s", sql)))
    metadados = {}
    try:
        with prazo_extracao(conn, prazo):
            conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
            for comando in (
                "SET LOCAL statement_timeout='60s'",
                "SET LOCAL lock_timeout='2s'",
                "SET LOCAL idle_in_transaction_session_timeout='15s'",
                "SET LOCAL work_mem='8MB'",
                "SET LOCAL max_parallel_workers_per_gather=0",
            ):
                conn.execute(comando)
            snapshot = str(conn.execute("SELECT pg_current_snapshot()").fetchone()[0])
            for i, (q, sql) in enumerate(consultas):
                arquivo = entrada / (q["nome"] + ".csv")
                n = 0
                with (
                    conn.cursor(name="analise_" + str(i)) as cur,
                    arquivo.open("w", newline="") as f,
                ):
                    cur.execute(sql, {"corte": corte})
                    w = csv.writer(f, lineterminator="\n")
                    w.writerow([c.name for c in cur.description])
                    for rows in iter(lambda: cur.fetchmany(1000), []):
                        for row in rows:
                            w.writerow(
                                [
                                    v.isoformat() if isinstance(v, datetime) else v
                                    for v in row
                                ]
                            )
                        n += len(rows)
                        exigir(
                            sum(
                                p.stat().st_size
                                for p in entrada.iterdir()
                                if p.is_file()
                            )
                            <= 2 * 1024**3,
                            "teto-disco-extracao",
                            5,
                        )
                arquivo.chmod(0o400)
                metadados[q["nome"]] = {
                    "sha256": hash_arquivo(arquivo),
                    "linhas": n,
                    "bytes": arquivo.stat().st_size,
                    "snapshot": snapshot,
                    "corte": str(corte),
                    "instante": agora().isoformat(),
                    "role": conn.info.user,
                    "origens": receita["tabelas_de_origem"],
                    "garantia": receita["corte"],
                }
    except Falha:
        raise
    except Exception as exc:
        # Nunca devolve o diagnóstico do servidor: pode conter linha de dado.
        raise Falha(
            4 if getattr(exc, "sqlstate", None) in {"42501", "25006"} else 5,
            "extracao-recusada"
            if getattr(exc, "sqlstate", None) in {"42501", "25006"}
            else "extracao-incompleta",
        ) from None
    finally:
        if not conn.closed:
            conn.rollback()
        conn.close()
    return metadados
