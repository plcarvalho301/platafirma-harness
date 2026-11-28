"""Regressão do incidente #4467: SQL_DIGEST_CLASSE sobre uuid e mapeamento de erro SQL."""
from __future__ import annotations

from leitura.moradas.banco import (
    SQL_DIGEST_CLASSE,
    SQL_LISTAR_CHAVE_CORTE,
    _mapear_erro_banco,
)


class _UndefinedFunctionFake(Exception):
    sqlstate = "42883"


class _OperationalErrorFake(Exception):
    sqlstate = "08006"


def test_sql_digest_classe_converte_uuid_antes_de_max() -> None:
    """casa.shape.fornada é uuid no PostgreSQL; max(uuid) não existe (#4467)."""
    assert "max(c.fornada)" not in SQL_DIGEST_CLASSE
    assert "max(c.fornada::text)" in SQL_DIGEST_CLASSE


def test_mapear_erro_banco_nao_mascara_erro_sql_como_morada_sem_resposta() -> None:
    """Erro de SQL (ex.: UndefinedFunction 42883) não deve virar morada-sem-resposta."""
    exc = _UndefinedFunctionFake("function max(uuid) does not exist")
    recusa = _mapear_erro_banco(exc, "conceito:capacidade-estatal")
    assert recusa.saida == 5
    assert recusa.codigo == "erro-consulta-banco"
    assert recusa.regra == "consulta-sql-valida"


def test_mapear_erro_banco_mantem_morada_sem_resposta_para_conexao() -> None:
    """Falha real de conexão continua devolvendo saída 3 e morada-sem-resposta."""
    exc = _OperationalErrorFake("connection refused")
    recusa = _mapear_erro_banco(exc, "conceito:capacidade-estatal")
    assert recusa.saida == 3
    assert recusa.codigo == "morada-sem-resposta"
    assert recusa.regra == "conexao-postgresql-direta"


def test_sql_listar_chave_corte_nao_consulta_coluna_inexistente_em_nome_da_ficha() -> None:
    """DT 1435: casa_leitura.nome_da_ficha não tem coluna rotulo (causava UndefinedColumn)."""
    assert "nome_da_ficha" not in SQL_LISTAR_CHAVE_CORTE
    assert "n.rotulo" not in SQL_LISTAR_CHAVE_CORTE
    assert "sh.rotulo" in SQL_LISTAR_CHAVE_CORTE
    assert "dc.rotulo" in SQL_LISTAR_CHAVE_CORTE
    assert "casa.dado" in SQL_LISTAR_CHAVE_CORTE
