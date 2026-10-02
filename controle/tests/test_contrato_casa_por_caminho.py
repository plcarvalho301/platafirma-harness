"""Contrato da trava «documento de casa não se lê por caminho» (arq:0115 §11.3; pós-morte do
incidente #3225).

Prova: `forma` pega o repositório extinto de arquitetura seguido de caminho ou de `@`,
`release() / "casa"` e `current/casa`, e deixa passar a instância (`/srv/platafirma/casa`), a
bancada de main da casa e a chave do acervo; o pre-commit recusa linha acrescentada com a
forma, nomeando arquivo e linha, e passa o commit limpo; a forma legada não trava a edição de
outro trecho; o próprio detector e o teste dele são isentos; `lint fossil` (via
`verificar_fossil`) relata o estoque como aviso, instrução de agente inclusive. Não prova: o
hook instalado nos clones (core.hooksPath).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[2]
PRE_COMMIT = HARNESS / "bin" / "_lint" / "pre_commit.py"

sys.path.insert(0, str(HARNESS / "bin"))
from _lint.casa_por_caminho import forma  # noqa: E402
from _lint.fossil import verificar_fossil  # noqa: E402

IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, **IDENT})


def _repo(tmp_path, arquivos, commitar=False):
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    if not (repo / ".git").exists():
        _git(repo, "init", "-q", "-b", "main")
    for nome, texto in arquivos.items():
        p = repo / nome
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto, encoding="utf-8")
    _git(repo, "add", "-A")
    if commitar:
        _git(repo, "commit", "-q", "--no-verify", "-m", "base")
    return repo


def _pre_commit(repo):
    env = {**os.environ, "KROKI_URL": "http://127.0.0.1:9"}
    return subprocess.run([sys.executable, str(PRE_COMMIT)], cwd=repo,
                          capture_output=True, text=True, env=env, check=False)


@pytest.mark.parametrize("linha", [
    "Ler de platafirma-arquitetura/macro-global/decisions/0039-x.md antes.",
    "lembrete: platafirma-arquitetura@docs/arquitetura-negocio-operacao.md",
    'REPO = str(release() / "casa")',
    "DIR=/opt/platafirma/current/casa/minuta",
])
def test_forma_pega(linha):
    assert forma(linha)


@pytest.mark.parametrize("linha", [
    "PLATAFIRMA_INSTANCIA[=/srv/platafirma/casa]",
    "worktree <bancada>/wt/platafirma-casa/<cadeira>/main para escrever",
    "acervo ler casa adr arq:0115",
    "O repositório platafirma-arquitetura saiu da release em 22/09.",
    'release() / "harness"',
])
def test_forma_passa(linha):
    assert forma(linha) is None


def test_pre_commit_recusa_leitura_por_caminho(tmp_path):
    repo = _repo(tmp_path, {"bin/x": '#!/bin/sh\n\nREPO="/opt/platafirma/current/casa"\n'})
    r = _pre_commit(repo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[casa-por-caminho] bin/x:3:" in r.stderr
    assert "acervo ler casa" in r.stderr


def test_pre_commit_recusa_instrucao_de_agente(tmp_path):
    repo = _repo(tmp_path, {"AGENTS.md": "Ler platafirma-arquitetura/docs/x.md primeiro.\n"})
    r = _pre_commit(repo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[casa-por-caminho] AGENTS.md:1:" in r.stderr


def test_pre_commit_passa_limpo(tmp_path):
    repo = _repo(tmp_path, {"AGENTS.md": "Ler `acervo ler casa adr arq:0039` primeiro.\n"})
    r = _pre_commit(repo)
    assert r.returncode == 0, r.stdout + r.stderr


def test_forma_legada_nao_trava_outro_trecho(tmp_path):
    repo = _repo(tmp_path, {"AGENTS.md": "legado: platafirma-arquitetura/docs/x.md\n"},
                 commitar=True)
    _repo(tmp_path, {"AGENTS.md": "legado: platafirma-arquitetura/docs/x.md\n\nlinha nova\n"})
    r = _pre_commit(repo)
    assert r.returncode == 0, r.stdout + r.stderr


def test_detector_e_teste_isentos(tmp_path):
    texto = 'X = release() / "casa"\n'
    repo = _repo(tmp_path, {"bin/_lint/casa_por_caminho.py": texto,
                            "controle/tests/test_contrato_casa_por_caminho.py": texto})
    r = _pre_commit(repo)
    assert "[casa-por-caminho]" not in r.stderr, r.stderr


def test_lint_fossil_relata_estoque_como_aviso(tmp_path):
    repo = _repo(tmp_path, {"AGENTS.md": "a\nLer platafirma-arquitetura/docs/x.md\n",
                            "lib/y.py": "ok = 1\n"}, commitar=True)
    apts = [a for a in verificar_fossil(repo) if a.id == "CASA_POR_CAMINHO"]
    assert [(a.arquivo, a.linha, a.severidade) for a in apts] == [("AGENTS.md", 2, "aviso")]
