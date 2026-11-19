"""Cobertura do DT-490 em bin/repo:

1. `repo ramo` cria bancada nova e nunca troca o branch de uma bancada existente.
2. `repo pr-merge` so remove bancada cujo eixo pertence ao proprio ramo entregue.
3. `repo git commit` aplica o mesmo portao de story em execucao que `repo commitar`.
"""

import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
}

GH_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
case "$1 $2" in
  "pr view")
    case "$*" in
      *"--json state,headRefName,headRefOid,mergeCommit"*)
        echo "$(cat "$d/estado") $(cat "$d/ramo") $(cat "$d/mergeoid" 2>/dev/null || echo -) $(cat "$d/oid")" ;;
      *"--json state,mergeCommit"*)
        echo "$(cat "$d/estado") $(cat "$d/mergeoid" 2>/dev/null || echo -)" ;;
      *"--json statusCheckRollup"*)
        echo '{"statusCheckRollup":[]}' ;;
      *) cat "$d/estado" ;;
    esac ;;
  "pr merge")
    echo MERGED > "$d/estado"
    [ -s "$d/mergeoid" ] || cat "$d/oid" > "$d/mergeoid"
    exit 0 ;;
  *) exit 9 ;;
esac
"""


def _git(*args, cwd=None):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **IDENT},
    ).stdout.strip()


def _montar(tmp_path: Path):
    origem = tmp_path / "origem.git"
    semente = tmp_path / "semente"
    bancada = tmp_path / "bancada"
    _git("init", "--bare", "-b", "main", str(origem))
    _git("init", "-b", "main", str(semente))
    (semente / "LEIA.md").write_text("x\n", encoding="utf-8")
    _git("add", "LEIA.md", cwd=semente)
    _git("commit", "-m", "semente", cwd=semente)
    _git("remote", "add", "origin", str(origem), cwd=semente)
    _git("push", "origin", "main", cwd=semente)
    bancada.mkdir()
    _git("clone", str(origem), str(bancada / "demo"))
    forge = tmp_path / "forge"
    forge.mkdir()
    gh = forge / "gh"
    gh.write_text(GH_FIXTURE, encoding="utf-8")
    gh.chmod(0o755)
    return bancada, forge


def _tarefas_falsa(tmp_path: Path, nivel="story", estado="priorizada"):
    script = tmp_path / f"tarefas_{estado}"
    script.write_text(
        f"""#!/usr/bin/env bash
if [ "$1" = api ]; then
  printf '{{"id": 42, "nivel_nome": "{nivel}", "estado": "{estado}", "cadeira": "ti", "executor": ""}}\\n'
  exit 0
