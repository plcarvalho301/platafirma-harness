"""Cliente do leitor único via soquete UNIX com repetição única em queda de conexão (story #4442, t7)."""
from __future__ import annotations

import json
import os
import socket
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .daemon import SOCKET_PADRAO, enviar_quadro_json, receber_quadro_json
from .tipos import ContextoChamada, FiltroCatalogo, Recusa, SeletorParte

_MAX_TENTATIVAS = 2
_MARGEM_REPETICAO_S = 0.02


class ErroClienteLeitor(Exception):
    """Recusa estruturada de transporte ou resposta do leitor único."""

    def __init__(self, recusa: Recusa) -> None:
        self.recusa = recusa
        self.saida = recusa.saida
        super().__init__(recusa.codigo)


def _recusa_de_dict(d: Mapping[str, Any], saida: int) -> Recusa:
    return Recusa(
        saida=saida,
        codigo=str(d.get("codigo") or "morada-sem-resposta"),
        onde=str(d.get("onde") or "leitor"),
        recebido=str(d.get("recebido") or ""),
        regra=str(d.get("regra") or ""),
        cura=str(d.get("cura") or ""),
        proximo=str(d.get("proximo") or ""),
    )


def _recusa_indisponivel(caminho: Path, verbo: str, detalhe: str) -> Recusa:
    return Recusa(
        saida=3,
        codigo="morada-sem-resposta",
        onde="leitor",
        recebido=str(caminho),
        regra="disponibilidade-do-leitor-unico",
        cura=f"leitor único não respondeu em {caminho}: {detalhe}",
        proximo=f"{verbo} ler" if verbo else "",
    )


def _recusa_tempo_esgotado(caminho: Path, prazo_ms: int) -> Recusa:
    return Recusa(
        saida=5,
        codigo="tempo-esgotado",
        onde="leitor",
        recebido=str(caminho),
        regra="prazo-da-chamada",
        cura=f"leitor único excedeu o prazo total de {prazo_ms} ms",
        proximo="",
    )


def _contexto_para_dict(ctx: ContextoChamada, prazo_restante_ms: int) -> dict[str, Any]:
    return {
        "sujeito": ctx.sujeito,
        "sessao_id": ctx.sessao_id,
        "ordem_id": ctx.ordem_id,
        "verbo": ctx.verbo,
        "origem_autenticada": ctx.origem_autenticada,
        "origem_declarada": ctx.origem_declarada,
        "prazo_ms": max(50, prazo_restante_ms),
    }


def _seletor_para_dict(sel: SeletorParte) -> dict[str, Any]:
    d = asdict(sel)
    if sel.linhas is not None:
        d["linhas"] = list(sel.linhas)
    if sel.paginas is not None:
        d["paginas"] = list(sel.paginas)
    return d


class ClienteLeitor:
    """Envia pedidos `ler` e `listar` ao soquete do leitor único respeitando o prazo restante."""

    def __init__(self, socket_path: Path | str | None = None) -> None:
        env_sock = (os.environ.get("PF_LEITOR_SOCKET") or "").strip()
        if socket_path is not None:
            self._socket_path = Path(socket_path)
        elif env_sock:
            self._socket_path = Path(env_sock)
        else:
            self._socket_path = SOCKET_PADRAO

    @property
    def socket_path(self) -> Path:
        return self._socket_path

    def _enviar_uma_vez(self, payload: Mapping[str, Any], timeout_s: float) -> dict[str, Any]:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout_s)
            sock.connect(str(self._socket_path))
            enviar_quadro_json(sock, payload)
            return receber_quadro_json(sock, max_bytes=32 * 1024 * 1024)
        finally:
            sock.close()

    def enviar_pedido(
        self, contexto: ContextoChamada, forma: str, corpo: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Envia pedido com no máximo uma repetição em queda de conexão dentro do prazo restante."""
        prazo_total_ms = max(50, int(contexto.prazo_ms))
        deadline = time.monotonic() + (prazo_total_ms / 1000.0)
        ultimo_erro: Exception | None = None

        for tentativa in range(_MAX_TENTATIVAS):
            restante_s = deadline - time.monotonic()
            if restante_s <= 0:
                if ultimo_erro is not None:
                    raise ErroClienteLeitor(
                        _recusa_indisponivel(self._socket_path, contexto.verbo, str(ultimo_erro))
                    ) from None
                raise ErroClienteLeitor(
                    _recusa_tempo_esgotado(self._socket_path, prazo_total_ms)
                ) from None

            payload = {
                "forma": forma,
                "contexto": _contexto_para_dict(contexto, int(restante_s * 1000)),
                **dict(corpo),
            }
            try:
                return self._enviar_uma_vez(payload, restante_s)
            except TimeoutError:
                raise ErroClienteLeitor(
                    _recusa_tempo_esgotado(self._socket_path, prazo_total_ms)
                ) from None
            except (
                EOFError,
                BrokenPipeError,
                ConnectionResetError,
                ConnectionRefusedError,
                FileNotFoundError,
                OSError,
                ValueError,
                TypeError,
                json.JSONDecodeError,
            ) as exc:
                ultimo_erro = exc
                if tentativa + 1 < _MAX_TENTATIVAS and (deadline - time.monotonic()) > _MARGEM_REPETICAO_S:
                    continue
                raise ErroClienteLeitor(
                    _recusa_indisponivel(self._socket_path, contexto.verbo, str(exc))
                ) from None

        raise ErroClienteLeitor(
            _recusa_indisponivel(self._socket_path, contexto.verbo, str(ultimo_erro))
        )

    def ler(
        self,
        contexto: ContextoChamada,
        chaves: Sequence[str],
        *,
        classe: str | None = None,
        seletor: SeletorParte | None = None,
        pesada: bool = False,
    ) -> dict[str, Any]:
        """Executa a forma `ler` (unitária ou multi-chave) no leitor único."""
        corpo: dict[str, Any] = {
            "chaves": list(chaves),
            "classe": classe,
            "seletor": _seletor_para_dict(seletor or SeletorParte()),
            "pesada": pesada,
        }
        return self.enviar_pedido(contexto, "ler", corpo)

    def listar(  # noqa: PLR0913 -- parâmetros da forma listar no cliente do leitor
        self,
        contexto: ContextoChamada,
        classe: str,
        *,
        filtros: Sequence[FiltroCatalogo] = (),
        termo: str | None = None,
        limite: int = 100,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """Executa a forma `listar` no leitor único."""
        corpo: dict[str, Any] = {
            "classe": classe,
            "filtros": [{"tipo": f.tipo, "nome": f.nome, "valor": f.valor} for f in filtros],
            "termo": termo,
            "limite": limite,
            "cursor": cursor,
        }
        return self.enviar_pedido(contexto, "listar", corpo)
