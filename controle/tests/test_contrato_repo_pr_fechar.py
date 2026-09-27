"""Contrato de `repo pr-fechar` (card #3072): descartar PR sem merge pela porta.

Git real contra bare local; o forge do PR e um `gh` de fixture (PF_GH_BIN) que guarda o
estado do PR em arquivo. Prova: motivo obrigatorio; MERGED recusa (4); OPEN fecha com o
motivo no comentario, confirma CLOSED no forge, remove a bancada do ramo e apaga o ramo
do origin; CLOSED e "ja feito" e ainda limpa; ramo que andou alem da ponta do PR fica.
Nao prova: o GitHub de verdade (refs/pull/<n>/head, fork).
"""
import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

GH_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
case "$1 $2" in
  "pr view")
    case "$*" in
      *headRefName*) echo "$(cat "$d/estado") $(cat "$d/ramo") $(cat "$d/oid") false" ;;
      *) cat "$d/estado" ;;
    esac ;;
  "pr close")
    printf '%s\\n' "$*" > "$d/fechou"
    echo CLOSED > "$d/estado" ;;
  *) exit 9 ;;
esac
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
    (semente / "LEIA.md").write_text("x\n")
    _git("add", "LEIA.md", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir()
    _git("clone", str(origem), str(bancada / "demo"))
    forge = tmp_path / "forge"
    forge.mkdir()
    gh = forge / "gh"
    gh.write_text(GH_FIXTURE)
    gh.chmod(0o755)
    return bancada, forge


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
        "PF_GH_BIN": str(tmp_path / "forge" / "gh"),
        **IDENT,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _pr_empurrado(tmp_path, bancada, forge, estado="OPEN"):
    """Bancada do card 42 com um commit empurrado; o PR #7 do forge aponta para a ponta."""
    r = _repo(tmp_path, bancada, "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "ti" / "42-x"
    (wt / "CARD.md").write_text("trabalho\n")
    _git("add", "CARD.md", cwd=wt)
    _git("commit", "-m", "card: CARD.md", cwd=wt)
    r = _repo(tmp_path, bancada, "empurrar", "demo")
    assert r.returncode == 0, r.stderr
    (forge / "estado").write_text(estado + "\n")
    (forge / "ramo").write_text("fabrica/42-x\n")
    (forge / "oid").write_text(_git("rev-parse", "HEAD", cwd=wt) + "\n")
    return wt


def _no_origin(tmp_path, ramo):
    r = subprocess.run(["git", "--git-dir", str(tmp_path / "origem.git"), "rev-parse", "--verify", "-q",
                        f"refs/heads/{ramo}"], capture_output=True, text=True)
    return r.returncode == 0


def test_sem_motivo_recusa_e_nao_fecha(tmp_path):
    bancada, forge = _montar(tmp_path)
    _pr_empurrado(tmp_path, bancada, forge)
    r = _repo(tmp_path, bancada, "pr-fechar", "demo", "7")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "--motivo" in r.stderr
    assert not (forge / "fechou").exists()


def test_open_fecha_com_motivo_e_limpa_bancada_e_origin(tmp_path):
    bancada, forge = _montar(tmp_path)
    wt = _pr_empurrado(tmp_path, bancada, forge)
    assert _no_origin(tmp_path, "fabrica/42-x")
    r = _repo(tmp_path, bancada, "pr-fechar", "demo", "7", "--motivo", "fora de escopo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PR #7 CLOSED (fabrica/42-x) [lido do forge]" in r.stdout
    assert "motivo: fora de escopo" in r.stdout
    assert "--comment fora de escopo" in (forge / "fechou").read_text()
    assert not wt.exists(), r.stdout
    assert "origin/fabrica/42-x: apagado" in r.stdout
    assert not _no_origin(tmp_path, "fabrica/42-x")


def test_merged_recusa_4(tmp_path):
    bancada, forge = _montar(tmp_path)
    wt = _pr_empurrado(tmp_path, bancada, forge, estado="MERGED")
    r = _repo(tmp_path, bancada, "pr-fechar", "demo", "7", "--motivo", "x")
    assert r.returncode == 4, r.stdout + r.stderr
    assert wt.exists()
    assert _no_origin(tmp_path, "fabrica/42-x")


def test_closed_e_ja_feito_e_ainda_limpa(tmp_path):
    bancada, forge = _montar(tmp_path)
    wt = _pr_empurrado(tmp_path, bancada, forge, estado="CLOSED")
    r = _repo(tmp_path, bancada, "pr-fechar", "demo", "7", "--motivo", "x")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "já feito: PR #7 CLOSED" in r.stdout
    assert not (forge / "fechou").exists()
    assert not wt.exists()
    assert not _no_origin(tmp_path, "fabrica/42-x")


def test_ramo_que_andou_alem_do_pr_fica_no_origin(tmp_path):
    bancada, forge = _montar(tmp_path)
    wt = _pr_empurrado(tmp_path, bancada, forge)
    (wt / "MAIS.md").write_text("depois do PR\n")
    _git("add", "MAIS.md", cwd=wt)
    _git("commit", "-m", "card: MAIS.md", cwd=wt)
    assert _repo(tmp_path, bancada, "empurrar", "demo").returncode == 0
    r = _repo(tmp_path, bancada, "pr-fechar", "demo", "7", "--motivo", "x")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "alem da ponta do PR" in r.stdout
    assert _no_origin(tmp_path, "fabrica/42-x")
