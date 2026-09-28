"""Leitura de página com procedência (spec pesquisa-web §3.2, §4.2, §4.8; card #3183).

Custódia antes do texto (minuta 0038, B2 de inteligencia; B8 de engenharia). O coletor HTTP
próprio (httpx) grava em `bruto/` o corpo da resposta como veio — sem decodificar charset,
sem recodificar —, e ao lado um `<n>.resposta.json` com status, cabeçalhos, URL pedida, URL
final, redirecionamentos e hora. O sha256 é sobre os bytes do corpo. A codificação de
transporte que o próprio cliente negociou (gzip, br) é desfeita; a de caractere, não.

Crawl4AI só em `--render`. O HTTP não escala sozinho para browser: página que depende de
JavaScript sai como falha com a sugestão `--render`. Em `--render` o bruto continua sendo
o corpo HTTP; o DOM renderizado e a captura de tela são derivados, cada um com hash próprio
na linha do manifesto.

Falha sai como falha (B3 de inteligencia). Guarda de rede (inclusive em cada
redirecionamento), rede, status ausente ou fora de 2xx, corpo vazio, tipo sem conversor e
extração abaixo do piso levantam `FalhaFonte` com `causa` DEPOIS de gravar a linha de
não-achado (§2.3: todo ato grava a linha). Corpo vazio e status ruim não deixam `bruto/`;
tipo sem conversor e extração abaixo do piso guardam o bruto, que é real e se reprocessa.
O cache casa por (URL, sha256 do bruto, estratégia), nunca pelo hash do extraído.

Derivação, transitória até o serviço de conversão (#3183 passo 4): HTML e texto são
decodificados pela ordem BOM → charset HTTP → meta → UTF-8 estrito → windows-1252, com a
origem da decisão e a contagem de U+FFFD na linha; o markdown sai do gerador da Crawl4AI
(função pura, sem browser), fit do Pruning e, se o fit vier vazio, o raw. PDF e demais
tipos saem `tipo-sem-conversor:<tipo>` até o serviço existir.

Piso de extração: um caractere útil. Os pisos por tipo são a C3 de inteligencia, ainda sem
medida (spec espelho-de-leitura §4.5: até medir, valem null); até lá só o vazio reprova.

Tudo que toca rede ou browser é injetável, para a suíte de contrato rodar sem os dois:
  coletor(url, verifica) -> Resposta                        default: httpx
  renderizador(url) -> {dom, md_fit, md_raw, captura}       default: Crawl4AI/Playwright
  derivador(html, base_url) -> {md_fit, md_raw}             default: gerador da Crawl4AI
"""

from __future__ import annotations

import codecs
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import manifesto as M
from .envelope import FalhaFonte
from .guarda import UrlRecusada, verifica_url

PISO_CARACTERES_UTEIS = 1  # C3 de inteligencia sem medida: só o vazio reprova
LIMIAR_TEXTO_CURTO = 400  # abaixo disso o retorno avisa que `--render` pode trazer mais
TETO_BYTES = 64 * 1024 * 1024
MAX_REDIRECIONAMENTOS = 10
TIMEOUT_S = 30.0

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
_RE_META_CHARSET = re.compile(rb"<meta[^>]+charset\s*=\s*[\"']?\s*([A-Za-z0-9_.:\-]+)", re.I)
_RE_BRANCO = re.compile(r"\s+")

TIPOS_HTML = frozenset({"text/html", "application/xhtml+xml"})
TIPOS_TEXTO = frozenset({"text/plain", "text/markdown", "text/csv", "application/json", "text/xml", "application/xml"})
_EXT = {
    "text/html": "html", "application/xhtml+xml": "xhtml", "text/plain": "txt",
    "text/markdown": "md", "text/csv": "csv", "application/json": "json",
    "text/xml": "xml", "application/xml": "xml", "application/pdf": "pdf",
    "application/zip": "zip", "application/epub+zip": "epub",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "image/png": "png", "image/jpeg": "jpg", "image/gif": "gif",
}
_ASSINATURAS = (
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF8", "image/gif"),
)
# WHATWG Encoding: estes rótulos significam windows-1252 na web.
_ROTULOS_1252 = frozenset({"iso-8859-1", "iso8859-1", "latin1", "latin-1", "l1", "us-ascii", "ascii", "cp1252"})


