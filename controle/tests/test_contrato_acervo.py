# Contrato de `acervo` (bin/acervo) — arq:0110 / spec_acervo
import json
import subprocess
import os
import pytest

# `teste <verbo>` mede a REV (arq:0110 §9): o bin do repo, nao a copia servida no PATH.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN = os.path.join(REPO, "bin", "acervo")
CONFERIR = os.path.join(REPO, "bin", "conferir")
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
    # A tabela existe; linha so nasce no apply de uma ingestao (servidor). Sem seed.
    out = psql("SELECT count(*) FROM information_schema.columns WHERE table_schema='acervo' AND table_name='casa_fonte';")
    assert int(out) == 4
    semeadas = psql("SELECT count(*) FROM acervo.casa_fonte WHERE ordem_id LIKE 'seed-%';")
    assert int(semeadas) == 0

def test_schema_ferramental_ato():
    out = psql("SELECT count(*) FROM information_schema.columns WHERE table_schema='acervo' AND table_name='ferramental_ato';")
    assert int(out) == 5
    colunas_velhas = psql("SELECT count(*) FROM information_schema.columns WHERE table_schema='acervo' AND table_name='ferramental_capacidade' AND column_name IN ('verbo','ato');")
    assert int(colunas_velhas) == 0

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


# --- Camada C: Contrato de Retorno ---

