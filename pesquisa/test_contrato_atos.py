"""Contrato dos atos — consultar/resolver gravam não-achado; manifesto renderiza (spec §4.1, §4.1b, §4.5)."""

from __future__ import annotations

from pesquisa import atos, manifesto as M, resolvedores, searxng


def test_consultar_grava_nao_achado_quando_zero(tmp_path, monkeypatch):
    t = M.Trabalho("a1", raiz=tmp_path)
    monkeypatch.setattr(searxng, "consultar",
                        lambda *a, **k: {"resultados": [], "engines_ok": ["ddg"], "engines_falha": []})
    env = atos.consultar("consulta absurda", k=8, categoria="geral", desde=None, idioma="auto", trab=t)
    assert env["ok"] and env["resultados"] == []
    linha = t.linhas()[-1]
    assert linha.get("nao_achado") is True and linha["resultados"] == 0


def test_consultar_grava_resultado(tmp_path, monkeypatch):
    t = M.Trabalho("a2", raiz=tmp_path)
    monkeypatch.setattr(searxng, "consultar",
                        lambda *a, **k: {"resultados": [{"n": 1, "url": "https://x.org", "titulo": "X",
                                                          "trecho": "", "engines": ["ddg"], "data": None,
                                                          "dominio": "x.org"}],
                                         "engines_ok": ["ddg"], "engines_falha": []})
    env = atos.consultar("q", k=8, categoria="geral", desde=None, idioma="auto", trab=t)
    assert env["resultados"][0]["url"] == "https://x.org"
    assert t.linhas()[-1]["resultado"] == 1


def test_resolver_nao_achado(tmp_path, monkeypatch):
    t = M.Trabalho("a3", raiz=tmp_path)
    monkeypatch.setattr(resolvedores, "resolver",
                        lambda tipo, ident, **k: {"status": 404, "url": "https://api/doi/x",
                                                  "resolvedor": "crossref", "resolvido": False,
                                                  "bruto_bytes": b"", "registro": None})
    env = atos.resolver("doi", "10.0/naoexiste", trab=t)
    assert env["resolvido"] is False
    assert t.linhas()[-1]["nao_achado"] is True


def test_resolver_grava_bruto_e_derivado(tmp_path, monkeypatch):
    t = M.Trabalho("a4", raiz=tmp_path)
    reg = {"title": "Obra", "author": "X"}
    import json
    monkeypatch.setattr(resolvedores, "resolver",
                        lambda tipo, ident, **k: {"status": 200, "url": "https://api/doi/x",
                                                  "resolvedor": "crossref", "resolvido": True,
                                                  "bruto_bytes": json.dumps(reg).encode(), "registro": reg})
    env = atos.resolver("doi", "10.1/abc", trab=t)
    n = t.linhas()[-1]["n"]
    assert env["resolvido"] and (t.bruto / f"{n}.json").exists() and (t.derivado / f"{n}.json").exists()


def test_manifesto_render_md(tmp_path):
    t = M.Trabalho("a5", raiz=tmp_path)
    t.grava_linha({"n": 1, "ato": "ler", "url": "https://f.org", "status": 200, "sha256": "abc" * 21 + "d"})
    env = atos.manifesto(t, md=True)
    assert "[m:1]" in env["_md"] and "Manifesto de pesquisa" in env["_md"]
