"""Contrato dos atos de segredo e keycloak em `seg` (#3053).

Cobre:
- `seg segredo ler`:
  - Recusa exit 4 sob stdout TTY (pty)
  - Recusa exit 4 com processo pai ops-server/server.py
  - Target <nome> sem stack: 0 achados -> 1, >1 -> 2 (candidatos), 1 -> 0
  - Target <stack>/<nome>: inexistente -> 1, existente -> 0
- `seg segredo listar`:
  - Lista nome, stack, bytes, mtime, modo; nunca valor
  - Exit 1 se algum arquivo != 600 ou dir != 700 (nomeando qual)
- `seg segredo gravar`:
  - Stdin vazio -> exit 2
  - Alvo sem stack -> exit 2
  - Escrita atomica: dir 700, arquivo 600
- `seg segredo importar`:
  - .env parseado para dir 700 e arquivos 600
  - Imprime apenas os nomes
  - Nao apaga nem edita .env
- `seg segredo rotacionar`:
  - docker falso simula kcadm.sh
  - Arquivo 600 criado e valor ausente de stdout/stderr/log
- `seg keycloak entrar`:
  - Falha com variaveis ausentes (mostra nomes com <oculto>)
  - Sucesso com variaveis presentes
"""
import os
import pty
import stat
import subprocess
import sys
from pathlib import Path

import pytest

REPO_RAIZ = Path(__file__).resolve().parents[2]
BIN_SEG = REPO_RAIZ / "bin" / "seg"


@pytest.fixture
def fake_docker(tmp_path):
    d_dir = tmp_path / "bin"
    d_dir.mkdir(parents=True, exist_ok=True)
    docker_bin = d_dir / "docker"
    docker_bin.write_text(
        r"""#!/usr/bin/env bash
set -euo pipefail
if [ "$1" = "exec" ]; then
  shift
  # container name: platafirma-core-keycloak-1
  shift
  if [ "$1" = "sh" ] && [ "$2" = "-c" ]; then
    cmd="$3"
    if [[ "$cmd" == *"config credentials"* ]]; then
      exit 0
    fi
    if [[ "$cmd" == *"KC_BOOTSTRAP_ADMIN_USERNAME"* ]] && [[ "$cmd" == *"["* ]]; then
      if [ -n "${FAKE_FAIL_ENV:-}" ]; then
        exit 1
      fi
      exit 0
    fi
    if [[ "$cmd" == *"env | sed"* ]]; then
      echo "KC_BOOTSTRAP_ADMIN_USERNAME=<oculto>"
      echo "PATH=<oculto>"
      exit 0
    fi
  fi
  if [ "$1" = "/opt/keycloak/bin/kcadm.sh" ]; then
    shift
    if [ "$1" = "get" ] && [ "$2" = "clients" ]; then
      echo '[ { "id" : "test-client-id-uuid" } ]'
      exit 0
    fi
    if [ "$1" = "create" ] && [[ "$2" == clients/*/client-secret ]]; then
      exit 0
    fi
    if [ "$1" = "get" ] && [[ "$2" == clients/*/client-secret ]]; then
      echo '[ { "value" : "super-secret-rotated-value-xyz" } ]'
      exit 0
    fi
    if [ "$1" = "get" ] && [ "$2" = "realms/platafirma" ]; then
      echo '[ { "realm" : "platafirma" } ]'
      exit 0
    fi
  fi
fi
echo "docker-stub: comando desconhecido: $*" >&2
exit 1
""",
        encoding="utf-8",
    )
    docker_bin.chmod(0o755)
    return d_dir


def _run_seg(args, stdin=None, env_extra=None):
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [str(BIN_SEG)] + list(args),
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
    )


def test_gravar_stdin_vazio(tmp_path):
    secrets_dir = tmp_path / "secrets"
    res = _run_seg(["segredo", "gravar", "stack1/chave"], stdin="", env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})
    assert res.returncode == 2
    assert "stdin vazio" in res.stderr


def test_gravar_e_ler_sucesso(tmp_path):
    secrets_dir = tmp_path / "secrets"
    res_grav = _run_seg(
        ["segredo", "gravar", "stack1/chave"],
        stdin="segredo-123",
        env_extra={"SEG_SECRETS_DIR": str(secrets_dir)},
    )
    assert res_grav.returncode == 0
    assert "gravado: stack1/chave (11 bytes)" in res_grav.stdout

    target = secrets_dir / "stack1" / "chave"
    assert target.is_file()
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700

    # Ler por stack/nome
    res_ler = _run_seg(["segredo", "ler", "stack1/chave"], env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})
    assert res_ler.returncode == 0
    assert res_ler.stdout == "segredo-123"

    # Ler por nome sem stack
    res_ler_sem_stack = _run_seg(["segredo", "ler", "chave"], env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})
    assert res_ler_sem_stack.returncode == 0
    assert res_ler_sem_stack.stdout == "segredo-123"


