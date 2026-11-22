# componente: componente:verbo-acervo
"""Prova de que `acervo ler casa` lê a casa nova da release no ar, nunca da bancada (DT 963)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def _carregar_casa(nome: str):
    caminho = RAIZ / "bin" / "_acervo" / "casa"
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_dt963_casa_nova_le_da_release_e_ignora_bancada(tmp_path: Path, monkeypatch, capsys) -> None:
    casa = _carregar_casa("_acervo_casa_dt963_release")

    release_dir = tmp_path / "release"
    doc_release = release_dir / "casa" / "instancias" / "controle-de-seguranca" / "borda-da-porta.md"
    doc_release.parent.mkdir(parents=True)
    doc_release.write_text("# Borda da porta\n\nTexto novo da release no ar (faces-da-borda.yaml).\n", encoding="utf-8")

    bancada_dir = tmp_path / "bancada"
    doc_bancada = bancada_dir / "platafirma-casa" / "instancias" / "controle-de-seguranca" / "borda-da-porta.md"
    doc_bancada.parent.mkdir(parents=True)
    doc_bancada.write_text("# Borda da porta\n\nTexto antigo da bancada.\n", encoding="utf-8")

    monkeypatch.delenv("PF_CASA_ESPELHO", raising=False)
    monkeypatch.delenv("PF_CASA_RAIZ", raising=False)
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(release_dir))
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(bancada_dir))
    monkeypatch.setattr(casa, "_q", lambda sql, alvo="consulta", falhar=True: None)

    rc = casa.ler("controle-de-seguranca", "borda-da-porta", True, cru=True)
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["repo"] == "platafirma-casa"
    assert payload["path"] == "instancias/controle-de-seguranca/borda-da-porta.md"
    assert "faces-da-borda.yaml" in payload["corpo"]
    assert "Texto antigo da bancada" not in payload["corpo"]


def test_dt963_casa_nova_nao_cai_na_bancada_sem_release(tmp_path: Path, monkeypatch) -> None:
    casa = _carregar_casa("_acervo_casa_dt963_sem_release")

    bancada_dir = tmp_path / "bancada"
    (bancada_dir / "platafirma-casa" / "instancias" / "controle-de-seguranca").mkdir(parents=True)

    monkeypatch.delenv("PF_CASA_ESPELHO", raising=False)
    monkeypatch.delenv("PF_CASA_RAIZ", raising=False)
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(tmp_path / "release-inexistente"))
    monkeypatch.setenv("PLATAFIRMA_BANCADA", str(bancada_dir))

    assert casa._raiz_casa_nova() is None


def test_dt963_casa_nova_aceita_overrides_de_teste(tmp_path: Path, monkeypatch) -> None:
    casa = _carregar_casa("_acervo_casa_dt963_override")

    override_espelho = tmp_path / "espelho"
    override_espelho.mkdir()
    override_raiz = tmp_path / "raiz"
    override_raiz.mkdir()

    monkeypatch.setenv("PF_CASA_ESPELHO", str(override_espelho))
    monkeypatch.setenv("PF_CASA_RAIZ", str(override_raiz))
    assert casa._raiz_casa_nova() == str(override_espelho)

    monkeypatch.delenv("PF_CASA_ESPELHO")
    assert casa._raiz_casa_nova() == str(override_raiz)
