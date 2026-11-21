# componente: componente:verbo-acervo
"""`acervo stack import` grava a coluna `forma` (conteiner ou host), obrigatória em acervo.stack.

Sem ela a importação de stack nova falhava no banco («null value in column forma», medido em
21/10/2026 ao registrar a stack eventos do core). Sem banco: o _psql é trocado por um que guarda o SQL.
DTs 289 e 291: unicidade do caminho de compose — recusa de duplicata na origem.
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


def test_import_recusa_duplicata_no_proprio_lote(tmp_path, capsys):
    # DT 289: o import recusa um slug cujo compose já pertence a outro slug no lote
    mod = _modulo()
    arq = tmp_path / "duplicata.json"
    arq.write_text(json.dumps({
        "stacks": {
            "borda": {"compose": "/opt/platafirma/current/harness/borda/compose.yaml"},
            "harness-borda": {"compose": "/opt/platafirma/current/harness/borda/compose.yaml"},
        }
    }), encoding="utf-8")
    with pytest.raises(SystemExit) as saida:
        mod.cmd_import(str(arq))
    assert saida.value.code == 2
    err = capsys.readouterr().err
    assert "compose '/opt/platafirma/current/harness/borda/compose.yaml' ja pertence ao slug 'borda'" in err
    assert "harness-borda" in err


def test_import_recusa_duplicata_contra_registro_existente(tmp_path, monkeypatch, capsys):
    # DT 291: checar unicidade contra as stacks existentes no banco
    mod = _modulo()
    # Simula retorno do banco com 'borda' já registrada
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: (
        "borda|/opt/platafirma/current/harness/borda/compose.yaml\n" if "from acervo.stack" in (sql or "") else ""
    ))
    arq = tmp_path / "nova_duplicata.json"
    arq.write_text(json.dumps({
        "stacks": {
            "harness-borda": {"compose": "/opt/platafirma/current/harness/borda/compose.yaml"},
        }
    }), encoding="utf-8")
    with pytest.raises(SystemExit) as saida:
        mod.cmd_import(str(arq))
    assert saida.value.code == 2
    err = capsys.readouterr().err
    assert "compose '/opt/platafirma/current/harness/borda/compose.yaml' ja pertence a outra stack ('borda' no registro" in err
    assert "harness-borda" in err


def test_import_permite_atualizar_o_proprio_slug(tmp_path, monkeypatch):
    mod = _modulo()
    sqls = []
    # Simula retorno do banco onde 'borda' já tem o compose
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: (
        "borda|/opt/platafirma/current/harness/borda/compose.yaml\n" if "from acervo.stack" in (sql or "") else (sqls.append(stdin) or "")
    ))
    arq = tmp_path / "atualiza_mesmo.json"
    arq.write_text(json.dumps({
        "stacks": {
            "borda": {"compose": "/opt/platafirma/current/harness/borda/compose.yaml", "papel": "novo"},
        }
    }), encoding="utf-8")
    mod.cmd_import(str(arq))
    assert len(sqls) == 1
    assert "insert into acervo.stack" in sqls[0]


def test_definir_como_subcomando_valido(tmp_path, monkeypatch):
    mod = _modulo()
    chamou = []
    monkeypatch.setattr(mod, "cmd_import", lambda arq: chamou.append(arq))
    arq = tmp_path / "definir.json"
    arq.write_text("{}", encoding="utf-8")
    mod.main(["definir", str(arq)])
    assert chamou == [str(arq)]


def test_import_aceita_lista_do_stack_ver_json(tmp_path, monkeypatch):
    # DT #20: `acervo stack ver --json` devolve uma lista de objetos com `slug` e `nota`
    mod = _modulo()
    sqls = []
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: sqls.append(stdin) or "")
    arq = tmp_path / "ver.json"
    arq.write_text(json.dumps([
        {
            "slug": "core",
            "papel": "núcleo",
            "critico": True,
            "repo": "platafirma-core",
            "compose": "/opt/platafirma/current/core/compose.yml",
            "rotas": None,
            "segredos": None,
            "reversao": None,
            "gate": None,
            "profiles": None,
            "nota": "nota preservada",
            "pre_build": None,
        },
        {
            "slug": "harness",
            "papel": "catálogo",
            "critico": False,
            "repo": "platafirma-harness",
            "compose": None,
            "nota": None,
        },
    ]), encoding="utf-8")
    mod.cmd_import(str(arq))
    sql = sqls[-1]
    assert "('core','núcleo',true,'platafirma-core','/opt/platafirma/current/core/compose.yml'" in sql
    assert "'nota preservada'" in sql
    assert "'conteiner')" in sql
    assert "('harness','catálogo',false,'platafirma-harness',null" in sql
    assert "'host')" in sql


def test_import_aceita_objeto_unico_com_slug(tmp_path, monkeypatch):
    mod = _modulo()
    sqls = []
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: sqls.append(stdin) or "")
    arq = tmp_path / "unica.json"
    arq.write_text(json.dumps({"slug": "borda", "compose": "/opt/platafirma/current/borda/compose.yml"}), encoding="utf-8")
    mod.cmd_import(str(arq))
    assert "('borda',null,false,null,'/opt/platafirma/current/borda/compose.yml'" in sqls[-1]


def test_import_le_stdin_com_hifen_e_sem_argumento(monkeypatch):
    import io
    mod = _modulo()
    sqls = []
    monkeypatch.setattr(mod, "_psql", lambda sql, stdin=None: sqls.append(stdin) or "")

    payload = json.dumps([{"slug": "via-stdin", "compose": None, "papel": "teste"}])
    fake_stdin = io.StringIO(payload)
    fake_stdin.isatty = lambda: False
    monkeypatch.setattr(mod.sys, "stdin", fake_stdin)
    mod.cmd_import("-")
    assert "('via-stdin','teste',false,null,null" in sqls[-1]

    fake_stdin2 = io.StringIO(json.dumps({"slug": "obj-stdin", "compose": None}))
    fake_stdin2.isatty = lambda: False
    monkeypatch.setattr(mod.sys, "stdin", fake_stdin2)
    mod.main(["import"])
    assert "('obj-stdin',null,false,null,null" in sqls[-1]


def test_import_recusa_lista_invalida(tmp_path):
    mod = _modulo()
    vazia = tmp_path / "vazia.json"
    vazia.write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit) as saida:
        mod.cmd_import(str(vazia))
    assert saida.value.code == 3

    sem_slug = tmp_path / "sem_slug.json"
    sem_slug.write_text(json.dumps([{"papel": "x"}]), encoding="utf-8")
    with pytest.raises(SystemExit) as saida2:
        mod.cmd_import(str(sem_slug))
    assert saida2.value.code == 2

    duplicada = tmp_path / "dup_slug.json"
    duplicada.write_text(json.dumps([{"slug": "a"}, {"slug": "a"}]), encoding="utf-8")
    with pytest.raises(SystemExit) as saida3:
        mod.cmd_import(str(duplicada))
    assert saida3.value.code == 2
