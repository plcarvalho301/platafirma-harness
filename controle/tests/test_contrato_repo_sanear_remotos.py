"""Contrato de `repo sanear` sobre os ramos do origin (card #3072; ordem do dono 27/09/2026).

Git real contra bare local; os PRs abertos vem de um `gh` de fixture (PF_GH_BIN). Prova:
ramo sem PR aberto com o ultimo commit mais velho que PF_SANEAR_DIAS some do origin, wip/
inclusive, com sha e linha da volta na saida; ramo novo, ramo com PR aberto, ramo de bancada
viva e main ficam; `--relatar` so lista; PRs abertos ilegiveis nao apagam nada.
Nao prova: o GitHub de verdade.
"""
import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
VELHO = {"GIT_AUTHOR_DATE": "2026-01-01T12:00:00", "GIT_COMMITTER_DATE": "2026-01-01T12:00:00"}

GH_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
case "$*" in
  *"--state open"*) [ -f "$d/quebrado" ] && exit 1; cat "$d/abertos" ;;
  *"--state merged"*) : ;;
  *) exit 9 ;;
esac
"""


def _git(*args, cwd=None, extra=None):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **IDENT, **(extra or {})}).stdout.strip()


def _ramo(semente, nome, velho):
    _git("checkout", "-q", "-B", nome, "main", cwd=semente)
    (semente / f"{nome.replace('/', '_')}.md").write_text(nome + "\n")
    _git("add", "-A", cwd=semente)
    _git("commit", "-q", "-m", nome, cwd=semente, extra=VELHO if velho else None)
    _git("push", "-q", "origin", nome, cwd=semente)
    _git("checkout", "-q", "main", cwd=semente)


def _montar(tmp_path):
    origem, semente, bancada = tmp_path / "origem.git", tmp_path / "semente", tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    (semente / "LEIA.md").write_text("x\n")
    _git("add", "LEIA.md", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    _ramo(semente, "fabrica/1-velho", velho=True)
    _ramo(semente, "wip/ti/fabrica/2-salvo", velho=True)
    _ramo(semente, "fabrica/3-novo", velho=False)
    _ramo(semente, "fabrica/4-com-pr", velho=True)
    _ramo(semente, "ti/vivo", velho=True)
    bancada.mkdir()
    _git("clone", "-q", str(origem), str(bancada / "demo"))
    # bancada viva da cadeira ti no ramo velho ti/vivo
    base = bancada / "demo"
    _git("branch", "-q", "ti/vivo", "origin/ti/vivo", cwd=base)
    (bancada / "wt" / "demo" / "ti").mkdir(parents=True)
    _git("worktree", "add", "-q", str(bancada / "wt" / "demo" / "ti" / "vivo"), "ti/vivo", cwd=base)
    forge = tmp_path / "forge"
    forge.mkdir()
    (forge / "gh").write_text(GH_FIXTURE)
    (forge / "gh").chmod(0o755)
    (forge / "abertos").write_text("fabrica/4-com-pr\n")
    return bancada, forge, origem


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


def _no_origin(origem):
    out = subprocess.run(["git", "--git-dir", str(origem), "for-each-ref", "--format=%(refname:short)",
                          "refs/heads"], capture_output=True, text=True).stdout
    return set(out.split())


def test_apaga_sem_pr_e_velho_e_deixa_o_resto(tmp_path):
    bancada, _, origem = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "sanear", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert _no_origin(origem) == {"main", "fabrica/3-novo", "fabrica/4-com-pr", "ti/vivo"}
    assert "origin/fabrica/1-velho: apagado" in r.stdout
    assert "origin/wip/ti/fabrica/2-salvo: apagado" in r.stdout
    assert "volta: git push origin " in r.stdout


def test_relatar_so_lista(tmp_path):
    bancada, _, origem = _montar(tmp_path)
    antes = _no_origin(origem)
    r = _repo(tmp_path, bancada, "sanear", "demo", "--relatar")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "origin/fabrica/1-velho: relataria apagar" in r.stdout
    assert _no_origin(origem) == antes


def test_prazo_maior_nao_apaga(tmp_path):
    bancada, _, origem = _montar(tmp_path)
    antes = _no_origin(origem)
    r = subprocess.run([str(REPO_BIN), "sanear", "demo"], capture_output=True, text=True,
                       env={**os.environ, **IDENT, "HOME": str(tmp_path), "PLATAFIRMA_BANCADA": str(bancada),
                            "PF_CADEIRA": "claudinho-ti", "PF_SESSAO": "s1", "PF_TAREFAS_BIN": "/bin/true",
                            "PF_RELEASE_RAIZ": str(tmp_path / "release"),
                            "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
                            "PF_GH_BIN": str(tmp_path / "forge" / "gh"), "PF_SANEAR_DIAS": "100000"})
    assert r.returncode == 0, r.stdout + r.stderr
    assert _no_origin(origem) == antes


def test_prs_abertos_ilegiveis_nao_apaga_nada(tmp_path):
    bancada, forge, origem = _montar(tmp_path)
    (forge / "quebrado").write_text("")
    antes = _no_origin(origem)
    r = _repo(tmp_path, bancada, "sanear", "demo")
    assert "PRs abertos ilegiveis" in r.stdout
    assert _no_origin(origem) == antes