def test_listar_casa_vazio_com_motivo():
    r = subprocess.run([BIN, "listar", "casa", "adr", "--dono", "cadeira_inexistente_xyz"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "motivo:" in r.stdout

def test_listar_casa_situacao():
    r = subprocess.run([BIN, "listar", "casa", "adr", "--situacao"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "fonte:" in r.stdout
    assert "ingerido:" in r.stdout
    assert "servido:" in r.stdout
    assert "vetorizado:" in r.stdout
    assert "status:" in r.stdout

def test_listar_obra_sobre_termo():
    r = subprocess.run([BIN, "listar", "obra", "obra", "--sobre", "mathematical"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "Proofs and Refutations" in r.stdout
    assert "[titulo]" in r.stdout

def test_listar_obra_situacao():
    r = subprocess.run([BIN, "listar", "obra", "obra", "--sobre", "mathematical", "--situacao"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "Proofs and Refutations" in r.stdout
    assert "servivel:" in r.stdout
    assert "degrau:" in r.stdout
    assert "store:" in r.stdout
    assert "impressao:" in r.stdout

def test_listar_obra_vazio_com_motivo():
    r = subprocess.run([BIN, "listar", "obra", "obra", "--sobre", "termo_completamente_inexistente_12345"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "motivo:" in r.stdout
    assert "varrido:" in r.stdout
    assert "acervo.obra" in r.stdout

def test_escrever_recusa_de_fronteira():
    r = subprocess.run([BIN, "escrever", "casa", "adr", "x"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "adr nasce em git, não se escreve no acervo." in r.stderr
    assert "Caminho: write_file → repo commitar → release promover → acervo ingerir casa <repo>." in r.stderr
    assert "escrever grava só: pagina, arquivo, ferramental, stack." in r.stderr

def test_curar_casa_alias():
    r_curar = subprocess.run([BIN, "curar", "casa", "alias", "conceito", "tempo-percebido", "teste-alias-tempo"], capture_output=True, text=True)
    assert r_curar.returncode == 0
    assert "vinculado" in r_curar.stdout

    r_res = subprocess.run([BIN, "resolver", "conceito", "teste-alias-tempo"], capture_output=True, text=True)
    assert r_res.returncode == 0
    assert "via: alias" in r_res.stdout
    # o teste nao deixa vocabulario de teste no canon
    psql("DELETE FROM acervo.entidade_alias WHERE alias='teste-alias-tempo' AND origem='curadoria';")

def test_ingerir_casa_dry_run():
    r = subprocess.run([BIN, "ingerir", "casa", "platafirma-arquitetura"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "Plano de ingestao casa:" in r.stdout
    assert "Aprovados por espécie:" in r.stdout
    assert "adr" in r.stdout
    assert "spec" in r.stdout
    assert "Reprovados sem cobertura" in r.stdout
    assert "nenhum padrao_path em acervo.especie_tipo cobre este caminho" in r.stdout


# --- CAMADA D: Despachante, Cabeçalho Q1 e Conferencia ---

def test_camada_d_cabecalho_q1():
    with open(BIN, "r", encoding="utf-8") as f:
        lines = [f.readline() for _ in range(15)]
    text = "".join(lines)
    assert "# capacidade: conhecimento" in text
    assert "# dono: dados" in text
    assert "# classe: B" in text
    with open(BIN, "r", encoding="utf-8") as f:
        text = "".join(f.readline() for _ in range(45))
    # acesso e POR ATO: uma linha `# le:`/`# escreve:` para cada um dos oito atos
    for ato in ("ler", "listar", "resolver", "escrever", "ingerir", "curar", "extrato", "psql"):
        assert f"# le: {ato}=" in text
        assert f"# escreve: {ato}=" in text
    # ato que escreve declara escrita (Q12): psql escreve, logo nao e 'leitura'
    assert "psql (escrita, acervo)" in text
    assert "# escreve: ler=nada" in text
    assert "# consome: motor_acervo_rest, rag_extractor_pg" in text


def test_camada_d_conferir_verbo_acervo():
    r = subprocess.run([CONFERIR, "verbo", "acervo"], capture_output=True, text=True)
    # symlink para release e a unica origem conforme (arq:0110 §2); copia identica e defeito
    # de instalacao e sai 1 — o gate mede o verbo, nao o passa por estar igual ao repo.
    if "origem  : symlink-release" in r.stdout:
        assert r.returncode == 0
    else:
        assert "origem  : copia-identica-ao-repo" in r.stdout
        assert r.returncode == 1
    assert "capacidade=conhecimento" in r.stdout


def test_camada_d_escrever_casa_ferramental_acervo():
    r = subprocess.run([BIN, "escrever", "casa", "ferramental", "acervo"], capture_output=True, text=True)
    assert r.returncode == 0
    # Verifica em acervo.ferramental_capacidade as 8 linhas
    out_ato = psql("SELECT count(*) FROM acervo.ferramental_ato WHERE verbo='acervo'")
    assert out_ato.strip() == "8"
    # acesso por ato: todo ato tem linha `le` e linha `escreve`; `nada` e linha explicita
    out_le = psql("SELECT count(DISTINCT ato) FROM acervo.ferramental_acesso WHERE verbo='acervo' AND modo='le'")
    assert out_le.strip() == "8"
    out_w = psql("SELECT count(DISTINCT ato) FROM acervo.ferramental_acesso WHERE verbo='acervo' AND modo='escreve'")
    assert out_w.strip() == "8"
    out_nada = psql("SELECT count(*) FROM acervo.ferramental_acesso WHERE verbo='acervo' AND ato='ler' AND modo='escreve' AND recurso_id='nada'")
    assert out_nada.strip() == "1"
    # Verifica acervo.ferramental_acesso
    out_acesso = psql("SELECT count(*) FROM acervo.ferramental_acesso WHERE verbo='acervo'")
    assert int(out_acesso.strip()) > 0
    # Verifica acervo.ferramental_consumo
    out_consumo = psql("SELECT count(*) FROM acervo.ferramental_consumo WHERE verbo='acervo'")
    assert int(out_consumo.strip()) > 0
    # Verifica acervo.ferramental_ambiente
    out_amb = psql("SELECT count(*) FROM acervo.ferramental_ambiente WHERE verbo='acervo'")
    assert int(out_amb.strip()) == 3


def test_camada_d_recusa_adr_deprecado():
    r = subprocess.run([BIN, "adr", "0110"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "acervo adr: ato deprecado e removido" in r.stderr
    assert "acervo ler casa adr" in r.stderr


def test_camada_d_recusa_ato_desconhecido():
    r = subprocess.run([BIN, "ato_inexistente"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "acervo: ato 'ato_inexistente' desconhecido" in r.stderr
    assert "Atos canonicos: ler, listar, resolver, escrever, ingerir, curar, extrato, psql" in r.stderr


def test_camada_d_aviso_uma_vez_por_sessao(tmp_path):
    sess_id = f"test-sess-{os.getpid()}"
    env = dict(os.environ, PF_SESSAO_ID=sess_id)
    # Primeira chamada: emite aviso
    r1 = subprocess.run([BIN, "bancada", "obra", "lote"], env=env, capture_output=True, text=True)
    assert "acervo: `acervo bancada` e a forma vigente" in r1.stderr
    # Segunda chamada na mesma sessão: NÃO emite aviso
    r2 = subprocess.run([BIN, "bancada", "obra", "lote"], env=env, capture_output=True, text=True)
    assert "acervo: `acervo bancada` e a forma vigente" not in r2.stderr
    # Limpa diretório efêmero de aviso
    import shutil
    shutil.rmtree(f"/tmp/platafirma-avisos-{sess_id}", ignore_errors=True)


def test_camada_d_oito_atos_canonicos_disponiveis():
    # 1. ler
    r_ler = subprocess.run([BIN, "ler", "casa", "adr", "0110"], capture_output=True, text=True)
    assert r_ler.returncode == 0
    # 2. listar
    r_listar = subprocess.run([BIN, "listar", "casa", "adr"], capture_output=True, text=True)
    assert r_listar.returncode == 0
    # 3. resolver
    r_res = subprocess.run([BIN, "resolver", "adr", "0110"], capture_output=True, text=True)
    assert r_res.returncode == 0
    # 4. escrever (fronteira)
    r_esc = subprocess.run([BIN, "escrever", "casa", "adr", "0110"], capture_output=True, text=True)
    assert r_esc.returncode == 2
    # 5. ingerir
    r_ing = subprocess.run([BIN, "ingerir", "casa", "platafirma-arquitetura"], capture_output=True, text=True)
    assert r_ing.returncode == 0
    # 6. curar
    r_cur = subprocess.run([BIN, "curar", "casa", "alias", "adr", "0110", "alias-teste-d"], capture_output=True, text=True)
    assert r_cur.returncode == 0
    psql("DELETE FROM acervo.entidade_alias WHERE alias='alias-teste-d' AND origem='curadoria';")
    # 7. extrato
    r_ext = subprocess.run([BIN, "extrato", "--ajuda"], capture_output=True, text=True)
    assert r_ext.returncode == 2
    # 8. psql
    r_psql = subprocess.run([BIN, "psql", "--ajuda"], capture_output=True, text=True)
    assert r_psql.returncode == 2


