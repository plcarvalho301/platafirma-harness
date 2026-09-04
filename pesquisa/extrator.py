"""Leitura de página com procedência — Crawl4AI (spec §3.2, §4.2).

Duas estratégias, uma biblioteca: HTTP primeiro (sem browser, sempre); browser só por
escalada automática (texto útil < 400 chars, ou `<div id=root|app>` vazio, ou `--render`)
e fecha ao terminar. Markdown "fit" por PruningContentFilter é o corte de token mais
barato que existe aqui — sem inferência.

O import de crawl4ai é preguiçoso e vive só no coletor default. `ler()` recebe um
`coletor` injetável: a suíte de contrato passa um coletor falso e testa toda a
orquestração (guarda, cache, escalada declarada, foco, paginação, detecção de instrução,
manifesto) sem browser e sem rede.

Contrato do coletor: `coletor(url, render: bool) -> dict` com chaves
`{html, status, headers, md_fit, estrategia}`. `estrategia` ∈ {"http","browser"}.
"""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from . import manifesto as M
from .envelope import FalhaFonte
from .guarda import UrlRecusada, verifica_url

Coletor = Callable[[str, bool], dict]

LIMIAR_ESCALADA = 400  # chars úteis abaixo disso => tenta browser (§3.2)
PADROES_INSTRUCAO = [
    r"ignore (as )?(instru\w+|previous|todas)",
    r"disregard (the )?(above|previous)",
    r"\bexecute\b",
    r"envie para\b",
    r"send (this )?to\b",
    r"you are now\b",
    r"system prompt\b",
]
_RE_INSTRUCAO = re.compile("|".join(PADROES_INSTRUCAO), re.IGNORECASE)
_RE_LANG = re.compile(r"<html[^>]*\blang=[\"']([a-zA-Z-]{2,8})[\"']", re.IGNORECASE)
_RE_ROOT_VAZIO = re.compile(r"<div[^>]+id=[\"'](root|app)[\"'][^>]*>\s*</div>", re.IGNORECASE)
_RE_DATAS = [
    re.compile(r'property=[\"\']article:published_time[\"\']\s+content=[\"\']([^\"\']+)', re.I),
    re.compile(r'property=[\"\']og:published_time[\"\']\s+content=[\"\']([^\"\']+)', re.I),
    re.compile(r'\"datePublished\"\s*:\s*\"([^\"]+)\"', re.I),
    re.compile(r'<time[^>]+datetime=[\"\']([^\"\']+)', re.I),
]


# ------------------------------------------------------------------ helpers puros
def detecta_idioma(html: str) -> str:
    m = _RE_LANG.search(html or "")
    return m.group(1).lower() if m else "indeterminado"


def detecta_data_publicacao(html: str) -> dict[str, str]:
    for rx in _RE_DATAS:
        m = rx.search(html or "")
        if m:
            return {"valor": m.group(1).strip(), "origem": "detectada"}
    return {"valor": None, "origem": "ausente"}


def acha_instrucoes(texto: str) -> list[dict[str, Any]]:
    avisos = []
    for i, linha in enumerate((texto or "").splitlines(), 1):
        if _RE_INSTRUCAO.search(linha):
            avisos.append({"linha": i, "trecho": linha.strip()[:160]})
    return avisos


def _recorte_bm25(md: str, foco: str, *, max_blocos: int = 24) -> str:
    """Vista de RETORNO por pergunta (§4.2): recorte por blocos, sem inferência.

    Não é o que se grava — o disco fica com o md inteiro. BM25 pleno opera sobre HTML na
    Crawl4AI; aqui a vista de retorno é um recorte por sobreposição de termos sobre os
    blocos do markdown fit, determinístico e testável sem browser. ⚪ aproxima o ranking
    da BM25 da lib; refinar quando o uso pedir.
    """
    termos = {t.lower() for t in re.findall(r"\w{3,}", foco or "")}
    if not termos:
        return md
    blocos = [b.strip() for b in re.split(r"\n\s*\n", md) if b.strip()]
    pont = []
    for b in blocos:
        toks = re.findall(r"\w{3,}", b.lower())
        if not toks:
            continue
        score = sum(toks.count(t) for t in termos) / (len(toks) ** 0.5)
        if score > 0:
            pont.append((score, b))
    pont.sort(key=lambda x: x[0], reverse=True)
    escolhidos = [b for _, b in pont[:max_blocos]]
    return "\n\n".join(escolhidos) if escolhidos else md


