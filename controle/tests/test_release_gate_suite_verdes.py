"""Contrato do estágio 1b da esteira (card #3150, comentário C1): `release promover`
passa a rodar a suíte de controle/tests/VERDES no venv da chave "harness" — a MESMA
suíte, o mesmo venv e o mesmo veredito memoizado que hooks/pre-push já usa — e não
só `conferir verbo` (estrutura, não comportamento). Suíte reprovada barra a
promoção com exit 4 e current intacto; suíte que já foi medida (mesma árvore,
mesma chave) reaproveita sem rodar de novo; `release estado <familia>` passa a
mostrar o último veredito do gate.

A família de teste tem que se chamar "platafirma-harness" (FAMILIA_BIN é constante
no script) para o gate ligar — o que também liga gate_conferir_verbo, reiniciar_porta
e publicar_abertura_da_familia; cada um deles no-opa graciosamente sem os arquivos
que exigem (bin/_release/conferir, abertura/), e PF_RELEASE_PORTA=0 desliga o
restart real da porta.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "release"

LOCK_SEM_DEP = "# fixture: venv vazio, sem dependência\n"
TESTE_OK = "def test_ok():\n    assert True\n"
TESTE_VERMELHO = "def test_ok():\n    assert False, 'quebrou de propósito'\n"


def _python_de_sistema() -> str:
    casa = str(Path.home())
    for candidato in ("/usr/bin/python3.12", "/usr/bin/python3", sys.executable):
        if candidato and os.path.isabs(candidato) and os.access(candidato, os.X_OK) \
                and not candidato.startswith(casa):
            return candidato
    pytest.skip("nenhum python de sistema fora do HOME para construir venv de fixture")


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True)


def _escreve(base: Path, rel: str, texto: str) -> None:
    caminho = base / rel
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")


def _commit(wt: Path, msg: str) -> str:
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", msg)
    r = subprocess.run(["git", "-C", str(wt), "rev-parse", "HEAD"],
                        capture_output=True, text=True, check=True)
    return r.stdout.strip()


class Ambiente:
    FAMILIA = "platafirma-harness"

    def __init__(self, tmp_path: Path, python_exe: str, teste_conteudo: str):
        self.tmp = tmp_path
        self.wt = tmp_path / "wt" / self.FAMILIA
        self.forge = tmp_path / "forge" / f"{self.FAMILIA}.git"
        self.wt.mkdir(parents=True)
        self.forge.parent.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", str(self.forge)],
                        check=True, capture_output=True)
        _git(self.wt, "init", "-q", "-b", "main")
        _git(self.wt, "config", "user.name", "fixture")
        _git(self.wt, "config", "user.email", "fixture@test.local")
        _escreve(self.wt, "lock.txt", LOCK_SEM_DEP)
        _escreve(self.wt, "controle/tests/VERDES", "tests/test_fixture.py\n")
        _escreve(self.wt, "controle/tests/test_fixture.py", teste_conteudo)
        self.sha1 = _commit(self.wt, "fixture inicial")
        _git(self.wt, "remote", "add", "origin", str(self.forge))
        _git(self.wt, "push", "-q", "-u", "origin", "main")

        stub_bin = tmp_path / "stub-bin"
        stub_bin.mkdir()
        acervo_stub = stub_bin / "acervo"
        acervo_stub.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"$1\" = ler ] && [ \"$2\" = casa ] && [ \"$3\" = stack ]; then echo '[]'; exit 0; fi\n"
            "exit 1\n", encoding="utf-8")
        acervo_stub.chmod(0o755)

        self.env = dict(os.environ)
        self.env["PF_RELEASE_RAIZ"] = str(tmp_path / "opt")
        self.env["PLATAFIRMA_INSTANCIA"] = str(tmp_path / "srv")
        self.env["PLATAFIRMA_FAMILIAS"] = str(tmp_path / "familias.json")
        self.env["PLATAFIRMA_VENVS"] = str(tmp_path / "venvs.json")
        self.env["PLATAFIRMA_TERCEIROS"] = str(tmp_path / "terceiros.json")
        self.env["PLATAFIRMA_PYTHON"] = python_exe
        self.env["PF_RELEASE_PORTA"] = "0"
        Path(self.env["PLATAFIRMA_FAMILIAS"]).write_text(
            json.dumps({self.FAMILIA: str(self.forge)}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_VENVS"]).write_text(
            json.dumps({"harness": {"familia": self.FAMILIA, "lock": "lock.txt"}}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_TERCEIROS"]).write_text("{}", encoding="utf-8")
        self.env["PATH"] = f"{stub_bin}{os.pathsep}" + self.env.get("PATH", "")

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(SCRIPT), *args], env=self.env,
                               capture_output=True, text=True, timeout=90)


@pytest.fixture()
def amb_verde(tmp_path):
    return Ambiente(tmp_path, _python_de_sistema(), TESTE_OK)


@pytest.fixture()
def amb_vermelho(tmp_path):
    return Ambiente(tmp_path, _python_de_sistema(), TESTE_VERMELHO)


def test_promover_roda_a_suite_e_sobe_quando_verde(amb_verde):
    r = amb_verde.run("promover", amb_verde.FAMILIA)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "suite:     verde" in r.stdout
    assert "no ar:" in r.stdout

    est = amb_verde.run("estado", amb_verde.FAMILIA)
    assert est.returncode == 0, est.stdout + est.stderr
    assert "gate: passou" in est.stdout


def test_promover_barra_quando_suite_vermelha_current_intacto(amb_vermelho):
    r = amb_vermelho.run("promover", amb_vermelho.FAMILIA)
    assert r.returncode == 4, r.stdout + r.stderr
    assert "reprova na suite VERDES" in r.stderr
    assert "test_fixture" in r.stderr

    est = amb_vermelho.run("estado", amb_vermelho.FAMILIA)
    assert est.returncode == 1, est.stdout + est.stderr  # sem current (nunca promoveu)


def test_segunda_promocao_mesma_arvore_reaproveita_veredito(amb_verde):
    # mesma ÁRVORE (tree hash), sha diferente — o caso que a chave por tree-hash
    # existe para cobrir (squash-merge): commit vazio não move um bit do conteúdo.
    r1 = amb_verde.run("promover", amb_verde.FAMILIA)
    assert r1.returncode == 0, r1.stdout + r1.stderr

    _git(amb_verde.wt, "commit", "-q", "--allow-empty", "-m", "fixture: segundo commit, mesma arvore")
    r = subprocess.run(["git", "-C", str(amb_verde.wt), "rev-parse", "HEAD"],
                        capture_output=True, text=True, check=True)
    sha2 = r.stdout.strip()
    _git(amb_verde.wt, "push", "-q", "origin", "main")

    r2 = amb_verde.run("promover", amb_verde.FAMILIA, sha2)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "suite:     verde (reaproveitado)" in r2.stdout
