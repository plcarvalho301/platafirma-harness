# componente: componente:verbo-acervo
"""Testes herméticos para projeção de `pre_build` em `acervo stack import` e `ver` (#3077, DT-216).

Substitui o antigo testes/test_acervo_stack.sh (que escrevia na tabela acervo.stack
de produção e saiu no #3326). Sem banco real: `_psql` é trocado por um dublê que
registra o SQL gerado pelo `import` e devolve linhas no formato `-tAF|` para o `ver`.
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


def test_import_com_pre_build(tmp_path, monkeypatch):
    mod = _modulo()
    sqls = []
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: sqls.append(stdin) or "")

    arq = tmp_path / "stacks.json"
    arq.write_text(json.dumps({
        "stacks": {
            "test-stack-prebuild": {
                "papel": "test",
                "critico": False,
                "repo": "test-repo",
                "compose": "docker-compose.yml",
                "pre_build": "wiki/montar-wiki",
            }
        }
    }), encoding="utf-8")

    mod.main(["import", str(arq)])
    sql = sqls[-1]
    assert "pre_build,forma) values" in sql
    assert "'wiki/montar-wiki','conteiner')" in sql
    assert "pre_build = excluded.pre_build" in sql


def test_import_sem_pre_build_grava_null(tmp_path, monkeypatch):
    mod = _modulo()
    sqls = []
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: sqls.append(stdin) or "")

    arq = tmp_path / "stacks.json"
    arq.write_text(json.dumps({
        "stacks": {
            "test-stack-noprebuild": {
                "papel": "test",
                "critico": False,
                "repo": "test-repo",
                "compose": "docker-compose.yml",
            }
        }
    }), encoding="utf-8")

    mod.cmd_import(str(arq))
    sql = sqls[-1]
    assert "null,'conteiner')" in sql


def test_import_escapa_aspas_em_pre_build(tmp_path, monkeypatch):
    mod = _modulo()
    sqls = []
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: sqls.append(stdin) or "")

    arq = tmp_path / "stacks.json"
    arq.write_text(json.dumps({
        "stacks": {
            "test-stack-quote": {
                "compose": None,
                "pre_build": "echo 'ok'",
            }
        }
    }), encoding="utf-8")

    mod.cmd_import(str(arq))
    assert "'echo ''ok''','host')" in sqls[-1]


def test_ver_json_projeta_pre_build_e_null(monkeypatch, capsys):
    mod = _modulo()
    sqls = []
    linhas = "\n".join([
        "test-stack-noprebuild|test|f|test-repo|docker-compose.yml|null|null|null|null|null||null",
        "test-stack-prebuild|test|f|test-repo|docker-compose.yml|null|null|null|null|null||wiki/montar-wiki",
        "test-stack-vazio|test|f|test-repo|docker-compose.yml|null|null|null|null|null||",
    ]) + "\n"

    def fake_psql(sql, stdin=None):
        sqls.append(sql)
        return linhas

    monkeypatch.setattr(mod, "_psql", fake_psql)
    mod.main(["ver", "--json"])

    assert "coalesce(pre_build,'null')" in sqls[-1]
    dados = json.loads(capsys.readouterr().out)
    por_slug = {item["slug"]: item for item in dados}
    assert por_slug["test-stack-prebuild"]["pre_build"] == "wiki/montar-wiki"
    assert por_slug["test-stack-noprebuild"]["pre_build"] is None
    assert por_slug["test-stack-vazio"]["pre_build"] is None
