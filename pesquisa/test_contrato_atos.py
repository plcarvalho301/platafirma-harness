"""Contrato dos atos — consultar/resolver gravam não-achado; manifesto renderiza (spec §4.1, §4.1b, §4.5)."""

from __future__ import annotations

from pesquisa import atos, extrator, manifesto as M, resolvedores, searxng


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


def test_ler_binario_envelope_e_campos(tmp_path, monkeypatch):
    t = M.Trabalho("a6", raiz=tmp_path)
    corpo = b"%PDF-1.7\nteste"
    monkeypatch.setattr(extrator, "_coletor_httpx",
                        lambda url, verifica: extrator.Resposta(corpo=corpo, status=200,
                                                               cabecalhos=[("content-type", "application/pdf")],
                                                               url_pedida=url, url_final=url,
                                                               hora="2026-11-06T12:00:00Z"))
    env = atos.ler("http://93.184.216.34/arquivo.pdf", foco=None, render=False, max_chars=6000, offset=0, trab=t)
    assert env["ok"] is True
    assert env["tipo"] == "dado"
    assert env["tipo_real"] == "application/pdf"
    assert env["binario"] is True
    assert env["conteudo"] is None


def test_coletar_com_imagens_passa_parametro(tmp_path, monkeypatch):
    t = M.Trabalho("a7", raiz=tmp_path)
    chamadas = []
    def falso_ler(url, trab, **kw):
        chamadas.append((url, kw.get("imagens")))
        return {"n": 1, "sha256": "abc", "status": 200, "tipo_real": "text/html", "binario": False, "imagens": []}
    monkeypatch.setattr(extrator, "ler", falso_ler)
    res = atos.coletar(["http://x.org"], imagens=True, trab=t)
    assert chamadas == [("http://x.org", True)]
    assert res["ok"] is True
