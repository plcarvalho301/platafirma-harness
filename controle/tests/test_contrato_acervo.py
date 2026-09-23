# Contrato de `acervo` (bin/acervo) — arq:0110 / spec_acervo
import json
import subprocess
import os
import pytest

# `teste <verbo>` mede a REV (arq:0110 §9): o bin do repo, nao a copia servida no PATH.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN = os.path.join(REPO, "bin", "acervo")
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

def test_schema_casa_chave():
    # arq:0115 §3.1 e §3.5 (migracao 059): a ficha tem chave/serie/numero, e a retirada guarda
    # a data e a sucessora. A forma da chave de adr mora no cliente (_acervo/casa), nao mais
    # em entidade_classe.forma_chave (§6.2 tira adr de entidade_classe).
    cols = psql("SELECT string_agg(column_name, ',') FROM information_schema.columns "
                "WHERE table_schema='acervo' AND table_name='casa';").split(",")
    for c in ("chave", "serie", "numero", "retirada_em", "substituida_por"):
        assert c in cols, c

def test_schema_especie_tipo_projecao():
    # arq:0115 §4.1/§5: a especie declara a projecao do caminho e o regime; padrao_path
    # deixou de classificar (§4.4).
    out = psql("SELECT projecao || '|' || regime FROM acervo.especie_tipo WHERE slug='adr';")
    assert out == "adr/<serie>/<numero>-<slug>.md|vivo"
    out = psql("SELECT projecao || '|' || regime FROM acervo.especie_tipo WHERE slug='nota-tecnica';")
    assert out == "nota-tecnica/<AAAA-MM-DD>-<slug>.md|datado"
    out = psql("SELECT regime || '|' || encerra_em FROM acervo.especie_tipo WHERE slug='minuta';")
    assert out == "transitorio|formalizacao"

def test_schema_pg_trgm_indices():
    out = psql("SELECT count(*) FROM pg_indexes WHERE schemaname='acervo' AND indexname LIKE '%trgm%';")
    assert int(out) >= 2

def test_fichario_de_referentes():
    # arq:0115 §6.2 (migracao 059, D7): o Sobre: resolve em fichas de verbo, capacidade,
    # stack, instancia e repositorio; platafirma-arquitetura saiu do inventario (§1.2).
    for classe, minimo in (("verbo", 31), ("capacidade", 37), ("stack", 12), ("instancia", 3)):
        n = psql(f"SELECT count(*) FROM acervo.entidade WHERE classe='{classe}' AND estado='ativa';")
        assert int(n) >= minimo, classe
    repos = psql("SELECT string_agg(chave_humana, ',') FROM acervo.entidade "
                 "WHERE classe='repositorio' AND estado='ativa';").split(",")
    assert "platafirma-casa" in repos
    assert "platafirma-arquitetura" not in repos

def test_backfill_chave_adr():
    # arq:0115 §3.2: toda ADR viva tem serie e numero, e a chave e <serie>:NNNN.
    sem = psql("SELECT count(*) FROM acervo.casa c JOIN acervo.especie_tipo e ON e.id=c.especie_id "
               "WHERE e.slug='adr' AND c.retirada_em IS NULL AND (c.numero IS NULL OR c.serie IS NULL "
               "OR c.chave <> c.serie || ':' || lpad(c.numero::text, 4, '0'));")
    assert int(sem) == 0
    n = psql("SELECT count(*) FROM acervo.casa c JOIN acervo.especie_tipo e ON e.id=c.especie_id "
             "WHERE e.slug='adr' AND c.retirada_em IS NULL;")
    assert int(n) >= 110

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
    # arq:0115 §3/§11: `ler casa adr` le a CHAVE em acervo.casa. 110, 0110, arq:110 e
    # arq:0110 devolvem o mesmo corpo (o numero nu resolve porque so a serie arq tem 0110).
    # O `resolver adr` deixou de ser o caminho da leitura (§6.2 tira adr de entidade_classe).
    rs = [subprocess.run([BIN, "ler", "casa", "adr", s], capture_output=True, text=True)
          for s in ("110", "0110", "arq:110", "arq:0110")]
    for r in rs:
        assert r.returncode == 0, r.stderr
    assert rs[0].stdout == rs[1].stdout == rs[2].stdout == rs[3].stdout
    assert len(rs[0].stdout) > 50

