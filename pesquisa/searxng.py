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

# /config do SearXNG, uma vez por processo: 271 engines com `enabled` e `categories`,
# 18ms em loopback (medido). E o unico jeito de saber QUEM DEVIA responder, e sem isso
# nao se distingue "todos cairam" de "responderam e nao acharam".
_HABILITADOS: dict[str, frozenset[str] | None] = {}


def habilitados(categoria_searx: str, fetch_config: Fetch | None = None) -> frozenset[str] | None:
    """Engines HABILITADOS na categoria, pelo /config. None quando o /config nao responde.

    None e indeterminado, e indeterminado nao vira juizo: sem saber quem devia responder,
    nao se afirma que todos cairam. Cacheado por processo — a lista so muda por deploy
    (settings.yml e politica do dono), nunca no meio de um trabalho.
    """
    if categoria_searx in _HABILITADOS:
        return _HABILITADOS[categoria_searx]
    try:
        if fetch_config is not None:
            dados = fetch_config(BASE, {})
        else:
            import httpx  # local: mantem o modulo importavel sem httpx no contrato

            r = httpx.get(BASE + "/config", timeout=5.0)
            r.raise_for_status()
            dados = r.json()
        nomes = frozenset(
            e["name"] for e in dados.get("engines", [])
            if e.get("enabled") and categoria_searx in (e.get("categories") or [])
        )
        _HABILITADOS[categoria_searx] = nomes or None
    except Exception:  # noqa: BLE001 — /config mudo nao pode derrubar uma consulta
        _HABILITADOS[categoria_searx] = None
    return _HABILITADOS[categoria_searx]


def _vivos(dados, engines_ok, engines_falha, categoria_searx, fetch_config=None):
    """Quem RESPONDEU — nao quem achou. None quando nao se pode saber.

    Esta e a distincao que faltava. `engines_ok` derivado de results[].engine mede
    COBERTURA: engine que responde "nao tenho nada" nao aparece em resultado nenhum e
    fica invisivel. Usar essa invisibilidade como prova de morte foi o defeito: consulta
    trivial em `ciencia`, com 5 dos 7 engines respondendo vazio e 2 em timeout, saia como
    FalhaFonte("nenhum-engine-respondeu") — nao-achado legitimo classificado como fonte
    fora (medido em 04/09). Vida se prova pelo COMPLEMENTO: habilitados menos os que se
    declararam fora.
    """
    if "engines" in dados:
        # Forma antiga (instancias < 2026.9): a resposta declara quem respondeu, nome a
        # nome. Nao ha o que inferir — a lista vazia e a afirmacao de que ninguem veio.
        return frozenset(engines_ok)
    todos = habilitados(categoria_searx, fetch_config)
    if todos is None:
        return None
    return todos - frozenset(engines_falha)


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
    fetch_config: Fetch | None = None,
) -> dict[str, Any]:
    """Metabusca. Devolve {resultados, engines_ok, engines_falha, engines_vivos}.

    Zero resultado NÃO é erro — é achado de não-achado, escrito no manifesto por quem
    chama (§4.1). Aqui só devolvemos `resultados: []` com os engines que responderam.

    Três campos, porque são três coisas: `engines_ok` é quem PRODUZIU resultado (medida
    de cobertura); `engines_falha` é quem se declarou fora; `engines_vivos` é quem
    RESPONDEU — o que dá procedência ao não-achado, e sem o qual "ninguém achou" é
    indistinguível de "ninguém procurou". `engines_vivos: null` é indeterminado
    declarado, não zero.
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
    vivos = _vivos(dados, engines_ok, engines_falha, CAT_SEARX[categoria], fetch_config)
    # Fonte fora é quando NINGUÉM respondeu — e isso só se afirma sabendo quem devia.
    # Com `vivos` indeterminado (None), zero resultado sai como não-achado: o HTTP 200
    # já prova que o SearXNG não está fora, e classificar não-achado como falha de fonte
    # é o erro mais caro dos dois — some do relatório como se ninguém tivesse procurado.
    if not dados.get("results") and vivos is not None and not vivos:
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
    return {"resultados": resultados, "engines_ok": engines_ok,
            "engines_falha": engines_falha,
            "engines_vivos": sorted(vivos) if vivos is not None else None}
