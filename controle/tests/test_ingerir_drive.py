import os
import shlex
import shutil
import stat
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN_ACERVO = os.path.join(REPO, "bin", "acervo")
BIN_INGERIR = os.path.join(REPO, "bin", "ingerir")


def _acha_python():
    """O primeiro python que tenha `requests`: o venv de teste pode nao ter, e
    `bin/ingerir` abre por `env python3`, que cai no python do PATH."""
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (ingerir precisa)")


def _roda(argv, env):
    return subprocess.run(argv, env=env, capture_output=True, text=True, check=False)


def _executavel(caminho, conteudo):
    caminho.write_text(conteudo)
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def env_py(tmp_path):
    """Ambiente cujo `python3` e o que tem `requests`. Um script, nao um link: o link
    perderia o pyvenv.cfg ao lado do executavel."""
    pasta = tmp_path / "py"
    pasta.mkdir()
    _executavel(pasta / "python3", f'#!/bin/sh\nexec {shlex.quote(PY)} "$@"\n')
    return dict(os.environ, PATH=f"{pasta}:{os.environ.get('PATH', '')}")


def test_ingerir_ajuda_mostra_drive_e_bucket(env_py):
    r = _roda([BIN_INGERIR, "--ajuda"], env_py)
    assert r.returncode == 2
    assert "--drive [<pasta>]" in r.stderr
    assert "--colecao, --bucket" in r.stderr


def test_ingerir_exclusividade_fontes(env_py):
    # lote + drive
    r = _roda([BIN_INGERIR, "--lote", "/tmp/a", "--drive"], env_py)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    # origem + drive
    r = _roda([BIN_INGERIR, "--origem", "gdrive:x", "--drive"], env_py)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    # sem fonte
    r = _roda([BIN_INGERIR, "--motor", "rag"], env_py)
    assert r.returncode == 2
    assert "informe --lote <pasta>, --origem <gdrive:pasta|url> ou --drive [<pasta>]" in r.stderr


def test_acervo_ingerir_dispatch_drive(env_py):
    # Testa que acervo ingerir repassa --drive sem tentar prefixar --lote
    r = _roda([BIN_ACERVO, "ingerir", "--drive", "--lote", "x"], env_py)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    r_bib = _roda([BIN_ACERVO, "ingerir", "biblioteca", "--drive", "--lote", "x"], env_py)
    assert r_bib.returncode == 2
    assert "mutuamente exclusivos" in r_bib.stderr


def test_portao_1_divergencia_aborta(tmp_path, env_py):
    # Cria binário fake do rclone no PATH que simula cópia incompleta
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    # O mock do rclone:
    # - 'copy': cria 2 arquivos no destino
    # - 'lsf': devolve 3 arquivos (simula que faltou 1 arquivo)
    _executavel(fake_bin / "rclone", """#!/usr/bin/env bash
if [ "$1" = "copy" ]; then
    dest="$3"
    mkdir -p "$dest"
    touch "$dest/arq1.pdf" "$dest/arq2.pdf"
    exit 0
elif [ "$1" = "lsf" ]; then
    echo "arq1.pdf"
    echo "arq2.pdf"
    echo "arq3.pdf"
    exit 0
fi
exit 0
""")

    env = dict(env_py, PATH=f"{fake_bin}:{env_py['PATH']}")
    r = _roda([BIN_INGERIR, "--drive", "Teste/lote", "--motor", "rag"], env)
    assert r.returncode == 1
    assert "PORTÃO 1: contagem de rclone lsf (3) diverge do staging (2) — lote incompleto" in r.stderr


def test_portao_1_aprovado(tmp_path, env_py):
    # Cria binário fake do rclone onde a contagem bate perfeitamente
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()

    _executavel(fake_bin / "rclone", """#!/usr/bin/env bash
if [ "$1" = "copy" ]; then
    dest="$3"
    mkdir -p "$dest"
    touch "$dest/doc1.pdf" "$dest/doc2.pdf"
    exit 0
elif [ "$1" = "lsf" ]; then
    echo "doc1.pdf"
    echo "doc2.pdf"
    exit 0
fi
exit 0
""")

    env = dict(env_py, PATH=f"{fake_bin}:{env_py['PATH']}")
    # Chama dry-run sem servidor do motor rodando (vai passar pelo portão 1)
    r = _roda([BIN_INGERIR, "--drive", "--motor", "rag"], env)
    assert "PORTÃO 1 aprovado: 2 arquivo(s) conferidos no staging" in r.stderr
