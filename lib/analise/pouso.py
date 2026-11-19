"""Carga de arquivo de fonte externa em tabela de pouso declarada, com linhagem e corte."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from psycopg import Connection

from . import Falha, agora, exigir, hash_arquivo, json_canonico
from .extrator import TETO_ENTRADA
from .publicacao import novo

FORMATOS = {"csv", "tsv", "json", "jsonl"}
MODOS = {"substituir", "acrescentar"}
EXTENSOES = {
    ".csv": "csv",
    ".tsv": "tsv",
    ".json": "json",
    ".jsonl": "jsonl",
    ".ndjson": "jsonl",
}
COLUNAS_LINHAGEM = (
    ("carga_id", "text NOT NULL"),
    ("fonte_arquivo", "text NOT NULL"),
    ("fonte_sha256", "text NOT NULL"),
    ("fonte_bytes", "bigint NOT NULL"),
    ("carregado_em", "timestamptz NOT NULL"),
    ("corte_em", "timestamptz NOT NULL"),
    ("sujeito", "text NOT NULL"),
)
_NOMES_LINHAGEM = {nome for nome, _ in COLUNAS_LINHAGEM}


def normalizar_tabela(nome: str) -> str:
    """Normaliza e valida o nome da tabela de pouso em `analise.pouso_<slug>`."""
    exigir(isinstance(nome, str) and bool(nome.strip()), "tabela-pouso-invalida")
    alvo = nome.strip().removeprefix("analise.")
    exigir("." not in alvo, "tabela-pouso-invalida")
    alvo = alvo.removeprefix("pouso_")
    exigir(re.fullmatch(r"[a-z][a-z0-9_]{0,44}", alvo), "tabela-pouso-invalida")
    return "pouso_" + alvo


def inferir_formato(arquivo: Path, formato: str | None = None) -> str:
    """Resolve e valida o formato do arquivo de origem."""
    fmt = formato or EXTENSOES.get(arquivo.suffix.lower())
    exigir(fmt in FORMATOS, "formato-pouso-invalido")
    return fmt


def _resolver_corte(corte: datetime | str | None, padrao: datetime) -> datetime:
    if corte is None:
        return padrao
    if isinstance(corte, str):
        try:
            dt = datetime.fromisoformat(corte.replace("Z", "+00:00"))
        except ValueError:
            raise Falha(2, "corte-invalido") from None
        exigir(dt.tzinfo is not None, "corte-sem-fuso")
        return dt
    exigir(corte.tzinfo is not None, "corte-sem-fuso")
    return corte


def _sanear_coluna(nome: str, usadas: set[str]) -> str:
    base = re.sub(r"[^a-z0-9_]+", "_", nome.strip().lower()).strip("_")
    if not base or not re.match(r"[a-z_]", base) or base in _NOMES_LINHAGEM:
        base = "c_" + (base or "col")
    base = base[:55]
    candidato = base
    i = 2
    while candidato in usadas:
        candidato = f"{base}_{i}"
        i += 1
    usadas.add(candidato)
    return candidato


def _serializar_valor(valor: object) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, bool):
        return "true" if valor else "false"
    if isinstance(valor, (dict, list)):
        return json_canonico(valor)
    return str(valor)


def ler_registros(
    arquivo: Path, formato: str
) -> tuple[list[str], list[dict[str, str | None]]]:
    """Lê registros de CSV, TSV, JSON ou JSONL e devolve colunas saneadas e linhas."""
    if formato in {"csv", "tsv"}:
        delim = "," if formato == "csv" else "\t"
        try:
            with arquivo.open("r", encoding="utf-8", newline="") as f:
                leitor = csv.DictReader(f, delimiter=delim)
                exigir(leitor.fieldnames, "arquivo-pouso-sem-cabecalho")
                brutas = list(leitor.fieldnames)
                usadas: set[str] = set()
                mapa = {b: _sanear_coluna(b, usadas) for b in brutas}
                colunas = [mapa[b] for b in brutas]
                linhas = [
                    {mapa[b]: _serializar_valor(row.get(b)) for b in brutas}
                    for row in leitor
                ]
                return colunas, linhas
        except UnicodeDecodeError:
            raise Falha(2, "arquivo-pouso-invalido") from None
    try:
        texto = arquivo.read_text(encoding="utf-8")
        if formato == "jsonl":
            itens = [json.loads(ln) for ln in texto.splitlines() if ln.strip()]
        else:
            dado = json.loads(texto)
            itens = dado if isinstance(dado, list) else [dado]
    except (OSError, UnicodeDecodeError, ValueError):
        raise Falha(2, "arquivo-pouso-invalido") from None
    exigir(
        itens and all(isinstance(it, dict) for it in itens),
        "arquivo-pouso-vazio" if not itens else "arquivo-pouso-invalido",
    )
    chaves: list[str] = []
    vistas: set[str] = set()
    for it in itens:
        for k in it:
            ks = str(k)
            if ks not in vistas:
                vistas.add(ks)
                chaves.append(ks)
    usadas = set()
    mapa = {k: _sanear_coluna(k, usadas) for k in chaves}
    colunas = [mapa[k] for k in chaves]
    linhas = [
        {mapa[k]: _serializar_valor(it.get(k)) for k in chaves} for it in itens
    ]
    return colunas, linhas


def carregar(
    conn: Connection,
    sujeito: str,
    tabela: str,
    arquivo: Path,
    opcoes: dict | None = None,
) -> dict:
    """Carrega um arquivo externo numa tabela de pouso em `analise` com linhagem e corte."""
    from psycopg import sql

    cfg = opcoes or {}
    modo = cfg.get("modo", "substituir")
    exigir(modo in MODOS, "modo-pouso-invalido")
    fisica = normalizar_tabela(tabela)
    arq = Path(arquivo)
    exigir(arq.is_file() and not arq.is_symlink(), "arquivo-pouso-ausente")
    tamanho = arq.stat().st_size
    exigir(tamanho <= TETO_ENTRADA, "teto-disco-pouso", 5)
    fmt = inferir_formato(arq, cfg.get("formato"))
    instante = agora()
    corte_em = _resolver_corte(cfg.get("corte"), instante)
    sha = hash_arquivo(arq)
    colunas, linhas = ler_registros(arq, fmt)
    carga_id = novo("cg")

    with conn.transaction():
        conn.execute(
            """CREATE TABLE IF NOT EXISTS analise.pouso_carga (
                id text PRIMARY KEY,
                tabela text NOT NULL,
                sujeito text NOT NULL,
                fonte_arquivo text NOT NULL,
                fonte_sha256 text NOT NULL,
                fonte_bytes bigint NOT NULL,
                formato text NOT NULL,
                modo text NOT NULL,
                linhas integer NOT NULL,
                corte_em timestamptz NOT NULL,
                carregado_em timestamptz NOT NULL
            )"""
        )
        defs = [
            sql.SQL("{} {}").format(sql.Identifier(n), sql.SQL(t))
            for n, t in COLUNAS_LINHAGEM
        ] + [sql.SQL("{} text").format(sql.Identifier(c)) for c in colunas]
        conn.execute(
            sql.SQL("CREATE TABLE IF NOT EXISTS analise.{} ({})").format(
                sql.Identifier(fisica), sql.SQL(", ").join(defs)
            )
        )
        if colunas:
            adicoes = [
                sql.SQL("ADD COLUMN IF NOT EXISTS {} text").format(sql.Identifier(c))
                for c in colunas
            ]
            conn.execute(
                sql.SQL("ALTER TABLE analise.{} {}").format(
                    sql.Identifier(fisica), sql.SQL(", ").join(adicoes)
                )
            )
        if modo == "substituir":
            conn.execute(
                sql.SQL("TRUNCATE TABLE analise.{}").format(sql.Identifier(fisica))
            )
        if linhas:
            todas_cols = [n for n, _ in COLUNAS_LINHAGEM] + colunas
            stmt = sql.SQL("INSERT INTO analise.{} ({}) VALUES ({})").format(
                sql.Identifier(fisica),
                sql.SQL(",").join(sql.Identifier(c) for c in todas_cols),
                sql.SQL(",").join(sql.Placeholder() for _ in todas_cols),
            )
            prefixo = (
                carga_id,
                arq.name,
                sha,
                tamanho,
                instante,
                corte_em,
                sujeito,
            )
            with conn.cursor() as cur:
                cur.executemany(
                    stmt,
                    [prefixo + tuple(row[c] for c in colunas) for row in linhas],
                )
        conn.execute(
            "INSERT INTO analise.pouso_carga VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                carga_id,
                "analise." + fisica,
                sujeito,
                arq.name,
                sha,
                tamanho,
                fmt,
                modo,
                len(linhas),
                corte_em,
                instante,
            ),
        )

    return {
        "carga_id": carga_id,
        "tabela": "analise." + fisica,
        "banco": "analise",
        "linhas": len(linhas),
        "fonte_arquivo": arq.name,
        "fonte_sha256": sha,
        "fonte_bytes": tamanho,
        "formato": fmt,
        "modo": modo,
        "corte_em": corte_em.isoformat(),
        "carregado_em": instante.isoformat(),
        "estado": "pronta",
    }
