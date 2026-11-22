# componente: componente:verbo-seg
"""seg segredo rotacionar --postgres (débito 1343): cunha ou troca a senha do papel, sem imprimir.

O docker é falso: um script no PATH que responde ao `inspect` e, no `exec`, grava o stdin
recebido (o ALTER ROLE) num arquivo, para o teste conferir que a senha do banco e a de cada
cópia são a mesma e que nenhuma saiu na tela. O `release migrar senha` deprecado repassa ao
mesmo corpo e mantém a trava do --rotacionar.
"""
from __future__ import annotations

import os
import re
import stat
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SEG = RAIZ / "bin" / "seg"
MIGRAR = RAIZ / "bin" / "_release" / "migrar"

DOCKER_FALSO = """#!/usr/bin/env bash
case "$1" in
  inspect) echo true ;;
  exec)
    cat > "$CAPTURA"
    [ -n "${FALHAR:-}" ] && { echo "ERROR:  role \\\\"x\\\\" does not exist" >&2; echo "LINE 1: $(cat "$CAPTURA")" >&2; exit 3; }
    exit 0 ;;
esac
"""


def _env(tmp_path: Path, *, falhar: bool = False, sujeito: bool = True) -> dict:
    bindir = tmp_path / "bin"
    bindir.mkdir(exist_ok=True)
    docker = bindir / "docker"
    docker.write_text(DOCKER_FALSO)
    docker.chmod(0o755)
    env = {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "HOME": str(tmp_path),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
        "SEG_SECRETS_DIR": str(tmp_path / "inst" / "segredos"),
        "SEG_LOG_DIR": str(tmp_path / "log"),
        "CAPTURA": str(tmp_path / "captura.sql"),
    }
    if sujeito:
        env["PF_SUJEITO"] = "teste"
    if falhar:
        env["FALHAR"] = "1"
    return env


def _seg(tmp_path: Path, *args: str, **kw):
    return subprocess.run(["bash", str(SEG), "segredo", "rotacionar", *args],
                          capture_output=True, text=True, env=_env(tmp_path, **kw))


def _senha(tmp_path: Path, papel: str) -> str:
    sql = (tmp_path / "captura.sql").read_text()
    m = re.fullmatch(rf"ALTER ROLE {papel} LOGIN PASSWORD '([0-9a-f]{{48}})';\n", sql)
    assert m, sql
    return m.group(1)


def test_cunha_mae_e_copia_com_a_mesma_senha_sem_imprimir(tmp_path):
    p = _seg(tmp_path, "casa-db/CASA_LEITOR_MOTOR_PASSWORD", "rag/CASA_LEITOR_MOTOR_PASSWORD",
             "--postgres", "casa", "casa_leitor_motor")
    assert p.returncode == 0, p.stderr
    senha = _senha(tmp_path, "casa_leitor_motor")
    seg = tmp_path / "inst" / "segredos"
    for alvo in (seg / "casa-db" / "CASA_LEITOR_MOTOR_PASSWORD", seg / "rag" / "CASA_LEITOR_MOTOR_PASSWORD"):
        assert alvo.read_text() == senha
        assert stat.S_IMODE(alvo.stat().st_mode) == 0o600
    assert senha not in p.stdout and senha not in p.stderr
    assert "nao se imprime" in p.stdout


def test_segunda_chamada_troca_todas_as_copias(tmp_path):
    alvos = ("casa-db/X", "rag/X")
    assert _seg(tmp_path, *alvos, "--postgres", "casa", "leitor").returncode == 0
    antiga = _senha(tmp_path, "leitor")
    p = _seg(tmp_path, *alvos, "--postgres", "casa", "leitor")
    assert p.returncode == 0, p.stderr
    nova = _senha(tmp_path, "leitor")
    seg = tmp_path / "inst" / "segredos"
    assert nova != antiga
    assert (seg / "casa-db" / "X").read_text() == nova == (seg / "rag" / "X").read_text()


def test_banco_recusa_nao_grava_e_nao_vaza(tmp_path):
    p = _seg(tmp_path, "casa-db/Y", "--postgres", "casa", "leitor", falhar=True)
    assert p.returncode == 1
    senha = _senha(tmp_path, "leitor")
    assert senha not in p.stderr and senha not in p.stdout
    assert list((tmp_path / "inst" / "segredos" / "casa-db").iterdir()) == []


def test_entradas_invalidas(tmp_path):
    assert _seg(tmp_path, "s/n", "--postgres", "fora", "r").returncode == 4
    assert _seg(tmp_path, "s/n", "--postgres", "casa", "Role;drop").returncode == 2
    assert _seg(tmp_path, "../etc/passwd", "--postgres", "casa", "r").returncode == 2
    assert _seg(tmp_path, "s/n/x", "--postgres", "casa", "r").returncode == 2
    assert _seg(tmp_path, "--postgres", "casa", "r").returncode == 2
    assert _seg(tmp_path, "s/n", "--postgres", "casa").returncode == 2
    assert _seg(tmp_path, "s/n", "--postgres", "casa", "r", "--keycloak-client", "c").returncode == 2
    assert _seg(tmp_path, "s/n", "--postgres", "casa", "r", sujeito=False).returncode == 3


def test_keycloak_segue_exigindo_um_alvo(tmp_path):
    p = _seg(tmp_path, "core/a", "core/b", "--keycloak-client", "c")
    assert p.returncode == 2
    assert "--keycloak-client" in p.stderr


def test_migrar_senha_repassa_ao_seg_com_aviso(tmp_path):
    env = _env(tmp_path)
    p = subprocess.run(["bash", str(MIGRAR), "senha", "casa", "leitor", "casa-db/Z"],
                       capture_output=True, text=True, env=env)
    assert p.returncode == 0, p.stderr
    assert "deprecado" in p.stderr and "seg segredo rotacionar" in p.stderr
    assert (tmp_path / "inst" / "segredos" / "casa-db" / "Z").read_text() == _senha(tmp_path, "leitor")
