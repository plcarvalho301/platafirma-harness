"""Contrato do manifesto e layout em disco (spec §4.8, §2.3)."""

from __future__ import annotations

import json

from pesquisa import manifesto as M


def test_layout_criado(tmp_path):
    t = M.Trabalho("t1", raiz=tmp_path)
    assert t.bruto.is_dir() and t.derivado.is_dir()
    assert t.dir == tmp_path / "t1"


def test_grava_linha_anexa_e_indexa(tmp_path):
    t = M.Trabalho("t2", raiz=tmp_path)
    i1 = t.grava_linha({"ato": "consultar", "consulta": "x"})
    i2 = t.grava_linha({"ato": "consultar", "consulta": "y"})
    assert (i1, i2) == (1, 2)
    linhas = t.linhas()
    assert len(linhas) == 2
    assert linhas[0]["ato"] == "consultar" and "ts" in linhas[0] and "ua" in linhas[0]


def test_proximo_n_continua_numeracao(tmp_path):
    t = M.Trabalho("t3", raiz=tmp_path)
    assert t.proximo_n() == 1
    t.grava_linha({"n": 1, "ato": "ler", "url": "u"})
    t.grava_linha({"n": 2, "ato": "ler", "url": "v"})
    # reabrir o trabalho continua de 3, não sobrescreve
    t2 = M.Trabalho("t3", raiz=tmp_path)
    assert t2.proximo_n() == 3


def test_sha256_estavel():
    assert M.sha256_bytes(b"abc") == M.sha256_texto("abc")
    assert len(M.sha256_bytes(b"abc")) == 64


def test_slug_default(monkeypatch):
    monkeypatch.delenv("PF_ORDEM_ID", raising=False)
    assert M.slug_trabalho("explicito") == "explicito"
    assert M.slug_trabalho(None).startswith("manual-")
    monkeypatch.setenv("PF_ORDEM_ID", "o-123")
    assert M.slug_trabalho(None) == "o-123"


def test_bruto_e_derivado_gravam(tmp_path):
    t = M.Trabalho("t4", raiz=tmp_path)
    t.guarda_bruto(1, b"<html>x</html>", "html")
    t.guarda_derivado(1, "# titulo", "md")
    assert (t.bruto / "1.html").read_bytes() == b"<html>x</html>"
    assert (t.derivado / "1.md").read_text(encoding="utf-8") == "# titulo"
