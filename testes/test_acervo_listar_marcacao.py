"""#3202: `acervo listar obra obra --situacao` mostra a marcação de uso da obra (arq:0119 §6; spec
acervo-obra §6; migração 071 em platafirma-conhecimento).

Sem banco: o módulo `bin/_acervo/listar` se carrega como fonte e `_psql_json` é trocado por uma função
que responde pelas consultas que o ato faz.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
LISTAR = RAIZ / "bin" / "_acervo" / "listar"

OBRA_A = "0000aaaa-0000-4000-8000-000000000000"
OBRA_B = "0000bbbb-0000-4000-8000-000000000000"


def _modulo():
    loader = importlib.machinery.SourceFileLoader("acervo_listar_3202", str(LISTAR))
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
            return [{"total": 2, "data": "2026-10-01"}]
        if alvo == "listar obra":
            return [
                {"id": OBRA_A, "titulo": "Lei 14.133", "objeto": "acervo/aa", "eixo": "titulo",
                 "subdominio": None, "conceito": None, "impressao_id": "1234567890ab", "impressao_estado": "servindo"},
                {"id": OBRA_B, "titulo": "Planilha", "objeto": "acervo/bb", "eixo": "titulo",
                 "subdominio": None, "conceito": None, "impressao_id": None, "impressao_estado": None},
            ]
        if alvo == "marcacao":
            return [{"id": OBRA_A, "marcacao": "transcrita e indexada"}, {"id": OBRA_B, "marcacao": "inteira"}]
        raise AssertionError(f"consulta inesperada: {alvo}")

    monkeypatch.setattr(mod, "_psql_json", falso)
    return mod, consultas


def test_situacao_em_texto_traz_a_marcacao_de_cada_obra(listar, capsys):
    mod, _ = listar
    mod.listar_obra("Lei", "titulo", True, False)
    saida = capsys.readouterr().out
    assert "marcacao: transcrita e indexada" in saida
    assert "marcacao: inteira" in saida


def test_situacao_em_json_traz_a_marcacao(listar, capsys):
    mod, _ = listar
    mod.listar_obra("Lei", "titulo", True, True)
    itens = json.loads(capsys.readouterr().out)
    assert {i["id"]: i["situacao"]["marcacao"] for i in itens} == {
        OBRA_A: "transcrita e indexada", OBRA_B: "inteira"}


def test_sem_situacao_nao_consulta_a_marcacao(listar, capsys):
    mod, consultas = listar
    mod.listar_obra("Lei", "titulo", False, True)
    capsys.readouterr()
    assert "marcacao" not in [alvo for alvo, _ in consultas]


def test_a_consulta_da_marcacao_vai_pelos_ids_listados_e_escapa_o_literal(listar, capsys):
    mod, consultas = listar
    mod.listar_obra("Lei", "titulo", True, True)
    capsys.readouterr()
    sql = next(sql for alvo, sql in consultas if alvo == "marcacao")
    assert f"'{OBRA_A}'" in sql and f"'{OBRA_B}'" in sql
    assert "acervo.obra" in sql and "marcacao" in sql