@dataclass
class Resposta:
    """O que a fonte entregou, antes de qualquer interpretação."""

    corpo: bytes
    status: int | None
    cabecalhos: list[tuple[str, str]]
    url_pedida: str
    url_final: str
    hora: str
    redirecionamentos: list[dict[str, Any]] = field(default_factory=list)

    def cabecalho(self, nome: str) -> str | None:
        alvo = nome.lower()
        for k, v in self.cabecalhos:
            if k.lower() == alvo:
                return v
        return None


Coletor = Callable[[str, Callable[[str], None]], Resposta]
Renderizador = Callable[[str], dict]
Derivador = Callable[[str, str], dict]


class _SemDerivado(Exception):
    """Os bytes chegaram, mas não há texto derivável deles aqui. Vira FalhaFonte com linha."""

    def __init__(self, causa: str, **extra: Any) -> None:
        super().__init__(causa)
        self.causa = causa
        self.extra = extra


# ------------------------------------------------------------------ helpers puros
def detecta_idioma(html: str) -> str:
    m = _RE_LANG.search(html or "")
    return m.group(1).lower() if m else "indeterminado"


def detecta_data_publicacao(html: str) -> dict[str, str | None]:
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


def caracteres_uteis(texto: str) -> int:
    return len(_RE_BRANCO.sub("", texto or ""))


def _mime(content_type: str | None) -> str | None:
    if not content_type:
        return None
    return content_type.split(";", 1)[0].strip().lower() or None


def _charset_http(content_type: str | None) -> str | None:
    for parte in (content_type or "").split(";")[1:]:
        k, _, v = parte.partition("=")
        if k.strip().lower() == "charset" and v.strip():
            return v.strip().strip("\"'")
    return None


def _codec(rotulo: str | None) -> str | None:
    """Rótulo de charset → codec Python, pela regra WHATWG; None se desconhecido."""
    if not rotulo:
        return None
    r = rotulo.strip().lower()
    if r in _ROTULOS_1252:
        return "cp1252"
    try:
        return codecs.lookup(r).name
    except LookupError:
        return None


def tipo_real(corpo: bytes, content_type: str | None) -> tuple[str, str]:
    """(mime, por): assinatura dos bytes, depois content-type (spec espelho §2.4, `tipo_por`)."""
    declarado = _mime(content_type)
    for sig, mime in _ASSINATURAS:
        if corpo.startswith(sig):
            # zip é o envelope de docx/xlsx/pptx/epub: o content-type diz qual
            if mime == "application/zip" and declarado and declarado != "application/octet-stream":
                return declarado, "content-type"
            return mime, "assinatura"
    if declarado and declarado != "application/octet-stream":
        return declarado, "content-type"
    cabeca = corpo[:1024].lstrip(b"\xef\xbb\xbf \t\r\n").lower()
    if cabeca.startswith((b"<!doctype html", b"<html")) or b"<html" in cabeca:
        return "text/html", "assinatura"
    return "application/octet-stream", "desconhecido"


def decodifica(corpo: bytes, content_type: str | None, *, html: bool) -> tuple[str, dict[str, Any]]:
    """Bytes → texto com a decisão declarada: BOM → HTTP → meta (só HTML) → UTF-8 → cp1252.

    Nunca `errors="replace"` calado: o que não decodifica vira U+FFFD e é contado.
    """
    for bom, cod in ((codecs.BOM_UTF8, "utf-8"), (codecs.BOM_UTF16_LE, "utf-16-le"), (codecs.BOM_UTF16_BE, "utf-16-be")):
        if corpo.startswith(bom):
            return _decodifica_com(corpo[len(bom):], cod, "bom")
    cod = _codec(_charset_http(content_type))
    if cod:
        return _decodifica_com(corpo, cod, "http")
    if html:
        m = _RE_META_CHARSET.search(corpo[:4096])
        cod = _codec(m.group(1).decode("ascii", "ignore")) if m else None
        if cod:
            return _decodifica_com(corpo, cod, "meta")
    try:
        return corpo.decode("utf-8"), {"decidido": "utf-8", "por": "deteccao", "substituicoes": 0}
    except UnicodeDecodeError:
        return _decodifica_com(corpo, "cp1252", "deteccao")


