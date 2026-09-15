"""Suite bash da frente uv/python/porta do `release` e do `infra` (card #3010).

Roda pelo `teste rodar platafirma-harness`. A suite monta release, instancia e HOME em /tmp,
com uv, python, systemctl e systemd-run falsos num PATH temporario; nao toca o servido.
"""
import os
import pathlib
import subprocess

RAIZ = pathlib.Path(__file__).resolve().parent


def test_suite_bash_uv_python_porta():
    caminho = RAIZ / "test_release_uv_porta.sh"
    assert caminho.exists(), "suite test_release_uv_porta.sh ausente"
    env = dict(os.environ)
    env.setdefault("LC_ALL", "C.UTF-8")
    p = subprocess.run(["bash", str(caminho)], capture_output=True, text=True, env=env)
    assert p.returncode == 0, (
        f"test_release_uv_porta.sh saiu {p.returncode}\n--- stdout ---\n{p.stdout[-4000:]}"
        f"\n--- stderr ---\n{p.stderr[-4000:]}"
    )
