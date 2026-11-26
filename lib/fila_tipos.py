"""Fonte unica dos tipos validos de mensagem da fila."""
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

# Cartas informativas nao pedem ato/volta da cadeira destinataria (#4432):
# recebem XACK na entrega e nao ficam presas na PEL nem entram como penduradas na pauta.
TIPOS_INFORMATIVOS: frozenset[str] = frozenset({
    "resposta",
    "decisao",
    "handoff",
    "recusa",
})

TIPOS_ACIONAVEIS: frozenset[str] = TIPOS_VALIDOS - TIPOS_INFORMATIVOS
