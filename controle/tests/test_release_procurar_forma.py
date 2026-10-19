"""Forma de `release procurar` igual a do irmao `repo procurar` (incidente #3885).

As cadeiras chamavam `release procurar <repo> <termo> [<prefixo>]`, a forma que `repo procurar`
aceita desde a #2856 linha 82, e o release recusava com 2 porque so aceitava `--termo`. O
parse nao depende de familia materializada: com a familia declarada e sem current, o verbo
sai 1 e o vizinho que imprime mostra o termo que entendeu.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "bin" / "release"
FAMILIA = "platafirma-demo"


@pytest.fixture()
def env(tmp_path):
    familias = tmp_path / "familias.json"
    familias.write_text(json.dumps({FAMILIA: str(tmp_path / "forge" / f"{FAMILIA}.git")}),
                        encoding="utf-8")
    # familia e pasta na raiz da release; sem current, o procurar sai 1 depois do parse
    (tmp_path / "opt" / FAMILIA).mkdir(parents=True)
    e = dict(os.environ)
    e["PF_RELEASE_RAIZ"] = str(tmp_path / "opt")
    e["PLATAFIRMA_INSTANCIA"] = str(tmp_path / "srv")
    e["PLATAFIRMA_FAMILIAS"] = str(familias)
    return e


def _procurar(env, *args):
    return subprocess.run([str(SCRIPT), "procurar", *args], env=env,
                          capture_output=True, text=True, timeout=60)


def test_termo_posicional_passa_do_parse(env):
    r = _procurar(env, FAMILIA, "latencia")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "--termo latencia" in r.stderr


def test_termo_e_prefixo_posicionais(env):
    r = _procurar(env, FAMILIA, "latencia", "rag")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "--termo latencia" in r.stderr


def test_forma_com_flag_segue_valendo_em_qualquer_ordem(env):
    antes = _procurar(env, FAMILIA, "--termo", "x")
    depois = _procurar(env, "--termo", "x", FAMILIA, "rag")
    for r in (antes, depois):
        assert r.returncode == 1, r.stdout + r.stderr
        assert "--termo x" in r.stderr


def test_caminho_e_apelido_do_prefixo(env):
    r = _procurar(env, FAMILIA, "--termo", "x", "--caminho", "rag")
    assert r.returncode == 1, r.stdout + r.stderr


def test_sem_termo_recusa_dizendo_a_forma(env):
    r = _procurar(env, FAMILIA)
    assert r.returncode == 2
    assert f"release procurar {FAMILIA} <termo>" in r.stderr


def test_posicional_a_mais_recusa(env):
    r = _procurar(env, FAMILIA, "x", "rag", "sobra")
    assert r.returncode == 2
    assert "argumento extra: sobra" in r.stderr
