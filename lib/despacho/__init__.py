"""despacho — cliente e borda da camada comum para o ato `despachar` do core (card #4455, t6/t11)."""
from __future__ import annotations

from .borda import (
    despachar_pela_borda,
    ler_execucao_pela_borda,
    verbo_declara_despachar,
)
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
    "despachar_pela_borda",
    "despachar_pelo_core",
    "ler_execucao",
    "ler_execucao_pela_borda",
    "verbo_declara_despachar",
]
