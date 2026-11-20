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

import pytest

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
    assert repos[ESPELHO] == {"esteira": "documento", "conferir_no_ar": True}


def test_resolvedor_do_teste_conhece_o_repositorio():
    r = subprocess.run(["python3", str(REGISTRO), ESPELHO], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(VENVS)}, check=False)
    assert r.returncode == 0, r.stderr
    campos = r.stdout.rstrip("\n").split("\t")
    assert campos[0] == ESPELHO and campos[3] == "documento", campos


def test_posto_esta_nas_familias_e_resolve_stacks_do_posto_e_espelho():
    """#4345 (premissa 2): o posto passa a familia promovida em familias.json e declara as stacks
    vault-ontologia, harnesses e espelho-posto-harnesses em venvs.json."""
    def resolver(nome):
        r = subprocess.run(["python3", str(REGISTRO), nome], capture_output=True, text=True,
                           env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(VENVS)}, check=False)
        assert r.returncode == 0, r.stderr
        return r.stdout.rstrip("\n").split("\t")

    vault = resolver("vault-ontologia")
    assert vault[:5] == ["platafirma-posto", "ferramentas/vault-ontologia/uv.lock",
                         "ferramentas/vault-ontologia/testes", "codigo", "vault-ontologia"], vault
    harnesses = resolver("harnesses")
    assert harnesses[:5] == ["platafirma-posto", "ferramentas/vault-ontologia/uv.lock",
                             "harnesses/tests", "codigo", "harnesses"], harnesses
    espelho_h = resolver("espelho-posto-harnesses")
    assert espelho_h[:5] == [ESPELHO, "outros_repos/posto/ferramentas/vault-ontologia/uv.lock",
                             "outros_repos/posto/harnesses/tests", "codigo", "espelho-posto-harnesses"], espelho_h
    venvs = json.loads(VENVS.read_text(encoding="utf-8"))
    assert venvs["espelho-posto-harnesses"]["promovida"] is False
    assert venvs["harnesses"].get("promovida", True) is True
    assert venvs["vault-ontologia"].get("promovida", True) is True
    familias = json.loads(FAMILIAS.read_text(encoding="utf-8"))
    assert familias["platafirma-posto"] == "https://github.com/plcarvalho301/platafirma-posto.git"

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


def test_diagrama_resolve_e_teste_roda_sob_venv(tmp_path):
    """DT 567: stack diagrama usa venv:rag e `teste rodar platafirma-harness <alvo>` cai nela."""
    raiz = Path(__file__).resolve().parents[2]
    reg = raiz / "bin" / "_release" / "registro.py"
    r_reg = subprocess.run(
        ["python3", str(reg), "diagrama"],
        env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(VENVS)},
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert r_reg.returncode == 0, r_reg.stderr
    assert r_reg.stdout.strip() == (
        "platafirma-harness\tvenv:rag\tlib/diagrama\tcodigo\tdiagrama\t-"
    )

    bancada = tmp_path / "bancada"
    wt = bancada / "wt" / "platafirma-harness" / "ti" / "t1"
    alvo_dir = wt / "lib" / "diagrama" / "tests"
    alvo_dir.mkdir(parents=True)
    (wt / ".git").mkdir()
    (alvo_dir / "test_ok.py").write_text("def test_ok(): assert True\n", encoding="utf-8")

    rel_venv = tmp_path / "release" / "current" / "venv" / "rag" / "bin"
    rel_venv.mkdir(parents=True)
    py_stub = rel_venv / "python"
    py_stub.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = -c ]; then\n"
        "  [[ \"${2:-}\" == *pytest* ]] && exit 0\n"
        "  exit 1\n"
        "fi\n"
        "echo \"PYTEST_ARGS: $*\"\n"
        "echo '1 passed in 0.01s'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    py_stub.chmod(0o755)

    inst = tmp_path / "instancia"
    inst.mkdir()
    terceiros = tmp_path / "terceiros.json"
    terceiros.write_text("{}", encoding="utf-8")
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PLATAFIRMA_VENVS": str(VENVS),
        "PLATAFIRMA_TERCEIROS": str(terceiros),
        "PF_CADEIRA": "ti",
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PF_TESTE_SEM_MEMO": "1",
    }
    r_teste = subprocess.run(
        [str(raiz / "bin" / "teste"), "rodar", "platafirma-harness@t1",
         "lib/diagrama/tests/test_ok.py"],
        env=env, capture_output=True, text=True, check=False, timeout=30,
    )
    assert r_teste.returncode == 0, r_teste.stdout + r_teste.stderr
    assert "suite VERDE: platafirma-harness@t1 (chave diagrama)" in r_teste.stdout


def _uv_de_sistema():
    """O uv que o `teste` procura (PLATAFIRMA_UV, /usr/local/bin, /usr/bin, PATH de sistema)."""
    import os
    import shutil
    return (os.environ.get("PLATAFIRMA_UV") or shutil.which("uv", path="/usr/local/bin:/usr/bin:/bin"))


