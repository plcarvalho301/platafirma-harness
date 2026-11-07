"""Débitos 140 e 364: lote em voo e abertura com registro indisponível."""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

RAIZ = Path(__file__).resolve().parents[2]


def carregar(nome, caminho):
    loader = SourceFileLoader(nome, str(RAIZ / caminho))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("lotes,confirmar,esperado", [([], False, 0), (["lote-1"], False, 4),
                                                    (["lote-1"], True, 0)])
def test_promocao_declara_e_pede_confirmacao(monkeypatch, capsys, lotes, confirmar, esperado):
    mod = carregar("lotes_dt140", "bin/_release/lotes.py")
    monkeypatch.setattr(mod.subprocess, "run", lambda *a, **k: SimpleNamespace(
        returncode=0, stdout=" lotes\n-------\n " + json.dumps(lotes) + "\n(1 row)\n", stderr=""))
    assert mod.conferir(confirmar=confirmar) == esperado
    if lotes:
        assert "lote-1" in capsys.readouterr().err


def test_banco_ilegivel_nao_vira_lista_vazia(monkeypatch):
    mod = carregar("lotes_dt140_fora", "bin/_release/lotes.py")
    monkeypatch.setattr(mod.subprocess, "run", MagicMock(side_effect=subprocess.TimeoutExpired("acervo", 20)))
    assert mod.conferir(confirmar=True) == 3


def test_registro_duravel_fora_nao_impede_cunhar_sessao(monkeypatch):
    mod = carregar("sessao_dt364", "bin/sessao")
    dados = {}
    mem = SimpleNamespace(get=dados.get, set=lambda chave, valor, **kw: dados.update({chave: valor}),
                          exists=lambda chave: chave in dados)
    monkeypatch.setenv("PF_SUJEITO", "sujeito-teste")
    monkeypatch.setattr(mod, "_msgmem", lambda: (mem, None))
    monkeypatch.setattr(mod, "_vocabulario", lambda: ({"ia": {"alias": "Elias", "chapeus": []}}, None))
    monkeypatch.setattr(mod, "_decidir", lambda *a: (0, {"regra": "r", "plano": "p"}, ""))
    monkeypatch.setattr(mod, "_senha_pg", lambda: ("senha-de-teste", None))
    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(
        connect=MagicMock(side_effect=RuntimeError("Postgres fora"))))
    saida = io.StringIO()
    with redirect_stdout(saida):
        assert mod.main(["abrir", "ia", "--json"]) == 0
    d = json.loads(saida.getvalue())
    assert d["registrada"] is True and d["duravel"] is False
    assert d["cadeira"] == "ia" and d["sujeito"] == "sujeito-teste"
    assert d["avisos"] and dados["sessao:" + d["sessao_id"]]


def test_registro_do_pacote_fora_nao_impede_montar(monkeypatch):
    mod = carregar("expediente_dt364", "bin/expediente")
    monkeypatch.setenv("PF_FITA", "fita-teste")
    monkeypatch.setattr(mod, "obtem_senha_sessao", lambda *a: "senha-de-teste")
    monkeypatch.setitem(sys.modules, "psycopg", SimpleNamespace(
        connect=MagicMock(side_effect=RuntimeError("Postgres fora"))))
    monkeypatch.setattr(mod, "executa_verbo", lambda *a, **k: (0, "conteúdo da peça", ""))
    monkeypatch.setattr(mod, "resolve_montador_sha", lambda: "sha-publicado")
    monkeypatch.setattr(mod, "chapeus_de", lambda *a: [])
    monkeypatch.setenv("PF_CADEIRA", "ia")
    saida = io.StringIO()
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    monkeypatch.setattr(sys, "argv", ["expediente", "montar", "--sem-acervo", "--json"])
    with redirect_stdout(saida):
        assert mod.main() == 0
    d = json.loads(saida.getvalue())
    assert d["pacote"]["registro"]["registrado"] is False
    assert "Postgres fora" in d["pacote"]["registro"]["motivo"]
    assert any(p["peca"] == "persona" and p["conteudo"] for p in d["pecas"])
    assert any("registro" in aviso for aviso in d["avisos"])