def _decodifica_com(corpo: bytes, cod: str, por: str) -> tuple[str, dict[str, Any]]:
    texto = corpo.decode(cod, errors="replace")
    return texto, {"decidido": cod, "por": por, "substituicoes": texto.count("�")}


def _recorte_bm25(md: str, foco: str, *, max_blocos: int = 24) -> str:
    """Vista de RETORNO por pergunta (§4.2): recorte por blocos, sem inferência.

    Não é o que se grava — o disco fica com o md inteiro. ⚪ aproxima o ranking da BM25 da
    lib; refinar quando o uso pedir (o #3183 passo 6 a leva para papel sobre blocos).
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
    renderizador: Renderizador | None = None,
    derivador: Derivador | None = None,
    guarda_resolvedor=None,
) -> dict[str, Any]:
    """Lê uma URL com procedência. Devolve os campos de retorno do §4.2 + `n`/`linha`.

    Fluxo: guarda → coleta HTTP (guarda em cada salto) → confere resposta → cache por
    (URL, sha256 do bruto, estratégia) → grava bruto → deriva (HTTP ou `--render`) → piso →
    grava derivado → manifesto. Toda saída por falha grava antes a linha de não-achado.
    """
    estrategia = "browser" if render else "http"

    def _verifica(u: str) -> None:
        try:
            verifica_url(u, resolvedor=guarda_resolvedor)
        except UrlRecusada as rec:
            raise FalhaFonte(f"guarda-de-rede:{rec.causa}") from rec

    resp: Resposta | None = None
    try:
        _verifica(url)
        resp = (coletor or _coletor_httpx)(url, _verifica)
        _confere(resp)
    except FalhaFonte as f:
        raise _nao_achado(trab, url, estrategia, f.causa, resp=resp, extra=f.extra) from f

    sha = M.sha256_bytes(resp.corpo)
    tipo, tipo_por = tipo_real(resp.corpo, resp.cabecalho("content-type"))

    anterior = _acha_cache(trab, url, sha, estrategia)
    if anterior is not None:
        return _serve_cache(trab, url, resp, sha, anterior, foco=foco, max_chars=max_chars, offset=offset)

    n = trab.proximo_n()
    p_bruto = trab.guarda_bruto(n, resp.corpo, _EXT.get(tipo, "bin"))
    trab.guarda_bruto(n, _resposta_json(resp, sha, tipo, tipo_por), "resposta.json")
    base = {"n": n, "sha256": sha, "bruto": str(p_bruto), "tipo": tipo, "tipo_por": tipo_por}

    try:
        if render:
            d = _deriva_render(trab, n, url, renderizador)
        else:
            d = _deriva_http(resp, tipo, derivador)
    except (FalhaFonte, _SemDerivado) as f:
        raise _nao_achado(trab, url, estrategia, f.causa, resp=resp, extra={**base, **f.extra}) from f

    md = d["md"]
    uteis = caracteres_uteis(md)
    if uteis < PISO_CARACTERES_UTEIS:
        raise _nao_achado(trab, url, estrategia, "extracao-abaixo-do-piso", resp=resp,
                          extra={**base, "caracteres_uteis": uteis, "encoding": d.get("encoding"),
                                 **({"sugestao": "--render"} if not render else {})})
    if not render and _RE_ROOT_VAZIO.search(d.get("html") or ""):
        raise _nao_achado(trab, url, estrategia, "pagina-depende-de-javascript", resp=resp,
                          extra={**base, "caracteres_uteis": uteis, "sugestao": "--render"})

    trab.guarda_derivado(n, md, "md")

    html_meta = d.get("html") or ""
    avisos = acha_instrucoes(md)
    idioma = detecta_idioma(html_meta)
    datapub = detecta_data_publicacao(html_meta)
    aviso = ("texto-curto: --render pode trazer mais" if (not render and tipo in TIPOS_HTML
             and uteis < LIMIAR_TEXTO_CURTO) else None)

    linha = trab.grava_linha({
        "ato": "ler", "url": url, "url_final": resp.url_final, "status": resp.status,
        **base, "estrategia": estrategia, "encoding": d.get("encoding"), "vista": d.get("vista"),
        "caracteres_uteis": uteis, "derivados": d.get("derivados") or None,
        "idioma": idioma, "data_publicacao": datapub,
        "achado": ({"instrucao_em_pagina": avisos} if avisos else None),
    })

    corpo = _recorte_bm25(md, foco) if foco else md
    return _retorno(n=n, url=url, resp=resp, sha=sha, bruto=str(p_bruto), tipo=tipo,
                    estrategia=estrategia, corpo=corpo, max_chars=max_chars, offset=offset,
                    idioma=idioma, datapub=datapub, avisos=avisos, encoding=d.get("encoding"),
                    uteis=uteis, aviso=aviso, manifesto=trab.ref_manifesto(linha))


def _confere(resp: Resposta) -> None:
    if resp.status is None or int(resp.status or 0) == 0:
        raise FalhaFonte("status-ausente")
    if not (200 <= int(resp.status) < 300):
        raise FalhaFonte(f"status-{resp.status}", status=int(resp.status))
    if not resp.corpo:
        raise FalhaFonte("corpo-vazio", status=int(resp.status))


def _nao_achado(trab, url, estrategia, causa, *, resp: Resposta | None, extra: dict | None = None) -> FalhaFonte:
    """Grava a linha de não-achado e devolve a FalhaFonte que o ato levanta (exit 1)."""
    extra = {k: v for k, v in (extra or {}).items() if v is not None}
    campos = {"ato": "ler", "url": url, "estrategia": estrategia, "nao_achado": True, "causa": causa}
    if resp is not None:
        campos.update({"url_final": resp.url_final, "status": resp.status})
    campos.update(extra)
    linha = trab.grava_linha(campos)
    return FalhaFonte(causa, **{**extra, "url": url, "manifesto": trab.ref_manifesto(linha)})


def _resposta_json(resp: Resposta, sha: str, tipo: str, tipo_por: str) -> bytes:
    doc = {
        "url_pedida": resp.url_pedida, "url_final": resp.url_final, "status": resp.status,
        "hora": resp.hora, "redirecionamentos": resp.redirecionamentos,
        "cabecalhos": [[k, v] for k, v in resp.cabecalhos],
        "bytes": len(resp.corpo), "sha256": sha, "tipo": tipo, "tipo_por": tipo_por,
    }
    return json.dumps(doc, ensure_ascii=False, indent=2).encode("utf-8")


def _deriva_http(resp: Resposta, tipo: str, derivador: Derivador | None) -> dict[str, Any]:
    ct = resp.cabecalho("content-type")
    if tipo in TIPOS_HTML:
        texto, enc = decodifica(resp.corpo, ct, html=True)
        d = (derivador or _derivador_crawl4ai)(texto, resp.url_final)
        fit = (d.get("md_fit") or "").strip()
        raw = (d.get("md_raw") or "").strip()
        return {"md": fit or raw, "vista": "fit" if fit else "raw", "encoding": enc, "html": texto}
    if tipo in TIPOS_TEXTO:
        texto, enc = decodifica(resp.corpo, ct, html=False)
        return {"md": texto, "vista": "texto", "encoding": enc, "html": ""}
    raise _SemDerivado(f"tipo-sem-conversor:{tipo}")


def _deriva_render(trab, n: int, url: str, renderizador: Renderizador | None) -> dict[str, Any]:
    r = (renderizador or _renderizador_crawl4ai)(url)
    dom = r.get("dom") or ""
    derivados: dict[str, Any] = {}
    if dom:
        p = trab.guarda_derivado(n, dom, "dom.html")
        derivados["dom"] = {"arquivo": str(p), "sha256": M.sha256_texto(dom)}
    captura = r.get("captura")
    if captura:
        p = trab.derivado / f"{n}.captura.png"
        p.write_bytes(captura)
        derivados["captura"] = {"arquivo": str(p), "sha256": M.sha256_bytes(captura)}
    fit = (r.get("md_fit") or "").strip()
    raw = (r.get("md_raw") or "").strip()
    return {"md": fit or raw, "vista": "fit" if fit else "raw", "encoding": None, "html": dom,
            "derivados": derivados}


def _acha_cache(trab, url: str, sha: str, estrategia: str) -> dict[str, Any] | None:
    for ln in reversed(trab.linhas()):
        if (ln.get("ato") == "ler" and ln.get("url") == url and ln.get("sha256") == sha
                and ln.get("estrategia") == estrategia and isinstance(ln.get("n"), int)
                and not ln.get("nao_achado")):
            md = trab.derivado / f"{ln['n']}.md"
            if md.exists() and Path(ln.get("bruto") or "").exists():
                return ln
    return None


def _serve_cache(trab, url, resp: Resposta, sha, ant, *, foco, max_chars, offset) -> dict[str, Any]:
    n = ant["n"]
    md = (trab.derivado / f"{n}.md").read_text(encoding="utf-8")
    linha = trab.grava_linha({"ato": "ler", "url": url, "status": resp.status, "sha256": sha,
                              "estrategia": "cache", "cache_de": n})
    corpo = _recorte_bm25(md, foco) if foco else md
    avisos = acha_instrucoes(md)
    return _retorno(n=n, url=url, resp=resp, sha=sha, bruto=ant.get("bruto"), tipo=ant.get("tipo"),
                    estrategia="cache", corpo=corpo, max_chars=max_chars, offset=offset,
                    idioma=ant.get("idioma", "indeterminado"),
                    datapub=ant.get("data_publicacao") or {"valor": None, "origem": "ausente"},
                    avisos=avisos, encoding=ant.get("encoding"),
                    uteis=ant.get("caracteres_uteis", caracteres_uteis(md)), aviso=None,
                    manifesto=trab.ref_manifesto(linha))


def _retorno(*, n, url, resp, sha, bruto, tipo, estrategia, corpo, max_chars, offset, idioma,
             datapub, avisos, encoding, uteis, aviso, manifesto) -> dict[str, Any]:
    chars_total = len(corpo)
    janela = corpo[offset: offset + max_chars]
    truncado = (offset + max_chars) < chars_total
    out = {
        "n": n, "url": url, "url_final": resp.url_final, "conteudo": janela,
        "chars_total": chars_total, "truncado": truncado,
        "next_offset": (offset + max_chars) if truncado else None,
        "estrategia": estrategia, "status": resp.status, "sha256": sha, "tipo": tipo,
        "encoding": encoding, "caracteres_uteis": uteis, "idioma": idioma,
        "data_publicacao": datapub, "avisos": avisos, "bruto": bruto, "manifesto": manifesto,
    }
    if aviso:
        out["aviso"] = aviso
    return out


# ------------------------------------------------------------------ coletor real
def _coletor_httpx(url: str, verifica: Callable[[str], None], *, transport=None) -> Resposta:
    """GET com o corpo como veio. Redirecionamento à mão: cada salto passa pela guarda.

    `transport` é injetável (httpx.MockTransport) para a suíte testar este coletor sem rede.
    """
    import httpx

    saltos: list[dict[str, Any]] = []
    atual = url
    try:
        with httpx.Client(timeout=TIMEOUT_S, follow_redirects=False, transport=transport,
                          headers={"User-Agent": M.UA, "Accept": "*/*"}) as cli:
            for _ in range(MAX_REDIRECIONAMENTOS + 1):
                with cli.stream("GET", atual) as r:
                    if r.is_redirect:
                        destino = str(r.url.join(r.headers["location"]))
                        saltos.append({"status": r.status_code, "de": atual, "para": destino})
                        verifica(destino)
                        atual = destino
                        continue
                    hora = M.agora_utc()
                    corpo = bytearray()
                    for pedaco in r.iter_bytes():
                        corpo.extend(pedaco)
                        if len(corpo) > TETO_BYTES:
                            raise FalhaFonte("corpo-acima-do-teto", status=r.status_code, teto=TETO_BYTES)
                    return Resposta(
                        corpo=bytes(corpo), status=r.status_code,
                        cabecalhos=list(r.headers.multi_items()),
                        url_pedida=url, url_final=str(r.url), hora=hora, redirecionamentos=saltos,
                    )
    except httpx.HTTPError as exc:
        raise FalhaFonte(f"rede:{type(exc).__name__}") from exc
    raise FalhaFonte("redirecionamentos-demais", redirecionamentos=len(saltos))


def _derivador_crawl4ai(html: str, base_url: str) -> dict[str, str]:
    """Markdown pelo gerador da Crawl4AI: função pura sobre o HTML já decodificado.

    O gerador devolve o erro como se fosse texto («Error in markdown generation: …»); aqui
    isso vira falha, nunca conteúdo.
    """
    import contextlib
    import sys

    with contextlib.redirect_stdout(sys.stderr):
        from crawl4ai import DefaultMarkdownGenerator
        from crawl4ai.content_filter_strategy import PruningContentFilter

        r = DefaultMarkdownGenerator(content_filter=PruningContentFilter()).generate_markdown(html, base_url)
    raw = r.raw_markdown or ""
    fit = r.fit_markdown or ""
    if raw.startswith(("Error in markdown generation", "Error converting HTML to markdown")):
        raise _SemDerivado("derivacao-falhou", detalhe=raw[:160])
    if fit.startswith("Error generating fit markdown"):
        fit = ""
    return {"md_fit": fit, "md_raw": raw}


def _renderizador_crawl4ai(url: str) -> dict[str, Any]:
    """`--render`: browser da Crawl4AI. Crawl4AI é falador; stdout vai ao stderr (§2.2)."""
    import asyncio
    import contextlib
    import sys

    with contextlib.redirect_stdout(sys.stderr):
        return asyncio.run(_renderiza_async(url))


async def _renderiza_async(url: str) -> dict[str, Any]:
    import base64

    from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, DefaultMarkdownGenerator
    from crawl4ai.async_crawler_strategy import AsyncPlaywrightCrawlerStrategy
    from crawl4ai.content_filter_strategy import PruningContentFilter

    cfg = CrawlerRunConfig(
        markdown_generator=DefaultMarkdownGenerator(content_filter=PruningContentFilter()),
        user_agent=M.UA, page_timeout=30000, verbose=False, screenshot=True,
    )
    try:
        async with AsyncWebCrawler(crawler_strategy=AsyncPlaywrightCrawlerStrategy()) as crawler:
            r = await crawler.arun(url=url, config=cfg)
    except Exception as exc:  # noqa: BLE001
        raise FalhaFonte(f"render:{type(exc).__name__}") from exc
    if not getattr(r, "success", True):
        raise FalhaFonte("render-falhou", detalhe=(getattr(r, "error_message", "") or "")[:160])
    md = r.markdown
    captura = getattr(r, "screenshot", None)
    return {
        "dom": r.html or "",
        "md_fit": getattr(md, "fit_markdown", None) or "",
        "md_raw": getattr(md, "raw_markdown", None) or str(md or ""),
        "captura": base64.b64decode(captura) if captura else None,
    }
