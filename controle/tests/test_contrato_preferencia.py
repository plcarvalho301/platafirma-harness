"""Contrato de `bin/preferencia` (#3449, decisão do arquiteto no #2143).

Prova o que o verbo promete a quem o chama:

(1) o sujeito nunca é argumento: os dois atos leem só o PF_SUJEITO que a porta injeta, então
    escrever como A não muda o que B lê, e `--sujeito` é recusado (exit 2);
(2) sem preferência gravada, `ler` sai 0 com vazio e `motivo: sem preferência gravada`;
(3) `escrever` valida o vocabulário (exit 2), diz o valor anterior, e `sistema` é uma linha
    gravada, não um apagamento;
(4) valor gravado fora do vocabulário (escrita direta no banco) sai vazio, nunca o texto cru;
(5) sem PF_SUJEITO sai 3 e nada é gravado; banco mudo sai 5 e não finge «sem preferência»;
(6) o cabeçalho põe `rotulo:` e `volta:` em todo ato que declara `face:`.

`bin/preferencia` não tem sufixo .py: carregado por SourceFileLoader, como o teste do mesa.
Teste não lê estado real (lib/teste_isolado.py): o psycopg entra por um falso sobre SQLite
em memória, que roda o SQL do próprio verbo. O que isto NÃO prova: o Postgres de verdade;
isso é a linha de aceite da migração 0101 e a chamada real depois da promoção, no card.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VERBO = REPO_ROOT / "bin" / "preferencia"

A = "b6986be0-c5b6-4693-839f-73c90b79b25a"
B = "0f6f2a1e-6d0e-4a55-9a3d-1b8c0c4e9a77"


def carrega():
    loader = SourceFileLoader("_preferencia", str(VERBO))
    spec = spec_from_loader("_preferencia", loader)
    mod = module_from_spec(spec)
    loader.exec_module(mod)
    return mod


class _Cursor:
    def __init__(self, con):
        self._cur = con.cursor()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._cur.close()

    def execute(self, sql, params=()):
        self._cur.execute(sql.replace("%s", "?"), params)

    def fetchone(self):
        return self._cur.fetchone()


class _Con:
    def __init__(self, banco):
        self._banco = banco

    def cursor(self):
        return _Cursor(self._banco)

    def commit(self):
        self._banco.commit()

    def close(self):
        pass  # o banco em memória é um só e vive o teste inteiro


class _Psycopg:
    """O que o verbo usa do psycopg: connect(dsn, connect_timeout=). Roda o SQL dele em SQLite."""

    def __init__(self, *, mudo=False):
        self.mudo = mudo
        self.banco = sqlite3.connect(":memory:", check_same_thread=False)
        self.banco.execute("ATTACH DATABASE ':memory:' AS sessao")
        self.banco.create_function("now", 0, lambda: "2026-10-12T00:00:00+00:00")
        self.banco.execute(
            "CREATE TABLE sessao.preferencia_sujeito ("
            "sujeito text NOT NULL, preferencia text NOT NULL, valor text NOT NULL, "
            "atualizado_em text NOT NULL DEFAULT 'x', PRIMARY KEY (sujeito, preferencia))")

    def connect(self, dsn, connect_timeout=None):
        if self.mudo:
            raise OSError("conexão recusada")
        return _Con(self.banco)

    def linhas(self):
        return self.banco.execute(
            "SELECT sujeito, preferencia, valor FROM sessao.preferencia_sujeito "
            "ORDER BY sujeito, preferencia").fetchall()


@pytest.fixture
def pref(monkeypatch):
    mod = carrega()
    fake = _Psycopg()
    monkeypatch.setitem(sys.modules, "psycopg", fake)
    monkeypatch.setattr(mod, "_senha_pg", lambda: "senha-de-teste")
    monkeypatch.setenv("PF_SUJEITO", A)
    return mod, fake


def roda(mod, capsys, *argv):
    """(exit, stdout, stderr) de uma chamada do verbo."""
    try:
        codigo = mod.main(list(argv))
    except SystemExit as e:
        codigo = e.code
    cap = capsys.readouterr()
    return codigo, cap.out, cap.err


def test_escrever_e_ler_devolvem_o_valor_do_sujeito(pref, capsys):
    mod, fake = pref
    codigo, out, _ = roda(mod, capsys, "escrever", "tema", "escuro")
    assert codigo == 0 and "escuro" in out
    assert fake.linhas() == [(A, "tema", "escuro")]
    codigo, out, _ = roda(mod, capsys, "ler", "tema")
    assert (codigo, out.strip()) == (0, "escuro")


def test_sujeito_sem_preferencia_recebe_vazio_com_motivo(pref, capsys):
    mod, _ = pref
    codigo, out, _ = roda(mod, capsys, "ler", "tema")
    assert codigo == 0
    assert out.strip() == "motivo: sem preferência gravada"


def test_escrever_como_um_sujeito_nao_muda_o_do_outro(pref, capsys, monkeypatch):
    mod, fake = pref
    roda(mod, capsys, "escrever", "tema", "escuro")
    monkeypatch.setenv("PF_SUJEITO", B)
    codigo, out, _ = roda(mod, capsys, "ler", "tema")
    assert codigo == 0 and "sem preferência gravada" in out
    roda(mod, capsys, "escrever", "tema", "claro")
    assert sorted(fake.linhas()) == sorted([(A, "tema", "escuro"), (B, "tema", "claro")])


def test_sujeito_nao_e_argumento(pref, capsys):
    mod, fake = pref
    codigo, _, err = roda(mod, capsys, "ler", "tema", "--sujeito", B)
    assert codigo == 2 and "--sujeito" in err
    codigo, _, _ = roda(mod, capsys, "escrever", "tema", "escuro", "--sujeito", B)
    assert codigo == 2 and fake.linhas() == []


def test_regravar_diz_o_valor_anterior_e_sistema_e_linha(pref, capsys):
    mod, fake = pref
    _, out, _ = roda(mod, capsys, "escrever", "tema", "escuro")
    assert "sem preferência gravada → escuro" in out
    _, out, _ = roda(mod, capsys, "escrever", "tema", "sistema")
    assert "escuro → sistema" in out
    assert fake.linhas() == [(A, "tema", "sistema")]
    _, out, _ = roda(mod, capsys, "ler", "tema")
    assert out.strip() == "sistema"


def test_valor_fora_do_vocabulario_recusa_e_nao_grava(pref, capsys):
    mod, fake = pref
    codigo, _, err = roda(mod, capsys, "escrever", "tema", "roxo")
    assert codigo == 2 and "roxo" in err and fake.linhas() == []


def test_preferencia_desconhecida_recusa(pref, capsys):
    mod, fake = pref
    assert roda(mod, capsys, "ler", "fonte")[0] == 2
    assert roda(mod, capsys, "escrever", "fonte", "grande")[0] == 2
    assert fake.linhas() == []


def test_valor_gravado_fora_do_vocabulario_sai_vazio(pref, capsys):
    mod, fake = pref
    fake.banco.execute(
        "INSERT INTO sessao.preferencia_sujeito (sujeito, preferencia, valor) VALUES (?, ?, ?)",
        (A, "tema", "roxo"))
    codigo, out, _ = roda(mod, capsys, "ler", "tema")
    assert codigo == 0 and "roxo" not in out and "fora do vocabulário" in out


def test_sem_pf_sujeito_sai_3_e_nao_grava(pref, capsys, monkeypatch):
    mod, fake = pref
    monkeypatch.delenv("PF_SUJEITO")
    assert roda(mod, capsys, "ler", "tema")[0] == 3
    assert roda(mod, capsys, "escrever", "tema", "escuro")[0] == 3
    assert fake.linhas() == []


def test_banco_mudo_sai_5_e_nao_finge_vazio(pref, capsys, monkeypatch):
    mod, _ = pref
    monkeypatch.setitem(sys.modules, "psycopg", _Psycopg(mudo=True))
    codigo, out, err = roda(mod, capsys, "ler", "tema")
    assert codigo == 5 and "sem preferência" not in out and "sessao-db" in err
    codigo, _, _ = roda(mod, capsys, "escrever", "tema", "escuro")
    assert codigo == 5


def test_json_traz_preferencia_valor_e_motivo(pref, capsys):
    mod, _ = pref
    _, out, _ = roda(mod, capsys, "ler", "tema", "--json")
    assert json.loads(out) == {"preferencia": "tema", "valor": None,
                               "motivo": "sem preferência gravada"}
    roda(mod, capsys, "escrever", "tema", "claro")
    _, out, _ = roda(mod, capsys, "ler", "tema", "--json")
    assert json.loads(out) == {"preferencia": "tema", "valor": "claro", "motivo": None}


def test_cabecalho_poe_rotulo_e_volta_em_todo_ato_de_face():
    """arq:0124 §3: ato que o cabeçalho põe numa face declara `rotulo:` e `volta:`."""
    padrao = re.compile(r"^#\s*(face|rotulo|volta)\s*:\s*([A-Za-z0-9_-]+)\s*=\s*(.*?)\s*$")
    linhas = VERBO.read_text(encoding="utf-8").splitlines()[:40]
    achados = [m for m in map(padrao.match, linhas) if m]
    campos = {c: {m.group(2): m.group(3) for m in achados if m.group(1) == c}
              for c in ("face", "rotulo", "volta")}
    assert campos["face"], "o verbo não declara face"
    for ato in campos["face"]:
        assert campos["rotulo"].get(ato), f"ato {ato} sem rotulo:"
        assert campos["volta"].get(ato), f"ato {ato} sem volta:"
    assert campos["volta"]["escrever"].startswith("sim — ")
