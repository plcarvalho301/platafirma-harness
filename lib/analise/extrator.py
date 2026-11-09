"""Extração: uma transação REPEATABLE READ só de leitura por banco, fechada antes de calcular.

#4185: a origem é qualquer Postgres de registro/bancos.json. Cada banco se lê pela role
analise_leitura (lib/analise/sql/leitura.sql), pelo socket local do contêiner, com
`docker exec … psql`: não depende de porta publicada nem de senha, e alcança também o banco
que só vive na rede do compose (rastreador, keycloak). O cruzamento entre bancos é do código
da receita, sobre as CSVs de entrada.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg import Connection

import csv
import os
import re
import subprocess
import uuid
from datetime import timedelta

from . import Falha, agora, exigir, hash_arquivo, relativo
from .receita import banco_da_consulta, bancos_registrados, validar_sql

ROLE_LEITURA = "analise_leitura"
TETO_ENTRADA = 2 * 1024**3
CORRECAO_ROLE = "release migrar aplicar {banco} com lib/analise/sql/leitura.sql no stdin"


def configuracao(parte: str) -> dict:
    # Só o destino (catálogo do analise, no banco do acervo) usa conexão com senha.
    from raizes import instancia

    exigir(parte == "destino", "origem-por-banco")
    prefixo = "ANALISE_DESTINO_"
    cofre = instancia() / "segredos/rag"
    arq = cofre / (prefixo + "PASSWORD")
    exigir(arq.is_file(), "credencial-ausente:" + arq.name, 3)
    return dict(
        host=os.getenv(prefixo + "HOST", "127.0.0.1"),
        port=int(os.getenv(prefixo + "PORT", "5432")),
        dbname=os.getenv(prefixo + "DB", "rag_extractor"),
        user="analise_publicacao",
        password=arq.read_text().strip(),
        connect_timeout=5,
    )


def conectar(parte: str) -> Connection | None:
    if parte == "origem":
        # A origem não é uma conexão: é o registro de bancos, lido na extração.
        return None
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
    margens = [0]
    for c in receita["corte"].values():
        if c.get("por") == "snapshot":
            continue
        exigir(c["por"] == "instante", "corte-chave-exige-valor")
        m = re.fullmatch(r"(\d+)(s|min|h|d)", str(c["margem"]))
        exigir(m, "margem-invalida")
        margens.append(int(m[1]) * {"s": 1, "min": 60, "h": 3600, "d": 86400}[m[2]])
    return agora() - timedelta(seconds=max(margens))


def _roteiro(consultas: list[tuple[dict, str]], corte: datetime, marca: str) -> str:
    linhas = [
        "\\set ON_ERROR_STOP 1",
        # O valor é um datetime validado: isoformat não tem aspa nem barra invertida.
        "\\set corte '" + corte.isoformat() + "'",
        "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;",
        "SET LOCAL statement_timeout = '120s';",
        "SET LOCAL lock_timeout = '2s';",
        "SET LOCAL idle_in_transaction_session_timeout = '30s';",
        "SET LOCAL TimeZone = 'UTC';",
        "SET LOCAL DateStyle = 'ISO, YMD';",
        "SET LOCAL extra_float_digits = 1;",
        "\\echo " + marca + " snapshot",
        "SELECT pg_current_snapshot();",
    ]
    for q, sql in consultas:
        corpo = sql.rstrip().rstrip(";")
        # Só o token conhecido vira a variável do psql, que o psql cita como literal.
        corpo = re.sub(r":corte\b", ":'corte'", corpo)
        linhas += [
            "\\echo " + marca + " q " + q["nome"],
            "COPY (\n" + corpo + "\n) TO STDOUT WITH (FORMAT csv, HEADER true);",
        ]
    linhas += ["ROLLBACK;", "\\echo " + marca + " fim", ""]
    return "\n".join(linhas)


def _comando(banco: dict) -> list[str]:
    return [
        os.getenv("PF_ANALISE_DOCKER", "docker"),
        "exec",
        "-i",
        banco["conteiner"],
        "psql",
        "-X",
        "-q",
        "-A",
        "-t",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        ROLE_LEITURA,
        "-d",
        banco["base"],
        "-f",
        "-",
    ]


def _causa(slug: str, rc: int, err: str) -> Falha:
    # Nunca devolve o diagnóstico do servidor: pode conter linha de dado.
    e = err.lower()
    if "no such container" in e or "is not running" in e or "cannot connect to the docker" in e:
        return Falha(3, "banco-indisponivel:" + slug)
    if 'role "analise_leitura" does not exist' in e or "not permitted to log in" in e:
        return Falha(3, "leitura-sem-role:" + slug, CORRECAO_ROLE.format(banco=slug))
    if "permission denied" in e or "read-only transaction" in e:
        return Falha(4, "extracao-recusada:" + slug)
    if "statement timeout" in e or "canceling statement" in e:
        return Falha(5, "extracao-estourou-prazo:" + slug)
    return Falha(5, "extracao-incompleta:" + slug)


def _extrair_banco(
    slug: str,
    banco: dict,
    consultas: list[tuple[dict, str]],
    entrada: Path,
    corte: datetime,
    prazo: float,
) -> tuple[str, dict]:
    marca = "--analise-" + uuid.uuid4().hex + "--"
    roteiro = _roteiro(consultas, corte, marca)
    abertos: dict[str, Path] = {}
    atual = None
    destino = None
    snapshot = None
    fim = False
    try:
        p = subprocess.Popen(
            _comando(banco),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        raise Falha(3, "docker-ausente") from None
    try:
        import threading

        erro: list[bytes] = []
        t = threading.Thread(target=lambda: erro.append(p.stderr.read()), daemon=True)
        t.start()
        p.stdin.write(roteiro.encode())
        p.stdin.close()
        relogio = threading.Timer(prazo, p.kill)
        relogio.start()
        try:
            for linha in p.stdout:
                texto = linha.rstrip(b"\r\n").decode("utf-8", "replace")
                if texto.startswith(marca + " "):
                    if destino:
                        destino.close()
                        destino = None
                    resto = texto[len(marca) + 1 :]
                    if resto == "snapshot":
                        atual = "snapshot"
                    elif resto == "fim":
                        atual, fim = None, True
                    else:
                        nome = resto[2:]
                        arq = entrada / (nome + ".csv")
                        abertos[nome] = arq
                        destino = arq.open("wb")
                        atual = nome
                    continue
                if atual == "snapshot":
                    snapshot = snapshot or texto.strip()
                elif destino is not None:
                    destino.write(linha)
                    if destino.tell() > TETO_ENTRADA:
                        p.kill()
                        raise Falha(5, "teto-disco-extracao")
        finally:
            relogio.cancel()
        rc = p.wait()
        t.join(timeout=5)
    finally:
        if destino:
            destino.close()
        if p.poll() is None:
            p.kill()
            p.wait()
    if rc != 0 or not fim:
        if rc in (-9, 137) and not fim:
            raise Falha(5, "extracao-estourou-prazo:" + slug)
        raise _causa(slug, rc, b"".join(erro).decode("utf-8", "replace"))
    exigir(set(abertos) == {q["nome"] for q, _ in consultas}, "extracao-incompleta:" + slug, 5)
    return snapshot or "", abertos


def _linhas(arq: Path) -> int:
    with arq.open(newline="") as f:
        return max(sum(1 for _ in csv.reader(f)) - 1, 0)


def extrair(
    conn: object,
    receita: dict,
    pasta: Path,
    entrada: Path,
    corte: datetime,
    prazo: float = 300,
    bancos: dict | None = None,
) -> dict:
    """`conn` fica pela assinatura antiga e não se usa: a origem vem do registro de bancos."""
    bancos = bancos if bancos is not None else bancos_registrados()
    por_banco: dict[str, list[tuple[dict, str]]] = {}
    for q in receita["consultas"]:
        sql = relativo(pasta, q["arquivo"]).read_text()
        slug = q.get("banco") or banco_da_consulta(q, sql, receita)
        validar_sql(sql, receita, slug)
        exigir(slug in bancos, "banco-fora-do-registro:" + slug)
        por_banco.setdefault(slug, []).append((q, sql))
    metadados = {}
    total = 0
    for slug, consultas in por_banco.items():
        snapshot, arquivos = _extrair_banco(
            slug, bancos[slug], consultas, entrada, corte, prazo
        )
        for q, _ in consultas:
            arquivo = arquivos[q["nome"]]
            arquivo.chmod(0o400)
            total += arquivo.stat().st_size
            exigir(total <= TETO_ENTRADA, "teto-disco-extracao", 5)
            metadados[q["nome"]] = {
                "sha256": hash_arquivo(arquivo),
                "linhas": _linhas(arquivo),
                "bytes": arquivo.stat().st_size,
                "banco": slug,
                "snapshot": snapshot,
                "corte": str(corte),
                "instante": agora().isoformat(),
                "role": ROLE_LEITURA + "@" + slug,
                "origens": [
                    t for t in receita["tabelas_de_origem"] if t.get("banco", "rag") == slug
                ],
                "garantia": receita["corte"],
            }
    return metadados
