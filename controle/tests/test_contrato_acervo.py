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


# --- Camada B: Identidade ---

def test_identidade_adr_equivalencia():
    # 110, 0110 e arq:110 devem devolver exatamente o mesmo corpo e o mesmo id
    r1 = subprocess.run([BIN, "ler", "casa", "adr", "110"], capture_output=True, text=True)
    r2 = subprocess.run([BIN, "ler", "casa", "adr", "0110"], capture_output=True, text=True)
    r3 = subprocess.run([BIN, "ler", "casa", "adr", "arq:110"], capture_output=True, text=True)
    assert r1.returncode == 0
    assert r2.returncode == 0
    assert r3.returncode == 0
    assert r1.stdout == r2.stdout == r3.stdout
    assert len(r1.stdout) > 50

    # No resolver tambem
    res1 = subprocess.run([BIN, "resolver", "adr", "110"], capture_output=True, text=True)
    res2 = subprocess.run([BIN, "resolver", "adr", "0110"], capture_output=True, text=True)
    res3 = subprocess.run([BIN, "resolver", "adr", "arq:110"], capture_output=True, text=True)
    assert res1.returncode == 0
    assert res2.returncode == 0
    assert res3.returncode == 0
    assert res1.stdout.strip() == res2.stdout.strip() == res3.stdout.strip()

def test_identidade_adr_forma_invalida():
    # arq:11O tem 'O' maiúsculo no lugar de zero; deve ser rejeitado com rc=2 e forma esperada
    r = subprocess.run([BIN, "ler", "casa", "adr", "arq:11O"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "invalido" in r.stderr
    assert "Forma esperada" in r.stderr

    r_res = subprocess.run([BIN, "resolver", "adr", "arq:11O"], capture_output=True, text=True)
    assert r_res.returncode == 2
    assert "invalido" in r_res.stderr

def test_identidade_alias_via_alias():
    # Resolvendo conceito por alias conhecido deve devolver rc=0 e emitir 'via: alias'
    r = subprocess.run([BIN, "resolver", "conceito", "information hiding"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "via: alias" in r.stdout

    # Com --json
    r_json = subprocess.run([BIN, "resolver", "conceito", "information hiding", "--json"], capture_output=True, text=True)
    assert r_json.returncode == 0
    d = json.loads(r_json.stdout)
    assert d["achou"] is True
    assert d["via"] == "alias"

def test_identidade_ambiguidade():
    # Seletor ambiguo em spec (README aponta para 2 fichas) deve sair 2 com a lista de candidatos
    r = subprocess.run([BIN, "resolver", "spec", "README"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "ambiguo" in r.stderr

def test_identidade_inexistente_exit_1():
    # Seletor inexistente deve sair 1 com as 4 linhas fixas da spec §4
    r = subprocess.run([BIN, "ler", "casa", "adr", "9999"], capture_output=True, text=True)
    assert r.returncode == 1
    assert "varrido:" in r.stderr
    assert "parecidos:" in r.stderr
    assert "vizinho:" in r.stderr
    assert "cura:" in r.stderr

    r_res = subprocess.run([BIN, "resolver", "adr", "9999"], capture_output=True, text=True)
    assert r_res.returncode == 1
    assert "varrido:" in r_res.stderr
    assert "parecidos:" in r_res.stderr
    assert "vizinho:" in r_res.stderr
    assert "cura:" in r_res.stderr
