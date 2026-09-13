# Contrato de `acervo` (bin/acervo) — arq:0110 / spec_acervo
import json
import subprocess
import os
import pytest

BIN = os.path.expanduser("~/AI/bin/acervo")
PG = "rag-extractor-pg"
DB = "rag_extractor"
USR = "rag"

def psql(sql):
    cmd = ["docker", "exec", "-i", PG, "psql", "-U", USR, "-d", DB, "-tA", "-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, f"SQL error: {r.stderr}"
    return r.stdout.strip()

# --- Camada A: Schema e Golden Record ---

def test_schema_ferramental_recurso():
    out = psql("SELECT count(*) FROM acervo.ferramental_recurso;")
    assert int(out) >= 11

    recursos = psql("SELECT id FROM acervo.ferramental_recurso ORDER BY id;").splitlines()
    assert "acervo.casa" in recursos
    assert "acervo.obra" in recursos
    assert "release" in recursos
    assert "repo" in recursos
    assert "nada" in recursos

def test_schema_ferramental_acesso():
    out = psql("SELECT count(*) FROM information_schema.columns WHERE table_schema='acervo' AND table_name='ferramental_acesso';")
    assert int(out) == 4

def test_schema_casa_fonte():
    out = psql("SELECT count(*) FROM acervo.casa_fonte WHERE repo='platafirma-arquitetura';")
    assert int(out) >= 1

def test_schema_entidade_classe_forma_chave():
    out = psql("SELECT forma_chave FROM acervo.entidade_classe WHERE slug='adr';")
    assert out == r"^(?:([a-z]+):)?(\d{1,4})$"

def test_schema_especie_tipo_padrao_path():
    out = psql("SELECT array_to_string(padrao_path, ',') FROM acervo.especie_tipo WHERE slug='adr';")
    assert "macro-global/decisions/*.md" in out

def test_schema_pg_trgm_indices():
    out = psql("SELECT count(*) FROM pg_indexes WHERE schemaname='acervo' AND indexname LIKE '%trgm%';")
    assert int(out) >= 2

def test_backfill_entidades_casa():
    out_adr = psql("SELECT count(*) FROM acervo.entidade WHERE classe='adr';")
    assert int(out_adr) >= 110

    out_spec = psql("SELECT count(*) FROM acervo.entidade WHERE classe='spec';")
    assert int(out_spec) >= 90

    out_suporte = psql("SELECT count(*) FROM acervo.entidade_suporte WHERE tipo='git';")
    assert int(out_suporte) >= 200

def test_acervo_usage_sem_argumento():
    r = subprocess.run([BIN], capture_output=True, text=True)
    assert r.returncode == 2
    assert "uso" in r.stderr.lower()

def test_acervo_ajuda():
    r = subprocess.run([BIN, "--ajuda"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "uso" in r.stderr.lower()

def test_acervo_ato_desconhecido():
    r = subprocess.run([BIN, "ato_inventado_xyz"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "desconhecido" in r.stderr.lower()
