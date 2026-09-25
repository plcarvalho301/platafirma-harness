"""Contrato de `release promover abertura --so-caderno` (card #3141 passo 7): o
gatilho AUTOMATICO do timer abertura-caderno so promove quando o diff entre o current
publicado e origin/main, restrito a abertura/, e SO caderno.md de cadeira/chapeu;
qualquer outro caminho no diff barra com exit 4 e a lista (current intacto); nada
mudando em abertura/, exit 0 sem publicar (current intacto).

Isola um forge bare local (sem rede) e materializa PROD_RAIZ/PONTOS/ABERTURA_DIR sob um
tmp_path por teste — mesmo desenho de testes/test_release_lote2.sh (env vars de
lib/raizes.sh), em python porque o card pede o arquivo em controle/tests/.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "release"
PUBLICAR_ABERTURA = REPO_ROOT / "bin" / "publicar-abertura"


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
    """Forge bare local + registro de familias + PROD_RAIZ/PONTOS/ABERTURA_DIR isolados."""

    def __init__(self, tmp_path: Path):
        self.tmp = tmp_path
        self.wt = tmp_path / "wt" / "platafirma-harness"
        self.forge = tmp_path / "forge" / "platafirma-harness.git"
        self.wt.mkdir(parents=True)
        self.forge.parent.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", str(self.forge)],
                        check=True, capture_output=True)
        _git(self.wt, "init", "-q", "-b", "main")
        _git(self.wt, "config", "user.name", "fixture")
        _git(self.wt, "config", "user.email", "fixture@test.local")
        # snapshot minimo que validar_snapshot() de bin/publicar-abertura exige
        _escreve(self.wt, "abertura/aliases.json", "{}\n")
        _escreve(self.wt, "abertura/rotas-chapeu.json", "{}\n")
        _escreve(self.wt, "abertura/dono.md", "# dono\nfixture.\n")
        _escreve(self.wt, "abertura/oficio.md", "# oficio\nfixture.\n")
        _escreve(self.wt, "abertura/ti/persona.md", "# ti\nfixture.\n")
        _escreve(self.wt, "abertura/ti/construcao/caderno.md", "# caderno construcao\nv1\n")
        self.sha1 = _commit(self.wt, "fixture inicial")
        _git(self.wt, "remote", "add", "origin", str(self.forge))
        _git(self.wt, "push", "-q", "-u", "origin", "main")

        self.env = dict(os.environ)
        self.env["PF_RELEASE_RAIZ"] = str(tmp_path / "opt")
        self.env["PLATAFIRMA_INSTANCIA"] = str(tmp_path / "srv")
        self.env["PF_ABERTURA_DIR"] = str(tmp_path / "srv" / "var" / "abertura-publicada")
        self.env["PLATAFIRMA_FAMILIAS"] = str(tmp_path / "familias.json")
        self.env["PLATAFIRMA_VENVS"] = str(tmp_path / "venvs.json")
        self.env["PLATAFIRMA_TERCEIROS"] = str(tmp_path / "terceiros.json")
        # sem motor acervo no teste: gancho de reindexacao desligado (comentario do
        # proprio publicar-abertura recomenda isto para "base sem motor, teste").
        self.env["PF_CASA_REINDEXA"] = "0"
        self.env["PF_RELEASE_PORTA"] = "0"
        Path(self.env["PLATAFIRMA_FAMILIAS"]).write_text(
            json.dumps({"platafirma-harness": str(self.forge)}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_VENVS"]).write_text("{}", encoding="utf-8")
        Path(self.env["PLATAFIRMA_TERCEIROS"]).write_text("{}", encoding="utf-8")
        # achar_verbo() acha publicar-abertura por `command -v` — basta por no PATH.
        stub_bin = tmp_path / "stub-bin"
        stub_bin.mkdir()
        (stub_bin / "publicar-abertura").symlink_to(PUBLICAR_ABERTURA)
        self.env["PATH"] = f"{stub_bin}{os.pathsep}" + self.env.get("PATH", "")

    def commit(self, arquivos: dict) -> str:
        """Escreve/edita arquivos (rel->texto), commita e empurra para main. Devolve o sha."""
        for rel, texto in arquivos.items():
            _escreve(self.wt, rel, texto)
        sha = _commit(self.wt, f"fixture: {', '.join(arquivos)}")
        _git(self.wt, "push", "-q", "origin", "main")
        return sha

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(SCRIPT), *args], env=self.env,
                               capture_output=True, text=True, timeout=60)

    def current_abertura(self) -> str | None:
        link = Path(self.env["PF_ABERTURA_DIR"]) / "current"
        if not link.is_symlink():
            return None
        return link.resolve().name


@pytest.fixture()
def amb(tmp_path):
    return Ambiente(tmp_path)


def test_so_caderno_promove_quando_diff_e_so_caderno(amb):
    r0 = amb.run("promover", "abertura")
    assert r0.returncode == 0, r0.stderr
    assert amb.current_abertura() == amb.sha1

    sha2 = amb.commit({"abertura/ti/construcao/caderno.md": "# caderno construcao\nv2\n"})
    r = amb.run("promover", "abertura", "--so-caderno")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "no ar" in r.stdout
    assert amb.current_abertura() == sha2


def test_so_caderno_recusa_quando_diff_toca_outra_coisa(amb):
    r0 = amb.run("promover", "abertura")
    assert r0.returncode == 0, r0.stderr

    amb.commit({
        "abertura/ti/construcao/caderno.md": "# caderno construcao\nv2\n",
        "abertura/dono.md": "# dono\nmudou\n",
    })
    r = amb.run("promover", "abertura", "--so-caderno")
    assert r.returncode == 4, r.stdout + r.stderr
    assert "abertura/dono.md" in (r.stdout + r.stderr)
    assert amb.current_abertura() == amb.sha1  # current intacto


def test_so_caderno_nada_muda_em_abertura_nao_publica(amb):
    r0 = amb.run("promover", "abertura")
    assert r0.returncode == 0, r0.stderr

    amb.commit({"README.md": "fora de abertura/\n"})
    r = amb.run("promover", "abertura", "--so-caderno")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "nada" in r.stdout.lower()
    assert amb.current_abertura() == amb.sha1  # current intacto, nada publicado


def test_so_caderno_recusa_fora_da_familia_abertura(amb):
    r = amb.run("promover", "platafirma-harness", "--so-caderno")
    assert r.returncode == 2
    assert "--so-caderno" in r.stderr
