"""despacho — cliente da camada comum para o ato `despachar` do core (card #4455, t6)."""
from __future__ import annotations

from .cliente import (
    ConfigClienteDespacho,
    PedidoClienteDespacho,
    RespostaClienteDespacho,
    despachar_pelo_core,
)
from .execucao import ler_execucao
from .suite import DelegadorSuiteDespacho

__all__ = [
    "ConfigClienteDespacho",
    "DelegadorSuiteDespacho",
    "PedidoClienteDespacho",
    "RespostaClienteDespacho",
    "despachar_pelo_core",
    "ler_execucao",
]
