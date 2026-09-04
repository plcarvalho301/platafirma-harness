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


# --- prova de vida: quem respondeu × quem achou ------------------------------
# A forma 2026.9 não traz o campo `engines`: quem respondeu tem de ser inferido. Inferir
# de results[].engine torna invisível o engine que responde "não tenho nada", e foi isso
# que classificou não-achado como fonte fora. Vida se prova pelo complemento.


def _config(nomes, categoria="science"):
    """/config falso: engines habilitados na categoria."""
    return lambda base, params: {
        "engines": [{"name": n, "enabled": True, "categories": [categoria]} for n in nomes]
    }


def _fake_2026(resultados, unresponsive=()):
    """Resposta da 2026.9: sem campo `engines`, com unresponsive_engines [nome, motivo]."""
    return lambda base, params: {
        "results": resultados,
        "unresponsive_engines": [list(u) for u in unresponsive],
    }


def test_nao_achado_com_engines_em_timeout_nao_e_fonte_fora():
    """O defeito, medido no SearXNG real em 04/09: consulta trivial em `ciencia` volta 0
    resultados com openaire{datasets,publications} em timeout — os outros 5 responderam e
    não acharam nada. Saía FalhaFonte, e um não-achado legítimo sumia do relatório como
    se ninguém tivesse procurado."""
    searxng._HABILITADOS.clear()
    r = searxng.consultar(
        "zxqwv-nao-existe-mesmo-9182734", categoria="ciencia",
        fetch=_fake_2026([], unresponsive=[("openairedatasets", "timeout"),
                                           ("openairepublications", "timeout")]),
        fetch_config=_config(["arxiv", "google scholar", "openairedatasets",
                              "openairepublications", "pdbe", "pubmed", "semantic scholar"]),
    )
    assert r["resultados"] == []
    assert r["engines_ok"] == []  # ninguém produziu resultado — cobertura zero
    assert r["engines_vivos"] == ["arxiv", "google scholar", "pdbe", "pubmed",
                                  "semantic scholar"]  # mas 5 responderam
    assert r["engines_falha"] == ["openairedatasets", "openairepublications"]


def test_todos_os_habilitados_fora_continua_sendo_fonte_fora():
    """A outra ponta segue firme: caindo todos os habilitados, não há não-achado a
    afirmar — ninguém procurou, e isso é falha de fonte."""
    searxng._HABILITADOS.clear()
    with pytest.raises(FalhaFonte):
        searxng.consultar(
            "q", categoria="ciencia",
            fetch=_fake_2026([], unresponsive=[("arxiv", "timeout"), ("pubmed", "timeout")]),
            fetch_config=_config(["arxiv", "pubmed"]),
        )


def test_config_mudo_deixa_vivos_indeterminado_e_nao_inventa_falha():
    """Sem /config não se sabe quem devia responder. Indeterminado se declara (`null`) e
    não vira juízo: o HTTP 200 já prova que o SearXNG não está fora, e fabricar falha de
    fonte é o erro mais caro dos dois."""
    searxng._HABILITADOS.clear()
    r = searxng.consultar(
        "q", categoria="ciencia", fetch=_fake_2026([], unresponsive=[("arxiv", "timeout")]),
        fetch_config=lambda base, params: {},  # /config sem engines
    )
    assert r["resultados"] == []
    assert r["engines_vivos"] is None
    assert r["engines_falha"] == ["arxiv"]


def test_habilitados_e_cacheado_por_processo():
    """Uma leitura de /config por processo: a lista só muda por deploy (settings.yml é
    política do dono), nunca no meio de um trabalho."""
    searxng._HABILITADOS.clear()
    chamadas = []

    def config(base, params):
        chamadas.append(base)
        return {"engines": [{"name": "arxiv", "enabled": True, "categories": ["science"]}]}

    for _ in range(3):
        searxng.consultar("q", categoria="ciencia",
                          fetch=_fake_2026([{"url": "https://a.org/1", "title": "a",
                                             "content": "", "engine": "arxiv"}]),
                          fetch_config=config)
    assert len(chamadas) == 1
