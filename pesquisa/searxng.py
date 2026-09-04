"""Cliente do SearXNG — metabusca em fonte aberta (spec §4.1).

Na Doutrina de Inteligência (ABIN), isto é ação de COLETA, não "busca" — daí o ato se
chamar `consultar`, não `buscar` (spec §9.5, carta inteligencia). Chama o SearXNG local
(`format=json`), deduplica por URL canônica, devolve ~100 tokens por item.

O SearXNG é decisão do dono por mandato FOSS (§1). Categorias e engines ligados são
política do dono, publicada no `settings.yml` versionado (TI/dono) — este cliente serve
o que estiver declarado ali; não decide recorte.

`fetch` é injetável (testes passam um SearXNG falso; o default usa httpx). A base vem de
`PF_SEARXNG_URL` (default http://127.0.0.1:8888) — loopback, sem conta, sem chave.
"""

from __future__ import annotations

import os
from typing import Any, Callable
from urllib.parse import urlsplit, urlunsplit

from .envelope import FalhaFonte

BASE = os.environ.get("PF_SEARXNG_URL", "http://127.0.0.1:8888").rstrip("/")
CATEGORIAS = ("geral", "ciencia", "codigo", "social")
# nome interno -> categoria do SearXNG (settings.yml mapeia; aqui o default do §3.1)
CAT_SEARX = {
    "geral": "general",
    "ciencia": "science",
    "codigo": "it",
    "social": "social media",
}

Fetch = Callable[[str, dict], dict]


def _canoniza(url: str) -> str:
    """Chave de dedup: esquema+host+path sem fragmento nem barra final redundante."""
    p = urlsplit(url)
    host = (p.hostname or "").lower()
    porta = f":{p.port}" if p.port and p.port not in (80, 443) else ""
    caminho = p.path.rstrip("/") or "/"
    return urlunsplit((p.scheme.lower(), host + porta, caminho, p.query, ""))


def _fetch_httpx(base_url: str, params: dict) -> dict:
    import httpx  # local: mantém o módulo importável sem httpx no contrato

    try:
        r = httpx.get(base_url + "/search", params=params, timeout=20.0)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        raise FalhaFonte(f"searxng-fora:{type(exc).__name__}") from exc


def consultar(
    consulta: str,
    *,
    k: int = 8,
    categoria: str = "geral",
    desde: int | None = None,
    idioma: str = "auto",
    fetch: Fetch | None = None,
) -> dict[str, Any]:
    """Metabusca. Devolve {resultados, engines_ok, engines_falha}.

    Zero resultado NÃO é erro — é achado de não-achado, escrito no manifesto por quem
    chama (§4.1). Aqui só devolvemos `resultados: []` com os engines que responderam.
    """
    if categoria not in CATEGORIAS:
        raise FalhaFonte(f"categoria-desconhecida:{categoria}")
    params: dict[str, Any] = {
        "q": consulta,
        "format": "json",
        "categories": CAT_SEARX[categoria],
        "language": "auto" if idioma == "auto" else idioma,  # SearXNG 2026.9 recusa vazio (400)
        "pageno": 1,
    }
    if desde:
        params["time_range"] = "year"  # SearXNG só tem janelas; --desde filtra abaixo
    dados = (fetch or _fetch_httpx)(BASE, params)

    # SearXNG mudou de forma entre versões: instâncias antigas devolvem `engines`
    # (lista de {name,error}); a 2026.9 não devolve esse campo — quem respondeu está
    # em results[].engine e quem falhou em unresponsive_engines ([nome, motivo]).
    if "engines" in dados:
        engines_ok = sorted({e.get("name") for e in dados["engines"] if not e.get("error")} - {None})
        engines_falha = sorted({e.get("name") for e in dados["engines"] if e.get("error")} - {None})
    else:
        engines_ok = sorted({r.get("engine") for r in dados.get("results", [])} - {None})
        engines_falha = sorted(
            {(e[0] if isinstance(e, (list, tuple)) else e) for e in dados.get("unresponsive_engines", [])} - {None}
        )
    if not engines_ok and not dados.get("results"):
        # nenhum engine respondeu E nada veio: é fonte fora, não não-achado
        raise FalhaFonte("nenhum-engine-respondeu", engines_falha=engines_falha)

    vistos: set[str] = set()
    resultados: list[dict[str, Any]] = []
    for r in dados.get("results", []):
        url = r.get("url") or ""
        if not url:
            continue
        chave = _canoniza(url)
        if chave in vistos:
            continue
        vistos.add(chave)
        data = r.get("publishedDate") or r.get("pubdate")
        if desde and data:
            ano = str(data)[:4]
            if ano.isdigit() and int(ano) < desde:
                continue
        resultados.append(
            {
                "n": len(resultados) + 1,
                "titulo": (r.get("title") or "").strip(),
                "url": url,
                "trecho": (r.get("content") or "").strip(),
                "engines": r.get("engines") or ([r["engine"]] if r.get("engine") else []),
                "data": data,
                "dominio": (urlsplit(url).hostname or "").lower(),
            }
        )
        if len(resultados) >= k:
            break
    return {"resultados": resultados, "engines_ok": engines_ok, "engines_falha": engines_falha}
