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
