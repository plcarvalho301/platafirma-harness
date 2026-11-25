"""Cliente da camada comum sobre o soquete AF_UNIX do escritor único."""
from __future__ import annotations

import base64
import os
import socket
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .moradas import proximo_repeticao_pedido
from .politica import PoliticaEscrita
from .servidor import escrever_quadro, ler_quadro
from .tipos import (
    ContextoEscrita,
    ErroEscrita,
    PedidoEscrita,
    RecusaEscrita,
    ResultadoEscrita,
)

_SOCKET_PADRAO = Path("/run/platafirma/escritor.sock")
_FOLGA_PADRAO_S = 2.0
_TIMEOUT_SAUDE_PADRAO_S = 2.0
_TETO_RESPOSTA_BYTES = 512 * 1024


@dataclass(frozen=True)
class ConfigCliente:
    """Parâmetros de transporte do cliente do escritor único."""

    politica: PoliticaEscrita
    socket_path: Path | None = None
    folga_s: float = _FOLGA_PADRAO_S


def socket_padrao() -> Path:
    """Resolve o caminho do soquete do escritor único."""
    env = (os.environ.get("PF_ESCRITOR_SOCKET") or "").strip()
    return Path(env) if env else _SOCKET_PADRAO


def _erro_conexao_antes_envio(caminho: Path, exc: OSError) -> RecusaEscrita:
    if isinstance(exc, PermissionError):
        return RecusaEscrita(
            ErroEscrita(
                saida=4,
                codigo="acesso-negado",
                onde="soquete",
                recebido=str(caminho),
                regra="processo chamador não tem permissão para conectar ao soquete do escritor",
                cura="verifique a filiação ao grupo platafirma-escrita e reinicie a porta",
                proximo="",
            )
        )
    return RecusaEscrita(
        ErroEscrita(
            saida=3,
            codigo="escritor-indisponivel",
            onde="soquete",
            recebido=f"{caminho}: {exc}",
            regra="escritor único indisponível antes do envio da chamada sai 3",
            cura="verifique o estado da unidade escritor.socket e escritor.service",
            proximo="",
        )
    )


def _erro_apos_envio(pedido: PedidoEscrita, codigo: str, detalhe: str) -> RecusaEscrita:
    if pedido.forma == "ensaiar":
        return RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="morada-sem-resposta",
                onde="soquete",
                recebido=detalhe,
                regra="ensaio interrompido não altera estado e sai 3",
                cura="repita o ensaio quando o escritor responder",
                proximo="",
            )
        )
    classe = pedido.classe or pedido.contexto.classe_unica or "componente"
    return RecusaEscrita(
        ErroEscrita(
            saida=5,
            codigo=codigo,
            onde="soquete",
            recebido=detalhe,
            regra="falha após o envio da escrita torna o desfecho indeterminável",
            cura="repita a chamada com o mesmo --pedido para dedup seguro",
            proximo=proximo_repeticao_pedido(pedido, classe),
        )
    )


def _reconstruir_recusa(payload: Mapping[str, Any], saida_padrao: int) -> RecusaEscrita:
    erros_raw = payload.get("erros")
    erros: list[ErroEscrita] = []
    if isinstance(erros_raw, list):
        for item in erros_raw:
            if not isinstance(item, Mapping):
                continue
            codigo = str(item.get("codigo") or "escritor-indisponivel")
            erros.append(
                ErroEscrita(
                    saida=saida_padrao,
                    codigo=codigo,
                    onde=str(item.get("onde") or ""),
                    recebido=str(item.get("recebido") or ""),
                    regra=str(item.get("regra") or ""),
                    cura=str(item.get("cura") or ""),
                    proximo=str(item.get("proximo") or ""),
                )
            )
    if erros:
        return RecusaEscrita(erros)
    return RecusaEscrita(
        ErroEscrita(
            saida=3,
            codigo="escritor-indisponivel",
            onde="soquete",
            recebido="payload de recusa vazio",
            regra="resposta de erro do escritor deve trazer ao menos um erro estruturado",
            cura="verifique os logs do escritor único",
            proximo="",
        )
    )


def _reconstruir_resultado(dados: Mapping[str, Any]) -> ResultadoEscrita:
    return ResultadoEscrita(
        chave=str(dados["chave"]),
        classe=str(dados["classe"]),
        forma=str(dados["forma"]),
        morada=str(dados["morada"]),
        release=str(dados.get("release") or ""),
        pedido=str(dados["pedido"]),
        alterou=bool(dados["alterou"]),
        ja_gravado=bool(dados["ja_gravado"]),
        substituiu=bool(dados["substituiu"]),
        bytes=int(dados["bytes"]),
        versao=dados.get("versao"),
        versao_completa=dados.get("versao_completa"),
        versao_anterior=dados.get("versao_anterior"),
        ocorrencias=dados.get("ocorrencias"),
        hunks_aplicados=dados.get("hunks_aplicados"),
        desfazer=dados.get("desfazer"),
        ensaiado=bool(dados.get("ensaiado", False)),
        mudaria=dados.get("mudaria"),
        fornada=dados.get("fornada"),
    )


