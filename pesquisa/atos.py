"""Os oito atos, cada um devolvendo o envelope do §4 — orquestra fina sobre os módulos.

Aqui mora a consequência que não depende de lembrança (§2.3): consultar e resolver
gravam a linha de resultado OU a de não-achado, sempre, sem flag. `ler`/`coletar`/
`historico` delegam a gravação aos seus módulos. Nenhum ato decide política de recorte —
isso é do dono (settings.yml).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from . import extrator, historico, manifesto as M, resolvedores, searxng, verificar as V
from .envelope import FalhaFonte, envelope


# ---------------------------------------------------------------------- consultar
def consultar(consulta, *, k, categoria, desde, idioma, trab: "M.Trabalho") -> dict[str, Any]:
    r = searxng.consultar(consulta, k=k, categoria=categoria, desde=desde, idioma=idioma)
    resultados = r["resultados"]
    if resultados:
        linha = trab.grava_linha({
            "ato": "consultar", "consulta": consulta, "categoria": categoria,
            "status": 200, "resultado": len(resultados), "engines_ok": r["engines_ok"],
        })
    else:
        linha = trab.grava_linha({
            "ato": "consultar", "consulta": consulta, "categoria": categoria,
            "status": 200, "nao_achado": True, "resultados": 0, "engines_ok": r["engines_ok"],
        })
    return envelope("consultar", trab.slug, consulta=consulta, categoria=categoria,
                    resultados=resultados, engines_ok=r["engines_ok"],
                    engines_falha=r["engines_falha"], manifesto=trab.ref_manifesto(linha))


# ------------------------------------------------------------------------ resolver
def resolver(tipo, ident, *, trab: "M.Trabalho") -> dict[str, Any]:
    r = resolvedores.resolver(tipo, ident)
    n = trab.proximo_n()
    if r["resolvido"]:
        trab.guarda_bruto(n, r["bruto_bytes"] or b"", "json")
        import json as _j
        trab.guarda_derivado(n, _j.dumps(r["registro"], ensure_ascii=False, indent=2), "json")
        sha = M.sha256_bytes(r["bruto_bytes"] or b"")
        linha = trab.grava_linha({
            "n": n, "ato": "resolver", "tipo": tipo, "identificador": ident,
            "url": r["url"], "status": r["status"], "sha256": sha,
            "bruto": str(trab.bruto / f"{n}.json"), "resolvedor": r["resolvedor"],
        })
        return envelope("resolver", trab.slug, tipo=tipo, identificador=ident,
                        resolvido=True, resolvedor=r["resolvedor"], status=r["status"],
                        sha256=sha, registro=r["registro"], manifesto=trab.ref_manifesto(linha))
    linha = trab.grava_linha({
        "ato": "resolver", "tipo": tipo, "identificador": ident, "url": r["url"],
        "status": r["status"], "nao_achado": True, "resolvedor": r["resolvedor"],
    })
    return envelope("resolver", trab.slug, tipo=tipo, identificador=ident, resolvido=False,
                    resolvedor=r["resolvedor"], status=r["status"], manifesto=trab.ref_manifesto(linha))


# ----------------------------------------------------------------------------- ler
def ler(url, *, foco, render, max_chars, offset, trab: "M.Trabalho") -> dict[str, Any]:
    r = extrator.ler(url, trab, foco=foco, render=render, max_chars=max_chars, offset=offset)
    return envelope("ler", trab.slug, **r)


# ------------------------------------------------------------------------- coletar
def coletar(urls, *, trab: "M.Trabalho") -> dict[str, Any]:
    """`ler` sem devolver conteúdo: só grava e manifesta. Paralelo com teto de 4 (§4.3)."""
    def _um(u):
        try:
            r = extrator.ler(u, trab, foco=None, render=False, max_chars=0, offset=0)
            return {"url": u, "n": r["n"], "sha256": r["sha256"], "status": r["status"], "ok": True}
        except FalhaFonte as f:
            return {"url": u, "ok": False, "causa": f.causa}

    with ThreadPoolExecutor(max_workers=4) as ex:
        colhidos = list(ex.map(_um, urls))
    return envelope("coletar", trab.slug, coletados=colhidos, total=len(colhidos),
                    manifesto={"arquivo": str(trab.manifesto)})


# ----------------------------------------------------------------------- historico
def hist(url, *, em, salvar, trab: "M.Trabalho") -> dict[str, Any]:
    if salvar:
        r = historico.salvar(url)
        linha = trab.grava_linha({"ato": "historico", "url": url, "status": r["status"],
                                  "arquivo_terceiro": r["arquivo_terceiro"]})
        return envelope("historico", trab.slug, url=url, **r, manifesto=trab.ref_manifesto(linha))
    if em:
        alvo = historico.url_captura(url, em)
        r = extrator.ler(alvo, trab, foco=None, render=False, max_chars=6000, offset=0)
        r["origem"] = "arquivo"
        return envelope("historico", trab.slug, url=url, em=em, **r)
    r = historico.capturas(url)
    linha = trab.grava_linha({"ato": "historico", "url": url, "status": 200,
                              "resultado": r["total"], **({"nao_achado": True} if not r["total"] else {})})
    return envelope("historico", trab.slug, url=url, **r, manifesto=trab.ref_manifesto(linha))


# ------------------------------------------------------------------------ manifesto
def manifesto(trab: "M.Trabalho", *, md: bool = False) -> dict[str, Any]:
    linhas = trab.linhas()
    env = envelope("manifesto", trab.slug, linhas=linhas, total=len(linhas),
                   arquivo=str(trab.manifesto))
    if md:
        env["_md"] = render_md(trab.slug, linhas)
    return env


def render_md(slug: str, linhas: list[dict[str, Any]]) -> str:
    """Vista humana (molde skills/osint §5). Uma fonte, duas vistas."""
    out = [f"# Manifesto de pesquisa — trabalho `{slug}`", "", f"{len(linhas)} atos.", ""]
    for i, ln in enumerate(linhas, 1):
        alvo = ln.get("url") or ln.get("consulta") or ln.get("identificador") or "—"
        marca = "∅ não-achado" if ln.get("nao_achado") else ln.get("status", "")
        n = f"[m:{ln['n']}] " if isinstance(ln.get("n"), int) else ""
        out.append(f"{i}. {n}`{ln.get('ato')}` {alvo} — {marca}  ({ln.get('ts','')})")
        if ln.get("sha256"):
            out.append(f"   sha256 `{ln['sha256'][:16]}…`  bruto `{ln.get('bruto','')}`")
    return "\n".join(out)


# ------------------------------------------------------------------------- verificar
def verificar(relatorio, *, trab: "M.Trabalho") -> dict[str, Any]:
    r = V.verificar(relatorio, trab)
    return envelope("verificar", trab.slug, ok=not r["reprovou"], **r,
                    relatorio=str(Path(relatorio)))


# ---------------------------------------------------------------------------- saude
def saude(*, trab: "M.Trabalho | None" = None) -> dict[str, Any]:
    """engines_ok/total, latência da sonda, versões, Chromium presente (§4.7)."""
    import concurrent.futures as cf
    import shutil
    import time

    engines_ok: list[str] = []
    engines_total = 0
    latencia_ms = None
    causa = None
    # A saude do servico e o que ele ENTREGA no conjunto curado, nao numa categoria so:
    # `geral` sozinha vive castigada por anti-bot (google responde, brave/ddg/startpage
    # nao), entao sondar so ela cravava saudavel=false com o searxng no ar e util. Sonda
    # todas as categorias e agrega os engines distintos — reflete a capacidade real.
    ok: set[str] = set()
    falha: set[str] = set()
    causas: list[str] = []

    def _sonda(cat: str):
        return cat, searxng.consultar("platafirma sonda saude", k=1, categoria=cat)

    # Sondas em paralelo: em serie o probe somava a latencia das 4 categorias (~10s),
    # cada uma esperando engine externo lento. Um healthcheck nao pode custar isso.
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=len(searxng.CATEGORIAS)) as ex:
        futs = {ex.submit(_sonda, c): c for c in searxng.CATEGORIAS}
        for fut in cf.as_completed(futs):
            try:
                _, r = fut.result()
                ok.update(r["engines_ok"])
                falha.update(r["engines_falha"])
            except FalhaFonte as f:
                causas.append(f"{futs[fut]}:{f.causa}")
    latencia_ms = int((time.time() - t0) * 1000)
    engines_ok = sorted(ok)
    engines_total = len(ok | falha)
    # `causa` so quando o servico nao entregou NADA em categoria alguma (searxng fora) —
    # uma categoria isolada capengando por anti-bot nao derruba o juizo de saude.
    if not ok and causas:
        causa = "; ".join(causas)

    try:
        import crawl4ai
        ver_crawl = getattr(getattr(crawl4ai, "__version__", None), "__version__", None) or "instalado"
    except Exception:  # noqa: BLE001
        ver_crawl = None
    chromium = bool(shutil.which("chromium") or shutil.which("chromium-browser")) or \
        _tem_chromium_playwright()

    # relatorio: o comando teve sucesso mesmo com o SearXNG fora — a saude esta no corpo
    # (engines_ok/causa), lida por `sinal`. `saudavel` e o juizo; `ok` e "o probe rodou".
    # O farol `saudavel` e liveness+utilidade minima ESTAVEL, nao cobertura: o servico
    # responde (causa None) e ha fontes distintas respondendo acima de um piso baixo. A
    # contagem de engines oscila com o anti-bot dos buscadores web (`geral`); amarrar o
    # farol num numero alto o fazia piscar e cravava false com o servico no ar. Piso 3
    # fica sob o patamar estavel dos engines-ancora (APIs cientificas, cse, mastodon:
    # ~6), tolera oscilacao/manutencao de fonte isolada e so cai em degradacao real. A
    # cobertura fina para diagnostico vive em engines_ok/engines_total, nao no farol.
    return envelope("saude", trab.slug if trab else "-",
                    saudavel=causa is None and len(engines_ok) >= 3,
                    engines_ok=engines_ok, engines_total=engines_total,
                    latencia_ms=latencia_ms, searxng_url=searxng.BASE,
                    crawl4ai=ver_crawl, chromium=chromium, causa=causa)


def _tem_chromium_playwright() -> bool:
    from pathlib import Path as _P
    cache = _P.home() / ".cache" / "ms-playwright"
    return cache.exists() and any(cache.glob("chromium-*"))
