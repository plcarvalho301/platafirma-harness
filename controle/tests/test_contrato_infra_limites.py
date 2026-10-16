"""`infra limites`: o teto de processos e threads da conta, lido pela porta (16/10/2026, #3496).

Nasceu para medir o `fork: retry: Resource temporarily unavailable` que o portão da ui
provocou (celular.mjs, 15/10): nenhum verbo lia o limite, e a porta recusa /proc e /sys.
É só leitura; o teste roda o ato no host do teste e confere a forma da saída, não os valores.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("ps") is None,
                                reason="sem bash ou ps no PATH")


def _infra(*args):
    return subprocess.run([BASH, str(INFRA), *args], capture_output=True, text=True,
                          env={**os.environ}, timeout=30)


def test_limites_imprime_teto_e_uso():
    r = _infra("limites")
    assert r.returncode == 0, r.stderr
    assert "ulimit -u (processos+threads da conta):" in r.stdout
    assert "threads vivas da conta agora:" in r.stdout
    vivas = [l for l in r.stdout.splitlines() if l.startswith("threads vivas da conta agora:")]
    assert int(vivas[0].rsplit(":", 1)[1]) >= 1


def test_limites_consta_do_uso_e_dos_atos():
    r = _infra("--ajuda")
    assert r.returncode == 2
    assert "infra limites" in r.stderr
    r = _infra("ato-que-nao-existe")
    assert r.returncode == 2
    assert "limites" in r.stderr.splitlines()[1]
