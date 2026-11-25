"""Ponto de entrada da camada comum dos verbos para o ato escrever."""
from __future__ import annotations

from .cliente import ConfigCliente, consultar_saude, enviar_escrita, socket_padrao
from .escrita import (
    OpcoesExecucao,
    aplicar_hunks,
    escrever,
    executar_ato_escrever,
    parse_patch,
    verbo_esta_ligado,
)
from .tipos import (
    ContextoEscrita,
    ErroEscrita,
    PedidoEscrita,
    RecusaEscrita,
    ResultadoEscrita,
    emitir_recusa,
)

__all__ = [
    "ConfigCliente",
    "ContextoEscrita",
    "ErroEscrita",
    "OpcoesExecucao",
    "PedidoEscrita",
    "RecusaEscrita",
    "ResultadoEscrita",
    "aplicar_hunks",
    "consultar_saude",
    "emitir_recusa",
    "enviar_escrita",
    "escrever",
    "executar_ato_escrever",
    "parse_patch",
    "socket_padrao",
    "verbo_esta_ligado",
]
