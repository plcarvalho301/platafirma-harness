"""Privilégios efetivos, idempotência e limites no PostgreSQL 16."""
import pytest

def test_grants_e_limites(pg):
    cfg,admin=pg
    assert admin.execute("SHOW server_version_num").fetchone()[0].startswith("16")
    assert not admin.execute("SELECT has_table_privilege('analise_extracao','acervo.log','SELECT')").fetchone()[0]
    assert admin.execute("SELECT has_column_privilege('analise_extracao','acervo.log','ts','SELECT')").fetchone()[0]
    assert not admin.execute("SELECT has_column_privilege('analise_extracao','acervo.log','segredo','SELECT')").fetchone()[0]
    assert not admin.execute("SELECT has_table_privilege('analise_publicacao','acervo.log','SELECT')").fetchone()[0]
    assert not admin.execute("SELECT has_schema_privilege('analise_extracao','analise','USAGE')").fetchone()[0]
    import psycopg
    with psycopg.connect(**{**cfg,"user":"analise_extracao"},autocommit=True) as conn:
        assert conn.execute("SHOW temp_file_limit").fetchone()[0]=="256MB"
        assert conn.execute("SHOW default_transaction_read_only").fetchone()[0]=="on"
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT segredo FROM acervo.log")

def test_migracao_idempotente(pg):
    from conftest import CONHECIMENTO
    _,admin=pg
    with admin.transaction():
        admin.execute((CONHECIMENTO/"rag/db/init/159_schema_analise.sql").read_text())
    assert admin.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema='analise' AND table_name IN ('execucao','base','resultado','tabela','projecao')").fetchone()[0]==5
