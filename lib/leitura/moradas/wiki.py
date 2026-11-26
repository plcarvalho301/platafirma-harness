"""Adaptador da morada `wiki` (MediaWiki interna) do componente leitura."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from typing import Any

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

_WIKI_API_PADRAO = "http://127.0.0.1:8080/api.php"

ClienteHttpWiki = Callable[[str, Mapping[str, str], float], dict[str, Any]]


def _requisitar_wiki_padrao(
    url_base: str, params: Mapping[str, str], timeout_s: float
) -> dict[str, Any]:
    url = f"{url_base}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        bruto = resp.read()
    dados = json.loads(bruto.decode("utf-8"))
    if not isinstance(dados, dict):
        raise TypeError("resposta inesperada da MediaWiki")
    return dados


def _titulo_do_alvo(alvo: AlvoResolvido) -> str:
    return alvo.endereco.split(":", 1)[1] if ":" in alvo.endereco else alvo.endereco


def _extrair_revisao(dados: Mapping[str, Any]) -> tuple[str, str] | None:
    query = dados.get("query")
    pages = query.get("pages") if isinstance(query, Mapping) else None
    if not isinstance(pages, Mapping) or not pages:
        return None
    pagina = next(iter(pages.values()))
    if not isinstance(pagina, Mapping) or "missing" in pagina:
        return None
    revs = pagina.get("revisions")
    if not isinstance(revs, list) or not revs or not isinstance(revs[0], Mapping):
        return None
    rev = revs[0]
    revid = str(rev.get("revid") or "")
    slots = rev.get("slots")
    if isinstance(slots, Mapping) and isinstance(slots.get("main"), Mapping):
        texto = str(slots["main"].get("content") or slots["main"].get("*") or "")
    else:
        texto = str(rev.get("content") or rev.get("*") or "")
    return (revid, texto) if revid else None


class AdaptadorWiki:
    """Lê páginas publicadas e lista títulos pela interface HTTP interna da MediaWiki."""

    def __init__(
        self,
        *,
        url_api: str | None = None,
        cliente_http: ClienteHttpWiki | None = None,
    ) -> None:
        self._url = url_api or os.environ.get("WIKI_API_URL", _WIKI_API_PADRAO)
        self._http = cliente_http or _requisitar_wiki_padrao

    def _chamar(
        self, params: Mapping[str, str], prazo_ms: int, recebido: str, proximo: str
    ) -> dict[str, Any]:
        timeout_s = max(0.05, prazo_ms / 1000.0)
        try:
            return self._http(self._url, params, timeout_s)
        except TimeoutError as exc:
            raise ErroMorada(
                Recusa(
                    saida=5,
                    codigo="tempo-esgotado",
                    onde="morada:wiki",
                    recebido=recebido,
                    regra="prazo-da-chamada",
                    cura=f"wiki excedeu o prazo de {prazo_ms} ms ({exc})",
                    proximo=proximo,
                )
            ) from None
        except (urllib.error.URLError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ErroMorada(
                Recusa(
                    saida=3,
                    codigo="morada-sem-resposta",
                    onde="morada:wiki",
                    recebido=recebido,
                    regra="disponibilidade-morada-wiki",
                    cura=f"interface interna da MediaWiki indisponível: {exc}",
                    proximo=proximo,
                )
            ) from None

    def ler_objeto(
        self, alvo: AlvoResolvido, seletor: SeletorParte, prazo_ms: int
    ) -> ObjetoBruto:
        titulo = _titulo_do_alvo(alvo)
        params: dict[str, str] = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "ids|content",
            "rvslots": "main",
            "format": "json",
        }
        if seletor.versao_pedida:
            params["revids"] = seletor.versao_pedida
        else:
            params["titles"] = titulo

        dados = self._chamar(
            params, prazo_ms, alvo.chave_pedida, f"acervo ler {alvo.chave_pedida}"
        )
        par = _extrair_revisao(dados)
        if par is None:
            raise ErroMorada(
                Recusa(
                    saida=1,
                    codigo="chave-inexistente",
                    onde="morada:wiki",
                    recebido=alvo.chave_pedida,
                    regra="pagina-existente-na-wiki",
                    cura=f"página {titulo!r} não encontrada na MediaWiki (universo aberto)",
                    proximo=f"busca buscar {titulo}",
                )
            )
        revid, texto = par
        conteudo_bytes = texto.encode("utf-8")
        return ObjetoBruto(
            alvo=alvo,
            versao=revid,
            dados=conteudo_bytes,
            nome_arquivo=f"{titulo}.wiki",
            total_bytes=len(conteudo_bytes),
        )

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, classe: str, filtros: Sequence[FiltroCatalogo], termo: str | None,
        limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        del filtros
        params: dict[str, str] = {
            "action": "query",
            "list": "allpages",
            "aplimit": str(max(1, limite) + 1),
            "format": "json",
        }
        if cursor is not None and cursor.ultima_chave:
            params["apfrom"] = cursor.ultima_chave.split(":", 1)[-1]

        dados = self._chamar(params, prazo_ms, f"listar:{classe}", f"acervo listar {classe}")
        brutas = (dados.get("query") or {}).get("allpages") or []
        termo_n = normalizar_termo(termo) if termo else None

        itens: list[dict[str, str]] = []
        for pg in brutas:
            if not isinstance(pg, Mapping):
                continue
            titulo = str(pg.get("title") or "")
            if not titulo:
                continue
            chave = f"{classe}:{titulo}"
            if termo_n and termo_n not in normalizar_termo(chave):
                continue
            itens.append({"chave": chave, "rotulo": titulo, "resumo_curto": ""})

        return montar_pagina_bruta(
            classe, itens, limite=limite, cursor=cursor, universo_fechado=False
        )
