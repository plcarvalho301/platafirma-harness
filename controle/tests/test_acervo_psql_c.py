"""`acervo psql -c "<sql>"` (#2856 linha 21).

Antes, `-c` caia no ramo posicional e a query seguia como «-c SELECT ...»: erro de sintaxe, e so o
SQL por stdin funcionava. Agora `-c` vale como `--sql`. O verbo roda de verdade, com um `docker`
de mentira no PATH que devolve o SQL que recebeu por stdin.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

PSQL = Path(__file__).resolve().parents[2] / "bin" / "_acervo" / "psql"

if not shutil.which("bash"):
    pytest.skip("precisa de bash real", allow_module_level=True)

DOCKER = """#!/usr/bin/env bash
case "$1" in
  inspect) echo true ;;
  exec)
    if [ -n "$LOG_EXEC" ]; then echo "$*" > "$LOG_EXEC"; fi
    cat ;;
  *) exit 1 ;;
esac
"""


def _psql(tmp_path: Path, *args: str, stdin: str | None = None) -> subprocess.CompletedProcess:
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    docker = stub / "docker"
    docker.write_text(DOCKER)
    docker.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub}{os.pathsep}{os.environ.get('PATH', '')}"}
    return subprocess.run([str(PSQL), *args], input=stdin, env=env, capture_output=True, text=True,
                          timeout=30, check=False)


def test_c_vale_como_sql(tmp_path):
    r = _psql(tmp_path, "-c", "SELECT 1")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "SELECT 1"


def test_c_com_banco_e_sql_e_posicional_seguem_iguais(tmp_path):
    assert _psql(tmp_path, "--banco", "motor", "-c", "SELECT 2").stdout.strip() == "SELECT 2"
    assert _psql(tmp_path, "--sql", "SELECT 3").stdout.strip() == "SELECT 3"
    assert _psql(tmp_path, "SELECT 4").stdout.strip() == "SELECT 4"
    assert _psql(tmp_path, stdin="SELECT 5").stdout.strip() == "SELECT 5"


def test_c_sem_query_sai_2(tmp_path):
    r = _psql(tmp_path, "-c")
    assert r.returncode == 2
    assert "--sql exige uma query" in r.stderr


def test_opcoes_formato_psql_passam_ao_exec(tmp_path):
    """DT 138: -A, -t, --csv, -F passam ao psql sem virar syntax error."""
    log = tmp_path / "exec.log"
    stub = tmp_path / "bin"
    stub.mkdir(exist_ok=True)
    docker = stub / "docker"
    docker.write_text(DOCKER)
    docker.chmod(0o755)
    env = {**os.environ, "PATH": f"{stub}{os.pathsep}{os.environ.get('PATH', '')}", "LOG_EXEC": str(log)}
    r = subprocess.run([str(PSQL), "-A", "-t", "--csv", "-F", ",", "-c", "SELECT 1"], env=env,
                       capture_output=True, text=True, timeout=30, check=False)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "SELECT 1"
    registrado = log.read_text()
    for flag in ("-A", "-t", "--csv", "-F ,"):
        assert flag in registrado, f"flag {flag} ausente de {registrado}"