def test_identidade_adr_forma_invalida():
    # arq:11O tem 'O' maiúsculo no lugar de zero; deve ser rejeitado com rc=2 e forma esperada
    r = subprocess.run([BIN, "ler", "casa", "adr", "arq:11O"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "invalido" in r.stderr
    assert "Forma esperada" in r.stderr

    # a forma de adr e do cliente (_identidade.FORMA_ADR), nao de entidade_classe: a recusa
    # vale antes e depois da 060 (arq:0115 §6.2)
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
    # arq:0115 §3.2: series de adr compartilham numeros (arq:0075 e ont:0075). Numero nu que
    # existe em mais de uma serie sai 2 com as opcoes, em vez de supor a serie arq. O numero
    # vem do estado do banco: a serie ont so entra com a 1a ingestao da arvore completa de
    # platafirma-casa; sem numero nenhum em duas series, nao ha o que medir.
    out = psql("SELECT c.numero || '|' || string_agg(c.chave, ',' ORDER BY c.chave) "
               "FROM acervo.casa c JOIN acervo.especie_tipo e ON e.id = c.especie_id "
               "WHERE e.slug = 'adr' AND c.numero IS NOT NULL GROUP BY c.numero "
               "HAVING count(DISTINCT c.serie) > 1 ORDER BY c.numero LIMIT 1;")
    if not out:
        pytest.skip("nenhum numero de adr em mais de uma serie em acervo.casa "
                    "(serie ont ainda nao ingerida de platafirma-casa)")
    numero, chaves = out.split("|", 1)
    r = subprocess.run([BIN, "ler", "casa", "adr", numero], capture_output=True, text=True)
    assert r.returncode == 2, r.stderr
    assert "ambiguo" in r.stderr
    for chave in chaves.split(","):
        assert chave in r.stderr, chave

def test_identidade_inexistente_exit_1():
    # Seletor inexistente deve sair 1 com as 4 linhas fixas da spec §4, sem caminho de
    # repo de release (arq:0115 §1.2): o vizinho e o catalogo e a cura e o suporte.
    r = subprocess.run([BIN, "ler", "casa", "adr", "arq:9999"], capture_output=True, text=True)
    assert r.returncode == 1
    assert "varrido:" in r.stderr
    assert "parecidos:" in r.stderr
    assert "vizinho:" in r.stderr
    assert "cura:" in r.stderr
    assert "acervo listar casa adr" in r.stderr
    assert "acervo ingerir casa platafirma-casa" in r.stderr
    assert "platafirma-arquitetura" not in r.stderr
    assert "macro-global" not in r.stderr
    assert "release promover" not in r.stderr
    # o varrido da leitura de casa e so o suporte: as fontes de antes da arq:0115 seguem em
    # acervo.casa_fonte (o servidor so insere) e nao se nomeiam na negativa
    varrido = next(l for l in r.stderr.splitlines() if l.startswith("varrido:"))
    assert "fonte platafirma-casa" in varrido

    # `resolver adr`: ate a 060, adr segue em entidade_classe e a negativa e a de 4 linhas;
    # depois dela (arq:0115 §6.2), o ato recusa (exit 2) e aponta a leitura pela chave.
    tem_classe = psql("SELECT count(*) FROM acervo.entidade_classe WHERE slug='adr';") != "0"
    r_res = subprocess.run([BIN, "resolver", "adr", "9999"], capture_output=True, text=True)
    if tem_classe:
        assert r_res.returncode == 1, r_res.stderr
        assert "varrido:" in r_res.stderr
        assert "parecidos:" in r_res.stderr
        assert "vizinho:" in r_res.stderr
        assert "cura:" in r_res.stderr
    else:
        assert r_res.returncode == 2, r_res.stderr
        assert "acervo ler casa adr 9999" in r_res.stderr


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

def test_listar_casa_servido_honesto():
    # arq:0110 Q6 / arq:0115 D9: `servido` compara o sha ingerido com o main do espelho do
    # suporte; nunca o "(igual)" fixo de antes.
    r = subprocess.run([BIN, "ler", "casa", "adr", "arq:0110", "--situacao"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "servido:" in r.stdout
    assert "(igual)" not in r.stdout

def test_listar_casa_primeira_linha_cobertura():
    # arq:0115 §11.2 e §4.3: a 1a linha diz o que veio, a fonte, a projecao, o regime e o
    # ultimo numero da serie; as linhas vem pela chave.
    r = subprocess.run([BIN, "listar", "casa", "adr"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    linhas = r.stdout.splitlines()
    assert " linha(s) · adr · fonte platafirma-casa" in linhas[0]
    assert "projeção adr/<serie>/<numero>-<slug>.md" in linhas[0]
    assert "regime vivo" in linhas[0]
    assert "arq:0" in linhas[0]  # ultimo: arq:NNNN
    assert any(l.startswith("arq:0110 ") for l in linhas[1:])
    assert "platafirma-arquitetura@" not in r.stdout

def test_listar_casa_catalogo_sem_especie():
    # arq:0115 §4.3/D9: `listar casa` sem especie e o catalogo, nao "falta a entidade".
    r = subprocess.run([BIN, "listar", "casa"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "espécie(s) de casa" in r.stdout.splitlines()[0]
    assert "adr/<serie>/<numero>-<slug>.md" in r.stdout
    assert "minuta/<numero>-<slug>.md" in r.stdout

def test_listar_casa_sobre():
    # arq:0115 §6.4: «a documentacao de X». Forma com classe e chave, e <classe>:<chave>.
    r = subprocess.run([BIN, "listar", "casa", "--sobre", "verbo", "acervo"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "documento(s) sobre verbo acervo" in r.stdout.splitlines()[0]
    r2 = subprocess.run([BIN, "listar", "casa", "--sobre", "verbo:acervo"], capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    assert r2.stdout.splitlines()[0] == r.stdout.splitlines()[0]
    # referente que nao resolve: nada, exit 1 (nao "0 linhas")
    r3 = subprocess.run([BIN, "listar", "casa", "--sobre", "verbo", "verbo-inexistente-0115"],
                        capture_output=True, text=True)
    assert r3.returncode == 1

def test_ler_casa_retirada_responde_sucessora():
    # arq:0115 §3.5 (D4): chave de documento retirado segue resolvivel e responde a data e a
    # sucessora, sem o texto. arq:0094 (superseded por arq:0112) sai do suporte na migracao, e
    # a retirada grava substituida_por = 'arq:0112' (servidor). Enquanto a linha nao existir
    # retirada (antes da 1a ingestao de platafirma-casa por arvore completa), nao ha o que medir.
    n = psql("SELECT count(*) FROM acervo.casa WHERE chave='arq:0094' AND retirada_em IS NOT NULL;")
    if n == "0":
        pytest.skip("arq:0094 ainda nao existe retirada em acervo.casa "
                    "(falta a 1a ingestao de platafirma-casa por arvore completa)")
    ret = psql("SELECT coalesce(substituida_por, '(nula)') FROM acervo.casa "
               "WHERE chave='arq:0094' AND retirada_em IS NOT NULL;")
    assert ret == "arq:0112", ret
    r = subprocess.run([BIN, "ler", "casa", "adr", "arq:0094"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    linhas = r.stdout.splitlines()
    assert linhas[0].startswith("arq:0094: retirada em "), r.stdout
    assert "substituída por arq:0112" in linhas[0]
    assert "sem sucessora declarada" not in r.stdout
    assert len(linhas) <= 2
    rj = subprocess.run([BIN, "ler", "casa", "adr", "arq:0094", "--json"],
                        capture_output=True, text=True)
    assert rj.returncode == 0, rj.stderr
    doc = json.loads(rj.stdout)
    assert doc["corpo"] is None and doc["substituida_por"] == "arq:0112"

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
    assert ("Caminho: write_file na bancada de platafirma-casa → PR → merge em main → "
            "acervo ingerir casa platafirma-casa.") in r.stderr
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


def test_camada_d_recusa_adr_deprecado():
    r = subprocess.run([BIN, "adr", "0110"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "acervo adr: ato deprecado e removido" in r.stderr
    assert "acervo ler casa adr" in r.stderr


def test_camada_d_recusa_ato_desconhecido():
    r = subprocess.run([BIN, "ato_inexistente"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "acervo: ato 'ato_inexistente' desconhecido" in r.stderr
    assert "Atos canonicos: ler, listar, resolver, escrever, ingerir, curar, extrato, exportar, psql" in r.stderr


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