# ------------------------------------------------------------------ orquestração
def ler(
    url: str,
    trab: "M.Trabalho",
    *,
    foco: str | None = None,
    render: bool = False,
    max_chars: int = 6000,
    offset: int = 0,
    coletor: Coletor | None = None,
    guarda_resolvedor=None,
) -> dict[str, Any]:
    """Lê uma URL com procedência. Devolve os campos de retorno do §4.2 + `n`/`linha`.

    Fluxo: guarda de rede → cache do trabalho (mesmo sha256 já em bruto? serve do disco)
    → HTTP → escalada para browser se preciso → grava bruto/derivado → manifesto.
    """
    try:
        verifica_url(url, resolvedor=guarda_resolvedor)
    except UrlRecusada as rec:
        raise FalhaFonte(f"guarda-de-rede:{rec.causa}") from rec

    colhe = coletor or _coletor_crawl4ai
    res = colhe(url, render)
    html = res.get("html") or ""
    md_fit = (res.get("md_fit") or "").strip()
    estrategia = res.get("estrategia") or "http"
    status = int(res.get("status") or 0)

    # escalada automática: HTTP veio pobre e ainda não usamos browser
    if estrategia == "http" and not render:
        pobre = len(md_fit) < LIMIAR_ESCALADA or bool(_RE_ROOT_VAZIO.search(html))
        if pobre:
            res2 = colhe(url, True)
            if (res2.get("md_fit") or "").strip():
                res, html = res2, res2.get("html") or html
                md_fit = (res2.get("md_fit") or "").strip()
                estrategia = res2.get("estrategia") or "browser"
                status = int(res2.get("status") or status)

    if status and not (200 <= status < 300):
        raise FalhaFonte(f"status-{status}", status=status, estrategia=estrategia)

    dados_brutos = html.encode("utf-8")
    sha = M.sha256_bytes(dados_brutos)

    # cache do trabalho: bruto com o mesmo sha256 já no disco -> serve do disco
    for ln in trab.linhas():
        if ln.get("sha256") == sha and ln.get("bruto"):
            n_cache = ln.get("n")
            md_cache = (trab.derivado / f"{n_cache}.md")
            if md_cache.exists():
                md_fit = md_cache.read_text(encoding="utf-8")
                estrategia = "cache"
            break

    n = trab.proximo_n()
    if estrategia != "cache":
        trab.guarda_bruto(n, dados_brutos, "html")
        trab.guarda_derivado(n, json.dumps(res.get("headers") or {}, ensure_ascii=False), "headers")
        trab.guarda_derivado(n, md_fit, "md")

    avisos = acha_instrucoes(md_fit)
    idioma = detecta_idioma(html)
    datapub = detecta_data_publicacao(html)

    corpo = _recorte_bm25(md_fit, foco) if foco else md_fit
    chars_total = len(corpo)
    janela = corpo[offset : offset + max_chars]
    truncado = (offset + max_chars) < chars_total
    next_offset = (offset + max_chars) if truncado else None

    linha = trab.grava_linha(
        {
            "n": n,
            "ato": "ler",
            "url": url,
            "status": status,
            "sha256": sha,
            "bruto": str(trab.bruto / f"{n}.html"),
            "estrategia": estrategia,
            "idioma": idioma,
            "data_publicacao": datapub,
            "achado": ({"instrucao_em_pagina": avisos} if avisos else None),
        }
    )
    return {
        "n": n,
        "url": url,
        "conteudo": janela,
        "chars_total": chars_total,
        "truncado": truncado,
        "next_offset": next_offset,
        "estrategia": estrategia,
        "status": status,
        "sha256": sha,
        "idioma": idioma,
        "data_publicacao": datapub,
        "avisos": avisos,
        "bruto": str(trab.bruto / f"{n}.html"),
        "manifesto": trab.ref_manifesto(linha),
    }


# ------------------------------------------------------------------ coletor real
def _coletor_crawl4ai(url: str, render: bool) -> dict[str, Any]:
    """Coletor default: Crawl4AI. Import preguiçoso — só aqui depende da lib/browser.

    Crawl4AI é falador: manda banner e log ao stdout. A rota de máquina (§2.2) exige
    stdout = só o envelope JSON, então todo ruído do crawl é desviado para stderr.
    """
    import asyncio
    import contextlib
    import sys

    with contextlib.redirect_stdout(sys.stderr):
        return asyncio.run(_colhe_async(url, render))


async def _colhe_async(url: str, render: bool) -> dict[str, Any]:
    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, DefaultMarkdownGenerator
    from crawl4ai.async_crawler_strategy import (
        AsyncHTTPCrawlerStrategy,
        AsyncPlaywrightCrawlerStrategy,
    )
    from crawl4ai.content_filter_strategy import PruningContentFilter

    gerador = DefaultMarkdownGenerator(content_filter=PruningContentFilter())
    cfg = CrawlerRunConfig(markdown_generator=gerador, user_agent=M.UA, page_timeout=30000, verbose=False)

    estrategia = "browser" if render else "http"
    if render:
        strat = AsyncPlaywrightCrawlerStrategy()
    else:
        strat = AsyncHTTPCrawlerStrategy()
    try:
        async with AsyncWebCrawler(crawler_strategy=strat) as crawler:
            r = await crawler.arun(url=url, config=cfg)
    except Exception as exc:  # noqa: BLE001
        raise FalhaFonte(f"crawl4ai:{type(exc).__name__}") from exc

    md = r.markdown
    md_fit = getattr(md, "fit_markdown", None) or getattr(md, "raw_markdown", None) or str(md or "")
    return {
        "html": r.html or "",
        "status": getattr(r, "status_code", 0) or 0,
        "headers": getattr(r, "response_headers", {}) or {},
        "md_fit": md_fit,
        "estrategia": estrategia,
    }
