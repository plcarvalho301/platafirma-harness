"""release migrar senha (card #3375): gera, troca no banco e guarda, sem imprimir o valor.

O docker e falso: um script no PATH que responde ao `inspect` e, no `exec`, grava o
stdin recebido (o ALTER ROLE) num arquivo, para o teste conferir que a senha do banco e
a do segredo sao a mesma e que nenhuma das duas saiu na tela.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

MIGRAR = Path(__file__).resolve().parents[2] / "bin" / "_release" / "migrar"

DOCKER_FALSO = """#!/usr/bin/env bash
case "$1" in
  inspect) echo true ;;
  exec)
    cat > "$CAPTURA"
    [ -n "${FALHAR:-}" ] && { echo "ERROR:  role \\"x\\" does not exist" >&2; echo "LINE 1: $(cat "$CAPTURA")" >&2; exit 3; }
    exit 0 ;;
esac
"""


def _rodar(tmp_path: Path, *args: str, falhar: bool = False, sujeito: bool = True):
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    docker = bindir / "docker"
    docker.write_text(DOCKER_FALSO)
    docker.chmod(0o755)
    env = {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
        "CAPTURA": str(tmp_path / "captura.sql"),
    }
    if sujeito:
        env["PF_SUJEITO"] = "teste"
    if falhar:
        env["FALHAR"] = "1"
    return subprocess.run(["bash", str(MIGRAR), "senha", *args], capture_output=True, text=True, env=env)


def _senha_do_alter(tmp_path: Path) -> str:
    sql = (tmp_path / "captura.sql").read_text()
    m = re.fullmatch(r"ALTER ROLE sessao_leitor LOGIN PASSWORD '([0-9a-f]{48})';\n", sql)
    assert m, sql
    return m.group(1)


def test_gera_troca_e_guarda_sem_imprimir(tmp_path):
    p = _rodar(tmp_path, "sessao", "sessao_leitor", "harness-sessao/SESSAO_LEITOR_PASSWORD")
    assert p.returncode == 0, p.stderr
    senha = _senha_do_alter(tmp_path)
    destino = tmp_path / "inst" / "segredos" / "harness-sessao" / "SESSAO_LEITOR_PASSWORD"
    assert destino.read_text() == senha
    assert stat.S_IMODE(destino.stat().st_mode) == 0o600
    assert senha not in p.stdout and senha not in p.stderr
    assert "nao se imprime" in p.stdout


def test_segredo_existente_exige_rotacionar(tmp_path):
    assert _rodar(tmp_path, "sessao", "sessao_leitor", "harness-sessao/X").returncode == 0
    p = _rodar(tmp_path, "sessao", "sessao_leitor", "harness-sessao/X")
    assert p.returncode == 4
    assert "--rotacionar" in p.stderr
    p = _rodar(tmp_path, "sessao", "sessao_leitor", "harness-sessao/X", "--rotacionar")
    assert p.returncode == 0, p.stderr


def test_banco_recusa_nao_grava_e_nao_vaza(tmp_path):
    p = _rodar(tmp_path, "sessao", "sessao_leitor", "harness-sessao/Y", falhar=True)
    assert p.returncode == 1
    senha = _senha_do_alter(tmp_path)
    assert senha not in p.stderr and senha not in p.stdout
    d = tmp_path / "inst" / "segredos" / "harness-sessao"
    assert list(d.iterdir()) == []


def test_entradas_invalidas(tmp_path):
    assert _rodar(tmp_path, "fora", "r", "s/n").returncode == 4
    assert _rodar(tmp_path, "sessao", "Role;drop", "s/n").returncode == 2
    assert _rodar(tmp_path, "sessao", "r", "../etc/passwd").returncode == 2
    assert _rodar(tmp_path, "sessao", "r", "s/n/x").returncode == 2
    assert _rodar(tmp_path, "sessao", "r", "s/n", sujeito=False).returncode == 3
