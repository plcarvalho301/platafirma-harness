"""Suites bash do verbo `release` (spec_release rev 2, arq:0110 Q9), uma por lote.

Rodam pelo `teste rodar platafirma-harness` e, por ele, no pre-push: verbo tocado sem
teste tocado reprova. Cada suite monta a propria fixture em /tmp e nao toca o servido.
"""
import os
import pathlib
import subprocess

import pytest

RAIZ = pathlib.Path(__file__).resolve().parent
SUITES = [
    "test_release.sh",
    "test_release_lote2.sh",
    "test_release_lote3.sh",
]


@pytest.mark.parametrize("suite", SUITES)
def test_suite_bash_do_release(suite):
    caminho = RAIZ / suite
    assert caminho.exists(), f"suite {suite} ausente"
    env = dict(os.environ)
    env.setdefault("LC_ALL", "C.UTF-8")
    p = subprocess.run(["bash", str(caminho)], capture_output=True, text=True, env=env)
    assert p.returncode == 0, f"{suite} saiu {p.returncode}\n--- stdout ---\n{p.stdout[-4000:]}\n--- stderr ---\n{p.stderr[-4000:]}"
