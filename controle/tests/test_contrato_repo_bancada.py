"""Contrato de `repo abrir` e da resolucao de bancada: worktree por CADEIRA (arq:0109 §2).

Defeito medido em 26/09/2026 (revisao do PR 22 de platafirma-casa): `repo abrir` criava
wt/<repo>/<sessao_id>; a sessao seguinte da mesma cadeira nao achava a bancada e caia no
clone compartilhado, com aviso so em stderr. Git real contra bare local, sem rede.

Prova: o worktree nasce em wt/<repo>/<cadeira>, e outra sessao da mesma cadeira resolve
a mesma bancada sem fallback. Nao prova: o forge (clone base ja existe; nao ha push).
"""
import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"


def _git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


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
    return bancada


def _repo(tmp_path, bancada, sessao, *args):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-ti",
        "PF_SESSAO": sessao,
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def test_abrir_cria_worktree_da_cadeira_e_nao_da_sessao(tmp_path):
    bancada = _montar(tmp_path)
    r = _repo(tmp_path, bancada, "sessao-1", "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    assert (bancada / "wt" / "demo" / "ti" / ".git").exists()
    assert not (bancada / "wt" / "demo" / "sessao-1").exists()


def test_outra_sessao_da_mesma_cadeira_acha_a_bancada_sem_fallback(tmp_path):
    bancada = _montar(tmp_path)
    assert _repo(tmp_path, bancada, "sessao-1", "abrir", "demo", "42", "--slug", "x").returncode == 0
    r = _repo(tmp_path, bancada, "sessao-2", "estado", "demo")
    assert r.returncode == 0, r.stderr
    assert "fallback" not in r.stderr
    assert "fabrica/42-x" in r.stdout


def test_worktree_legado_por_sessao_segue_legivel_ate_a_cadeira_ter_o_seu(tmp_path):
    bancada = _montar(tmp_path)
    _git("worktree", "add", "-b", "fabrica/7-legado",
         str(bancada / "wt" / "demo" / "sessao-velha"), "origin/main", cwd=bancada / "demo")
    r = _repo(tmp_path, bancada, "sessao-velha", "estado", "demo")
    assert r.returncode == 0, r.stderr
    assert "fabrica/7-legado" in r.stdout
    assert "fallback" not in r.stderr
