"""Compara procedência, entrada e cálculo, nesta ordem."""

from __future__ import annotations


def comparar(original: dict, nova: dict) -> tuple[int, str]:
    for camada, chaves in (
        ("ambiente", ("receita", "ambiente", "parametros", "semente")),
        ("entrada", ("entradas",)),
        ("calculo", ("saidas",)),
    ):
        for chave in chaves:
            a, b = original.get(chave), nova.get(chave)
            if chave in {"entradas", "saidas"}:
                a = {k: v["sha256"] for k, v in (a or {}).items()}
                b = {k: v["sha256"] for k, v in (b or {}).items()}
            if a != b:
                return 1, camada
    return 0, "iguais"
