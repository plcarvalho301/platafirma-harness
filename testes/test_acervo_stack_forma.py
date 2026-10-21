"""`acervo stack import` grava a coluna `forma` (conteiner ou host), obrigatória em acervo.stack.

Sem ela a importação de stack nova falhava no banco («null value in column forma», medido em
21/10/2026 ao registrar a stack eventos do core). Sem banco: o _psql é trocado por um que guarda o SQL.
"""

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

ARQ = Path(__file__).resolve().parents[1] / "bin" / "_acervo" / "stack"


def _modulo():
    carregador = importlib.machinery.SourceFileLoader("acervo_stack", str(ARQ))
    spec = importlib.util.spec_from_loader("acervo_stack", carregador)
    mod = importlib.util.module_from_spec(spec)
    carregador.exec_module(mod)
    return mod


@pytest.fixture
def importar(tmp_path, monkeypatch):
    mod = _modulo()
    sqls = []
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: sqls.append(stdin) or "")

    def roda(stacks):
        arq = tmp_path / "stacks.json"
        arq.write_text(json.dumps({"stacks": stacks}), encoding="utf-8")
        mod.cmd_import(str(arq))
        return sqls[-1]

    return roda


def test_forma_sai_do_compose(importar):
    sql = importar({"com": {"compose": "/opt/platafirma/current/core/x.yml"}, "sem": {"compose": None}})
    assert "pre_build,forma) values" in sql
    linha_com = next(l for l in sql.splitlines() if l.startswith("('com'"))
    linha_sem = next(l for l in sql.splitlines() if l.startswith("('sem'"))
    assert linha_com.endswith("'conteiner')") or linha_com.endswith("'conteiner'),")
    assert linha_sem.endswith("'host')") or linha_sem.endswith("'host'),")
    assert "forma = excluded.forma" in sql


def test_forma_declarada_vence(importar):
    sql = importar({"x": {"compose": None, "forma": "conteiner"}})
    assert "'conteiner')" in sql


def test_forma_fora_do_vocabulario_recusa(importar):
    with pytest.raises(SystemExit) as saida:
        importar({"x": {"compose": None, "forma": "vm"}})
    assert saida.value.code == 2
