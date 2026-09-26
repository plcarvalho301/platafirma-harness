"""Contrato de hooks/pre-push pós card #3150 (comentário A): mede a REV empurrada
no venv da CHAVE do registro (harness), não em `uvx --with redis` isolado; grava e
reaproveita veredito por (hash da árvore, chave); distingue "não medido" (chave
ausente, lock ausente) de "vermelho real" (barra o push); nomeia os reprovados.

Ponta a ponta de verdade: instala o hook num clone comum e dispara `git push` real
contra um forge bare local — não chama o script por fora, é o próprio git que
decide invocar o hook, exatamente como em produção.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK = REPO_ROOT / "hooks" / "pre-push"
LIB_VENV = REPO_ROOT / "lib" / "venv.sh"
REGISTRO = REPO_ROOT / "bin" / "_release" / "registro.py"

LOCK_SEM_DEP = "# fixture: venv vazio, sem dependência (uv venv puro, sem rede)\n"

TESTE_OK = "def test_ok():\n    assert True\n"
TESTE_VERMELHO = "def test_ok():\n    assert False, 'quebrou de propósito'\n"


def _python_de_sistema() -> str:
    casa = str(Path.home())
    for candidato in ("/usr/bin/python3.12", "/usr/bin/python3", sys.executable):
        if candidato and os.path.isabs(candidato) and os.access(candidato, os.X_OK) \
                and not candidato.startswith(casa):
            return candidato
    pytest.skip("nenhum python de sistema fora do HOME para construir venv de fixture")


def _git(cwd: Path, *args: str, env=None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                           check=check, env=env)


class Ambiente:
    def __init__(self, tmp_path: Path, python_exe: str):
        self.tmp = tmp_path
        self.wt = tmp_path / "wt"
        self.forge = tmp_path / "forge.git"
        self.wt.mkdir()
        subprocess.run(["git", "init", "-q", "--bare", str(self.forge)],
                        check=True, capture_output=True)
        _git(self.wt, "init", "-q", "-b", "main")
        _git(self.wt, "config", "user.name", "fixture")
        _git(self.wt, "config", "user.email", "fixture@test.local")
        _git(self.wt, "remote", "add", "origin", str(self.forge))

        # o proprio git so aceita hook em .git/hooks/<nome>, executavel
        hooks_dir = self.wt / ".git" / "hooks"
        hooks_dir.mkdir(exist_ok=True)
        alvo = hooks_dir / "pre-push"
        alvo.write_text(HOOK.read_text(encoding="utf-8"), encoding="utf-8")
        alvo.chmod(0o755)
        # o hook resolve $AQUI/../lib e $AQUI/../bin a partir de ONDE ELE MORA
        # ($AQUI = dirname do proprio script = .git/hooks aqui) — entao os irmaos
        # de hooks/ tem que estar em .git/, nao em .git/hooks/. Symlink pra arvore
        # REAL do repo (lib/venv.sh, bin/_release/registro.py), nao uma copia.
        (self.wt / ".git" / "lib").symlink_to(REPO_ROOT / "lib")
        (self.wt / ".git" / "bin").symlink_to(REPO_ROOT / "bin")

        (self.wt / "controle" / "tests").mkdir(parents=True)
        (self.wt / "controle" / "tests" / "VERDES").write_text(
            "tests/test_fixture.py\n", encoding="utf-8")
        (self.wt / "controle" / "tests" / "test_fixture.py").write_text(TESTE_OK, encoding="utf-8")
        (self.wt / "venvs.json").write_text(
            json.dumps({"harness": {"familia": "fixture", "lock": "lock.txt"}}), encoding="utf-8")
        (self.wt / "lock.txt").write_text(LOCK_SEM_DEP, encoding="utf-8")
        _git(self.wt, "add", "-A")
        _git(self.wt, "commit", "-q", "-m", "fixture inicial")
        _git(self.wt, "push", "-q", "-u", "origin", "main")

        self.env = dict(os.environ)
        self.env["PF_RELEASE_RAIZ"] = str(tmp_path / "opt")
        self.env["PLATAFIRMA_INSTANCIA"] = str(tmp_path / "srv")
        self.env["PLATAFIRMA_VENVS"] = str(self.wt / "venvs.json")
        self.env["PLATAFIRMA_PYTHON"] = python_exe

    def push(self) -> subprocess.CompletedProcess:
        return _git(self.wt, "push", "origin", "main", env=self.env, check=False)

    def commit(self, rel: str, texto: str) -> str:
        caminho = self.wt / rel
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(texto, encoding="utf-8")
        _git(self.wt, "add", "-A")
        _git(self.wt, "commit", "-q", "-m", f"fixture: {rel}")
        r = _git(self.wt, "rev-parse", "HEAD")
        return r.stdout.strip()

    def squash_tree_atual_em_novo_commit(self) -> str:
        """Novo commit com a MESMA árvore do HEAD atual — simula squash-merge
        (comentário do card: hash de commit muda, hash da árvore não)."""
        tree = _git(self.wt, "rev-parse", "HEAD^{tree}").stdout.strip()
        parent = _git(self.wt, "rev-parse", "HEAD").stdout.strip()
        r = subprocess.run(["git", "commit-tree", tree, "-p", parent, "-m", "squash fixture"],
                            cwd=str(self.wt), capture_output=True, text=True, check=True,
                            env=dict(self.env, GIT_AUTHOR_NAME="fixture", GIT_AUTHOR_EMAIL="f@test",
                                     GIT_COMMITTER_NAME="fixture", GIT_COMMITTER_EMAIL="f@test"))
        novo = r.stdout.strip()
        _git(self.wt, "update-ref", "refs/heads/main", novo)
        return novo


@pytest.fixture()
def amb(tmp_path):
    return Ambiente(tmp_path, _python_de_sistema())


def test_push_verde_mede_no_venv_da_chave(amb):
    amb.commit("outro.txt", "muda algo\n")
    r = amb.push()
    assert r.returncode == 0, r.stdout + r.stderr
    saida = r.stdout + r.stderr
    assert "harness-" in saida
    assert "verde" in saida
    assert "uvx" not in saida


def test_squash_reaproveita_veredito_pela_arvore(amb):
    amb.commit("outro.txt", "muda algo\n")
    r1 = amb.push()
    assert r1.returncode == 0, r1.stdout + r1.stderr

    amb.squash_tree_atual_em_novo_commit()
    r2 = amb.push()
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "reaproveitado" in (r2.stdout + r2.stderr)


def test_push_vermelho_e_barrado_e_nomeia_o_teste(amb):
    amb.commit("controle/tests/test_fixture.py", TESTE_VERMELHO)
    r = amb.push()
    assert r.returncode != 0, r.stdout + r.stderr
    assert "BASELINE VERDE QUEBROU" in r.stderr
    assert "test_fixture::test_ok" in r.stderr


def test_push_vermelho_reaproveita_o_bloqueio(amb):
    amb.commit("controle/tests/test_fixture.py", TESTE_VERMELHO)
    r1 = amb.push()
    assert r1.returncode != 0, r1.stdout + r1.stderr

    amb.squash_tree_atual_em_novo_commit()
    r2 = amb.push()
    assert r2.returncode != 0, r2.stdout + r2.stderr
    assert "veredito reaproveitado" in r2.stderr


def test_chave_ausente_nao_medido_deixa_passar(amb):
    (amb.wt / "venvs.json").write_text("{}", encoding="utf-8")
    amb.commit("venvs.json", "{}")
    r = amb.push()
    assert r.returncode == 0, r.stdout + r.stderr
    assert "não medido" in r.stderr
