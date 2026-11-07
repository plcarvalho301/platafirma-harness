"""DT 166: `curar --reextrair <id> <id> ... --bancada <pasta>` aceita a lista separada por espaco.

Antes, so o primeiro id ia ao `--reextrair`; os outros caiam em «argumento que o verbo nao le» (exit 2) e
nada rodava. O motor aqui e uma porta que ninguem ouve: cada obra sai `erro` (rede), o que basta para
provar que as duas entradas chegaram ao laco da bancada.
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
A = "0000a1fe-0000-4000-8000-000000000000"
B = "0000b2ff-0000-4000-8000-000000000000"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


def _curar(*argv):
    env = {**os.environ, "MOTOR_ACERVO_URL": "http://127.0.0.1:9", "RAG_API_TOKEN": "t", "PF_CADEIRA": "dados"}
    return subprocess.run([PY, str(CURAR), *argv], capture_output=True, text=True, env=env, timeout=90,
                          check=False)


def test_lista_separada_por_espaco_chega_as_duas_obras(tmp_path):
    r = _curar("--reextrair", A, B, "--bancada", str(tmp_path))
    assert "argumento que o verbo não lê" not in r.stderr, r.stderr
    saida = r.stdout + r.stderr
    assert "total  2 obra(s)" in saida, saida


def test_lista_com_virgula_continua_igual(tmp_path):
    r = _curar("--reextrair", f"{A},{B}", "--bancada", str(tmp_path))
    assert "total  2 obra(s)" in r.stdout + r.stderr


def test_lista_depois_da_pasta_tambem_vale(tmp_path):
    r = _curar("--reextrair", A, "--bancada", str(tmp_path), B)
    assert "argumento que o verbo não lê" not in r.stderr, r.stderr
    assert "total  2 obra(s)" in r.stdout + r.stderr


def test_flag_desconhecida_segue_recusada_mesmo_com_lista(tmp_path):
    r = _curar("--reextrair", A, B, "--bancada", str(tmp_path), "--nao-existe")
    assert r.returncode == 2 and "--nao-existe" in r.stderr


def test_palavra_solta_fora_da_bancada_segue_recusada():
    # a lista por espaco so existe na bancada: `--reextrair <obra> <palavra>` sem --bancada nao muda
    r = _curar("--reextrair", A, B)
    assert r.returncode == 2 and B in r.stderr
