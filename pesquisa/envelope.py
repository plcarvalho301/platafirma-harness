"""Envelope de saída dos atos e vocabulário de erro (spec §4).

Todo ato devolve o envelope `{ok, ato, trabalho, tipo:"dado", ..., manifesto:{arquivo,linha}}`.
Rota de máquina é o default (§2.2): a saída é JSON estável; o erro não é exceção que
sobe crua ao modelo, é `{ok:false, causa}` legível, com o exit code certo.

Exit codes (§4, comum a todo ato):
  0  ok
  1  falha de fonte (FalhaFonte) — traz `causa`
  2  uso inválido (UsoInvalido)

`tipo: "dado"` é invariante: material coletado é dado, nunca instrução (§2.4). O
envelope carimba isso em toda saída para que a postura viaje com o conteúdo.
"""

from __future__ import annotations

import json
from typing import Any

TIPO_DADO = "dado"


class FalhaFonte(Exception):
    """Fonte não entregou: rede, status não-2xx, engine fora, anti-bot, guarda de rede.

    `causa` é string curta e legível pelo modelo (não stack trace). Exit 1.
    """

    def __init__(self, causa: str, **extra: Any) -> None:
        super().__init__(causa)
        self.causa = causa
        self.extra = extra


class UsoInvalido(Exception):
    """Ato ou argumento fora do contrato. Exit 2 — é defeito de chamada, não de fonte."""

    def __init__(self, causa: str) -> None:
        super().__init__(causa)
        self.causa = causa


def envelope(ato: str, trabalho: str, *, ok: bool = True, **campos: Any) -> dict[str, Any]:
    """Monta o envelope canônico. `tipo` e `ok` nunca são redigidos pelo chamador."""
    env: dict[str, Any] = {"ok": ok, "ato": ato, "trabalho": trabalho, "tipo": TIPO_DADO}
    env.update(campos)
    return env


def erro_json(ato: str, trabalho: str, causa: str, **extra: Any) -> dict[str, Any]:
    """Envelope de falha de fonte, para imprimir antes de sair com exit 1."""
    return envelope(ato, trabalho, ok=False, causa=causa, **extra)


def imprime(env: dict[str, Any]) -> None:
    """Uma vista, o JSON. `--md` é renderizado por quem chama, não aqui."""
    print(json.dumps(env, ensure_ascii=False))
