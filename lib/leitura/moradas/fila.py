"""Adaptador da morada `fila` (Valkey sem consumo, lousa e execuções)."""
from __future__ import annotations

import contextvars
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from ..tipos import (
    AlvoResolvido,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    Recusa,
    SeletorParte,
)
from . import ErroMorada, montar_pagina_bruta, normalizar_termo

SUJEITO_ATUAL: contextvars.ContextVar[str] = contextvars.ContextVar(
    "pf_leitor_sujeito", default=""
)

try:
    import redis as _redis_mod

    _ERROS_VALKEY: tuple[type[BaseException], ...] = (
        OSError,
        TimeoutError,
        RuntimeError,
        ValueError,
        TypeError,
        _redis_mod.RedisError,
    )
except ImportError:  # pragma: no cover
    _ERROS_VALKEY = (OSError, TimeoutError, RuntimeError, ValueError, TypeError)


class ClienteValkeyLeitura(Protocol):
    """Subconjunto estritamente somente leitura de Valkey/Redis (nunca XREADGROUP/XACK)."""

    def xrange(
        self, name: str, min: str = "-", max: str = "+", count: int | None = None
    ) -> list[tuple[str, Mapping[str, Any]]]: ...

    def get(self, name: str) -> str | bytes | None: ...

    def scan_iter(self, match: str | None = None) -> Sequence[str]: ...


def _slug(alvo: AlvoResolvido) -> str:
    return alvo.endereco.split(":", 1)[1] if ":" in alvo.endereco else alvo.endereco


def _decodificar_json(bruto: str | bytes | None) -> Any:
    if bruto is None:
        return None
    texto = bruto.decode("utf-8") if isinstance(bruto, bytes) else str(bruto)
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return texto


def _conectar_valkey_padrao(host: str, porta: int, prazo_ms: int) -> Any:
    try:
        import redis
    except ImportError as exc:
        raise ErroMorada(
            Recusa(
                saida=3,
                codigo="morada-sem-resposta",
                onde="morada:fila",
                recebido=f"{host}:{porta}",
                regra="cliente-valkey-instalado",
                cura=f"cliente redis/valkey ausente: {exc}",
                proximo="",
            )
        ) from None
    timeout_s = max(0.05, prazo_ms / 1000.0)
    return redis.Redis(
        host=host,
        port=porta,
        decode_responses=True,
        socket_timeout=timeout_s,
        socket_connect_timeout=min(2.0, timeout_s),
    )


def _erro_indisponivel(exc: Exception, recebido: str) -> ErroMorada:
    if isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower():
        return ErroMorada(
            Recusa(
                saida=5,
                codigo="tempo-esgotado",
                onde="morada:fila",
                recebido=recebido,
                regra="prazo-da-chamada",
                cura=f"Valkey excedeu o prazo da chamada: {exc}",
                proximo="",
            )
        )
    return ErroMorada(
        Recusa(
            saida=3,
            codigo="morada-sem-resposta",
            onde="morada:fila",
            recebido=recebido,
            regra="disponibilidade-morada-fila",
            cura=f"Valkey indisponível: {exc}",
            proximo="",
        )
    )


def _recusa_acesso_execucao(chave: str) -> ErroMorada:
    return ErroMorada(
        Recusa(
            saida=4,
            codigo="acesso-negado",
            onde="morada:fila",
            recebido=chave,
            regra="isolamento-execucao-por-sujeito",
            cura="execução pertence a outro sujeito ou não é acessível por esta sessão",
            proximo="",
        )
    )