def test_diagrama_cai_para_uv_quando_venv_nao_tem_pytest(tmp_path):
    """Venv de execução sem pytest (ex.: rag em produção) deve cair para `uv run --no-project --with pytest`."""
    import venv

    raiz = Path(__file__).resolve().parents[2]
    bancada = tmp_path / "bancada"
    wt = bancada / "wt" / "platafirma-harness" / "ti" / "t1"
    alvo_dir = wt / "lib" / "diagrama" / "tests"
    alvo_dir.mkdir(parents=True)
    (wt / ".git").mkdir()
    (alvo_dir / "test_ok.py").write_text("def test_ok(): assert True\n", encoding="utf-8")

    venv_rag = tmp_path / "release" / "current" / "venv" / "rag"
    venv.EnvBuilder(with_pip=False).create(venv_rag)
    (wt / "lib" / "diagrama" / "pyproject.toml").write_text(
        "[project]\nname = 'dummy'\nversion = '0.0.1'\n", encoding="utf-8"
    )

    uv_stub = tmp_path / "uv-stub"
    uv_log = tmp_path / "uv-args.txt"
    uv_stub.write_text(
        "#!/usr/bin/env bash\n"
        f"printf '%s\\n' \"$*\" > {str(uv_log)!r}\n"
        "echo '1 passed in 0.01s'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    uv_stub.chmod(0o755)

    inst = tmp_path / "instancia"
    inst.mkdir()
    terceiros = tmp_path / "terceiros.json"
    terceiros.write_text("{}", encoding="utf-8")
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "PLATAFIRMA_UV": str(uv_stub),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PLATAFIRMA_VENVS": str(VENVS),
        "PLATAFIRMA_TERCEIROS": str(terceiros),
        "PF_CADEIRA": "ti",
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PF_TESTE_SEM_MEMO": "1",
    }
    r_teste = subprocess.run(
        [str(raiz / "bin" / "teste"), "rodar", "platafirma-harness@t1",
         "lib/diagrama/tests/test_ok.py"],
        env=env, capture_output=True, text=True, check=False, timeout=30,
    )
    assert r_teste.returncode == 0, r_teste.stdout + r_teste.stderr
    assert "suite VERDE: platafirma-harness@t1 (chave diagrama)" in r_teste.stdout
    args_uv = uv_log.read_text(encoding="utf-8")
    assert "run --no-project" in args_uv and "--with pytest" in args_uv, args_uv


def test_espelho_vault_ontologia_resolve_no_registro():
    """DT 666: espelho-vault-ontologia declara lock e subarvore proprios do espelho, com promovida: false."""
    r = subprocess.run(
        ["python3", str(REGISTRO), "espelho-vault-ontologia"],
        env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(VENVS)},
        capture_output=True, text=True, check=False, timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == (
        f"{ESPELHO}\toutros_repos/posto/ferramentas/vault-ontologia/uv.lock\t"
        "outros_repos/posto/ferramentas/vault-ontologia/testes\tcodigo\tespelho-vault-ontologia\t-"
    )
    assert json.loads(VENVS.read_text(encoding="utf-8"))["espelho-vault-ontologia"]["promovida"] is False


def test_espelho_conhecimento_saiu_do_registro_de_venvs():
    """#4402: espelho-conhecimento e espelho-conversor sairam do registro quando o codigo voltou ao conhecimento."""
    venvs = json.loads(VENVS.read_text(encoding="utf-8"))
    assert "espelho-conhecimento" not in venvs
    assert "espelho-conversor" not in venvs


def test_espelho_sem_alvo_roda_portao_das_stacks_e_nao_chama_acervo_ingerir(tmp_path):
    """DT 534: platafirma-casa-espelho nao tem ingestao; rodar sem alvo e detectar apontam para as stacks da familia."""
    raiz = Path(__file__).resolve().parents[2]
    bancada = tmp_path / "bancada"
    wt = bancada / "wt" / ESPELHO / "ti" / "t1"
    (wt / ".git").mkdir(parents=True)

    vjson = tmp_path / "venvs.json"
    vjson.write_text(json.dumps({
        "repositorios": {ESPELHO: {"esteira": "documento"}},
        "espelho-demo": {
            "familia": ESPELHO,
            "esteira": "codigo",
            "promovida": False,
            "venv": "rag",
            "teste": "outros_repos/demo",
        },
    }), encoding="utf-8")

    teste_dir = wt / "outros_repos" / "demo" / "tests"
    teste_dir.mkdir(parents=True)
    (teste_dir / "test_ok.py").write_text("def test_ok(): assert True\n", encoding="utf-8")
    (teste_dir / "VERDES").write_text("tests/test_ok.py\n", encoding="utf-8")

    rel_venv = tmp_path / "release" / "current" / "venv" / "rag" / "bin"
    rel_venv.mkdir(parents=True)
    py_stub = rel_venv / "python"
    py_stub.write_text(
        "#!/usr/bin/env bash\n"
        "if [ \"$1\" = -c ]; then\n"
        "  [[ \"${2:-}\" == *pytest* ]] && exit 0\n"
        "  exit 1\n"
        "fi\n"
        "echo '1 passed in 0.01s'\n"
        "exit 0\n",
        encoding="utf-8",
    )
    py_stub.chmod(0o755)

    acervo_stub = tmp_path / "acervo-nao-chamar"
    acervo_stub.write_text("#!/usr/bin/env bash\nexit 99\n", encoding="utf-8")
    acervo_stub.chmod(0o755)

    inst = tmp_path / "instancia"
    inst.mkdir()
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PLATAFIRMA_VENVS": str(vjson),
        "PF_CADEIRA": "ti",
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PF_ACERVO_BIN": str(acervo_stub),
        "PF_TESTE_SEM_MEMO": "1",
    }

    r_det = subprocess.run(
        [str(raiz / "bin" / "teste"), "detectar", f"{ESPELHO}@t1"],
        env=env, capture_output=True, text=True, check=False, timeout=30,
    )
    assert r_det.returncode == 0, r_det.stdout + r_det.stderr
    assert f"teste rodar {ESPELHO} --portao" in r_det.stdout

    r_rodar = subprocess.run(
        [str(raiz / "bin" / "teste"), "rodar", f"{ESPELHO}@t1"],
        env=env, capture_output=True, text=True, check=False, timeout=30,
    )
    assert r_rodar.returncode == 0, r_rodar.stdout + r_rodar.stderr
    assert "suite VERDE:" in r_rodar.stdout
