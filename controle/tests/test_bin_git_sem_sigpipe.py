"""Verbos bash com `set -o pipefail` nao resolvem o git por `command -v ... | head -1`.

Com /bin -> /usr/bin o `command -v /usr/bin/git /bin/git` imprime duas linhas; o `head -1` fecha o pipe
e o builtin leva SIGPIPE em corrida. Sob pipefail + set -e o verbo sai 141 de forma intermitente (medido
em 10/10: `release naoexiste` e `release promover <rev fora de main>` saindo 141 no gate de promocao, em
suites bash diferentes a cada rodada). A resolucao e por laco com `[ -x ]`, sem pipe.
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
VERBOS = ["bin/release", "bin/repo", "bin/publicar-abertura"]
PIPE_NO_COMMAND_V = re.compile(r"command -v[^\n]*\|\s*head")


@pytest.mark.parametrize("verbo", VERBOS)
def test_verbo_nao_resolve_git_por_pipe_com_head(verbo):
    texto = (RAIZ / verbo).read_text(encoding="utf-8")
    achados = [
        linha for linha in texto.splitlines() if PIPE_NO_COMMAND_V.search(linha)
    ]
    assert achados == [], f"{verbo}: `command -v | head` sob pipefail da SIGPIPE intermitente: {achados}"


@pytest.mark.parametrize("verbo", VERBOS)
def test_verbo_resolve_git_por_laco_com_teste_de_executavel(verbo):
    texto = (RAIZ / verbo).read_text(encoding="utf-8")
    assert "for _g in /usr/bin/git /bin/git" in texto, f"{verbo}: resolucao do git por laco ausente"
