"""Testes de unidade do contrato de `release conferir sessao-orfa` (card #3375).

Cobre:
  - Todas as tabelas dentro da linha de base -> conforme (exit 0)
  - Órfão novo acima da linha de base -> divergente (exit 1)
  - Banco fora do ar (Indeterminavel) -> indeterminavel (exit 5)
  - Filtro por alvo (ex: alvo="registro")
  - Saída em JSON com estrutura de Veredito
"""
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir"))

import sessao_orfa as so  # noqa: E402
import resultado  # noqa: E402


def test_sessao_orfa_todas_conforme_contra_base(monkeypatch):
    sessoes_validas = {"s1", "s2", "s3"}
    monkeypatch.setattr(so, "carregar_sessoes_validas", lambda fn: sessoes_validas)

    # Simula contagens onde os órfãos batem com a linha de base
    def mock_contar(banco, sql, validas, fn_psql):
        return (10, 0)

    monkeypatch.setattr(so, "contar_orfaos_tabela", mock_contar)

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = so.conferir(sha_release="abc1234", como_json=True)

    assert rc == 0
    dados = json.loads(buf.getvalue())
    assert dados["classe"] == "sessao-orfa"
    assert dados["release"] == "abc1234"
    assert all(it["estado"] == "conforme" for it in dados["itens"])
    assert len(dados["itens"]) == len(so.TABELAS_A_CONFERIR)


def test_sessao_orfa_divergente_com_novo_orfao(monkeypatch):
    sessoes_validas = {"s1"}
    monkeypatch.setattr(so, "carregar_sessoes_validas", lambda fn: sessoes_validas)

    def mock_contar(banco, sql, validas, fn_psql):
        if "registro" in sql:
            # 5 órfãos quando a base é 0
            return (10, 5)
        return (10, 0)

    monkeypatch.setattr(so, "contar_orfaos_tabela", mock_contar)

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = so.conferir(sha_release="abc1234", como_json=True)

    assert rc == 1
    dados = json.loads(buf.getvalue())
    reg_item = next(it for it in dados["itens"] if it["nome"] == "acervo.registro")
    assert reg_item["estado"] == "divergente"
    assert "5 órfãos (5 novo(s) acima da linha de base de 0" in reg_item["motivo"]


def test_sessao_orfa_indeterminavel_quando_sessao_db_fora(monkeypatch):
    def mock_carregar(fn):
        raise so.Indeterminavel("harness-sessao-db fora do ar")

    monkeypatch.setattr(so, "carregar_sessoes_validas", mock_carregar)

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = so.conferir(sha_release="abc1234", como_json=True)

    assert rc == 5
    dados = json.loads(buf.getvalue())
    assert any(it["estado"] == "indeterminavel" for it in dados["itens"])


def test_sessao_orfa_indeterminavel_quando_rag_db_fora(monkeypatch):
    monkeypatch.setattr(so, "carregar_sessoes_validas", lambda fn: {"s1"})

    def mock_contar(banco, sql, validas, fn_psql):
        if banco == "rag":
            raise so.Indeterminavel("rag-extractor-pg fora do ar")
        return (10, 0)

    monkeypatch.setattr(so, "contar_orfaos_tabela", mock_contar)

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = so.conferir(sha_release="abc1234", como_json=True)

    assert rc == 5
    dados = json.loads(buf.getvalue())
    assert any(it["estado"] == "indeterminavel" for it in dados["itens"])


def test_sessao_orfa_filtro_alvo(monkeypatch):
    monkeypatch.setattr(so, "carregar_sessoes_validas", lambda fn: {"s1"})
    monkeypatch.setattr(so, "contar_orfaos_tabela", lambda b, s, v, fn_psql=None: (5, 0))

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = so.conferir(alvo="registro", sha_release="abc1234", como_json=True)

    assert rc == 0
    dados = json.loads(buf.getvalue())
    assert len(dados["itens"]) == 1
    assert dados["itens"][0]["nome"] == "acervo.registro"


def test_sessao_orfa_alvo_inexistente(monkeypatch):
    monkeypatch.setattr(so, "carregar_sessoes_validas", lambda fn: {"s1"})

    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = so.conferir(alvo="tabela_que_nao_existe", sha_release="abc1234", como_json=True)

    assert rc == 1
    dados = json.loads(buf.getvalue())
    assert "nenhuma tabela corresponde" in dados["erro"]


def test_contar_orfaos_tabela_calculo():
    grupos = [
        {"sid": "s1", "qtd": 10},
        {"sid": "s2", "qtd": 5},
        {"sid": "orfao1", "qtd": 3},
        {"sid": "orfao2", "qtd": 2},
    ]
    fn = lambda b, s: grupos
    total, orfaos = so.contar_orfaos_tabela("rag", "sql", {"s1", "s2"}, fn_psql=fn)
    assert total == 20
    assert orfaos == 5
