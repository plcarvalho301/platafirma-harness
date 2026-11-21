# componente: componente:verbo-acervo
"""Regressão #4428: acervo psql lê registro/bancos.json pela role analise_leitura somente-leitura."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ACERVO_PSQL = RAIZ / "bin" / "_acervo" / "psql"
BANCOS_JSON = RAIZ / "registro" / "bancos.json"

DOCKER_STUB = """#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  inspect)
    echo "true"
    ;;
  exec)
    if [ -n "${LOG_EXEC:-}" ]; then
      printf '%s\n' "$*" > "$LOG_EXEC"
    fi
    cat
    ;;
  *)
    exit 1
    ;;
esac
"""


def _rodar_psql(tmp_path: Path, *args: str, env_extra: dict[str, str] | None = None) -> tuple[subprocess.CompletedProcess[str], str]:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir(exist_ok=True)
    docker = fake_bin / "docker"
    docker.write_text(DOCKER_STUB, encoding="utf-8")
    docker.chmod(0o755)
    log = tmp_path / "docker_exec.log"
    if log.exists():
        log.unlink()
    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "LOG_EXEC": str(log),
    }
    env.pop("PF_CADEIRA", None)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        ["bash", str(ACERVO_PSQL), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
        check=False,
    )
    registrado = log.read_text(encoding="utf-8").strip() if log.exists() else ""
    return proc, registrado


def test_aceita_todos_os_bancos_do_registro_com_analise_leitura_read_only(tmp_path: Path) -> None:
    bancos = json.loads(BANCOS_JSON.read_text(encoding="utf-8"))
    esperados = {k: v for k, v in bancos.items() if not k.startswith("_") and isinstance(v, dict)}
    assert "casa" in esperados

    for slug, info in esperados.items():
        proc, registrado = _rodar_psql(
            tmp_path,
            "--banco",
            slug,
            "--sql",
            "SELECT 1;",
            env_extra={"PF_CADEIRA": "seguranca"},
        )
        assert proc.returncode == 0, f"{slug}: {proc.stderr}"
        assert proc.stdout.strip() == "SELECT 1;"
        assert "PGOPTIONS=-c default_transaction_read_only=on" in registrado
        assert f"{info['conteiner']} psql -U analise_leitura -d {info['base']}" in registrado


def test_banco_desconhecido_sai_4(tmp_path: Path) -> None:
    proc, _ = _rodar_psql(tmp_path, "--banco", "nao_existe", "--sql", "SELECT 1;")
    assert proc.returncode == 4
    assert "fora da allowlist" in proc.stderr


def test_keycloak_restrito_a_seguranca_e_ti(tmp_path: Path) -> None:
    proc_dados, _ = _rodar_psql(
        tmp_path,
        "--banco",
        "keycloak",
        "--sql",
        "SELECT 1;",
        env_extra={"PF_CADEIRA": "dados"},
    )
    assert proc_dados.returncode == 4
    assert "restrito" in proc_dados.stderr

    proc_ti, _ = _rodar_psql(
        tmp_path,
        "--banco",
        "keycloak",
        "--sql",
        "SELECT 1;",
        env_extra={"PF_CADEIRA": "ti"},
    )
    assert proc_ti.returncode == 0, proc_ti.stderr
