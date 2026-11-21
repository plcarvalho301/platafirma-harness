# componente: componente:oplog
"""Testes de classificacao de desfecho interrompido por sinal em lib/oplog.py (card #4369)."""
from __future__ import annotations

import sys
from pathlib import Path

HARNESS_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(HARNESS_LIB) not in sys.path:
    sys.path.insert(0, str(HARNESS_LIB))

import oplog  # noqa: E402


def test_classificar_interrompido_por_sigterm_negativo():
    res = oplog.classificar({"interrompido": True, "exit_code": -15})
    assert res["classe"] == "interrompida"
    assert "causa" not in res


def test_classificar_interrompido_por_sigterm_143():
    res = oplog.classificar({"interrompido": True, "exit_code": 143})
    assert res["classe"] == "interrompida"
    assert "causa" not in res


def test_classificar_interrompido_sem_exit_code():
    res = oplog.classificar({"interrompido": True})
    assert res["classe"] == "interrompida"


def test_classificar_exit_negativo_sem_interrompido_segue_fora_da_tabela():
    res = oplog.classificar({"interrompido": False, "exit_code": -15})
    assert res["classe"] == "execucao"
    assert res["causa"] == "exit_fora_da_tabela"


def test_classificar_cancelado_segue_interrompida():
    res = oplog.classificar({"cancelado": True})
    assert res["classe"] == "interrompida"
