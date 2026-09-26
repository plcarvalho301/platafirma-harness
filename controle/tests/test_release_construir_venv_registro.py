"""Contrato de `release promover <familia> <sha>` construindo venv pelo leitor único
bin/_release/registro.py (card #3150 passo 2): construir_venvs deixou de reler o
JSON com jq por conta própria e passa a chamar o mesmo leitor que --chave usa.
Prova que a promoção de uma família comum (não "abertura", sem stack de deploy)
ainda constrói o venv declarado e reaproveita quando o lock não mudou.

Isola um forge bare local e registro/{familias,venvs,terceiros}.json sob tmp_path
— mesmo desenho de test_release_abertura.py. Stub de `acervo` (só `ler casa stack`,
lista vazia) porque ler_stacks_da_familia chama esse verbo antes de tocar venv.
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

LOCK_SEM_DEP = "# fixture: venv vazio, sem dependência (uv venv puro, sem rede)\n"


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
    def __init__(self, tmp_path: Path, python_exe: str):
        self.tmp = tmp_path
        self.wt = tmp_path / "wt" / "fixture"
        self.forge = tmp_path / "forge" / "fixture.git"
        self.wt.mkdir(parents=True)
        self.forge.parent.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", str(self.forge)],
                        check=True, capture_output=True)
        _git(self.wt, "init", "-q", "-b", "main")
        _git(self.wt, "config", "user.name", "fixture")
        _git(self.wt, "config", "user.email", "fixture@test.local")
        _escreve(self.wt, "lock.txt", LOCK_SEM_DEP)
        self.sha1 = _commit(self.wt, "fixture inicial")
        _git(self.wt, "remote", "add", "origin", str(self.forge))
        _git(self.wt, "push", "-q", "-u", "origin", "main")

        stub_bin = tmp_path / "stub-bin"
        stub_bin.mkdir()
        acervo_stub = stub_bin / "acervo"
        acervo_stub.write_text(
            "#!/usr/bin/env bash\n"
            "if [ \"$1\" = ler ] && [ \"$2\" = casa ] && [ \"$3\" = stack ]; then\n"
            "  echo '[]'\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n",
            encoding="utf-8",
        )
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
            json.dumps({"fixture": str(self.forge)}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_VENVS"]).write_text(
            json.dumps({"fx": {"familia": "fixture", "lock": "lock.txt"}}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_TERCEIROS"]).write_text("{}", encoding="utf-8")
        self.env["PATH"] = f"{stub_bin}{os.pathsep}" + self.env.get("PATH", "")

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(SCRIPT), *args], env=self.env,
                               capture_output=True, text=True, timeout=90)

    def commit(self, arquivos: dict) -> str:
        for rel, texto in arquivos.items():
            _escreve(self.wt, rel, texto)
        sha = _commit(self.wt, f"fixture: {', '.join(arquivos)}")
        _git(self.wt, "push", "-q", "origin", "main")
        return sha


@pytest.fixture()
def amb(tmp_path):
    return Ambiente(tmp_path, _python_de_sistema())


def test_promover_constroi_venv_pelo_registro(amb):
    r = amb.run("promover", "fixture")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "fx-" in r.stdout and "construído" in r.stdout
    assert "no ar:" in r.stdout


def test_segunda_promocao_com_mesmo_lock_reaproveita_o_venv(amb):
    r1 = amb.run("promover", "fixture")
    assert r1.returncode == 0, r1.stdout + r1.stderr

    sha2 = amb.commit({"README.md": "muda algo fora do lock\n"})
    r2 = amb.run("promover", "fixture", sha2)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    assert "já construído" in r2.stdout