def _garantir_pedido_em_argv(argv: Sequence[str], pedido_id: str) -> list[str]:
    lista = list(argv)
    if "--pedido" in lista:
        return lista
    return [*lista, "--pedido", pedido_id]


def _prazo_restante_s(contexto: ContextoEscrita, politica: PoliticaEscrita) -> float:
    if contexto.prazo_ns <= 0:
        return float(politica.prazo_max_s)
    restante_ns = contexto.prazo_ns - time.monotonic_ns()
    if restante_ns <= 0:
        raise RecusaEscrita(
            ErroEscrita(
                saida=3,
                codigo="escritor-indisponivel",
                onde="prazo",
                recebido="prazo esgotado antes de conectar ao escritor",
                regra="chamada expirada antes do ponto de não volta sai 3",
                cura="repita a chamada com prazo suficiente",
                proximo="",
            )
        )
    return min(restante_ns / 1_000_000_000.0, float(politica.prazo_max_s))


def consultar_saude(
    socket_path: Path | None = None,
    *,
    timeout_s: float = _TIMEOUT_SAUDE_PADRAO_S,
) -> dict[str, Any]:
    """Envia quadro `saude` ao soquete do escritor único e devolve a resposta."""
    caminho = socket_padrao() if socket_path is None else Path(socket_path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(max(0.05, timeout_s))
    try:
        try:
            sock.connect(str(caminho))
        except OSError as exc:
            raise _erro_conexao_antes_envio(caminho, exc) from exc
        try:
            escrever_quadro(sock, {"tipo": "saude"})
            resp = ler_quadro(sock, teto_bytes=_TETO_RESPOSTA_BYTES)
        except (OSError, ValueError, TypeError, EOFError) as exc:
            raise RecusaEscrita(
                ErroEscrita(
                    saida=3,
                    codigo="escritor-indisponivel",
                    onde="soquete",
                    recebido=str(exc),
                    regra="escritor não respondeu ao quadro de saúde",
                    cura="verifique o estado da unidade escritor.service",
                    proximo="",
                )
            ) from exc
        if not resp.get("ok"):
            raise _reconstruir_recusa(resp.get("payload") or {}, int(resp.get("exit_code") or 3))
        return resp
    finally:
        sock.close()


def enviar_escrita(
    pedido: PedidoEscrita,
    argv: Sequence[str],
    stdin_bytes: bytes | None,
    config: ConfigCliente,
) -> ResultadoEscrita:
    """Envia um pedido já validado na borda ao daemon do escritor único."""
    caminho = socket_padrao() if config.socket_path is None else Path(config.socket_path)
    prazo_s = _prazo_restante_s(pedido.contexto, config.politica)
    stdin_b64 = (
        base64.b64encode(stdin_bytes).decode("ascii") if stdin_bytes is not None else None
    )
    quadro = {
        "tipo": "escrever",
        "verbo": pedido.verbo,
        "argv": _garantir_pedido_em_argv(argv, pedido.pedido),
        "stdin_b64": stdin_b64,
        "prazo_restante_s": prazo_s,
        "contexto": {
            "cadeira": pedido.contexto.cadeira,
            "sujeito": pedido.contexto.sujeito,
            "sessao_id": pedido.contexto.sessao_id,
            "ordem_id": pedido.contexto.ordem_id,
            "card": pedido.contexto.card,
            "token": pedido.contexto.token,
            "classe_unica": pedido.contexto.classe_unica,
            "exige_objeto_casa": pedido.contexto.exige_objeto_casa,
        },
    }
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.settimeout(max(0.05, prazo_s))
        try:
            sock.connect(str(caminho))
        except OSError as exc:
            raise _erro_conexao_antes_envio(caminho, exc) from exc

        try:
            escrever_quadro(sock, quadro)
        except OSError as exc:
            raise _erro_apos_envio(pedido, "resposta-perdida", str(exc)) from exc

        sock.settimeout(max(0.05, prazo_s + max(0.0, config.folga_s)))
        try:
            resp = ler_quadro(sock, teto_bytes=_TETO_RESPOSTA_BYTES)
        except TimeoutError as exc:
            raise _erro_apos_envio(pedido, "tempo-esgotado", str(exc)) from exc
        except (OSError, ValueError, TypeError, EOFError) as exc:
            raise _erro_apos_envio(pedido, "resposta-perdida", str(exc)) from exc
    finally:
        sock.close()

    if not resp.get("ok"):
        raise _reconstruir_recusa(resp.get("payload") or {}, int(resp.get("exit_code") or 3))
    return _reconstruir_resultado(resp["resultado"])


__all__ = [
    "ConfigCliente",
    "consultar_saude",
    "enviar_escrita",
    "socket_padrao",
]
