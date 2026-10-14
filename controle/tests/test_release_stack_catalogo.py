"""Stack de catálogo (registrada sem compose) não entra na promoção por release.

Regressivo do dia 14/10/2026: o #3551 registrou a stack `harness` com `compose: null`, de propósito
(existe para dar stack a verbo, porta e documento, e não sobe em contêiner). O `ler_stacks_da_familia`
de `bin/release` a pôs entre as que promovem, o passo de teste da imagem chamou `stack testar harness`,
que recusa stack sem compose (exit 2), e toda promoção do `platafirma-harness` parou com
«passo de teste da imagem da stack harness não rodou … current intacto».

Prova, com forge bare local, `acervo` de mentira (só `ler casa stack`) e a release em tmp: a stack sem
compose não vai a `STACKS_PROMOVER`, a promoção inteira chega ao fim, a linha do ensaio a nomeia como de
catálogo, e a stack com compose (ou de fixture antiga, sem a chave) segue promovendo como sempre.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "release"

CATALOGO = {"slug": "cat", "repo": "fixture", "compose": None, "reversao": {"via": "promover"}}
COM_COMPOSE = {"slug": "x", "repo": "fixture", "compose": "deploy/x/compose.yaml",
               "reversao": {"via": "promover"}}
SEM_A_CHAVE = {"slug": "velha", "repo": "fixture", "reversao": {"via": "promover"}}


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                          check=True).stdout.strip()


class Ambiente:
    def __init__(self, tmp_path: Path, registro: list):
        self.wt = tmp_path / "wt" / "fixture"
        self.forge = tmp_path / "forge" / "fixture.git"
        self.wt.mkdir(parents=True)
        self.forge.parent.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", "--bare", str(self.forge)], check=True, capture_output=True)
        _git(self.wt, "init", "-q", "-b", "main")
        _git(self.wt, "config", "user.name", "fixture")
        _git(self.wt, "config", "user.email", "fixture@test.local")
        (self.wt / "README.md").write_text("um\n", encoding="utf-8")
        _git(self.wt, "add", "-A")
        _git(self.wt, "commit", "-q", "-m", "fixture inicial")
        self.sha = _git(self.wt, "rev-parse", "HEAD")
        _git(self.wt, "remote", "add", "origin", str(self.forge))
        _git(self.wt, "push", "-q", "-u", "origin", "main")

        stub_bin = tmp_path / "stub-bin"
        stub_bin.mkdir()
        (tmp_path / "stacks.json").write_text(json.dumps(registro), encoding="utf-8")
        acervo = stub_bin / "acervo"
        acervo.write_text(
            "#!/usr/bin/env bash\n"
            'if [ "$1" = ler ] && [ "$2" = casa ] && [ "$3" = stack ]; then\n'
            f"  cat '{tmp_path / 'stacks.json'}'\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n", encoding="utf-8")
        acervo.chmod(0o755)

        self.env = dict(os.environ)
        self.env.update({
            "PF_RELEASE_RAIZ": str(tmp_path / "opt"),
            "PLATAFIRMA_INSTANCIA": str(tmp_path / "srv"),
            "PLATAFIRMA_FAMILIAS": str(tmp_path / "familias.json"),
            "PLATAFIRMA_VENVS": str(tmp_path / "venvs.json"),
            "PLATAFIRMA_TERCEIROS": str(tmp_path / "terceiros.json"),
            "PF_RELEASE_PORTA": "0",
            "PATH": f"{stub_bin}{os.pathsep}" + self.env.get("PATH", ""),
        })
        Path(self.env["PLATAFIRMA_FAMILIAS"]).write_text(json.dumps({"fixture": str(self.forge)}), encoding="utf-8")
        Path(self.env["PLATAFIRMA_VENVS"]).write_text("{}", encoding="utf-8")
        Path(self.env["PLATAFIRMA_TERCEIROS"]).write_text("{}", encoding="utf-8")

    def com_espelho(self):
        """Família já conhecida: o ensaio de família nova sai antes de listar as stacks."""
        fam = Path(self.env["PF_RELEASE_RAIZ"]) / "fixture"
        fam.mkdir(parents=True)
        _git(fam, "clone", "-q", "--bare", str(self.forge), str(fam / ".repo.git"))
        return self

    def run(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([str(SCRIPT), *args], env=self.env, capture_output=True, text=True, timeout=90)


def _amb(tmp_path, *stacks):
    return Ambiente(tmp_path, list(stacks))


def test_ensaio_nomeia_a_stack_de_catalogo_e_nao_a_promove(tmp_path):
    amb = _amb(tmp_path, CATALOGO).com_espelho()
    r = amb.run("promover", "fixture", "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "de catálogo, sem compose" in r.stdout and "cat" in r.stdout
    assert "(bin/_release/stack promover)" not in r.stdout


def test_familia_so_de_catalogo_promove_inteira_sem_passar_pelo_passo_de_imagem(tmp_path):
    """O defeito: `stack testar cat` saía 2 e a promoção parava com current intacto."""
    amb = _amb(tmp_path, CATALOGO)
    r = amb.run("promover", "fixture")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "passo de teste da imagem" not in r.stderr
    assert "no ar:" in r.stdout


def test_stack_com_compose_continua_na_lista_de_promocao_ao_lado_da_de_catalogo(tmp_path):
    amb = _amb(tmp_path, CATALOGO, COM_COMPOSE).com_espelho()
    r = amb.run("promover", "fixture", amb.sha, "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "stacks:    x (bin/_release/stack promover)" in r.stdout
    assert "de catálogo, sem compose — nada sobe nem se mede: cat" in r.stdout


def test_registro_sem_a_chave_compose_segue_como_stack_de_promocao(tmp_path):
    """Fixtures e registros antigos não trazem `compose`: só a chave presente e nula é catálogo."""
    amb = _amb(tmp_path, SEM_A_CHAVE).com_espelho()
    r = amb.run("promover", "fixture", amb.sha, "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "stacks:    velha (bin/_release/stack promover)" in r.stdout
    assert "de catálogo" not in r.stdout


def test_reverter_tambem_nomeia_a_stack_de_catalogo(tmp_path):
    amb = _amb(tmp_path, CATALOGO)
    assert amb.run("promover", "fixture").returncode == 0
    (amb.wt / "README.md").write_text("dois\n", encoding="utf-8")
    _git(amb.wt, "commit", "-q", "-am", "dois")
    _git(amb.wt, "push", "-q", "origin", "main")
    assert amb.run("promover", "fixture").returncode == 0
    r = amb.run("reverter", "fixture", amb.sha, "--ensaio")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "de catálogo, sem compose — nada a reverter: cat" in r.stdout
