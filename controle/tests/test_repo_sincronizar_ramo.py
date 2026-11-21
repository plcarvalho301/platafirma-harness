# componente: componente:verbo-repo
from __future__ import annotations

import os
from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_REPO = REPO_ROOT / "bin" / "repo"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
        env={
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        },
    )


def _setup_origin_e_base(tmp_path: Path, nome: str = "demo") -> tuple[Path, Path]:
    bancada = tmp_path / "bancada"
    bancada.mkdir(parents=True, exist_ok=True)
    origin = tmp_path / f"{nome}-origin.git"
    _git(tmp_path, "init", "--bare", "-b", "main", str(origin))

    seed = tmp_path / f"{nome}-seed"
    _git(tmp_path, "clone", str(origin), str(seed))
    (seed / "README.md").write_text("base\n", encoding="utf-8")
    _git(seed, "add", "README.md")
    _git(seed, "commit", "-m", "init")
    _git(seed, "push", "-u", "origin", "main")

    base = bancada / nome
    _git(tmp_path, "clone", str(origin), str(base))
    _git(base, "checkout", "--detach", "origin/main")
    return bancada, base


def _run_repo(bancada: Path, *args: str, cadeira: str = "ti") -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_CADEIRA": cadeira,
        "GIT_AUTHOR_NAME": "t",
        "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t",
        "GIT_COMMITTER_EMAIL": "t@t",
    }
    return subprocess.run(
        [str(BIN_REPO), *args],
        text=True,
        capture_output=True,
        env=env,
    )


def test_dt7_commitar_em_head_destacado_recusa_com_vizinho(tmp_path: Path) -> None:
    """DT 7: commitar em HEAD destacado não acusa outra cadeira; sai 4 com vizinho repo ramo."""
    bancada, base = _setup_origin_e_base(tmp_path)
    wt = bancada / "wt" / "demo" / "ti" / "destacado"
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git(base, "worktree", "add", "--detach", str(wt), "origin/main")

    (wt / "nota.txt").write_text("teste\n", encoding="utf-8")

    r = _run_repo(bancada, "commitar", "demo", "-m", "em head destacado", "nota.txt")
    assert r.returncode == 4, (r.stdout, r.stderr)
    assert "HEAD destacado" in r.stderr
    assert "pertence a outra cadeira" not in r.stderr
    assert "vizinho: repo ramo demo" in r.stderr

    r_git = _run_repo(bancada, "git", "demo", "commit", "-m", "via git")
    assert r_git.returncode == 4, (r_git.stdout, r_git.stderr)
    assert "HEAD destacado" in r_git.stderr
    assert "pertence a outra cadeira" not in r_git.stderr


def test_dt7_ramo_preso_em_outro_worktree_recusa_com_vizinho(tmp_path: Path) -> None:
    """DT 7: trocar para ramo já aberto em outro worktree sai 4 nomeando a pasta e o vizinho."""
    bancada, base = _setup_origin_e_base(tmp_path)
    wt1 = bancada / "wt" / "demo" / "ti" / "42-x"
    wt2 = bancada / "wt" / "demo" / "ti" / "outro"
    wt1.parent.mkdir(parents=True, exist_ok=True)
    _git(base, "worktree", "add", "-b", "fabrica/42-x", str(wt1), "origin/main")
    _git(base, "worktree", "add", "--detach", str(wt2), "origin/main")

    r = _run_repo(bancada, "ramo", "demo@outro", "42", "--slug", "x")
    assert r.returncode == 4, (r.stdout, r.stderr)
    assert "preso em outro worktree" in r.stderr
    assert str(wt1) in r.stderr
    assert "demo@42-x" in r.stderr
    assert "vizinho:" in r.stderr


def test_dt7_ramo_novo_em_head_destacado_e_commitar(tmp_path: Path) -> None:
    """DT 7: criar ramo novo a partir de HEAD destacado destrava o commitar."""
    bancada, base = _setup_origin_e_base(tmp_path)
    wt = bancada / "wt" / "demo" / "ti" / "outro"
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git(base, "worktree", "add", "--detach", str(wt), "origin/main")

    (wt / "nota.txt").write_text("teste\n", encoding="utf-8")

    r_ramo = _run_repo(bancada, "ramo", "demo@outro", "99", "--slug", "novo")
    assert r_ramo.returncode == 0, (r_ramo.stdout, r_ramo.stderr)
    assert "ramo criado: fabrica/99-novo" in r_ramo.stdout

    r_commit = _run_repo(bancada, "commitar", "demo@outro", "-m", "commit no ramo", "nota.txt")
    assert r_commit.returncode == 0, (r_commit.stdout, r_commit.stderr)
