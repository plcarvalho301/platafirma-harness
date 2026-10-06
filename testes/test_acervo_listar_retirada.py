"""#3317: `acervo listar biblioteca obra` não lista obra retirada (expurgada_em preenchido), em nenhum eixo
de --sobre e na listagem sem termo, com ou sem --situacao. Sem banco: o módulo `bin/_acervo/listar` se
carrega como fonte e `_psql_json` é trocado por uma função que guarda o SQL que o ato manda.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
LISTAR = RAIZ / "bin" / "_acervo" / "listar"

def _modulo():
    loader = importlib.machinery.SourceFileLoader("acervo_listar_3317", str(LISTAR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod

@pytest.fixture
def listar(monkeypatch):
    mod = _modulo()
    consultas = []

    def falso(sql, alvo):
        consultas.append((alvo, sql))
        if alvo == "catalogo_obra":
            return [{"total": 3, "data": "2026-10-06"}]
        return []

    monkeypatch.setattr(mod, "_psql_json", falso)
    return mod, consultas

@pytest.mark.parametrize("termo,eixo", [("e-ARQ Brasil", None), ("e-ARQ Brasil", "titulo"),
                                        ("Descrição multinível", "conceito"),
                                        ("arquivologia", "subdominio"), (None, None)])
@pytest.mark.parametrize("situacao", [False, True])
def test_a_consulta_de_obra_tira_a_retirada(listar, termo, eixo, situacao, capsys):
    mod, consultas = listar
    mod.listar_obra(termo, eixo, situacao, False)
    capsys.readouterr()
    sql = next(sql for alvo, sql in consultas if alvo == "listar obra")
    assert "expurgada_em is not null" in sql
    assert "t.id not in" in sql

def test_o_total_do_catalogo_conta_so_obra_viva(listar, capsys):
    mod, consultas = listar
    mod.listar_obra("x", None, False, False)
    capsys.readouterr()
    sql = next(sql for alvo, sql in consultas if alvo == "catalogo_obra")
    assert "expurgada_em is null" in sql
