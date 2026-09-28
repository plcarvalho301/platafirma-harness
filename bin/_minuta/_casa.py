#!/usr/bin/env python3
"""_casa — a worktree de main de platafirma-casa, para os atos de minuta que escrevem.

Regime direto em main (arq:0083 §1; ordem do dono de 28/09/2026; a lista que declara o
regime mora em bin/repo, REPOS_DIRETO_EM_MAIN): repositorio de deliberacao commita direto
em main, sem ramo nem PR. escrever, circular e formalizar editam na MESMA worktree que
`repo abrir platafirma-casa` da a cadeira, <bancada>/wt/platafirma-casa/<cadeira>/main
(segue origin/main); puxam antes de numerar e de editar, commitam e empurram para main.
Sem a worktree, criam-na chamando `repo abrir platafirma-casa`; se nem isso, saem 3 com a
chamada exata. MINUTA_REPO aponta outro checkout (teste).

git e gh pelo caminho real: o PATH da porta tem shims de `git` e `gh` (bilhete que so sai
2) a frente dos reais. `git` nu mata o ato com exit 2 ou 128 e sem mensagem; sem o gh real
na frente do PATH, o credential helper do pull/push HTTPS morre em "could not read
Username". Mesma cura de bin/repo.

Uso por modulo (circular, formalizar): import _casa. Uso por linha de comando (escrever,
que e bash): `_casa.py worktree <ato>` imprime o caminho; `_casa.py puxar <repo>` e
`_casa.py publicar <repo>`; exit e mensagem os da Falha.
"""
from __future__ import annotations

import os
import subprocess
import sys

_AQUI = os.path.dirname(os.path.realpath(__file__))
_BIN = os.path.dirname(_AQUI)
sys.path.insert(0, os.path.join(os.path.dirname(_BIN), "lib"))
from raizes import BancadaNaoDeclarada, bancada  # noqa: E402

REPO_CASA = "platafirma-casa"
PASTA_MAIN = "main"

GIT = next((p for p in ("/usr/bin/git", "/bin/git") if os.path.exists(p)), "git")
_GH = next(
    (p for p in ("/usr/bin/gh", "/bin/gh", os.path.expanduser("~/.local/bin/gh"))
     if os.path.exists(p)),
    None,
)
ENV = dict(os.environ)
if _GH:
    ENV["PATH"] = os.path.dirname(_GH) + ":" + ENV.get("PATH", "")


class Falha(Exception):
    """O ato nao segue: mensagem para o stderr e o exit da tabela (arq:0110 §4)."""

    def __init__(self, msg: str, code: int):
        super().__init__(msg)
        self.msg = msg
        self.code = code


def _ultima(texto: str) -> str:
    """A ultima linha nao vazia: e onde o git e o repo dizem o motivo."""
    linhas = [l for l in (texto or "").strip().splitlines() if l.strip()]
    return linhas[-1] if linhas else "sem mensagem"


def git(repo: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [GIT, "-C", repo, *args], capture_output=True, text=True, check=check, env=ENV
    )


def cadeira() -> str:
    c = os.environ.get("PF_CADEIRA", "").strip()
    return c.removeprefix("claudinho-").removeprefix("claudinha-")


def worktree(ato: str) -> str:
    """MINUTA_REPO, senao <bancada>/wt/platafirma-casa/<cadeira>/main; ausente, abre-a por
    `repo abrir platafirma-casa`. Sem cadeira: 2. Sem bancada ou sem worktree: 3."""
    explicito = os.environ.get("MINUTA_REPO")
    if explicito:
        return explicito
    cad = cadeira()
    if not cad:
        raise Falha("exporte PF_CADEIRA=<cadeira>: a minuta se edita na worktree de main da cadeira.", 2)
    try:
        raiz = bancada()
    except BancadaNaoDeclarada as e:
        raise Falha(str(e), 3)
    wt = os.path.join(str(raiz), "wt", REPO_CASA, cad, PASTA_MAIN)
    if os.path.exists(os.path.join(wt, ".git")):
        return wt
    chamada = f"repo abrir {REPO_CASA}"
    try:
        r = subprocess.run([os.path.join(_BIN, "repo"), "abrir", REPO_CASA],
                           capture_output=True, text=True, env=ENV, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as e:
        raise Falha(f"worktree de main ausente: {wt} — rode `{chamada}` antes de {ato} ({e}).", 3)
    if r.returncode != 0 or not os.path.exists(os.path.join(wt, ".git")):
        raise Falha(
            f"worktree de main ausente: {wt} — rode `{chamada}` antes de {ato} "
            f"(tentei: saiu {r.returncode}, {_ultima(r.stderr or r.stdout)}).", 3)
    print(_ultima(r.stdout), file=sys.stderr)
    return wt


def puxar(repo: str) -> None:
    """Traz origin/main antes de numerar ou editar (rebase; o sujo se guarda e volta)."""
    r = git(repo, "pull", "--rebase", "--autostash", "-q", "origin", "main", check=False)
    if r.returncode != 0:
        git(repo, "rebase", "--abort", check=False)
        raise Falha(
            f"pull de origin/main falhou em {repo}: {_ultima(r.stderr or r.stdout)} — "
            f"resolva e rode `repo sincronizar {REPO_CASA}`.", 4)


def publicar(repo: str) -> bool:
    """Empurra HEAD para main quando ha commit local a frente de origin/main."""
    frente = git(repo, "rev-list", "--count", "origin/main..HEAD", check=False).stdout.strip()
    if frente in ("", "0"):
        return False
    r = git(repo, "push", "-q", "origin", "HEAD:refs/heads/main", check=False)
    if r.returncode != 0:
        raise Falha(
            f"push para main falhou em {repo}: {_ultima(r.stderr or r.stdout)} — o commit "
            f"ficou local; rode `repo sincronizar {REPO_CASA}`.", 3)
    return True


def _cli(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in ("worktree", "puxar", "publicar"):
        print("uso: _casa.py worktree <ato> | puxar <repo> | publicar <repo>", file=sys.stderr)
        return 2
    try:
        if argv[0] == "worktree":
            print(worktree(argv[1]))
        elif argv[0] == "puxar":
            puxar(argv[1])
        else:
            publicar(argv[1])
    except Falha as f:
        print(f.msg, file=sys.stderr)
        return f.code
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