def test_ler_recusa_sob_pty(tmp_path):
    secrets_dir = tmp_path / "secrets"
    _run_seg(["segredo", "gravar", "stack1/chave"], stdin="segredo", env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})

    master, slave = pty.openpty()
    env = os.environ.copy()
    env["SEG_SECRETS_DIR"] = str(secrets_dir)
    proc = subprocess.run(
        [str(BIN_SEG), "segredo", "ler", "stack1/chave"],
        stdout=slave,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    os.close(slave)
    os.close(master)
    assert proc.returncode == 4
    assert "segredo não atravessa a porta" in proc.stderr


def test_ler_recusa_pai_ops_server(tmp_path):
    secrets_dir = tmp_path / "secrets"
    _run_seg(["segredo", "gravar", "stack1/chave"], stdin="segredo", env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})

    fake_server_dir = tmp_path / "ops-server"
    fake_server_dir.mkdir(parents=True, exist_ok=True)
    fake_server = fake_server_dir / "server.py"
    fake_server.write_text(
        f"""#!/usr/bin/env python3
import subprocess, sys
res = subprocess.run(["{BIN_SEG}", "segredo", "ler", "stack1/chave"], capture_output=True, text=True)
sys.stdout.write(res.stdout)
sys.stderr.write(res.stderr)
sys.exit(res.returncode)
""",
        encoding="utf-8",
    )
    fake_server.chmod(0o755)

    env = os.environ.copy()
    env["SEG_SECRETS_DIR"] = str(secrets_dir)
    res = subprocess.run([sys.executable, str(fake_server)], capture_output=True, text=True, env=env)
    assert res.returncode == 4
    assert "segredo não atravessa a porta" in res.stderr


def test_ler_nome_sem_stack_multiplos_e_zero(tmp_path):
    secrets_dir = tmp_path / "secrets"
    _run_seg(["segredo", "gravar", "stack1/chave"], stdin="v1", env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})
    _run_seg(["segredo", "gravar", "stack2/chave"], stdin="v2", env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})

    # >1 achados -> exit 2 listando candidatos
    res_mult = _run_seg(["segredo", "ler", "chave"], env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})
    assert res_mult.returncode == 2
    assert "stack1/chave" in res_mult.stderr
    assert "stack2/chave" in res_mult.stderr

    # 0 achados -> exit 1
    res_zero = _run_seg(["segredo", "ler", "naoexiste"], env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})
    assert res_zero.returncode == 1


def test_listar_sucesso_e_modo_invalido(tmp_path):
    secrets_dir = tmp_path / "secrets"
    _run_seg(["segredo", "gravar", "stk/s1"], stdin="segredo-conteudo", env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})

    res_ok = _run_seg(["segredo", "listar"], env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})
    assert res_ok.returncode == 0
    assert "s1" in res_ok.stdout
    assert "stk" in res_ok.stdout
    assert "600" in res_ok.stdout
    # Nunca o valor
    assert "segredo-conteudo" not in res_ok.stdout

    # listar com arquivo 644 -> exit 1
    target = secrets_dir / "stk" / "s1"
    target.chmod(0o644)
    res_inval = _run_seg(["segredo", "listar"], env_extra={"SEG_SECRETS_DIR": str(secrets_dir)})
    assert res_inval.returncode == 1
    assert "s1" in res_inval.stderr


def test_importar_env(tmp_path):
    secrets_dir = tmp_path / "secrets"
    env_file = tmp_path / "sample.env"
    env_content = """# Arquivo .env de teste
POSTGRES_USER=myuser
POSTGRES_PASS="p@ssword"
export DB_PORT=5432
"""
    env_file.write_text(env_content, encoding="utf-8")

    res = _run_seg(
        ["segredo", "importar", "core", "--de", str(env_file)],
        env_extra={"SEG_SECRETS_DIR": str(secrets_dir)},
    )
    assert res.returncode == 0
    output_names = res.stdout.strip().splitlines()
    assert set(output_names) == {"POSTGRES_USER", "POSTGRES_PASS", "DB_PORT"}

    # .env nao foi apagado nem editado
    assert env_file.read_text(encoding="utf-8") == env_content

    # Checar arquivos gravados
    user_f = secrets_dir / "core" / "POSTGRES_USER"
    assert user_f.read_text() == "myuser"
    assert stat.S_IMODE(user_f.stat().st_mode) == 0o600

    pass_f = secrets_dir / "core" / "POSTGRES_PASS"
    assert pass_f.read_text() == "p@ssword"


def test_rotacionar_com_docker_falso(tmp_path, fake_docker):
    secrets_dir = tmp_path / "secrets"
    env = {
        "SEG_SECRETS_DIR": str(secrets_dir),
        "PATH": f"{fake_docker}:{os.environ['PATH']}",
    }
    res = _run_seg(
        ["segredo", "rotacionar", "core/kc_secret", "--keycloak-client", "platafirma-web"],
        env_extra=env,
    )
    assert res.returncode == 0
    assert "rotacionado: core/kc_secret <- client platafirma-web (test-client-id-uuid)" in res.stdout

    # Arquivo 600 criado
    secret_file = secrets_dir / "core" / "kc_secret"
    assert secret_file.is_file()
    assert stat.S_IMODE(secret_file.stat().st_mode) == 0o600
    assert secret_file.read_text() == "super-secret-rotated-value-xyz"

    # Valor NUNCA em stdout nem stderr
    assert "super-secret-rotated-value-xyz" not in res.stdout
    assert "super-secret-rotated-value-xyz" not in res.stderr


def test_keycloak_entrar(tmp_path, fake_docker):
    env_ok = {"PATH": f"{fake_docker}:{os.environ['PATH']}"}
    res_ok = _run_seg(["keycloak", "entrar"], env_extra=env_ok)
    assert res_ok.returncode == 0
    assert "sessao kcadm: ok" in res_ok.stdout

    env_fail = {
        "PATH": f"{fake_docker}:{os.environ['PATH']}",
        "FAKE_FAIL_ENV": "1",
    }
    res_fail = _run_seg(["keycloak", "entrar"], env_extra=env_fail)
    assert res_fail.returncode == 1
    assert "KC_BOOTSTRAP_ADMIN_USERNAME=<oculto>" in res_fail.stderr
