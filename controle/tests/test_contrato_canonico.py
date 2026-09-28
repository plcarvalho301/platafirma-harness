"""Contrato da trava «canônico não cita minuta» (ordem do dono, 28/09/2026; régua arq:0028).

Prova: o pre-commit recusa linha acrescentada a ADR (`decisions/*.md`) ou spec (`spec_*.md`)
que cite minuta por número ou pela decisão da minuta, nomeando arquivo e linha; passa a
menção da minuta como instrumento; não trava a edição de outro trecho quando a citação é
legada; não olha documento que não é canônico. E `minuta formalizar` recusa minuta cuja
Decisão já cite minuta. Não prova: o hook instalado nos clones (core.hooksPath).
"""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[2]
PRE_COMMIT = HARNESS / "bin" / "_lint" / "pre_commit.py"
FORMALIZAR = HARNESS / "bin" / "_minuta" / "formalizar"

sys.path.insert(0, str(HARNESS / "bin"))
from _lint.canonico import citacao, e_canonico  # noqa: E402

IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
ADR = "macro-global/decisions/0200-exemplo.md"


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, **IDENT})


def _repo(tmp_path, arquivos, commitar=False):
    repo = tmp_path / "repo"
    repo.mkdir()
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
    "Decisão tomada fechando a minuta 0038.",
    "Conforme minuta 0038, A1, a espécie fica.",
    "As questões resolvidas na minuta ficam assim.",
    "Ver minuta nº 12.",
    "minutas 0012 e 0013",
])
def test_citacao_pega(linha):
    assert citacao(linha)


@pytest.mark.parametrize("linha", [
    "A minuta é deliberação em trânsito.",
    "Referencial: arq:NNNN, spec_<slug>, minuta NNNN",
    "Leia com `minuta ler 0038` antes de circular.",
    "O verbo minuta formalizar cria o canônico vazio.",
])
def test_instrumento_passa(linha):
    assert citacao(linha) is None


def test_e_canonico():
    assert e_canonico(ADR)
    assert e_canonico("ont/decisions/0001-x.md")
    assert e_canonico("docs/spec_verbo-minuta.md")
    assert not e_canonico("minuta/0038-processamento-de-texto.md")
    assert not e_canonico("docs/guia-x.md")


def test_pre_commit_recusa_adr_que_cita_minuta(tmp_path):
    repo = _repo(tmp_path, {ADR: "# 0200 — Exemplo\n\nDecisão fechando a minuta 0038.\n"})
    r = _pre_commit(repo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert f"[canonico] {ADR}:3:" in r.stderr


def test_pre_commit_recusa_spec_que_cita_minuta(tmp_path):
    repo = _repo(tmp_path, {"docs/spec_x.md": "# X\n\nResolvidas na minuta as três.\n"})
    r = _pre_commit(repo)
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[canonico] docs/spec_x.md:3:" in r.stderr


def test_pre_commit_passa_canonico_limpo(tmp_path):
    repo = _repo(tmp_path, {ADR: "# 0200 — Exemplo\n\nDecisão do dono, 28/09/2026.\n"})
    r = _pre_commit(repo)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pre_commit_nao_olha_minuta_nem_documento_comum(tmp_path):
    repo = _repo(tmp_path, {"minuta/0040-x.md": "Ver minuta 0038.\n",
                            "docs/guia.md": "Ver minuta 0038.\n"})
    r = _pre_commit(repo)
    assert r.returncode == 0, r.stdout + r.stderr


def test_pre_commit_citacao_legada_nao_trava_outro_trecho(tmp_path):
    repo = _repo(tmp_path, {ADR: "# 0200\n\nlegado: minuta 0038.\n"}, commitar=True)
    (repo / ADR).write_text("# 0200\n\nlegado: minuta 0038.\n\nNova linha limpa.\n",
                            encoding="utf-8")
    _git(repo, "add", "-A")
    r = _pre_commit(repo)
    assert r.returncode == 0, r.stdout + r.stderr


def _formalizar_mod():
    loader = importlib.machinery.SourceFileLoader("formalizar_mod", str(FORMALIZAR))
    spec = importlib.util.spec_from_loader("formalizar_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_formalizar_acha_citacao_na_decisao():
    mod = _formalizar_mod()
    texto = ("# 0041 — X\n\nConvocadas: dados\n\n## Contexto\n\nminuta 0038 citada aqui passa\n\n"
             "## Decisão\n\nFica como na minuta 0038.\n")
    assert mod.decisao_cita_minuta(texto) == (11, "minuta 0038")


def test_formalizar_decisao_limpa_passa():
    mod = _formalizar_mod()
    texto = "# 0041 — X\n\n## Decisão\n\nDecisão do dono, 28/09/2026.\n"
    assert mod.decisao_cita_minuta(texto) is None
