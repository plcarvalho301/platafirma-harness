"""Contrato de `teste rodar` em bloco fixo, com veredito reaproveitado (card #3150 passo 3).

Prova: o pytest cru vai ao log da instancia; a tela traz a contagem, os reprovados
nomeados pelo junit.xml e a alca do log; a mesma arvore medida de novo devolve
«veredito reaproveitado» sem rodar; mudar a arvore mede de novo. Tambem que `teste` acha
a bancada wt/<repo>/<cadeira>/<card> (antes caia no clone base). Nao prova: stack node,
--chave (mesmo caminho de codigo, outro runner).
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

TESTE_BIN = Path(__file__).resolve().parents[2] / "bin" / "teste"
IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def _git(*args, cwd=None):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, **IDENT})


def _python():
    for p in ("/usr/bin/python3.12", "/usr/bin/python3", sys.executable):
        if p and os.access(p, os.X_OK):
            return p
    pytest.skip("sem python de sistema")


@pytest.fixture()
def bancada(tmp_path):
    if not shutil.which("uv"):
        pytest.skip("uv ausente")
    b = tmp_path / "bancada"
    base = b / "demo"
    base.mkdir(parents=True)
    _git("init", "-q", "-b", "main", cwd=base)
    (base / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0"\nrequires-python = ">=3.10"\ndependencies = []\n')
    (base / ".gitignore").write_text(".venv/\n__pycache__/\n")
    (base / "tests").mkdir()
    (base / "tests" / "test_ok.py").write_text("def test_ok():\n    assert True\n")
    _git("add", "-A", cwd=base)
    _git("commit", "-q", "-m", "semente", cwd=base)
    wt = b / "wt" / "demo" / "ti" / "1-x"
    _git("worktree", "add", "-q", "-b", "fabrica/1-x", str(wt), cwd=base)
    return tmp_path, b, wt


def _teste(tmp_path, b, *args):
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(Path.home()),       # cache do uv (pytest ja baixado), nada mais
        "PLATAFIRMA_BANCADA": str(b),
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "instancia"),
        "PF_RELEASE_RAIZ": str(tmp_path / "release"),
        "PF_CADEIRA": "ti",
        "PF_TESTE_PYTHON": _python(),
        **IDENT,
    }
    return subprocess.run([str(TESTE_BIN), *args], env=env, capture_output=True, text=True,
                          timeout=240)


def test_bloco_fixo_verde_e_reaproveitado_na_mesma_arvore(bancada):
    tmp_path, b, wt = bancada
    r = _teste(tmp_path, b, "rodar", "demo")
    assert r.returncode == 0, r.stdout + r.stderr
    linhas = r.stdout.strip().splitlines()
    assert linhas[0].startswith("suite VERDE: demo (python)"), r.stdout
    assert "passed" in linhas[0]
    assert any(l.startswith("saida inteira:") for l in linhas)
    assert len(linhas) <= 8, r.stdout
    assert "test session starts" not in r.stdout      # pytest cru foi ao log

    r2 = _teste(tmp_path, b, "rodar", "demo")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "veredito reaproveitado" in r2.stdout, r2.stdout


def test_vermelho_nomeia_o_reprovado_e_arvore_nova_mede_de_novo(bancada):
    tmp_path, b, wt = bancada
    assert _teste(tmp_path, b, "rodar", "demo").returncode == 0
    (wt / "tests" / "test_ok.py").write_text("def test_ok():\n    assert False, 'quebrou'\n")
    r = _teste(tmp_path, b, "rodar", "demo")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "reaproveitado" not in r.stdout
    assert "suite VERMELHA" in r.stdout
    assert "reprovado:" in r.stdout and "test_ok" in r.stdout
