"""Contrato do leitor único bin/_release/registro.py e de `teste rodar/detectar
--chave` (card #3150 passos 2-3, comentário B1): --chave usa o MESMO construtor de
venv que `release promover` (lock+python -> hash -> venv em
$PF_RELEASE_RAIZ/venv/<chave>-<hash>), não a escada heurística; ambiente construído
uma vez e reaproveitado; chave desconhecida sai 2 com a lista; chave sem lock
declarado (ou lock ausente na árvore do clone) sai 5.

Isola bancada, registro de venvs e a raiz de venv (PF_RELEASE_RAIZ) num tmp_path por
teste — mesmo desenho de test_release_abertura.py, agora sobre bin/teste. O lock de
fixture é só comentário: `construir_venv` (lib/venv.sh) pula o pip install e faz
apenas `uv venv`, sem rede.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTE = REPO_ROOT / "bin" / "teste"
REGISTRO = REPO_ROOT / "bin" / "_release" / "registro.py"

LOCK_SEM_DEP = "# fixture: venv vazio, sem dependência (uv venv puro, sem rede)\n"


def _python_de_sistema() -> str:
    """Um python de sistema fora do HOME — python_gerenciado() em lib/venv.sh
    recusa interpretador sob $HOME ou gerenciado pelo uv."""
    casa = str(Path.home())
    for candidato in ("/usr/bin/python3.12", "/usr/bin/python3", sys.executable):
        if candidato and os.path.isabs(candidato) and os.access(candidato, os.X_OK) \
                and not candidato.startswith(casa):
            return candidato
    pytest.skip("nenhum python de sistema fora do HOME para construir venv de fixture")


class Bancada:
    """wt/alvo/cadeira com pyproject-like fixture e registro/venvs.json isolado."""

    def __init__(self, tmp_path: Path, python_exe: str):
        self.tmp = tmp_path
        bancada = tmp_path / "bancada"
        self.clone = bancada / "wt" / "alvo" / "cadeira"
        self.clone.mkdir(parents=True)
        (self.clone / ".git").mkdir()  # só a marca que bancada_de() confere
        sub = self.clone / "subarvore"
        sub.mkdir()
        (sub / "lock.txt").write_text(LOCK_SEM_DEP, encoding="utf-8")
        (sub / "test_fixture.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
        (sub / "test_fixture_vermelho.py").write_text(
            "def test_falha():\n    assert False\n", encoding="utf-8")

        registro = {
            "chave-fixture": {"familia": "alvo", "lock": "subarvore/lock.txt", "teste": "subarvore"},
            "sem-lock": {"familia": "alvo", "lock": ""},
        }
        self.venvs_json = tmp_path / "venvs.json"
        self.venvs_json.write_text(json.dumps(registro), encoding="utf-8")

        self.env = dict(os.environ)
        self.env["PLATAFIRMA_BANCADA"] = str(bancada)
        self.env["PLATAFIRMA_VENVS"] = str(self.venvs_json)
        self.env["PF_RELEASE_RAIZ"] = str(tmp_path / "opt")
        self.env["PLATAFIRMA_PYTHON"] = python_exe
        self.env["PF_CADEIRA"] = "cadeira"
        self.env.pop("PF_SESSAO", None)

    def detectar(self, *args: str, timeout: int = 90) -> subprocess.CompletedProcess:
        return subprocess.run([str(TESTE), "detectar", *args], env=self.env,
                               capture_output=True, text=True, timeout=timeout)

    def rodar(self, *args: str, timeout: int = 90) -> subprocess.CompletedProcess:
        return subprocess.run([str(TESTE), "rodar", *args], env=self.env,
                               capture_output=True, text=True, timeout=timeout)


@pytest.fixture()
def banc(tmp_path):
    return Bancada(tmp_path, _python_de_sistema())


def test_chave_desconhecida_sai_2_com_a_lista(banc):
    r = banc.detectar("alvo", "--chave", "nao-existe")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "nao-existe" in r.stderr
    assert "chave-fixture" in r.stderr


def test_chave_sem_lock_sai_5(banc):
    r = banc.detectar("alvo", "--chave", "sem-lock")
    assert r.returncode == 5, r.stdout + r.stderr


def test_chave_constroi_e_depois_reaproveita(banc):
    r1 = banc.detectar("alvo", "--chave", "chave-fixture")
    assert r1.returncode == 0, r1.stdout + r1.stderr
    assert "construido" in r1.stderr
    assert "chave-fixture-" in r1.stdout

    r2 = banc.detectar("alvo", "--chave", "chave-fixture")
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "reaproveitado" in r2.stderr


def test_rodar_chave_suite_verde(banc):
    r = banc.rodar("alvo", "subarvore/test_fixture.py", "--chave", "chave-fixture")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "suite VERDE" in r.stdout


def test_rodar_chave_suite_vermelha(banc):
    r = banc.rodar("alvo", "subarvore/test_fixture_vermelho.py", "--chave", "chave-fixture")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "suite VERMELHA" in r.stdout


def _env_registro(tmp_path: Path, dados: dict) -> dict:
    caminho = tmp_path / "v.json"
    caminho.write_text(json.dumps(dados), encoding="utf-8")
    env = dict(os.environ)
    env["PLATAFIRMA_VENVS"] = str(caminho)
    return env


def test_registro_stack_desconhecida(tmp_path):
    env = _env_registro(tmp_path, {"a": {"familia": "f", "lock": "x"}})
    r = subprocess.run([sys.executable, str(REGISTRO), "b"], env=env, capture_output=True, text=True)
    assert r.returncode == 2
    assert "b" in r.stderr and "a" in r.stderr


def test_registro_sem_lock(tmp_path):
    env = _env_registro(tmp_path, {"a": {"familia": "f", "lock": ""}})
    r = subprocess.run([sys.executable, str(REGISTRO), "a"], env=env, capture_output=True, text=True)
    assert r.returncode == 5


def test_registro_json_ilegivel(tmp_path):
    caminho = tmp_path / "v.json"
    caminho.write_text("nao e json", encoding="utf-8")
    env = dict(os.environ)
    env["PLATAFIRMA_VENVS"] = str(caminho)
    r = subprocess.run([sys.executable, str(REGISTRO), "a"], env=env, capture_output=True, text=True)
    assert r.returncode == 3


def test_registro_familia_lista_stacks(tmp_path):
    env = _env_registro(tmp_path, {
        "a": {"familia": "f1", "lock": "x", "teste": "sub"},
        "b": {"familia": "f2", "lock": "y"},
        "_nota": "comentario, fora da lista",
    })
    r = subprocess.run([sys.executable, str(REGISTRO), "--familia", "f1"], env=env,
                        capture_output=True, text=True)
    assert r.returncode == 0
    assert r.stdout.strip() == "a\tx\tsub"
