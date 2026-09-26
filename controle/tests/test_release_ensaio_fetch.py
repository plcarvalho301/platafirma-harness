"""Contrato do fetch em `release promover --ensaio` (card #3150, comentário C7):
antes, o espelho já existente pulava o fetch em ensaio ("sem fetch em ensaio") — e
uma rev recém-mesclada só aparecia depois de um fetch, então o ensaio sempre dizia
"rev não resolve no forge" mesmo para um sha real, recém-empurrado. Medido de
verdade (comentário do card, passo 1): 2 falhas seguidas de `release promover` numa
promoção real, exatamente por isso.

Prova aqui: promove uma vez (materializa o espelho), empurra um commit NOVO pro
forge sem passar por este processo, e confere que `--ensaio` (sem sha explícito,
resolvendo origin/main) ACHA o commit novo — teve fetch. Confere também que uma rev
que de fato não existe sai 1 ("varrido:"), não 2 ("erro:") — rev ausente não é erro
de uso.
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
            json.dumps({"fixture": str(self.forge)}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_VENVS"]).write_text("{}", encoding="utf-8")
        Path(self.env["PLATAFIRMA_TERCEIROS"]).write_text("{}", encoding="utf-8")
        self.env["PATH"] = f"{stub_bin}{os.pathsep}" + self.env.get("PATH", "")

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(SCRIPT), *args], env=self.env,
                               capture_output=True, text=True, timeout=90)

    def commit_sem_promover(self, arquivos: dict) -> str:
        """Empurra pro forge SEM passar por release promover — simula outra fita
        mesclando um PR enquanto o espelho local já existe."""
        for rel, texto in arquivos.items():
            _escreve(self.wt, rel, texto)
        sha = _commit(self.wt, f"fixture: {', '.join(arquivos)}")
        _git(self.wt, "push", "-q", "origin", "main")
        return sha


@pytest.fixture()
def amb(tmp_path):
    return Ambiente(tmp_path, _python_de_sistema())


def test_ensaio_busca_o_forge_mesmo_com_espelho_existente(amb):
    # materializa o espelho (1a promoção real)
    r0 = amb.run("promover", "fixture")
    assert r0.returncode == 0, r0.stdout + r0.stderr

    # sha novo no forge, SEM passar por release (não deixou o espelho com ele)
    sha2 = amb.commit_sem_promover({"README.md": "mudou depois do espelho existir\n"})

    r = amb.run("promover", "fixture", "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "sem fetch em ensaio" not in (r.stdout + r.stderr)
    assert sha2[:7] in r.stdout


def test_rev_inexistente_sai_1_nao_2(amb):
    r0 = amb.run("promover", "fixture")
    assert r0.returncode == 0, r0.stdout + r0.stderr

    r = amb.run("promover", "fixture", "0" * 40, "--ensaio")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "varrido:" in r.stderr
