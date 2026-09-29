"""Contrato de `repo lock` (mesa ti#3; cartas 20260928T104616-engenharia e 20260928T232833-dados).

Git real contra bare local; o uv e um script de fixture (PLATAFIRMA_UV) que registra a
chamada e o ambiente e escreve o lock pedido; o python e o de sistema que roda a suite
(PLATAFIRMA_PYTHON). Prova: uso sem projeto (2); caminho que escapa (4); projeto sem
pyproject (1); o lock sai do uv com --project do projeto, --python de sistema,
only-system e sem download de python; a diferenca de pacotes (+ - ~) lida dos dois locks;
nada commitado; lock igual diz "ja em dia"; sem solucao sai 1 com o lock intocado; falha de
indice sai 3; --conferir so mede (0 em dia, 1 defasado) e nao escreve.
Nao prova: o uv de verdade nem o indice de pacotes.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
PY = os.path.realpath(sys.executable)

UV_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
printf '%s\\n' "$*" >> "$d/chamadas"
printf '%s %s\\n' "${UV_PYTHON_PREFERENCE:-}" "${UV_PYTHON_DOWNLOADS:-}" > "$d/env"
proj=""; check=0
while [ $# -gt 0 ]; do
  case "$1" in
    --project) proj="$2"; shift 2 ;;
    --check) check=1; shift ;;
    *) shift ;;
  esac
done
if [ "$check" = 1 ]; then
  [ -f "$d/check_err" ] && cat "$d/check_err" >&2
  exit "$(cat "$d/check_rc" 2>/dev/null || echo 0)"
fi
if [ -f "$d/falha" ]; then cat "$d/falha" >&2; exit 1; fi
cp "$d/novo.lock" "$proj/uv.lock"
"""

LOCK_ANTES = """version = 1
[[package]]
name = "a"
version = "1.0"
[[package]]
name = "b"
version = "1.0"
"""

LOCK_DEPOIS = """version = 1
[[package]]
name = "a"
version = "1.1"
[[package]]
name = "c"
version = "2.0"
"""


def _git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **IDENT}).stdout.strip()


def _montar(tmp_path):
    origem = tmp_path / "origem.git"
    semente = tmp_path / "semente"
    bancada = tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    proj = semente / "venvs" / "x"
    proj.mkdir(parents=True)
    (proj / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0"\n')
    (proj / "uv.lock").write_text(LOCK_ANTES)
    _git("add", "venvs", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir()
    _git("clone", str(origem), str(bancada / "demo"))
    ferr = tmp_path / "uvfix"
    ferr.mkdir()
    uv = ferr / "uv"
    uv.write_text(UV_FIXTURE)
    uv.chmod(0o755)
    (ferr / "novo.lock").write_text(LOCK_DEPOIS)
    return bancada, ferr


def _repo(tmp_path, bancada, *args):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-ti",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": "/bin/true",
        "PF_GH_BIN": "/bin/false",
        "PLATAFIRMA_UV": str(tmp_path / "uvfix" / "uv"),
        "PLATAFIRMA_PYTHON": PY,
        **IDENT,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _aberta(tmp_path):
    bancada, ferr = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "abrir", "demo", "--slug", "l")
    assert r.returncode == 0, r.stderr
    return bancada, ferr, bancada / "wt" / "demo" / "ti" / "l"


def test_sem_projeto_e_uso(tmp_path):
    bancada, _, _ = _aberta(tmp_path)
    r = _repo(tmp_path, bancada, "lock", "demo")
    assert r.returncode == 2, r.stdout + r.stderr


def test_projeto_que_escapa_recusa_4(tmp_path):
    bancada, ferr, _ = _aberta(tmp_path)
    r = _repo(tmp_path, bancada, "lock", "demo", "../fora")
    assert r.returncode == 4, r.stdout + r.stderr
    assert not (ferr / "chamadas").exists()


def test_projeto_sem_pyproject_sai_1(tmp_path):
    bancada, ferr, _ = _aberta(tmp_path)
    r = _repo(tmp_path, bancada, "lock", "demo", "venvs/nada")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "sem pyproject.toml" in r.stderr
    assert not (ferr / "chamadas").exists()


def test_gera_lock_com_uv_e_python_da_release_e_relata_diferenca(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    r = _repo(tmp_path, bancada, "lock", "demo", "venvs/x")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "lock: venvs/x/uv.lock atualizado" in r.stdout
    assert "  ~ a 1.0 -> 1.1" in r.stdout
    assert "  - b 1.0" in r.stdout
    assert "  + c 2.0" in r.stdout
    assert "próximo: repo commitar demo" in r.stdout
    assert (wt / "venvs" / "x" / "uv.lock").read_text() == LOCK_DEPOIS
    chamada = (ferr / "chamadas").read_text()
    assert f"--python {PY}" in chamada
    assert f"--project {wt}/venvs/x" in chamada
    assert (ferr / "env").read_text().strip() == "only-system never"
    # nao commita: o lock fica modificado na arvore
    assert "venvs/x/uv.lock" in _git("status", "--porcelain", cwd=wt)


def test_lock_igual_diz_ja_em_dia(tmp_path):
    bancada, ferr, _ = _aberta(tmp_path)
    (ferr / "novo.lock").write_text(LOCK_ANTES)
    r = _repo(tmp_path, bancada, "lock", "demo", "venvs/x")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "já em dia" in r.stdout
    assert "próximo:" not in r.stdout


def test_sem_solucao_sai_1_e_lock_intocado(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    (ferr / "falha").write_text("  x No solution found when resolving dependencies:\n")
    r = _repo(tmp_path, bancada, "lock", "demo", "venvs/x")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "sem solução" in r.stderr
    assert (wt / "venvs" / "x" / "uv.lock").read_text() == LOCK_ANTES


def test_falha_de_indice_sai_3(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    (ferr / "falha").write_text("error: Failed to fetch: `https://pypi.org/simple/a/`\n")
    r = _repo(tmp_path, bancada, "lock", "demo", "venvs/x")
    assert r.returncode == 3, r.stdout + r.stderr
    assert (wt / "venvs" / "x" / "uv.lock").read_text() == LOCK_ANTES


def test_conferir_em_dia_sai_0_sem_escrever(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    r = _repo(tmp_path, bancada, "lock", "demo", "venvs/x", "--conferir")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "em dia" in r.stdout
    assert "--check" in (ferr / "chamadas").read_text()
    assert (wt / "venvs" / "x" / "uv.lock").read_text() == LOCK_ANTES


def test_conferir_defasado_sai_1_sem_escrever(tmp_path):
    bancada, ferr, wt = _aberta(tmp_path)
    (ferr / "check_rc").write_text("2\n")
    (ferr / "check_err").write_text("error: The lockfile at `uv.lock` needs to be updated, but `--locked` was provided.\n")
    r = _repo(tmp_path, bancada, "lock", "demo", "venvs/x", "--conferir")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "defasado" in r.stdout
    assert "vizinho: repo lock demo venvs/x" in r.stdout
    assert (wt / "venvs" / "x" / "uv.lock").read_text() == LOCK_ANTES
