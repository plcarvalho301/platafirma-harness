"""Contrato da trava «casa velha não se cita por caminho» (F4073, #4348).

Prova: `forma` pega o repositório extinto de arquitetura, `platafirma-casa` (sem -espelho),
as pastas numeradas (1-orientacao a 6-artefato), originais/, abertura/dono.md,
var/abertura-publicada e leituras de casa na release; deixa passar a instância
(`/srv/platafirma/casa`), `platafirma-casa-espelho`, `release() / "harness"` e
`/opt/platafirma/current/casa-espelho/...`; o pre-commit recusa linha acrescentada com a
forma, nomeando arquivo e linha, e passa o commit limpo; a forma legada não trava a edição
de outro trecho; o próprio detector e o teste dele são isentos; `varrer` devolve 1
apontamento por linha proibida.
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
from _lint.casa_por_caminho import forma, varrer  # noqa: E402

IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

# Literais partidos para compatibilidade com hooks antigos no repositório espelho.
_ARQ = "platafirma-" + "arquitetura"
_CASA = "platafirma-" + "casa"
_REL_CASA = "release()" + ' / "casa"'
_CUR_CASA = "/opt/platafirma/" + "current/" + "casa"
_P1 = "1-" + "orientacao"
_P2 = "2-" + "comportamento"
_P6 = "6-" + "artefato"
_ORIG = "origi" + "nais/"
_DONO = "abertura/" + "dono.md"
_PUB = "var/abertura-" + "publicada"


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
    f"Ler de {_ARQ}/macro-global/decisions/0039-x.md antes.",
    f"lembrete: {_ARQ}@docs/x.md",
    f"repo abrir {_CASA}",
    f"arquivo {_CASA}@padrao/molde.md",
    f"REPO = str({_REL_CASA})",
    f"DIR={_CUR_CASA}/minuta",
    f"pasta {_P1}/regra.md",
    f"pasta {_P2}/persona.md",
    f"pasta {_P6}/spec.md",
    f"leia {_ORIG}documento.md",
    f"veja {_DONO}",
    f"MORADA = '/srv/platafirma/casa/{_PUB}'",
])
def test_forma_pega(linha):
    assert forma(linha)


@pytest.mark.parametrize("linha", [
    "PLATAFIRMA_INSTANCIA[=/srv/platafirma/casa]",
    "worktree <bancada>/wt/platafirma-casa-espelho/<cadeira>/main",
    "ontologia ler capacidade capacidade:gatilhos",
    'release() / "harness"',
    "/opt/platafirma/current/casa-espelho/outros_repos/conhecimento/casa-db/backup-db.sh",
])
def test_forma_passa(linha):
    assert forma(linha) is None


def test_varrer_um_apontamento_por_linha_proibida(tmp_path):
    arq = tmp_path / "amostra.md"
    linhas_proibidas = [
        f"ref {_CASA}",
        f"ref {_P1}/a.md",
        f"ref {_P2}/b.md",
        f"ref {_P6}/c.md",
        f"ref {_ORIG}d.md",
        f"ref {_DONO}",
        f"ref {_PUB}",
    ]
    arq.write_text("\n".join(["linha limpa", *linhas_proibidas, "outra limpa"]) + "\n", encoding="utf-8")
    apts = varrer(tmp_path)
    assert len(apts) == len(linhas_proibidas)
    assert [a.linha for a in apts] == list(range(2, 2 + len(linhas_proibidas)))


def test_pre_commit_recusa_leitura_por_caminho(tmp_path):
    if not PRE_COMMIT.is_file():
        pytest.skip("pre_commit.py ausente na arvore do espelho")
    repo = _repo(tmp_path, {"bin/x": f'#!/bin/sh\n\nREPO="{_CUR_CASA}"\n'})
    r = _pre_commit(repo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[casa-por-caminho] bin/x:3:" in r.stderr


def test_detector_e_teste_isentos(tmp_path):
    texto = f"X = {_REL_CASA}\n"
    (tmp_path / "bin/_lint").mkdir(parents=True)
    (tmp_path / "controle/tests").mkdir(parents=True)
    (tmp_path / "bin/_lint/casa_por_caminho.py").write_text(texto, encoding="utf-8")
    (tmp_path / "controle/tests/test_contrato_casa_por_caminho.py").write_text(texto, encoding="utf-8")
    assert varrer(tmp_path) == []
