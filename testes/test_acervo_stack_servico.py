"""`acervo stack ver <stack>` e `acervo stack resolver <unit>` leem a ficha de serviço `parte-de` stack (arq:0025 §2).

A unit é a declaração do serviço na forma de processo de host e mora no suporte da ficha, tipo `unit`.
Unit sem serviço ligado a uma stack sai `unit_sem_stack` (R4 da spec eixos-do-host). Sem banco: o _psql é
trocado por um que guarda o SQL e devolve o que o teste manda.
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
def banco(monkeypatch):
    mod = _modulo()
    estado = {"sqls": [], "saida": ""}

    def _psql(sql, stdin=None):
        estado["sqls"].append(sql)
        return estado["saida"]

    monkeypatch.setattr(mod, "_psql", _psql)
    return mod, estado

def test_ver_stack_lista_servico_e_unit(banco, capsys):
    mod, estado = banco
    estado["saida"] = "harness/agregador|harness-agregador.service\nharness/sinal|sinal.service,sinal.timer\n"
    mod.main(["ver", "harness"])
    saida = capsys.readouterr().out
    assert "harness/agregador  harness-agregador.service" in saida
    assert "harness/sinal  sinal.service, sinal.timer" in saida
    assert "st.chave_humana = 'harness'" in estado["sqls"][-1]
    assert "r.tipo = 'parte-de'" in estado["sqls"][-1]

def test_ver_stack_json(banco, capsys):
    mod, estado = banco
    estado["saida"] = "core/cdi-gpu|cdi-gpu.service\n"
    mod.main(["ver", "core", "--json"])
    assert json.loads(capsys.readouterr().out) == [{"servico": "core/cdi-gpu", "units": ["cdi-gpu.service"]}]

def test_ver_stack_sem_servico_sai_1(banco):
    mod, estado = banco
    with pytest.raises(SystemExit) as saida:
        mod.main(["ver", "vazia"])
    assert saida.value.code == 1

def test_ver_sem_stack_segue_listando_as_stacks(banco, monkeypatch):
    mod, estado = banco
    chamado = []
    monkeypatch.setattr(mod, "cmd_ver", lambda quero_json: chamado.append(quero_json))
    mod.main(["ver", "--json"])
    assert chamado == [True]

def test_resolver_unit_registrada(banco, capsys):
    mod, estado = banco
    estado["saida"] = "chat/worker\n"
    mod.main(["resolver", "chat-worker.service"])
    assert capsys.readouterr().out.strip() == "chat/worker"
    assert "su.endereco = 'chat-worker.service'" in estado["sqls"][-1]

def test_resolver_unit_fora_do_registro_e_unit_sem_stack(banco, capsys):
    mod, estado = banco
    estado["saida"] = ""
    with pytest.raises(SystemExit) as saida:
        mod.main(["resolver", "dbus.service"])
    assert saida.value.code == 1
    assert "unit_sem_stack: dbus.service" in capsys.readouterr().err

def test_resolver_prefixo_pelo_endereco_com_asterisco(banco):
    mod, estado = banco
    estado["saida"] = "harness/job\n"
    mod.main(["resolver", "platafirma-job-portao-3931-20261020T213031.service"])
    sql = estado["sqls"][-1]
    assert "like '%*'" in sql
    assert "starts_with('platafirma-job-portao-3931-20261020T213031.service', rtrim(su.endereco, '*'))" in sql

def test_resolver_aspas_na_unit_nao_quebram_o_sql(banco):
    mod, estado = banco
    estado["saida"] = ""
    with pytest.raises(SystemExit):
        mod.main(["resolver", "x'; drop table acervo.entidade; --"])
    assert "'x''; drop table acervo.entidade; --'" in estado["sqls"][-1]

def test_resolver_sem_unit_recusa(banco):
    mod, estado = banco
    with pytest.raises(SystemExit) as saida:
        mod.main(["resolver"])
    assert saida.value.code == 2
