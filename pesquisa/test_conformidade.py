"""Conformidade contra os REAIS — SearXNG e Crawl4AI (spec §8.6).

Roda só quando o serviço responde; senão PULA com motivo impresso. Nunca reprova o build
por falta de infra que é de TI (stack `searxng`) — a suíte de contrato é que fecha as
stories de ia. Estes testes fecham a story da stack quando TI a sobe.
"""

from __future__ import annotations

import os

import pytest

from pesquisa import manifesto as M


def _searxng_no_ar() -> bool:
    try:
        import httpx

        from pesquisa import searxng
        r = httpx.get(searxng.BASE + "/search", params={"q": "ping", "format": "json"}, timeout=3.0)
        return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False


def _crawl4ai_utilizavel() -> bool:
    try:
        import crawl4ai  # noqa: F401
        from pathlib import Path
        cache = Path.home() / ".cache" / "ms-playwright"
        return cache.exists() and any(cache.glob("chromium-*"))
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _searxng_no_ar(), reason="SearXNG fora (stack de TI não promovida): conformidade pulada")
def test_conformidade_consultar_real():
    from pesquisa import searxng
    r = searxng.consultar("crawl4ai fit markdown", k=5, categoria="geral")
    assert isinstance(r["resultados"], list)
    assert r["engines_ok"], "nenhum engine respondeu à sonda real"


@pytest.mark.skipif(not (_crawl4ai_utilizavel()), reason="Crawl4AI/Chromium indisponível: conformidade pulada")
def test_conformidade_ler_real(tmp_path):
    from pesquisa import extrator
    t = M.Trabalho("conf-ler", raiz=tmp_path)
    r = extrator.ler("https://example.com/", t, max_chars=2000)
    assert r["status"] == 200 and r["sha256"]
    # sha256 do retorno bate com o do bruto no disco
    bruto = (t.bruto / f"{r['n']}.html").read_bytes()
    assert M.sha256_bytes(bruto) == r["sha256"]
