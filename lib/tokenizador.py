"""Tokenizador da casa num lugar só, para a porta e a métrica (#4120).

Usa o tokenizador canônico qwen2.5 (terceiros/tokenizers/qwen2.5.json).
Se o módulo tokenizers ou o arquivo estiverem ausentes, recorre à estimativa
por bytes/4 declarada, para compatibilidade sem queda.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
TOKENIZADOR_PADRAO = (os.environ.get("PLATAFIRMA_TOKENIZADOR")
                      or str(RAIZ / "terceiros" / "tokenizers" / "qwen2.5.json"))

_CACHE_MEDIDOR: dict[str, tuple[Callable[[str], int], str]] = {}


def caminho_tokenizador() -> str:
    return os.environ.get("PLATAFIRMA_TOKENIZADOR") or TOKENIZADOR_PADRAO


def medidor(caminho: str | None = None) -> tuple[Callable[[str], int], str]:
    c = caminho or caminho_tokenizador()
    if c in _CACHE_MEDIDOR:
        return _CACHE_MEDIDOR[c]

    try:
        from tokenizers import Tokenizer
        if os.path.isfile(c):
            tk = Tokenizer.from_file(c)
            res = (lambda s: len(tk.encode(s).ids), "tokenizador qwen2.5")
            _CACHE_MEDIDOR[c] = res
            return res
        motivo = f"tokenizador ausente: {c}"
    except ImportError:
        motivo = "modulo `tokenizers` ausente"

    res = (lambda s: max(0 if not s else 1, len(s.encode("utf-8")) // 4),
           f"ESTIMATIVA por bytes/4 ({motivo})")
    _CACHE_MEDIDOR[c] = res
    return res


def conta_tokens(texto: str, caminho: str | None = None) -> tuple[int, str]:
    if not texto:
        _, metodo = medidor(caminho)
        return 0, metodo
    fn, metodo = medidor(caminho)
    return fn(texto), metodo