fi
exit 0
""",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def _repo(tmp_path: Path, bancada: Path, *args, tarefas_bin="/bin/true"):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(tmp_path),
        "PLATAFIRMA_BANCADA": str(bancada),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_CADEIRA": "claudinho-ti",
        "PF_SESSAO": "s1",
        "PF_TAREFAS_BIN": str(tarefas_bin),
        "PF_GH_BIN": str(tmp_path / "forge" / "gh"),
        **IDENT,
    }
    return subprocess.run(["bash", str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def test_ramo_cria_bancada_nova_e_nunca_troca_existente(tmp_path):
    bancada, _ = _montar(tmp_path)
    r0 = _repo(tmp_path, bancada, "abrir", "demo", "--slug", "leitura-regras")
    assert r0.returncode == 0, r0.stderr
    wt_existente = bancada / "wt" / "demo" / "ti" / "leitura-regras"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt_existente) == "ti/leitura-regras"

    r1 = _repo(tmp_path, bancada, "ramo", "demo", "3961")
    assert r1.returncode == 0, r1.stdout + r1.stderr
    wt_nova = bancada / "wt" / "demo" / "ti" / "3961"
    assert wt_nova.exists()
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt_nova) == "fabrica/3961"
    assert _git("rev-parse", "--abbrev-ref", "HEAD", cwd=wt_existente) == "ti/leitura-regras"

    r2 = _repo(tmp_path, bancada, "ramo", "demo@leitura-regras", "3962")
    assert r2.returncode == 2
    assert "nao use @<chave>" in r2.stderr


def test_pr_merge_nao_remove_bancada_de_outro_trabalho_mesmo_no_ramo(tmp_path):
    bancada, forge = _montar(tmp_path)
    r_other = _repo(tmp_path, bancada, "abrir", "demo", "--slug", "leitura-regras")
    assert r_other.returncode == 0, r_other.stderr
    wt_outro = bancada / "wt" / "demo" / "ti" / "leitura-regras"

    r_card = _repo(tmp_path, bancada, "abrir", "demo", "42", "--slug", "x")
    assert r_card.returncode == 0, r_card.stderr
    wt_card = bancada / "wt" / "demo" / "ti" / "42-x"
    (wt_card / "CARD.md").write_text("trabalho\n", encoding="utf-8")
    _git("add", "CARD.md", cwd=wt_card)
    _git("commit", "-m", "card: CARD.md", cwd=wt_card)
    r_push = _repo(tmp_path, bancada, "empurrar", "demo@42-x")
    assert r_push.returncode == 0, r_push.stderr

    # Simula worktree de outro trabalho temporariamente no ramo do PR
    _git("checkout", "-q", "--detach", cwd=wt_card)
    _git("checkout", "-q", "fabrica/42-x", cwd=wt_outro)
    _git("checkout", "-q", "fabrica/42-x", cwd=wt_card) if False else None

    (forge / "estado").write_text("OPEN\n", encoding="utf-8")
    (forge / "ramo").write_text("fabrica/42-x\n", encoding="utf-8")
    (forge / "oid").write_text(_git("rev-parse", "HEAD", cwd=wt_outro) + "\n", encoding="utf-8")
    vdir = tmp_path / "instancia" / "var" / "esteira"
    vdir.mkdir(parents=True, exist_ok=True)
    import json as _json
    (vdir / "demo.jsonl").write_text(
        _json.dumps({
            "repositorio": "demo",
            "arvore_mudanca": _git("rev-parse", "HEAD^{tree}", cwd=wt_outro),
            "arvore_main": _git("rev-parse", "origin/main^{tree}", cwd=wt_outro),
            "estado": "verde",
            "fichas": [],
        }) + "\n",
        encoding="utf-8",
    )

    r_merge = _repo(tmp_path, bancada, "pr-merge", "demo", "7", "--forcar")
    assert r_merge.returncode == 0, r_merge.stdout + r_merge.stderr
    assert wt_outro.exists(), "pr-merge nao deve remover bancada de outro trabalho"
    assert "chave 'leitura-regras' e de outro trabalho" in r_merge.stdout


def test_git_commit_respeita_portao_de_story_em_execucao(tmp_path):
    bancada, _ = _montar(tmp_path)
    tarefas_priorizada = _tarefas_falsa(tmp_path, nivel="story", estado="priorizada")
    r0 = _repo(tmp_path, bancada, "abrir", "demo", "42", "--slug", "x", tarefas_bin=tarefas_priorizada)
    assert r0.returncode == 0, r0.stderr
    wt = bancada / "wt" / "demo" / "ti" / "42-x"
    (wt / "novo.py").write_text("x = 1\n", encoding="utf-8")

    r_add = _repo(tmp_path, bancada, "git", "demo@42-x", "add", "novo.py", tarefas_bin=tarefas_priorizada)
    assert r_add.returncode == 0, r_add.stderr

    r_commit = _repo(
        tmp_path, bancada, "git", "demo@42-x", "commit", "-m", "teste (#42)", tarefas_bin=tarefas_priorizada
    )
    assert r_commit.returncode == 4, r_commit.stderr
    assert "story #42 em priorizada: a dona escreve o Plano" in r_commit.stderr

    tarefas_exec = _tarefas_falsa(tmp_path, nivel="story", estado="em-execucao")
    r_ok = _repo(tmp_path, bancada, "git", "demo@42-x", "commit", "-m", "teste (#42)", tarefas_bin=tarefas_exec)
    assert r_ok.returncode == 0, r_ok.stderr
