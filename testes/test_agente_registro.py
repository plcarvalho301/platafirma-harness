"""O cabecalho de bin/agente se registra no golden record (card #3156).

Um verbo so entra em `verbos_servidos` da porta depois de `acervo registrar <verbo>`, que le o cabecalho por
chave e recusa `# le:`/`# escreve:` fora da forma `<ato>=<recurso>`. Hermetico: o psql e um duble que guarda o SQL.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("registrar", str(REPO_ROOT / "bin" / "_acervo" / "registrar"))
spec = importlib.util.spec_from_loader("registrar", loader)
assert spec and spec.loader
registrar = importlib.util.module_from_spec(spec)
loader.exec_module(registrar)


@pytest.fixture
def sql(monkeypatch):
    enviados: list[str] = []
    monkeypatch.setattr(registrar, "_psql", lambda s, escreve=False: enviados.append(s) or "")
    cap, desc = registrar.registrar_um("agente")
    return cap, desc, "".join(enviados)


def test_capacidade_e_descricao_saem_do_cabecalho(sql):
    cap, desc, _ = sql
    assert cap == "construcao"
    assert desc.startswith("a caixa de especialistas") and "use para: especialista" in desc
    assert "atos: listar (leitura, construcao), ler (leitura, construcao)" in desc


@pytest.mark.parametrize("ato,op", [("listar", "leitura"), ("ler", "leitura"), ("rodar", "escrita"), ("projetar", "escrita")])
def test_cada_ato_entra_com_a_acao_e_a_folha(sql, ato, op):
    assert f"'agente', '{ato}', 'construcao', '{op}', 'construcao'" in sql[2]


def test_o_acesso_de_cada_ato_e_declarado(sql):
    texto = sql[2]
    for ato in ("listar", "ler", "rodar", "projetar"):
        assert f"'agente', '{ato}', 'arquivo-local', 'le'" in texto
    assert "'agente', 'listar', 'nada', 'escreve'" in texto and "'agente', 'ler', 'nada', 'escreve'" in texto
    assert "'agente', 'rodar', 'malha', 'escreve'" in texto and "'agente', 'rodar', 'arquivo-local', 'escreve'" in texto
    assert "'agente', 'projetar', 'arquivo-local', 'escreve'" in texto


def test_as_variaveis_de_ambiente_obrigatorias_entram(sql):
    texto = sql[2]
    assert "'agente', 'PF_SUJEITO', true" in texto and "'agente', 'PF_SESSAO', true" in texto
    assert "'agente', 'PF_BIN', false" in texto
