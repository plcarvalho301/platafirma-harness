"""#3159 (ont:0071): `curar --reclassificar --vinculacao` é flag que o verbo lê.

O motor é uma porta que ninguém ouve: o teste prova só o parse. A recusa de flag desconhecida sai 2
antes de qualquer chamada; flag lida passa do parse e só falha no motor fora (exit != 2).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CURAR = RAIZ / "bin" / "curar"
OBRA = "0000a1fe-0000-4000-8000-000000000000"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
precisa_requests = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


def _curar(*argv):
    env = {**os.environ, "MOTOR_ACERVO_URL": "http://127.0.0.1:9", "RAG_API_TOKEN": "t", "PF_CADEIRA": "dados"}
    return subprocess.run([PY, str(CURAR), *argv], capture_output=True, text=True, env=env, timeout=60,
                          check=False)


@precisa_requests
@pytest.mark.parametrize("valor", ["hard-law", "soft-law", "convencao", "nenhuma", "null"])
def test_vinculacao_passa_do_parse(valor):
    r = _curar("--reclassificar", "--obra", OBRA, "--vinculacao", valor)
    assert r.returncode != 2, r.stdout + r.stderr
    assert "argumento que o verbo não lê" not in r.stderr


@precisa_requests
def test_forca_deixou_de_ser_flag():
    r = _curar("--reclassificar", "--obra", OBRA, "--forca", "requisito")
    assert r.returncode == 2 and "--forca" in r.stderr
