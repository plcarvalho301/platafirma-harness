"""Lê o documento fixo em origin/main na hora da chamada."""

from __future__ import annotations

import subprocess

from . import Falha

CAMINHO = "6-processo/procedimento/escrever-receita-de-preparacao.md"


def ler() -> str:
    from raizes import release

    repo = release() / "harness/bin/repo"
    try:
        fetch = subprocess.run(
            [str(repo), "git", "platafirma-casa-espelho", "fetch", "origin", "main"],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
        if fetch.returncode:
            raise Falha(3, "guia-indisponivel", CAMINHO)
        p = subprocess.run(
            [
                str(repo),
                "git",
                "platafirma-casa-espelho",
                "show",
                "origin/main:" + CAMINHO,
            ],
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
        if p.returncode:
            raise Falha(3, "guia-indisponivel", CAMINHO)
        return p.stdout
    except (OSError, subprocess.TimeoutExpired):
        raise Falha(3, "guia-indisponivel", CAMINHO) from None
