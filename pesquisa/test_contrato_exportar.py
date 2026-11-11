"""Contrato de `pesquisar exportar`: um arquivo por URL, o último bruto íntegro, sem sobrescrever."""

from __future__ import annotations

import json

from pesquisa import exportar as X
from pesquisa import manifesto as M


def _ler(t, n, url, corpo, ext="html", status=200, **extra):
    p = t.guarda_bruto(n, corpo, ext)
    t.grava_linha({"n": n, "ato": "ler", "url": url, "status": status,
                   "sha256": M.sha256_bytes(corpo), "bruto": str(p), **extra})
    return p


def test_um_arquivo_por_url_o_ultimo_integro(tmp_path):
    t = M.Trabalho("t", raiz=tmp_path / "pesq")
    _ler(t, 1, "https://ex.org/a/", b"<html>velho</html>")
    _ler(t, 2, "https://ex.org/a/", b"<html>novo</html>")
    _ler(t, 3, "https://ex.org/b/index.md", b"# b", ext="md")
    t.grava_linha({"ato": "ler", "url": "https://ex.org/a/", "status": 200, "sha256": "x", "bruto": ""})  # cache
    t.grava_linha({"n": 4, "ato": "ler", "url": "https://ex.org/c", "status": 404, "nao_achado": True})
    r = X.exportar(t, "lote", raiz=tmp_path / "entrada")
    nomes = sorted(e["arquivo"] for e in r["exportados"])
    assert nomes == ["b.md", "ex.org_a.html"]
    assert (tmp_path / "entrada/lote/ex.org_a.html").read_bytes() == b"<html>novo</html>"
    proc = [json.loads(l) for l in (tmp_path / "entrada/lote/PROCEDENCIA.jsonl").read_text().splitlines()]
    assert {p["url"] for p in proc} == {"https://ex.org/a/", "https://ex.org/b/index.md"}
    assert r["ok_destino"]


def test_nome_pelo_titulo_e_titulo_repetido_ganha_o_caminho(tmp_path):
    t = M.Trabalho("t", raiz=tmp_path / "pesq")
    _ler(t, 1, "https://ex.org/p/azure", b"<html><title>Azure | OAuth2 Proxy</title></html>")
    _ler(t, 2, "https://ex.org/x/termos/index.md", b"---\ntitle: Useful terms\n---\n# Useful terms", ext="md")
    _ler(t, 3, "https://ex.org/y/termos/index.md", b"# Useful terms\noutro", ext="md")
    r = X.exportar(t, "lote", raiz=tmp_path / "entrada")
    nomes = sorted(e["arquivo"] for e in r["exportados"])
    assert nomes == ["Azure OAuth2 Proxy.html", "Useful terms (y-termos).md", "Useful terms.md"]


def test_juntar_faz_do_site_um_markdown_so(tmp_path):
    t = M.Trabalho("t", raiz=tmp_path / "pesq")
    _ler(t, 1, "https://ex.org/doc/b/index.md", b"---\ntitle: Filha\n---\n# Filha\n## Passo\n```\n# comentario\n```", ext="md")
    _ler(t, 2, "https://ex.org/doc/index.md", b"# Inicio\ntexto", ext="md")
    _ler(t, 3, "https://ex.org/doc/c", b"<html><title>C | Ex Docs</title></html>")
    t.guarda_derivado(3, "corpo de c, sem H1", "md")
    _ler(t, 4, "https://ex.org/doc/d", b"<html><title>D</title></html>")  # sem derivado
    r = X.juntar(t, "Doc de Ex", "lote", raiz=tmp_path / "entrada")
    assert r["arquivo"] == "Doc de Ex.md" and r["paginas"] == 3 and r["ok_destino"]
    assert [p["motivo"] for p in r["pulados"]] == ["sem-markdown"]
    md = (tmp_path / "entrada/lote/Doc de Ex.md").read_text()
    assert md.count("\n# ") == 1 and "# Doc de Ex" in md
    assert md.index("## Inicio") < md.index("## Filha") < md.index("## C")
    assert "### Passo" in md and "\n# comentario" in md
    assert "Fonte: <https://ex.org/doc/b/index.md>" in md
    proc = [json.loads(l) for l in (tmp_path / "entrada/lote/PROCEDENCIA.jsonl").read_text().splitlines()]
    assert len(proc) == 1 and len(proc[0]["juntado_de"]) == 3
    r2 = X.juntar(t, "Doc de Ex", "lote", raiz=tmp_path / "entrada")
    assert r2["ok_destino"] and r2["sha256"] == r["sha256"]


def test_bruto_sobrescrito_nao_sai(tmp_path):
    t = M.Trabalho("t", raiz=tmp_path / "pesq")
    p = _ler(t, 1, "https://ex.org/a", b"<html>a</html>")
    p.write_bytes(b"<html>outra pagina</html>")
    r = X.exportar(t, "lote", raiz=tmp_path / "entrada")
    assert r["exportados"] == [] and r["pulados"][0]["motivo"] == "bruto-nao-confere"


def test_excluir_e_nao_sobrescrever(tmp_path):
    t = M.Trabalho("t", raiz=tmp_path / "pesq")
    _ler(t, 1, "https://ex.org/llms.txt", b"indice", ext="txt")
    _ler(t, 2, "https://ex.org/a", b"<html>a</html>")
    dest = tmp_path / "entrada/lote"
    dest.mkdir(parents=True)
    (dest / "ex.org_a.html").write_bytes(b"<html>outro</html>")
    r = X.exportar(t, "lote", [r"llms\.txt$"], raiz=tmp_path / "entrada")
    assert r["pulados"][0]["motivo"] == "excluida"
    assert r["conflitos"][0]["motivo"] == "outro-sha256-no-destino"
    assert (dest / "ex.org_a.html").read_bytes() == b"<html>outro</html>"
    assert not r["ok_destino"]
