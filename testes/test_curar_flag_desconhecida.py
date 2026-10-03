"""#2856 linha 151: `curar` recusa argumento que não lê (exit 2) em vez de ignorá-lo em silêncio.

Antes, `--reclassificar --emitido_por X` (sublinhado) saía 0 e o plano não mudava nada. A recusa
vem do parse, antes de qualquer chamada ao motor: aqui o motor é uma porta que ninguém ouve, e o
teste prova que nada é chamado (a recusa sai 2, não 3 de «motor fora»).
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
def test_sublinhado_no_lugar_do_hifen_e_recusado_com_a_grafia_certa():
    r = _curar("--reclassificar", "--obra", OBRA, "--emitido_por", "ISO", "--id_canonico", "X", "--apply")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "--emitido_por (a grafia é --emitido-por)" in r.stderr
    assert "--id_canonico (a grafia é --id-canonico)" in r.stderr
    assert r.stdout == ""


@precisa_requests
def test_flag_que_nao_existe_e_recusada_sem_dica():
    r = _curar("--situacao", OBRA, "--nao-existe")
    assert r.returncode == 2 and "--nao-existe" in r.stderr and "a grafia é" not in r.stderr


@precisa_requests
def test_forma_com_igual_tambem_acusa():
    r = _curar("--reclassificar", "--obra", OBRA, "--emitido_por=ISO")
    assert r.returncode == 2 and "--emitido_por=ISO (a grafia é --emitido-por)" in r.stderr


@precisa_requests
def test_flag_certa_passa_do_parse_e_so_falha_no_motor_fora():
    """A recusa nova não pega o uso correto: chega ao motor (porta 9, ninguém ouve), exit != 2."""
    r = _curar("--reclassificar", "--obra", OBRA, "--emitido-por", "ISO")
    assert "argumento que o verbo não lê" not in r.stderr
