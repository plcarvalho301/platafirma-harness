"""Suites bash novas do card #3010: `deploy`, `seg`, `teste`/`lint` e o fechamento do harness.

Rodam pelo `teste rodar platafirma-harness`. Cada suite monta a propria fixture em /tmp
(release, instancia e tmpfs de env-file), com docker de stub, e nao toca producao nem bancada.
"""
import os
import pathlib
import subprocess
import tempfile

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent
SUITES = [
    "test_deploy.sh",
    "test_seg.sh",
    "test_teste.sh",
    "test_fechamento_3010_harness.sh",
]


@pytest.mark.parametrize("suite", SUITES)
def test_suite_bash(suite):
    caminho = RAIZ / suite
    assert caminho.exists(), f"suite {suite} ausente"
    env = dict(os.environ)
    env.setdefault("LC_ALL", "C.UTF-8")
    with tempfile.TemporaryDirectory() as tmp:
        env["PLATAFIRMA_BANCADA"] = os.path.join(tmp, "bancada-inexistente")
        p = subprocess.run(["bash", str(caminho)], capture_output=True, text=True, env=env)
    assert p.returncode == 0, f"{suite} saiu {p.returncode}\n--- stdout ---\n{p.stdout[-4000:]}\n--- stderr ---\n{p.stderr[-4000:]}"
