"""Percurso em largura de um site sem API, com cortesia e grafo JSONL (card #4458).

Visita páginas por HTTP (sem navegador), respeitando `robots.txt` antes do primeiro
pedido a cada host, esperando intervalo mínimo entre pedidos ao mesmo host sobre uma
única conexão keep-alive por host, consultando HEAD em links de arquivo, descobrindo
URLs por sitemap (`.xml` e `.xml.gz`) e links internos, custodiando cada página com
`sha256` como no `ler` e gravando o grafo completo em `grafo.jsonl`.
"""
from __future__ import annotations

import contextlib
import heapq
import json
import re
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urldefrag, urlsplit

from . import extrator
from . import manifesto as M
from . import robots as R
from .envelope import FalhaFonte, UsoInvalido
from .guarda import UrlRecusada, verifica_url
from .prazo import CONEXAO_S

INTERVALO_PADRAO_S = 0.2
PROFUNDIDADE_PADRAO = 3
TETO_PADRAO = 100
TIMEOUT_PERCURSO_S = 20.0
MAX_REDIRECIONAMENTOS = 10
MAX_SITEMAPS = 8
MAX_URLS_SITEMAP = 5_000
MIN_TETO_ARQUIVOS = 200

_HTTP_OK_MIN = 200
_HTTP_OK_MAX = 300
_CODIGOS_REDIRECT = frozenset({301, 302, 303, 307, 308})
_EXTS_ARQUIVO = frozenset(
    {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".odt",
        ".ods",
        ".odp",
        ".rtf",
        ".csv",
        ".tsv",
        ".zip",
        ".rar",
        ".7z",
        ".tar",
        ".gz",
        ".bz2",
        ".xz",
        ".epub",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".svg",
        ".ico",
        ".bmp",
        ".tif",
        ".tiff",
        ".mp3",
        ".mp4",
        ".ogg",
        ".wav",
        ".webm",
        ".avi",
        ".mov",
        ".exe",
        ".msi",
        ".dmg",
        ".apk",
        ".iso",
    }
)
_RE_SEGMENTO_ARQUIVO_CMS = re.compile(
    r"\.(?:pdf|docx?|xlsx?|pptx?|odt|ods|odp|zip|csv|epub|png|jpe?g|gif|webp|svg)/(?:@@download|view|download)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ConfigPercurso:
    """Parâmetros de entrada do ato `percorrer`."""

    semente: str
    dominios: tuple[str, ...] = ()
    profundidade_max: int = PROFUNDIDADE_PADRAO
    teto: int = TETO_PADRAO
    intervalo_s: float = INTERVALO_PADRAO_S


@dataclass(frozen=True)
class OpcoesRede:
    """Pontos de injeção para testes herméticos sem rede externa."""

    requisitor: Callable[[str, str], extrator.Resposta] | None = None
    transport_por_host: Callable[[str], Any] | None = None
    guarda_resolvedor: Callable[[str], list[str]] | None = None
    dormir: Callable[[float], None] = time.sleep
    relogio_mono: Callable[[], float] = time.monotonic
    derivador: Callable[[str, str], dict[str, str]] | None = None


class _PuladaPorRobots(Exception):
    """Sinal interno quando o próprio pedido ou redirecionamento cai em rota proibida."""

    def __init__(self, url: str, motivo: str) -> None:
        super().__init__(motivo)
        self.url = url
        self.motivo = motivo


def eh_link_de_arquivo(url: str) -> bool:
    """Identifica links de arquivo/mídia (incluindo rotas `/@@download/` e `/@@images/` do Plone)."""
    caminho = (urlsplit(url).path or "").lower()
    if not caminho or caminho.endswith((".xml", ".xml.gz")):
        return False
    if "/@@download/" in caminho or "/@@images/" in caminho or caminho.endswith("/@@download"):
        return True
    if _RE_SEGMENTO_ARQUIVO_CMS.search(caminho):
        return True
    sufixo = Path(caminho.rstrip("/")).suffix.lower()
    return sufixo in _EXTS_ARQUIVO


def _normalizar_host(host: str) -> str:
    limpo = host.strip().lower().rstrip(".")
    if "://" in limpo:
        limpo = (urlsplit(limpo).hostname or "").lower().rstrip(".")
    return limpo.split("/", 1)[0].split(":", 1)[0]


def _validar_config(cfg: ConfigPercurso) -> tuple[str, frozenset[str], str]:
    if cfg.profundidade_max < 0:
        raise UsoInvalido("profundidade-negativa")
    if cfg.teto < 1:
        raise UsoInvalido("teto-invalido")
    if cfg.intervalo_s < 0:
        raise UsoInvalido("intervalo-negativo")

    semente_limpa = urldefrag((cfg.semente or "").strip())[0]
    partes = urlsplit(semente_limpa)
    esquema = (partes.scheme or "").lower()
    host_semente = (partes.hostname or "").lower().rstrip(".")
    if esquema not in ("http", "https") or not host_semente:
        raise UsoInvalido("semente-invalida")

    if cfg.dominios:
        brutos = [p.strip() for item in cfg.dominios for p in item.split(",")]
        if any(not b for b in brutos):
            raise UsoInvalido("dominio-vazio")
        dominios = frozenset(_normalizar_host(b) for b in brutos if _normalizar_host(b))
    else:
        dominios = frozenset({host_semente})

    if host_semente not in dominios:
        raise UsoInvalido("semente-fora-dos-dominios")

    caminho_base = partes.path.rstrip("/")
    prefixo = f"{esquema}://{partes.netloc.lower()}{caminho_base}" if caminho_base else ""
    return semente_limpa, dominios, prefixo


def _chave_origem(url: str) -> tuple[str, str, str]:
    p = urlsplit(url)
    esquema = (p.scheme or "https").lower()
    host = (p.hostname or "").lower().rstrip(".")
    netloc = (p.netloc or host).lower()
    return esquema, host, netloc


class _ControladorCortesia:
    """Mantém 1 conexão HTTP por host, intervalo mínimo entre pedidos e cache de `robots.txt`."""

    def __init__(self, intervalo_s: float, dominios: frozenset[str], rede: OpcoesRede) -> None:
        self.intervalo_s = intervalo_s
        self.dominios = dominios
        self.rede = rede
        self.clientes_host: dict[str, Any] = {}
        self.conexoes_criadas: dict[str, int] = {}
        self.ultimo_pedido: dict[str, float] = {}
        self.robots_por_host: dict[str, R.PoliticaRobots] = {}
        self.esperas: list[dict[str, Any]] = []
        self.pedidos_feitos: list[dict[str, Any]] = []

    def fechar(self) -> None:
        for cli in self.clientes_host.values():
            cli.close()
        self.clientes_host.clear()

    def verifica_guarda(self, url: str) -> None:
        try:
            verifica_url(url, resolvedor=self.rede.guarda_resolvedor)
        except UrlRecusada as rec:
            raise FalhaFonte(f"guarda-de-rede:{rec.causa}") from rec

    def _obter_pool_host(self, host: str) -> Any:
        import httpx

        if host in self.clientes_host:
            return self.clientes_host[host]
        transport = self.rede.transport_por_host(host) if self.rede.transport_por_host else None
        limites = httpx.Limits(max_connections=1, max_keepalive_connections=1)
        novo = httpx.Client(
            timeout=httpx.Timeout(TIMEOUT_PERCURSO_S, connect=CONEXAO_S),
            follow_redirects=False,
            limits=limites,
            transport=transport,
            headers={"User-Agent": M.UA_PERCORRER, "Accept": "*/*"},
        )
        self.clientes_host[host] = novo
        self.conexoes_criadas[host] = self.conexoes_criadas.get(host, 0) + 1
        return novo

    def _intervalo_do_host(self, host: str) -> float:
        pol = self.robots_por_host.get(host)
        if pol and pol.crawl_delay is not None:
            return max(self.intervalo_s, pol.crawl_delay)
        return self.intervalo_s

    def _aguardar_cortesia(self, host: str) -> None:
        anterior = self.ultimo_pedido.get(host)
        if anterior is None:
            return
        exigido = self._intervalo_do_host(host)
        restante = exigido - (self.rede.relogio_mono() - anterior)
        if restante > 0:
            self.esperas.append({"host": host, "segundos": round(restante, 4)})
            self.rede.dormir(restante)

    def _um_hop(self, metodo: str, url: str) -> extrator.Resposta:
        import httpx

        _, host, _ = _chave_origem(url)
        self.verifica_guarda(url)
        self._aguardar_cortesia(host)
        self.pedidos_feitos.append({"metodo": metodo, "url": url, "host": host})
        try:
            if self.rede.requisitor is not None:
                resp = self.rede.requisitor(metodo, url)
            else:
                cli = self._obter_pool_host(host)
                with cli.stream(metodo, url) as r:
                    hora = M.agora_utc()
                    corpo = bytearray()
                    if metodo != "HEAD" and r.status_code not in _CODIGOS_REDIRECT:
                        for pedaco in r.iter_bytes():
                            corpo.extend(pedaco)
                            if len(corpo) > extrator.TETO_BYTES:
                                raise FalhaFonte("corpo-acima-do-teto", status=r.status_code)
                    resp = extrator.Resposta(
                        corpo=bytes(corpo),
                        status=r.status_code,
                        cabecalhos=list(r.headers.multi_items()),
                        url_pedida=url,
                        url_final=str(r.url),
                        hora=hora,
                    )
        except httpx.HTTPError as exc:
            raise FalhaFonte(f"rede:{type(exc).__name__}", detalhe=str(exc)[:200]) from exc
        finally:
            self.ultimo_pedido[host] = self.rede.relogio_mono()
        return resp

    def garantir_robots(self, url: str) -> R.PoliticaRobots:
        esquema, host, netloc = _chave_origem(url)
        existente = self.robots_por_host.get(host)
        if existente is not None:
            return existente
        url_rob = f"{esquema}://{netloc}/robots.txt"
        self.verifica_guarda(url_rob)
        atual = url_rob
        resp: extrator.Resposta | None = None
        try:
            for _ in range(MAX_REDIRECIONAMENTOS + 1):
                r = self._um_hop("GET", atual)
                loc = r.cabecalho("location")
                if r.status in _CODIGOS_REDIRECT and loc and loc.strip():
                    from urllib.parse import urljoin

                    atual = urljoin(atual, loc.strip())
                    continue
                resp = r
                break
        except FalhaFonte:
            pol_erro = R.analisa_robots("", status=None, host=host)
            self.robots_por_host[host] = pol_erro
            return pol_erro

        if resp is None:
            pol_vazia = R.analisa_robots("", status=None, host=host)
            self.robots_por_host[host] = pol_vazia
            return pol_vazia
        texto, _ = extrator.decodifica(resp.corpo, resp.cabecalho("content-type"), html=False)
        pol = R.analisa_robots(texto, status=resp.status, host=host)
        self.robots_por_host[host] = pol
        return pol

    def pode_buscar(self, url: str) -> tuple[bool, str | None]:
        pol = self.garantir_robots(url)
        return pol.pode_buscar(url)

    def pedir(self, metodo: str, url: str, *, exigir_dominio: bool = True) -> extrator.Resposta:
        from urllib.parse import urljoin

        saltos: list[dict[str, Any]] = []
        atual = url
        for _ in range(MAX_REDIRECIONAMENTOS + 1):
            _, host_atual, _ = _chave_origem(atual)
            if exigir_dominio and host_atual not in self.dominios:
                raise FalhaFonte("redirecionamento-fora-do-dominio", destino=atual)
            permitido, motivo = self.pode_buscar(atual)
            if not permitido:
                raise _PuladaPorRobots(atual, motivo or "robots")
            r = self._um_hop(metodo, atual)
            if r.status in _CODIGOS_REDIRECT:
                loc = r.cabecalho("location")
                if not loc or not loc.strip():
                    raise FalhaFonte("redirecionamento-sem-destino", status=r.status)
                destino = urldefrag(urljoin(atual, loc.strip()))[0]
                saltos.append({"status": r.status, "de": atual, "para": destino})
                atual = destino
                continue
            return extrator.Resposta(
                corpo=r.corpo,
                status=r.status,
                cabecalhos=r.cabecalhos,
                url_pedida=url,
                url_final=atual,
                hora=r.hora,
                redirecionamentos=saltos,
            )
        raise FalhaFonte("redirecionamentos-demais", redirecionamentos=len(saltos))


@dataclass
class _EstadoGrafo:
    dominios: frozenset[str]
    prefixo_semente: str
    urls_sitemap: set[str] = field(default_factory=set)
    sitemaps_lidos: list[dict[str, Any]] = field(default_factory=list)
    nos_por_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    alias_para_no: dict[str, str] = field(default_factory=dict)
    canonicals_expandidos: set[str] = field(default_factory=set)
    arestas: list[dict[str, Any]] = field(default_factory=list)
    fila: list[tuple[int, int, int, int, int, str, int | None]] = field(default_factory=list)
    melhor_prof_enfileirada: dict[str, int] = field(default_factory=dict)
    enfileiradas_sitemap: set[str] = field(default_factory=set)
    visitadas_get: set[str] = field(default_factory=set)
    arquivos_checados: set[str] = field(default_factory=set)
    seq: int = 0
    paginas_get: int = 0
    bateu_teto: bool = False
    bateu_profundidade: bool = False

    def enfileirar_clique(self, url: str, prof: int) -> None:
        ant = self.melhor_prof_enfileirada.get(url)
        if ant is not None and ant <= prof:
            return
        self.melhor_prof_enfileirada[url] = prof
        fora = 0 if (self.prefixo_semente and url.startswith(self.prefixo_semente)) else 1
        tem_q = 1 if urlsplit(url).query else 0
        self.seq += 1
        heapq.heappush(self.fila, (0, fora, prof, tem_q, self.seq, url, prof))

    def enfileirar_sitemap(self, url: str, prof_ordem: int) -> None:
        if url in self.melhor_prof_enfileirada or url in self.enfileiradas_sitemap:
            return
        self.enfileiradas_sitemap.add(url)
        fora = 0 if (self.prefixo_semente and url.startswith(self.prefixo_semente)) else 1
        tem_q = 1 if urlsplit(url).query else 0
        self.seq += 1
        heapq.heappush(self.fila, (1, fora, prof_ordem, tem_q, self.seq, url, None))


@dataclass
class _ContextoPercurso:
    cfg: ConfigPercurso
    trab: M.Trabalho
    cortesia: _ControladorCortesia
    est: _EstadoGrafo


def _atualizar_prof_minima(no: dict[str, Any], nova_prof: int | None) -> None:
    atual = no.get("profundidade")
    if nova_prof is None:
        return
    if atual is None or nova_prof < atual:
        no["profundidade"] = nova_prof


def _registrar_pulada(est: _EstadoGrafo, url: str, motivo: str, prof: int | None) -> None:
    no = est.nos_por_id.get(url)
    if no is None:
        est.nos_por_id[url] = {
            "tipo": "no",
            "id": url,
            "tipo_no": "pulada",
            "urls": [url],
            "profundidade": prof,
            "pedida": False,
            "pulada": True,
            "motivo": motivo,
            "status": None,
        }
        est.alias_para_no[url] = url
        return
    _atualizar_prof_minima(no, prof)


def _registrar_erro_http(
    est: _EstadoGrafo,
    url: str,
    causa: str,
    prof: int | None,
    resp: extrator.Resposta | None = None,
) -> None:
    chave = est.alias_para_no.get(url, url)
    existente = est.nos_por_id.get(chave)
    if existente is not None and existente.get("tipo_no") == "pagina":
        _atualizar_prof_minima(existente, prof)
        return
    urls = [url]
    if resp and resp.url_final and resp.url_final not in urls:
        urls.append(resp.url_final)
    est.nos_por_id[url] = {
        "tipo": "no",
        "id": url,
        "tipo_no": "erro",
        "url_pedida": url,
        "url_final": resp.url_final if resp else None,
        "urls": urls,
        "profundidade": prof,
        "pedida": True,
        "pulada": False,
        "status": resp.status if resp else None,
        "redirecionamentos": resp.redirecionamentos if resp else [],
        "causa": causa,
    }
    est.alias_para_no[url] = url


def _checar_arquivo_head(ctx: _ContextoPercurso, url: str, prof: int | None) -> None:
    est = ctx.est
    teto_arquivos = max(ctx.cfg.teto * 2, MIN_TETO_ARQUIVOS)
    if url in est.arquivos_checados or len(est.arquivos_checados) >= teto_arquivos:
        if url in est.nos_por_id:
            _atualizar_prof_minima(est.nos_por_id[url], prof)
        return
    permitido, motivo = ctx.cortesia.pode_buscar(url)
    if not permitido:
        _registrar_pulada(est, url, motivo or "robots", prof)
        return
    est.arquivos_checados.add(url)
    try:
        resp = ctx.cortesia.pedir("HEAD", url)
    except _PuladaPorRobots as pul:
        _registrar_pulada(est, pul.url, pul.motivo, prof)
        return
    except FalhaFonte as exc:
        _registrar_erro_http(est, url, exc.causa, prof)
        return

    ct = extrator._mime(resp.cabecalho("content-type"))
    tam_raw = (resp.cabecalho("content-length") or "").strip()
    tamanho = int(tam_raw) if tam_raw.isdigit() else None
    formas = [url]
    for salto in resp.redirecionamentos:
        if salto["para"] not in formas:
            formas.append(salto["para"])
    if resp.url_final not in formas:
        formas.append(resp.url_final)
    est.nos_por_id[url] = {
        "tipo": "no",
        "id": url,
        "tipo_no": "arquivo",
        "metodo": "HEAD",
        "url_pedida": url,
        "url_final": resp.url_final,
        "urls": formas,
        "profundidade": prof,
        "pedida": True,
        "pulada": False,
        "status": resp.status,
        "redirecionamentos": resp.redirecionamentos,
        "tipo_conteudo": ct,
        "tamanho_bytes": tamanho,
    }
    for f in formas:
        est.alias_para_no[f] = url


def _ingerir_um_sitemap(ctx: _ContextoPercurso, url_sm: str) -> list[str]:
    est = ctx.est
    permitido, motivo = ctx.cortesia.pode_buscar(url_sm)
    if not permitido:
        _registrar_pulada(est, url_sm, motivo or "robots", None)
        est.sitemaps_lidos.append({"url": url_sm, "ok": False, "causa": motivo})
        return []
    try:
        resp = ctx.cortesia.pedir("GET", url_sm)
        if resp.status is None or not (_HTTP_OK_MIN <= resp.status < _HTTP_OK_MAX) or not resp.corpo:
            est.sitemaps_lidos.append({"url": url_sm, "ok": False, "status": resp.status})
            return []
        extraido = extrator.extrai_sitemap(resp.corpo)
    except (_PuladaPorRobots, FalhaFonte) as exc:
        causa = exc.motivo if isinstance(exc, _PuladaPorRobots) else exc.causa
        est.sitemaps_lidos.append({"url": url_sm, "ok": False, "causa": causa})
        return []

    chave_ord = lambda u: 0 if (est.prefixo_semente and u.startswith(est.prefixo_semente)) else 1
    subs = sorted(extraido["sitemaps"], key=chave_ord)
    adicionadas = 0
    for u_bruta in sorted(extraido["urls"], key=chave_ord):
        if len(est.urls_sitemap) >= MAX_URLS_SITEMAP:
            break
        u = urldefrag(u_bruta.strip())[0]
        if _chave_origem(u)[1] in est.dominios:
            est.urls_sitemap.add(u)
            adicionadas += 1
    est.sitemaps_lidos.append({"url": url_sm, "ok": True, "urls": adicionadas, "sitemaps": len(subs)})
    return subs


def _descobrir_sitemaps(ctx: _ContextoPercurso, semente: str) -> None:
    esquema, _, netloc = _chave_origem(semente)
    pol = ctx.cortesia.garantir_robots(semente)
    fila_sm = (
        list(pol.sitemaps)
        if pol.sitemaps
        else [f"{esquema}://{netloc}/sitemap.xml", f"{esquema}://{netloc}/sitemap.xml.gz"]
    )
    vistos_sm: set[str] = set()
    while fila_sm and len(vistos_sm) < MAX_SITEMAPS:
        url_sm = urldefrag(fila_sm.pop(0).strip())[0]
        if not url_sm or url_sm in vistos_sm or _chave_origem(url_sm)[1] not in ctx.est.dominios:
            continue
        vistos_sm.add(url_sm)
        for sub in _ingerir_um_sitemap(ctx, url_sm):
            if sub not in vistos_sm:
                fila_sm.append(sub)


def _formas_url_da_pagina(resp: extrator.Resposta, meta: dict[str, Any]) -> list[str]:
    formas: list[str] = []
    for cand in (
        resp.url_pedida,
        *(s["de"] for s in resp.redirecionamentos),
        *(s["para"] for s in resp.redirecionamentos),
        resp.url_final,
        meta.get("canonical"),
        meta.get("url_base"),
    ):
        if cand:
            limpa = urldefrag(str(cand))[0]
            if limpa and limpa not in formas:
                formas.append(limpa)
    return formas


def _fundir_no_pagina(
    est: _EstadoGrafo,
    resp: extrator.Resposta,
    meta: dict[str, Any],
    custodia: dict[str, Any],
    prof: int | None,
) -> str:
    url_final_limpa = urldefrag(resp.url_final)[0]
    chave_no = meta["canonical"] or url_final_limpa
    formas = _formas_url_da_pagina(resp, meta)
    em_sm = any(f in est.urls_sitemap for f in formas)
    existente = est.nos_por_id.get(chave_no)

    if existente is not None and existente.get("tipo_no") == "pagina":
        for f in formas:
            if f not in existente["urls"]:
                existente["urls"].append(f)
            est.alias_para_no[f] = chave_no
        _atualizar_prof_minima(existente, prof)
        if em_sm:
            existente["em_sitemap"] = True
        return chave_no

    novo = {
        "tipo": "no",
        "id": chave_no,
        "tipo_no": "pagina",
        "pedida": True,
        "pulada": False,
        "status": resp.status,
        "url_pedida": resp.url_pedida,
        "url_final": resp.url_final,
        "url_base": meta["url_base"],
        "redirecionamentos": resp.redirecionamentos,
        "canonical": meta["canonical"],
        "urls": formas,
        "profundidade": prof,
        "em_sitemap": em_sm,
        "titulo": meta["titulo"],
        "breadcrumb": meta["breadcrumb"],
        "data_visivel": meta["data_visivel"],
        "links_total": len(meta["links"]),
        **custodia,
    }
    est.nos_por_id[chave_no] = novo
    for f in formas:
        est.alias_para_no[f] = chave_no
    return chave_no


def _custodiar_pagina(
    trab: M.Trabalho,
    resp: extrator.Resposta,
    tipo: str,
    tipo_por: str,
    derivador: Callable[[str, str], dict[str, str]] | None,
) -> tuple[dict[str, Any], str]:
    sha = M.sha256_bytes(resp.corpo)
    n = trab.proximo_n()
    ext = extrator._EXT.get(tipo, "html")
    p_bruto = trab.guarda_bruto(n, resp.corpo, ext)
    trab.guarda_bruto(n, extrator._resposta_json(resp, sha, tipo, tipo_por), "resposta.json")

    ct = resp.cabecalho("content-type")
    html = tipo in extrator.TIPOS_HTML
    texto, _ = extrator.decodifica(resp.corpo, ct, html=html)
    if html:
        try:
            d = (derivador or extrator._derivador_crawl4ai)(texto, resp.url_final)
            md_fit = (d.get("md_fit") or "").strip()
            md_raw = (d.get("md_raw") or "").strip()
            md_principal = md_fit or md_raw
            if md_principal:
                trab.guarda_derivado(n, md_principal, "md")
            if md_fit and md_raw:
                trab.guarda_derivado(n, md_raw, "raw.md")
        except (FalhaFonte, extrator._SemDerivado, OSError, RuntimeError) as exc:
            sys.stderr.write(f"percorrer: aviso de derivação em {resp.url_final}: {exc}\n")
    elif texto.strip():
        trab.guarda_derivado(n, texto, "md")

    return {"n": n, "sha256": sha, "bruto": str(p_bruto), "tipo_real": tipo}, (texto if html else "")


def _processar_links_da_pagina(
    ctx: _ContextoPercurso,
    chave_no: str,
    url_origem: str,
    links: list[dict[str, Any]],
    prof: int | None,
) -> None:
    est = ctx.est
    ja_expandido = chave_no in est.canonicals_expandidos
    est.canonicals_expandidos.add(chave_no)
    prox_prof = (prof + 1) if prof is not None else None

    for lk in links:
        dest = lk["destino"]
        dom_ok = bool(dest and _chave_origem(dest)[1] in est.dominios)
        aresta = {
            "tipo": "aresta",
            "de": chave_no,
            "url_origem": url_origem,
            "href": lk["href"],
            "texto": lk["texto"],
            "destino": dest,
            "mesmo_dominio": lk["mesmo_dominio"],
            "dominio_permitido": dom_ok,
            "quebrada": lk["quebrada"],
            "motivo": lk["motivo"],
        }
        est.arestas.append(aresta)
        if ja_expandido or lk["quebrada"] or not dest or not dom_ok:
            continue
        permitido, mot_rob = ctx.cortesia.pode_buscar(dest)
        if not permitido:
            aresta["pulada"] = True
            aresta["motivo"] = mot_rob
            _registrar_pulada(est, dest, mot_rob or "robots", prox_prof)
            continue
        if eh_link_de_arquivo(dest):
            _checar_arquivo_head(ctx, dest, prox_prof)
            continue
        if prof is not None and prof >= ctx.cfg.profundidade_max:
            est.bateu_profundidade = True
            continue
        if prox_prof is not None:
            est.enfileirar_clique(dest, prox_prof)


def _visitar_uma_pagina(ctx: _ContextoPercurso, url: str, prof: int | None) -> None:
    est = ctx.est
    permitido, motivo = ctx.cortesia.pode_buscar(url)
    if not permitido:
        _registrar_pulada(est, url, motivo or "robots", prof)
        return
    if eh_link_de_arquivo(url):
        _checar_arquivo_head(ctx, url, prof)
        return
    if est.paginas_get >= ctx.cfg.teto:
        est.bateu_teto = True
        return

    est.visitadas_get.add(url)
    est.paginas_get += 1
    try:
        resp = ctx.cortesia.pedir("GET", url)
    except _PuladaPorRobots as pul:
        _registrar_pulada(est, pul.url, pul.motivo, prof)
        return
    except FalhaFonte as exc:
        ctx.trab.grava_linha(
            {"ato": "percorrer", "url": url, "nao_achado": True, "causa": exc.causa, "ua": M.UA_PERCORRER}
        )
        _registrar_erro_http(est, url, exc.causa, prof)
        return

    if resp.status is None or not (_HTTP_OK_MIN <= resp.status < _HTTP_OK_MAX) or not resp.corpo:
        causa = f"status-{resp.status}" if resp.status else "corpo-vazio"
        ctx.trab.grava_linha(
            {
                "ato": "percorrer",
                "url": url,
                "url_final": resp.url_final,
                "status": resp.status,
                "nao_achado": True,
                "causa": causa,
                "ua": M.UA_PERCORRER,
            }
        )
        _registrar_erro_http(est, url, causa, prof, resp=resp)
        return

    tipo, tipo_por = extrator.tipo_real(resp.corpo, resp.cabecalho("content-type"))
    custodia, html_txt = _custodiar_pagina(
        ctx.trab, resp, tipo, tipo_por, ctx.cortesia.rede.derivador
    )
    meta = (
        extrator.extrai_metadados_pagina(html_txt, resp.url_final)
        if tipo in extrator.TIPOS_HTML
        else {
            "url_base": resp.url_final,
            "canonical": None,
            "titulo": None,
            "breadcrumb": [],
            "data_visivel": None,
            "links": [],
        }
    )
    chave_no = _fundir_no_pagina(est, resp, meta, custodia, prof)
    ctx.trab.grava_linha(
        {
            "ato": "percorrer",
            "n": custodia["n"],
            "url": resp.url_pedida,
            "url_final": resp.url_final,
            "canonical": meta["canonical"],
            "profundidade": est.nos_por_id[chave_no]["profundidade"],
            "status": resp.status,
            "sha256": custodia["sha256"],
            "bruto": custodia["bruto"],
            "tipo": tipo,
            "tipo_por": tipo_por,
            "titulo": meta["titulo"],
            "breadcrumb": meta["breadcrumb"],
            "data_visivel": meta["data_visivel"],
            "redirecionamentos": resp.redirecionamentos,
            "bytes": len(resp.corpo),
            "nao_achado": False,
            "ua": M.UA_PERCORRER,
        }
    )
    _processar_links_da_pagina(ctx, chave_no, resp.url_final, meta["links"], prof)


def _gravar_grafo_jsonl(trab: M.Trabalho, est: _EstadoGrafo) -> tuple[Path, str, list[dict[str, Any]]]:
    nos = list(est.nos_por_id.values())
    linhas_jsonl: list[str] = [json.dumps(no, ensure_ascii=False) for no in nos]
    for ar in est.arestas:
        dest = ar.get("destino")
        enriquecida = {
            **ar,
            "destino_no": est.alias_para_no.get(dest, dest) if dest else None,
        }
        linhas_jsonl.append(json.dumps(enriquecida, ensure_ascii=False))
    conteudo = ("\n".join(linhas_jsonl) + "\n").encode("utf-8") if linhas_jsonl else b""
    sha = M.sha256_bytes(conteudo)
    p_grafo = trab.dir / "grafo.jsonl"
    p_grafo.write_bytes(conteudo)
    return p_grafo, sha, nos


def _motivo_parada(est: _EstadoGrafo) -> str:
    if est.bateu_teto:
        return "teto"
    if est.bateu_profundidade:
        return "profundidade"
    return "esgotado"


def _drenar_fila(ctx: _ContextoPercurso) -> None:
    est = ctx.est
    while est.fila:
        _, _, _, _, _, url, prof = heapq.heappop(est.fila)
        if url in est.visitadas_get:
            no_id = est.alias_para_no.get(url)
            if no_id and no_id in est.nos_por_id:
                _atualizar_prof_minima(est.nos_por_id[no_id], prof)
            continue
        if est.paginas_get >= ctx.cfg.teto and not eh_link_de_arquivo(url):
            est.bateu_teto = True
            break
        _visitar_uma_pagina(ctx, url, prof)


def percorrer(
    cfg: ConfigPercurso,
    trab: M.Trabalho,
    *,
    opcoes_rede: OpcoesRede | None = None,
) -> dict[str, Any]:
    """Executa o percurso em largura e devolve o resumo + referência ao `grafo.jsonl`."""
    semente, dominios, prefixo = _validar_config(cfg)
    rede = opcoes_rede or OpcoesRede()
    cortesia = _ControladorCortesia(cfg.intervalo_s, dominios, rede)
    est = _EstadoGrafo(dominios=dominios, prefixo_semente=prefixo)
    ctx = _ContextoPercurso(cfg=cfg, trab=trab, cortesia=cortesia, est=est)

    with contextlib.redirect_stdout(sys.stderr):
        try:
            cortesia.verifica_guarda(semente)
            _descobrir_sitemaps(ctx, semente)
            est.enfileirar_clique(semente, 0)

            while True:
                _drenar_fila(ctx)
                if est.bateu_teto or est.paginas_get >= cfg.teto:
                    break
                pendentes_sm = [
                    u
                    for u in sorted(
                        est.urls_sitemap,
                        key=lambda x: 0 if (prefixo and x.startswith(prefixo)) else 1,
                    )
                    if u not in est.visitadas_get
                    and u not in est.alias_para_no
                    and u not in est.enfileiradas_sitemap
                ]
                if not pendentes_sm:
                    break
                for u_sm in pendentes_sm:
                    est.enfileirar_sitemap(u_sm, cfg.profundidade_max + 1)
        finally:
            cortesia.fechar()

    p_grafo, sha_grafo, nos = _gravar_grafo_jsonl(trab, est)
    paginas_ok = [n for n in nos if n.get("tipo_no") == "pagina"]
    puladas = [n for n in nos if n.get("tipo_no") == "pulada"]
    arquivos = [n for n in nos if n.get("tipo_no") == "arquivo"]
    erros = [n for n in nos if n.get("tipo_no") == "erro"]
    quebradas = [a for a in est.arestas if a.get("quebrada")]
    parou_por = _motivo_parada(est)

    linha_m = trab.grava_linha(
        {
            "ato": "percorrer",
            "semente": semente,
            "dominios": sorted(dominios),
            "profundidade_max": cfg.profundidade_max,
            "teto": cfg.teto,
            "parou_por": parou_por,
            "status": 200,
            "paginas": len(paginas_ok),
            "nos": len(nos),
            "arestas": len(est.arestas),
            "arestas_quebradas": len(quebradas),
            "puladas_robots": len(puladas),
            "arquivos_head": len(arquivos),
            "grafo": str(p_grafo),
            "sha256": sha_grafo,
            "ua": M.UA_PERCORRER,
        }
    )

    return {
        "semente": semente,
        "dominios": sorted(dominios),
        "profundidade_max": cfg.profundidade_max,
        "teto": cfg.teto,
        "intervalo_s": cfg.intervalo_s,
        "parou_por": parou_por,
        "resumo": {
            "paginas_visitadas": len(paginas_ok),
            "requisicoes_get": est.paginas_get,
            "nos": len(nos),
            "arestas": len(est.arestas),
            "arestas_quebradas": len(quebradas),
            "puladas_robots": len(puladas),
            "arquivos_head": len(arquivos),
            "erros_http": len(erros),
            "canonicals_com_multiplas_urls": sum(1 for p in paginas_ok if len(p.get("urls", [])) > 1),
            "esperas_cortesia": len(cortesia.esperas),
            "conexoes_por_host": cortesia.conexoes_criadas,
        },
        "sitemaps": est.sitemaps_lidos,
        "grafo": {
            "arquivo": str(p_grafo),
            "sha256": sha_grafo,
            "nos": len(nos),
            "arestas": len(est.arestas),
        },
        "nos": nos,
        "arestas_quebradas": quebradas,
        "manifesto": trab.ref_manifesto(linha_m),
    }
