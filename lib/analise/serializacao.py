"""CSV canônica: ordem tipada total, nulo distinto de NaN e UTC."""

from __future__ import annotations

import csv
import hashlib
import io
from datetime import UTC, datetime
from decimal import ROUND_HALF_EVEN, Decimal, InvalidOperation
from pathlib import Path

from . import Falha, exigir


def valor(texto: str, tipo: str, ser: dict) -> tuple[tuple, str]:
    if texto == str(ser["nulo"]):
        return (0, ""), str(ser["nulo"])
    if texto == str(ser["nan"]):
        exigir(tipo in {"real", "decimal"}, "nan-fora-de-numero", 4)
        return (2, ""), str(ser["nan"])
    try:
        if tipo == "uuid":
            import uuid

            v = str(uuid.UUID(texto))
            return (1, v), v
        if tipo == "inteiro":
            v = int(texto)
            return (1, v), str(v)
        if tipo in {"real", "decimal"}:
            v = Decimal(texto)
            exigir(v.is_finite(), "numero-nao-finito", 4)
            v = v.quantize(
                Decimal(1).scaleb(-ser["decimais"]), rounding=ROUND_HALF_EVEN
            )
            return (1, v), format(v, "f")
        if tipo == "instante":
            v = datetime.fromisoformat(texto.replace("Z", "+00:00"))
            exigir(v.tzinfo is not None, "instante-sem-fuso", 4)
            v = v.astimezone(UTC)
            return (1, v), v.isoformat(timespec="microseconds")
        if tipo == "data":
            from datetime import date

            v = date.fromisoformat(texto)
            return (1, v), v.isoformat()
        if tipo == "booleano":
            exigir(texto.lower() in {"true", "false"}, "booleano-invalido", 4)
            v = texto.lower()
            return (1, v), v
        return (1, texto), texto
    except (ValueError, InvalidOperation):
        raise Falha(4, "saida-tipo-invalido") from None


def canonizar(arquivo: Path, tabela: dict, ser: dict) -> dict:
    colunas = tabela["colunas"]
    nomes = [c["nome"] for c in colunas]
    registros = []
    try:
        with open(arquivo, newline="", encoding="utf-8") as f:
            leitor = csv.reader(f)
            exigir(next(leitor, None) == nomes, "saida-colunas-nao-declaradas", 4)
            for row in leitor:
                exigir(len(row) == len(nomes), "saida-linha-invalida", 4)
                pares = [valor(t, c["tipo"], ser) for t, c in zip(row, colunas)]
                chave = tuple(pares[nomes.index(n)][0] for n in tabela["ordem"])
                registros.append((chave, [p[1] for p in pares]))
    except (OSError, UnicodeError, csv.Error):
        raise Falha(4, "saida-csv-invalida") from None
    registros.sort(key=lambda p: p[0])
    exigir(
        all(a[0] != b[0] for a, b in zip(registros, registros[1:])),
        "ordem-sem-desempate",
        4,
    )
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(nomes)
    w.writerows(row for _, row in registros)
    conteudo = buf.getvalue().encode()
    return {
        "conteudo": conteudo,
        "linhas": len(registros),
        "bytes": len(conteudo),
        "sha256": hashlib.sha256(conteudo).hexdigest(),
    }


def conferir_sha(conteudo: bytes, esperado: str) -> None:
    exigir(hashlib.sha256(conteudo).hexdigest() == esperado, "base-adulterada", 5)
