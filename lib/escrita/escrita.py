"""Fachada da camada comum do ato escrever."""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .cliente import ConfigCliente, enviar_escrita
from .pedido import parsear_pedido
from .politica import PoliticaEscrita, carregar_politica, verbo_ligado
from .tipos import (
    ContextoEscrita,
    ErroEscrita,
    PedidoEscrita,
    RecusaEscrita,
    ResultadoEscrita,
)


@dataclass(frozen=True)
class OpcoesExecucao:
    """Opções de despacho da fachada da camada comum do ato escrever."""

    contexto: ContextoEscrita | None = None
    politica: PoliticaEscrita | None = None
    socket_path: Path | None = None
    folga_s: float = 2.0
    fallback_desligado: Callable[[PedidoEscrita], ResultadoEscrita] | None = None


def verbo_esta_ligado(verbo: str, *, politica: PoliticaEscrita | None = None) -> bool:
    """Informa se o verbo está ativado em `registro/escrita.yaml`."""
    pol = carregar_politica() if politica is None else politica
    return verbo_ligado(pol, verbo)


def executar_ato_escrever(
    verbo: str,
    argv: Sequence[str],
    stdin_bytes: bytes | None,
    *,
    opcoes: OpcoesExecucao | None = None,
) -> ResultadoEscrita:
    """Ponto único da camada comum: valida na borda e delega ao escritor quando ligado."""
    opt = OpcoesExecucao() if opcoes is None else opcoes
    pol = carregar_politica() if opt.politica is None else opt.politica
    ctx = ContextoEscrita(verbo=verbo) if opt.contexto is None else opt.contexto
    pedido = parsear_pedido(verbo, argv, stdin_bytes, politica=pol, contexto=ctx)
    if not verbo_ligado(pol, verbo):
        if opt.fallback_desligado is not None:
            return opt.fallback_desligado(pedido)
        raise RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="escritor-indisponivel",
                onde="verbos_ligados",
                recebido=verbo,
                regra=f"verbo {verbo} ainda não está ligado ao escritor em registro/escrita.yaml",
                cura="use o caminho legado do verbo ou ative o verbo em registro/escrita.yaml",
                proximo="",
            )
        )
    cfg = ConfigCliente(politica=pol, socket_path=opt.socket_path, folga_s=opt.folga_s)
    return enviar_escrita(pedido, argv, stdin_bytes, cfg)


__all__ = [
    "OpcoesExecucao",
    "executar_ato_escrever",
    "verbo_esta_ligado",
]
