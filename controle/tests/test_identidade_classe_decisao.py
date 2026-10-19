"""A ficha da ADR mora na classe `decisao` do catálogo da raiz (triagem da #3764; migração 114 da #3761).

`adr` segue valendo como nome de entrada: a espécie do documento é o que o humano digita, e a biblioteca de
identidade (`bin/_acervo/_identidade.py`) a lê na classe nova, sem tocar o banco (psql dublê)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
ACERVO = RAIZ / "bin" / "_acervo"


def _ident():
    sys.path.insert(0, str(ACERVO))
    try:
        loader = importlib.machinery.SourceFileLoader("identidade_decisao_teste", str(ACERVO / "_identidade.py"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(ACERVO))


@pytest.fixture
def ident():
    return _ident()


def test_adr_se_le_na_classe_decisao_e_o_resto_fica_como_esta(ident):
    assert ident.da_raiz("adr") == "decisao"
    assert ident.da_raiz("decisao") == "decisao"
    assert ident.da_raiz("spec") == "spec" and ident.da_raiz("capacidade") == "capacidade"


@pytest.mark.parametrize("entrada", ["adr", "decisao"])
def test_a_forma_da_chave_vem_da_classe_decisao(ident, monkeypatch, entrada):
    vistos = []
    monkeypatch.setattr(ident, "psql_json", lambda sql, alvo="query": vistos.append(sql) or [
        {"slug": "decisao", "forma_chave": None}])
    canon, _ = ident.validar_forma(entrada, "arq:0110")
    assert canon == "arq:0110"
    assert "slug = 'decisao'" in vistos[-1] and "'adr'" not in vistos[-1]


@pytest.mark.parametrize("entrada", ["adr", "decisao"])
def test_a_resolucao_procura_a_ficha_na_classe_decisao(ident, monkeypatch, entrada):
    vistos = []
    monkeypatch.setattr(ident, "psql_json", lambda sql, alvo="query": vistos.append(sql) or [])
    ident.resolver_canon(entrada, "arq:0110")
    ident.resolver_canon(entrada, "arq:0110", "0110")
    assert len(vistos) == 2
    assert all("e.classe = 'decisao'" in sql and "'adr'" not in sql for sql in vistos)


def test_o_seletor_malformado_de_adr_segue_recusando_com_exit_2(ident, capsys):
    with pytest.raises(SystemExit) as e:
        ident.validar_forma("adr", "arq:11O")
    assert e.value.code == 2
    assert "Forma esperada" in capsys.readouterr().err
