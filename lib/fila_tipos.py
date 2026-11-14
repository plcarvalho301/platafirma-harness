"""Fonte unica dos tipos validos de mensagem da fila (ont:0082, DT 202)."""
from __future__ import annotations

TIPOS_VALIDOS: frozenset[str] = frozenset({
    "decisao",
    "resposta",
    "pedido",
    "minuta",
    "demanda",
    "handoff",
    "recusa",
    "contestacao",
})
