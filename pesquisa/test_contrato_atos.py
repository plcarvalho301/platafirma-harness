# componente: componente:verbo-pesquisar
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
    corpo = b"PK\x03\x04fakezip"
    monkeypatch.setattr(extrator, "_coletor_httpx",
                        lambda url, verifica: extrator.Resposta(corpo=corpo, status=200,
                                                               cabecalhos=[("content-type", "application/zip")],
                                                               url_pedida=url, url_final=url,
                                                               hora="2026-11-06T12:00:00Z"))
    env = atos.ler("http://93.184.216.34/arquivo.zip", foco=None, render=False, max_chars=6000, offset=0, trab=t)
    assert env["ok"] is True
    assert env["tipo"] == "dado"
    assert env["tipo_real"] == "application/zip"
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


def test_resolver_doi_usa_select_e_devolve_resumo_sem_registro(tmp_path, monkeypatch):
    import json
    chamadas = []

    def falso_fetch(url, headers):
        chamadas.append(url)
        corpo = json.dumps({
            "status": "ok",
            "message": {
                "items": [{
                    "DOI": "10.1145/3597503",
                    "title": ["Estudo de Caso"],
                    "author": [{"given": "Ana", "family": "Silva"}, {"name": "Grupo X"}],
                    "published": {"date-parts": [[2024, 5, 1]]},
                    "container-title": ["Anais"],
                    "publisher": "ACM",
                    "ISSN": ["1234-5678"],
                    "type": "proceedings-article",
                    "URL": "https://doi.org/10.1145/3597503",
                }],
            },
        }).encode()
        return 200, corpo

    t = M.Trabalho("a8", raiz=tmp_path)
    monkeypatch.setattr(resolvedores, "_fetch_httpx", falso_fetch)
    env = atos.resolver("doi", "https://doi.org/10.1145/3597503", trab=t)
    assert chamadas == [
        "https://api.crossref.org/works?filter=doi:10.1145/3597503&select="
        "DOI,title,author,published,issued,container-title,publisher,ISSN,ISBN,type,URL"
    ]
    assert env["resolvido"] is True
    assert "registro" not in env
    assert env["resumo"] == {
        "titulo": "Estudo de Caso",
        "autores": ["Ana Silva", "Grupo X"],
        "ano": 2024,
        "veiculo": "Anais",
        "editora": "ACM",
        "tipo": "proceedings-article",
        "identificadores": {
            "doi": "10.1145/3597503",
            "issn": ["1234-5678"],
            "url": "https://doi.org/10.1145/3597503",
        },
    }


def test_resolver_doi_vazio_marca_nao_achado(tmp_path, monkeypatch):
    import json

    def falso_fetch(url, headers):
        return 200, json.dumps({"status": "ok", "message": {"items": []}}).encode()

    t = M.Trabalho("a9", raiz=tmp_path)
    monkeypatch.setattr(resolvedores, "_fetch_httpx", falso_fetch)
    env = atos.resolver("doi", "10.0/inexistente", trab=t)
    assert env["resolvido"] is False
    assert t.linhas()[-1]["nao_achado"] is True


def test_resolver_doi_completo_usa_works_e_devolve_registro(tmp_path, monkeypatch):
    import json
    chamadas = []

    def falso_fetch(url, headers):
        chamadas.append(url)
        return 200, json.dumps({"status": "ok", "message": {"DOI": "10.1/x", "reference": [1, 2]}}).encode()

    t = M.Trabalho("a10", raiz=tmp_path)
    monkeypatch.setattr(resolvedores, "_fetch_httpx", falso_fetch)
    env = atos.resolver("doi", "10.1/x", completo=True, trab=t)
    assert chamadas == ["https://api.crossref.org/works/10.1/x"]
    assert env["resolvido"] is True
    assert env["registro"] == {"status": "ok", "message": {"DOI": "10.1/x", "reference": [1, 2]}}