class AdaptadorFila:
    """Lê mensagens por XRANGE (sem avançar consumo), lousa e execuções filtradas por sujeito."""

    def __init__(
        self,
        *,
        cliente: ClienteValkeyLeitura | None = None,
        host: str | None = None,
        porta: int | None = None,
        stream_padrao: str = "fila:mensagens",
        sujeito: str | None = None,
    ) -> None:
        self._cliente = cliente
        self._host = host or os.environ.get("FILA_REDIS_HOST", "127.0.0.1")
        self._porta = int(porta or os.environ.get("FILA_REDIS_PORT", "6379"))
        self._stream_padrao = stream_padrao
        self._sujeito_fixo = sujeito

    def _obter_sujeito(self) -> str:
        return self._sujeito_fixo if self._sujeito_fixo is not None else SUJEITO_ATUAL.get("")

    def _obter_cliente(self, prazo_ms: int) -> Any:
        if self._cliente is not None:
            return self._cliente
        return _conectar_valkey_padrao(self._host, self._porta, prazo_ms)

    def _ler_mensagem(self, cli: Any, alvo: AlvoResolvido) -> tuple[str, dict[str, Any]]:
        slug = _slug(alvo)
        stream, entry_id = slug.split("/", 1) if "/" in slug else (self._stream_padrao, slug)
        entradas = cli.xrange(stream, min=entry_id, max=entry_id, count=1)
        if not entradas:
            raise ErroMorada(
                Recusa(
                    saida=1,
                    codigo="chave-inexistente",
                    onde="morada:fila",
                    recebido=alvo.chave_pedida,
                    regra="mensagem-existente-na-fila",
                    cura=f"mensagem {entry_id!r} não encontrada no stream {stream!r}",
                    proximo="fila listar mensagem",
                )
            )
        eid, campos = entradas[0]
        return str(eid), {"id": str(eid), "stream": stream, "campos": dict(campos)}

    def _ler_lousa(self, cli: Any, alvo: AlvoResolvido) -> tuple[str, Any]:
        slug = _slug(alvo)
        bruto = cli.get(f"lousa:{slug}")
        if bruto is None:
            raise ErroMorada(
                Recusa(
                    saida=1,
                    codigo="chave-inexistente",
                    onde="morada:fila",
                    recebido=alvo.chave_pedida,
                    regra="lousa-existente",
                    cura=f"lousa {slug!r} não encontrada",
                    proximo="mesa listar lousa",
                )
            )
        obj = _decodificar_json(bruto)
        serial = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(serial).hexdigest()[:16], obj

    def _ler_execucao(self, cli: Any, alvo: AlvoResolvido) -> tuple[str, dict[str, Any]]:
        slug = _slug(alvo)
        sujeito = self._obter_sujeito()
        obj = _decodificar_json(cli.get(f"execucao:{slug}"))
        if not isinstance(obj, Mapping):
            raise _recusa_acesso_execucao(alvo.chave_pedida)
        dono = str(obj.get("sujeito") or obj.get("dono") or "")
        if not sujeito or dono != sujeito:
            raise _recusa_acesso_execucao(alvo.chave_pedida)
        versao = str(obj.get("versao") or "")
        if not versao:
            serial = json.dumps(dict(obj), sort_keys=True, ensure_ascii=False).encode("utf-8")
            versao = hashlib.sha256(serial).hexdigest()[:16]
        return versao, dict(obj)

    def ler_objeto(
        self, alvo: AlvoResolvido, seletor: SeletorParte, prazo_ms: int
    ) -> ObjetoBruto:
        cli = self._obter_cliente(prazo_ms)
        try:
            if alvo.classe == "mensagem":
                versao, corpo_obj = self._ler_mensagem(cli, alvo)
            elif alvo.classe == "lousa":
                versao, corpo_obj = self._ler_lousa(cli, alvo)
            elif alvo.classe == "execucao":
                versao, corpo_obj = self._ler_execucao(cli, alvo)
            else:
                raise ErroMorada(
                    Recusa(
                        saida=1,
                        codigo="chave-inexistente",
                        onde="morada:fila",
                        recebido=alvo.chave_pedida,
                        regra="classe-suportada-em-fila",
                        cura=f"classe {alvo.classe!r} não suportada na morada fila",
                        proximo="",
                    )
                )
        except ErroMorada:
            raise
        except _ERROS_VALKEY as exc:
            raise _erro_indisponivel(exc, alvo.chave_pedida) from None

        if seletor.versao_pedida and seletor.versao_pedida != versao:
            raise ErroMorada(
                Recusa(
                    saida=2,
                    codigo="versao-divergente",
                    onde="--versao",
                    recebido=seletor.versao_pedida,
                    regra="versao-vigente-na-morada-fila",
                    cura=f"a versão vigente é {versao}, diferente de {seletor.versao_pedida}",
                    proximo=f"fila ler {alvo.chave_pedida}",
                )
            )
        dados = json.dumps(corpo_obj, sort_keys=True, ensure_ascii=False, indent=2).encode("utf-8")
        return ObjetoBruto(
            alvo=alvo,
            versao=versao,
            dados=dados,
            nome_arquivo=f"{alvo.classe}.json",
            total_bytes=len(dados),
        )

    def _coletar_execucoes(self, cli: Any) -> list[dict[str, str]]:
        sujeito = self._obter_sujeito()
        if not sujeito:
            return []
        itens: list[dict[str, str]] = []
        for k in cli.scan_iter("execucao:*"):
            obj = _decodificar_json(cli.get(str(k)))
            if not isinstance(obj, Mapping):
                continue
            dono = str(obj.get("sujeito") or obj.get("dono") or "")
            if dono != sujeito:
                continue
            slug = str(k).split(":", 1)[1]
            itens.append(
                {
                    "chave": f"execucao:{slug}",
                    "rotulo": str(obj.get("rotulo") or slug),
                    "resumo_curto": str(obj.get("estado") or ""),
                }
            )
        return itens

    def _coletar_itens_lista(self, cli: Any, classe: str) -> list[dict[str, str]]:
        if classe == "mensagem":
            return [
                {
                    "chave": f"mensagem:{eid}",
                    "rotulo": str(campos.get("assunto") or campos.get("tipo") or eid),
                    "resumo_curto": "",
                }
                for eid, campos in cli.xrange(self._stream_padrao, "-", "+")
            ]
        if classe == "lousa":
            return [
                {
                    "chave": f"lousa:{str(k).split(':', 1)[1]}",
                    "rotulo": str(k).split(":", 1)[1],
                    "resumo_curto": "",
                }
                for k in cli.scan_iter("lousa:*")
            ]
        if classe == "execucao":
            return self._coletar_execucoes(cli)
        return []

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, classe: str, filtros: Sequence[FiltroCatalogo], termo: str | None,
        limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        del filtros
        cli = self._obter_cliente(prazo_ms)
        try:
            todos = self._coletar_itens_lista(cli, classe)
        except ErroMorada:
            raise
        except _ERROS_VALKEY as exc:
            raise _erro_indisponivel(exc, f"listar:{classe}") from None

        if termo:
            termo_n = normalizar_termo(termo)
            todos = [
                it
                for it in todos
                if termo_n in normalizar_termo(it["chave"]) or termo_n in normalizar_termo(it["rotulo"])
            ]

        return montar_pagina_bruta(
            classe, todos, limite=limite, cursor=cursor, universo_fechado=True
        )
