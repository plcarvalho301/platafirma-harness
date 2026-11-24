# componente: componente:verbo-repo
"""Testes de segurança de `bin/repo` para os DTs 1360, 1361 e 1362."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BIN_REPO = RAIZ / "bin" / "repo"


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "teste",
        "GIT_AUTHOR_EMAIL": "teste@platafirma",
        "GIT_COMMITTER_NAME": "teste",
        "GIT_COMMITTER_EMAIL": "teste@platafirma",
    }
    return subprocess.run(
        ["git", "-C", str(cwd), *args],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )


def _preparar_bancada(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, str]]:
    """Cria bare remote, clone base e worktree na estrutura esperada por bin/repo."""
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-b", "main", str(bare)], check=True, capture_output=True)

    bancada = tmp_path / "bancada"
    base = bancada / "demo"
    base.mkdir(parents=True)
    _git(base, "init", "-b", "main")
    (base / "README.md").write_text("ola\n", encoding="utf-8")
    _git(base, "add", "README.md")
    _git(base, "commit", "-m", "inicial")
    _git(base, "remote", "add", "origin", str(bare))
    _git(base, "push", "-u", "origin", "main")

    wt = bancada / "wt" / "demo" / "engenharia" / "card-1"
    wt.parent.mkdir(parents=True, exist_ok=True)
    _git(base, "worktree", "add", "-b", "engenharia/card-1", str(wt), "main")

    inst = tmp_path / "instancia"
    (inst / "var" / "tmp").mkdir(parents=True)

    env = {
        **os.environ,
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_CADEIRA": "engenharia",
        "PLATAFIRMA_INSTANCIA": str(inst),
        "PF_ORDEM_ID": "ordem-a",
    }
    return bare, base, wt, env


def _rodar_repo(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BIN_REPO), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
        check=False,
    )


def test_dt1361_repo_ler_recusa_symlink_fora_da_bancada(tmp_path: Path) -> None:
    _bare, _base, wt, env = _preparar_bancada(tmp_path)
    segredo = tmp_path / "fora-da-bancada.txt"
    segredo.write_text("SEGREDO-EXTERNO\n", encoding="utf-8")

    (wt / "fuga.txt").symlink_to(segredo)
    (wt / "interno.txt").symlink_to(wt / "README.md")

    proc_fuga = _rodar_repo(env, "ler", "demo@card-1", "fuga.txt")
    assert proc_fuga.returncode == 4, (proc_fuga.returncode, proc_fuga.stdout, proc_fuga.stderr)
    assert "SEGREDO-EXTERNO" not in proc_fuga.stdout

    proc_ok = _rodar_repo(env, "ler", "demo@card-1", "interno.txt")
    assert proc_ok.returncode == 0, proc_ok.stderr
    assert "ola" in proc_ok.stdout


def test_dt1362_repo_copiar_confina_ao_pf_ordem_id(tmp_path: Path) -> None:
    _bare, _base, wt, env = _preparar_bancada(tmp_path)
    inst = Path(env["PLATAFIRMA_INSTANCIA"])
    arq_a = inst / "var" / "tmp" / "ordem-a" / "meu.txt"
    arq_b = inst / "var" / "tmp" / "ordem-b" / "alheio.txt"
    arq_a.parent.mkdir(parents=True, exist_ok=True)
    arq_b.parent.mkdir(parents=True, exist_ok=True)
    arq_a.write_text("da-ordem-a\n", encoding="utf-8")
    arq_b.write_text("da-ordem-b\n", encoding="utf-8")

    # Caminho absoluto de outra ordem deve ser recusado com código 4
    proc_outra = _rodar_repo(env, "copiar", "demo@card-1", str(arq_b), "roubado.txt")
    assert proc_outra.returncode == 4, (proc_outra.returncode, proc_outra.stdout, proc_outra.stderr)
    assert not (wt / "roubado.txt").exists()

    # Sem PF_ORDEM_ID também deve ser recusado com código 4
    env_sem_ordem = {k: v for k, v in env.items() if k != "PF_ORDEM_ID"}
    proc_sem = _rodar_repo(env_sem_ordem, "copiar", "demo@card-1", str(arq_a), "sem-ordem.txt")
    assert proc_sem.returncode == 4, (proc_sem.returncode, proc_sem.stdout, proc_sem.stderr)

    # Origem dentro da própria ordem (relativa e absoluta) funciona
    proc_rel = _rodar_repo(env, "copiar", "demo@card-1", "meu.txt", "copia-rel.txt")
    assert proc_rel.returncode == 0, proc_rel.stderr
    assert (wt / "copia-rel.txt").read_text(encoding="utf-8") == "da-ordem-a\n"

    proc_abs = _rodar_repo(env, "copiar", "demo@card-1", str(arq_a), "copia-abs.txt")
    assert proc_abs.returncode == 0, proc_abs.stderr
    assert (wt / "copia-abs.txt").read_text(encoding="utf-8") == "da-ordem-a\n"


def test_dt1360_salva_arvore_exclui_arquivos_sensiveis(tmp_path: Path) -> None:
    bare, _base, wt, env = _preparar_bancada(tmp_path)

    # Caso 1: árvore suja com arquivo de trabalho + arquivos sensíveis
    (wt / "trabalho.txt").write_text("codigo ok\n", encoding="utf-8")
    sensiveis = [".env", ".env.local", "priv.key", "cert.pem", "sig.asc", "cofre.kdbx", "sub/.env"]
    for rel in sensiveis:
        p = wt / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("SEGREDO\n", encoding="utf-8")

    # Executa salva_arvore carregando apenas as funções de bin/repo (sem disparar o main)
    script = f"""
set -euo pipefail
GIT="$(command -v git)"
PATH_FORGE="$PATH"
eval "$(sed -n '/^ramo_atual()/,/^}}/p' {BIN_REPO})"
eval "$(sed -n '/^salva_arvore()/,/^}}/p' {BIN_REPO})"
salva_arvore "{wt}" "engenharia"
"""
    proc = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, check=False)
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    wip = proc.stdout.strip()
    assert wip.startswith("wip/engenharia/"), wip

    arqs_wip = _git(bare, "ls-tree", "-r", "--name-only", wip).stdout.splitlines()
    assert "trabalho.txt" in arqs_wip
    for rel in sensiveis:
        assert rel not in arqs_wip, f"arquivo sensível {rel!r} vazou no ramo {wip}: {arqs_wip}"

    # Caso 2: árvore suja APENAS com arquivo sensível não sobe nenhum ramo wip novo
    branches_antes = set(_git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads/wip/").stdout.splitlines())
    proc2 = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, check=False)
    assert proc2.returncode == 3, (proc2.returncode, proc2.stdout, proc2.stderr)
    branches_depois = set(_git(bare, "for-each-ref", "--format=%(refname:short)", "refs/heads/wip/").stdout.splitlines())
    assert branches_depois == branches_antes
