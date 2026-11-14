"""Debito 432: platafirma-casa-espelho (a casa nova, F3974) e repositorio de trabalho do `release`
e do `teste`, como esteira documento.

Prova, no registro real da arvore: a familia esta em familias.json com a URL do forge; esta em
venvs.json como esteira documento (sem lock, que a esteira documento dispensa); o resolvedor do
`teste` e do `pre-push` a conhece; e o `release promover --ensaio` a aceita (sem a declaracao,
sai 2). As leituras do `release` (ler, listar, estado) so passam a achar a familia depois da
primeira promocao, que cria a pasta dela em /opt/platafirma.
Nao prova: promover (o gate da esteira documento chama `acervo ingerir casa --arvore`, que so
aceita platafirma-casa) nem a escrita pela porta (ops-server/test_raizes_porta.py).
"""
import json
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
FAMILIAS = RAIZ / "registro" / "familias.json"
VENVS = RAIZ / "registro" / "venvs.json"
REGISTRO = RAIZ / "bin" / "_release" / "registro.py"
RELEASE = RAIZ / "bin" / "release"
ESPELHO = "platafirma-casa-espelho"


def test_familia_declarada_com_a_url_do_forge():
    familias = json.loads(FAMILIAS.read_text(encoding="utf-8"))
    assert familias[ESPELHO] == f"https://github.com/plcarvalho301/{ESPELHO}.git"


def test_repositorio_declarado_como_esteira_documento():
    repos = json.loads(VENVS.read_text(encoding="utf-8"))["repositorios"]
    assert repos[ESPELHO] == {"esteira": "documento"}


def test_resolvedor_do_teste_conhece_o_repositorio():
    r = subprocess.run(["python3", str(REGISTRO), ESPELHO], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(VENVS)}, check=False)
    assert r.returncode == 0, r.stderr
    campos = r.stdout.rstrip("\n").split("\t")
    assert campos[0] == ESPELHO and campos[3] == "documento", campos


def test_posto_resolve_para_a_stack_do_vault_e_fica_fora_das_familias():
    """#2856 linha 453: o posto e repositorio de trabalho do `teste`, sem release. A stack
    vault-ontologia tem lock e subarvore no posto, declara `promovida: false` e o posto fica fora
    de familias.json. Nao prova: que o venv constroi (isso e `teste rodar vault-ontologia`)."""
    def resolver(nome):
        r = subprocess.run(["python3", str(REGISTRO), nome], capture_output=True, text=True,
                           env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(VENVS)}, check=False)
        assert r.returncode == 0, r.stderr
        return r.stdout.rstrip("\n").split("\t")
    pela_stack, pelo_repo = resolver("vault-ontologia"), resolver("platafirma-posto")
    # colunas do registro.py: familia, lock, subarvore, esteira, stack, globs
    assert pela_stack == pelo_repo
    assert pela_stack[:5] == ["platafirma-posto", "ferramentas/vault-ontologia/uv.lock",
                              "ferramentas/vault-ontologia/testes", "codigo", "vault-ontologia"], pela_stack
    assert json.loads(VENVS.read_text(encoding="utf-8"))["vault-ontologia"]["promovida"] is False
    assert "platafirma-posto" not in json.loads(FAMILIAS.read_text(encoding="utf-8"))

def _promover_em_ensaio(tmp_path, familias):
    """Mesmo arranjo de test_release_ensaio_fetch.py: stub de `acervo` (registro de stacks vazio)."""
    stub_bin = tmp_path / "stub-bin"
    stub_bin.mkdir(exist_ok=True)
    acervo = stub_bin / "acervo"
    acervo.write_text("#!/usr/bin/env bash\n"
                      "if [ \"$1\" = ler ] && [ \"$2\" = casa ] && [ \"$3\" = stack ]; then echo '[]'; exit 0; fi\n"
                      "exit 1\n", encoding="utf-8")
    acervo.chmod(0o755)
    terceiros = tmp_path / "terceiros.json"
    terceiros.write_text("{}", encoding="utf-8")
    env = {"PATH": f"{stub_bin}:/usr/bin:/bin", "HOME": str(tmp_path),
           "PLATAFIRMA_FAMILIAS": str(familias), "PLATAFIRMA_VENVS": str(VENVS),
           "PLATAFIRMA_TERCEIROS": str(terceiros), "PF_RELEASE_PORTA": "0",
           "PF_RELEASE_RAIZ": str(tmp_path / "release"),
           "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia")}
    return subprocess.run([str(RELEASE), "promover", ESPELHO, "--ensaio"], env=env,
                          capture_output=True, text=True, check=False, timeout=90)


def test_release_promove_a_familia_declarada_e_recusa_a_fora_do_registro(tmp_path):
    """Com a declaracao, o ensaio chega a «clonaria <url>»; sem ela, sai 2 «fora do registro»."""
    r = _promover_em_ensaio(tmp_path, FAMILIAS)
    assert f"clonaria https://github.com/plcarvalho301/{ESPELHO}.git" in r.stdout + r.stderr, r.stderr
    sem = tmp_path / "sem-espelho.json"
    declaradas = json.loads(FAMILIAS.read_text(encoding="utf-8"))
    declaradas.pop(ESPELHO)
    sem.write_text(json.dumps(declaradas), encoding="utf-8")
    r = _promover_em_ensaio(tmp_path, sem)
    assert r.returncode == 2 and "fora do registro de famílias" in r.stderr, (r.returncode, r.stderr)


def test_espelho_conhecimento_resolve_e_teste_roda_sob_venv(tmp_path):
    """DT 567: stack espelho-conhecimento usa venv:rag e `teste rodar <espelho> <alvo>` cai nela."""
    raiz = Path(__file__).resolve().parents[2]
    reg = raiz / "bin" / "_release" / "registro.py"
    r_reg = subprocess.run(
        ["python3", str(reg), "espelho-conhecimento"],
        env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(VENVS)},
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert r_reg.returncode == 0, r_reg.stderr
    assert r_reg.stdout.strip() == (
        f"{ESPELHO}\tvenv:rag\toutros_repos/conhecimento/rag\tcodigo\tespelho-conhecimento\t-"
    )

    bancada = tmp_path / "bancada"
    wt = bancada / "wt" / ESPELHO / "ti" / "t1"
    alvo_dir = wt / "outros_repos" / "conhecimento" / "rag" / "tests"
    alvo_dir.mkdir(parents=True)
    (wt / ".git").mkdir()
    (alvo_dir / "test_ok.py").write_text("def test_ok(): assert True\n", encoding="utf-8")

    rel_venv = tmp_path / "release" / "current" / "venv" / "rag" / "bin"
    rel_venv.mkdir(parents=True)
    py_stub = rel_venv / "python"
    py_stub.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = -c ]; then exit 1; fi\n"
        "echo \"PYTEST_ARGS: $*\"\n"
        "echo '1 passed in 0.01s'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    py_stub.chmod(0o755)

    inst = tmp_path / "instancia"
    inst.mkdir()
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PLATAFIRMA_VENVS": str(VENVS),
        "PF_CADEIRA": "ti",
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PF_TESTE_SEM_MEMO": "1",
    }
    r_teste = subprocess.run(
        [str(raiz / "bin" / "teste"), "rodar", f"{ESPELHO}@t1",
         "outros_repos/conhecimento/rag/tests/test_ok.py"],
        env=env, capture_output=True, text=True, check=False, timeout=30,
    )
    assert r_teste.returncode == 0, r_teste.stdout + r_teste.stderr
    assert "suite VERDE: platafirma-casa-espelho@t1 (chave espelho-conhecimento)" in r_teste.stdout
