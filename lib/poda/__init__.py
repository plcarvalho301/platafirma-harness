"""Poda e derrame de retornos no harness (story #4342, task t3).

Executável por processo via `python -m poda` a partir de `outros_repos/harness/lib`,
sem importação pelo processo da porta no core.
"""
from __future__ import annotations

from .poda import (
    CAP_PADRAO,
    LedgerSessao,
    atos_que_escrevem,
    corta,
    derrama,
    eh_cosmetica,
    eh_escrita,
    lavar,
    linha_humana,
    perfil_verbo,
    podar_envelope,
    podar_texto,
    resolver_ato,
    sha_servido,
)

__all__ = [
    "CAP_PADRAO",
    "LedgerSessao",
    "atos_que_escrevem",
    "corta",
    "derrama",
    "eh_cosmetica",
    "eh_escrita",
    "lavar",
    "linha_humana",
    "perfil_verbo",
    "podar_envelope",
    "podar_texto",
    "resolver_ato",
    "sha_servido",
]
