"""O promover so confere no ar, com o conferir da release, a familia que declara
`conferir_no_ar: true` no registro de venvs (card #3535).

Prova: a funcao `conferir_no_ar_declarado` de bin/release liga so com o booleano true, e o
registro real liga so o rastreador. Nao prova: a conferencia no ar em si (gancho
PF_RELEASE_CONFERENCIA_AR em test_release_gate_suite_verdes.py).
"""
import json
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
REGISTRO = RAIZ / "registro" / "venvs.json"
RELEASE = RAIZ / "bin" / "release"


def _declarado(tmp_path, repos, repo):
    venvs = tmp_path / "venvs.json"
    venvs.write_text(json.dumps({"repositorios": repos}), encoding="utf-8")
    script = f"source <(sed -n '/^conferir_no_ar_declarado()/,/^}}/p' '{RELEASE}'); conferir_no_ar_declarado '{repo}'"
    return subprocess.run(["bash", "-c", script], env={"PATH": "/usr/bin:/bin", "PLATAFIRMA_VENVS": str(venvs)},
                          capture_output=True, text=True).returncode


def test_conferir_no_ar_so_com_true_declarado(tmp_path):
    repos = {"platafirma-rastreador": {"esteira": "codigo", "conferir_no_ar": True},
             "platafirma-core": {"esteira": "codigo"},
             "platafirma-motor": {"esteira": "codigo", "conferir_no_ar": "sim"}}
    assert _declarado(tmp_path, repos, "platafirma-rastreador") == 0
    assert _declarado(tmp_path, repos, "platafirma-core") == 1
    assert _declarado(tmp_path, repos, "platafirma-motor") == 1, "so o booleano true liga"
    assert _declarado(tmp_path, repos, "nao-existe") == 1


def test_registro_real_liga_a_conferencia_so_no_rastreador():
    repos = json.loads(REGISTRO.read_text(encoding="utf-8"))["repositorios"]
    assert sorted(n for n, d in repos.items() if (d or {}).get("conferir_no_ar") is True) == ["platafirma-rastreador"]
