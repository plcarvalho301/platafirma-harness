"""despacho — cliente e borda comum para o ato `despachar` do core (card #4455, t6 e t11)."""
from __future__ import annotations

from .borda import (
    AmbienteBordaDespachar,
    PedidoBordaDespachar,
    PedidoBordaLerExecucao,
    converter_chamada_despachar,
    despachar_pela_borda,
    executar_ato,
    executar_despachar,
    executar_ler_execucao,
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
    "AmbienteBordaDespachar",
    "ConfigClienteDespacho",
    "DelegadorSuiteDespacho",
    "PedidoBordaDespachar",
    "PedidoBordaLerExecucao",
    "PedidoClienteDespacho",
    "RespostaClienteDespacho",
    "converter_chamada_despachar",
    "despachar_pela_borda",
    "despachar_pelo_core",
    "executar_ato",
    "executar_despachar",
    "executar_ler_execucao",
    "ler_execucao",
    "ler_execucao_pela_borda",
    "verbo_declara_despachar",
]
