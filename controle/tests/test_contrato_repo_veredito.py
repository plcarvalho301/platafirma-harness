# componente: componente:verbo-repo
"""Contrato do veredito do portao depois da entrega direta na main (ordem do dono de 22/11/2026).

Git real contra bare local; o forge e um `gh` de fixture (PF_GH_BIN) que anota cada chamada
de `gh api`. A marca do portao e escrita a mao no lugar em que `hooks/pre-push` a grava
(<instancia>/var/pre-push/vereditos/portao-<repo>-<sha>). Prova: o `empurrar` so guarda o
ramo no origin, nao publica status no forge nem aponta pedido de integracao, mesmo com a
marca verde; `pr-abrir`, enquanto existir, segue publicando e apontando `pr-ver`.
Nao prova: o hook gravando a marca (os clones de teste nao tem hooksPath).
"""
import os
import subprocess
from pathlib import Path

REPO_BIN = Path(__file__).resolve().parents[2] / "bin" / "repo"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

GH_FIXTURE = """#!/bin/sh
d="$(dirname "$0")"
if [ "$1" = api ]; then
  [ -f "$d/recusa" ] && exit 1
  echo "$*" >> "$d/api"
  exit 0
fi
case "$1 $2" in
  "pr list") [ -f "$d/pr" ] && cat "$d/pr"; exit 0 ;;
  "pr create") echo "#7 OPEN https://forge/pr/7 (head abc1234)" > "$d/pr"; exit 0 ;;
  "pr view") cat "$d/pr" ;;
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


def _repo(tmp_path, bancada, *args, extra=None):
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
        # sem hook por padrao (debito 604): o hook real mediria o clone de fixture
        "PF_HOOK_PREPUSH": "/nao-existe/pre-push",
        **IDENT,
        **(extra or {}),
    }
    return subprocess.run([str(REPO_BIN), *args], env=env, capture_output=True, text=True)


def _commit_na_bancada(tmp_path, bancada, marca=None):
    """Bancada do card 42 com um commit ainda nao empurrado; grava a marca do portao, se pedida."""
    r = _repo(tmp_path, bancada, "abrir", "demo", "42", "--slug", "x")
    assert r.returncode == 0, r.stderr
    wt = bancada / "wt" / "demo" / "ti" / "42-x"
    (wt / "CARD.md").write_text("trabalho\n")
    _git("add", "CARD.md", cwd=wt)
    _git("commit", "-m", "card: CARD.md", cwd=wt)
    sha = _git("rev-parse", "HEAD", cwd=wt)
    if marca is not None:
        pasta = tmp_path / "instancia" / "var" / "pre-push" / "vereditos"
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / f"portao-demo-{sha}").write_text(marca + "\n")
    return wt, sha


def test_empurrar_so_guarda_o_ramo_e_nao_publica_veredito(tmp_path):
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada, marca="verde harness-0123456789ab")
    r = _repo(tmp_path, bancada, "empurrar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "empurrado: demo -> origin/fabrica/42-x" in r.stdout
    assert not (forge / "api").exists()
    assert "veredito" not in r.stdout
    assert "pr-abrir" not in r.stdout
    assert r.stdout.strip().splitlines()[-1] == "próximo: repo sincronizar demo"


def test_pr_abrir_publica_e_aponta_pr_ver_no_lugar_de_pr_merge(tmp_path):
    bancada, forge = _montar(tmp_path)
    _, sha = _commit_na_bancada(tmp_path, bancada, marca="verde harness-0123456789ab")
    assert _repo(tmp_path, bancada, "empurrar", "demo").returncode == 0
    r = _repo(tmp_path, bancada, "pr-abrir", "demo", "--titulo", "t")
    assert r.returncode == 0, r.stdout + r.stderr
    assert f"statuses/{sha}" in (forge / "api").read_text()
    assert "repo pr-ver demo 7" in r.stdout
    assert "repo pr-merge" not in r.stdout
    de_novo = _repo(tmp_path, bancada, "pr-abrir", "demo", "--titulo", "t")
    assert de_novo.returncode == 0, de_novo.stdout + de_novo.stderr
    assert "já feito: PR #7" in de_novo.stdout
    assert "repo pr-ver demo 7" in de_novo.stdout
    assert "repo pr-merge" not in de_novo.stdout
