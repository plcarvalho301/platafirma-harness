"""Contrato do cliente SearXNG — consultar (spec §4.1) com SearXNG falso."""

from __future__ import annotations

import pytest

from pesquisa import searxng
from pesquisa.envelope import FalhaFonte


def _fake(resultados, engines=None):
    payload = {
        "results": resultados,
        "engines": engines or [{"name": "duckduckgo"}, {"name": "brave"}],
    }
    return lambda base, params: payload


def test_dedup_por_url_canonica():
    res = [
        {"url": "https://a.org/x/", "title": "A", "content": "t", "engine": "ddg"},
        {"url": "https://a.org/x", "title": "A dup", "content": "t2", "engine": "brave"},
        {"url": "https://b.org/y", "title": "B", "content": "t3", "engine": "ddg"},
    ]
    r = searxng.consultar("q", fetch=_fake(res))
    urls = [x["url"] for x in r["resultados"]]
    assert urls == ["https://a.org/x/", "https://b.org/y"]  # a.org/x colapsou


def test_k_limita():
    res = [{"url": f"https://s{i}.org/", "title": str(i), "content": "", "engine": "ddg"} for i in range(20)]
    r = searxng.consultar("q", k=5, fetch=_fake(res))
    assert len(r["resultados"]) == 5


def test_zero_resultado_nao_e_erro():
    r = searxng.consultar("consulta absurda", fetch=_fake([]))
    assert r["resultados"] == [] and r["engines_ok"]  # engines responderam, zero achado


def test_nenhum_engine_respondeu_e_falha():
    with pytest.raises(FalhaFonte):
        searxng.consultar("q", fetch=lambda b, p: {"results": [], "engines": []})


def test_categoria_desconhecida_recusa():
    with pytest.raises(FalhaFonte):
        searxng.consultar("q", categoria="inexistente", fetch=_fake([]))


def test_desde_filtra_por_ano():
    res = [
        {"url": "https://n.org/1", "title": "novo", "content": "", "engine": "d", "publishedDate": "2025-03-01"},
        {"url": "https://v.org/2", "title": "velho", "content": "", "engine": "d", "publishedDate": "2010-01-01"},
    ]
    r = searxng.consultar("q", desde=2020, fetch=_fake(res))
    assert [x["dominio"] for x in r["resultados"]] == ["n.org"]
