import os
import shutil
import stat
import subprocess
import sys
import tempfile
import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN_ACERVO = os.path.join(REPO, "bin", "acervo")
BIN_INGERIR = os.path.join(REPO, "bin", "ingerir")


def test_ingerir_ajuda_mostra_drive_e_bucket():
    r = subprocess.run([BIN_INGERIR, "--ajuda"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "--drive [<pasta>]" in r.stderr
    assert "--colecao, --bucket" in r.stderr


def test_ingerir_exclusividade_fontes():
    # lote + drive
    r = subprocess.run([BIN_INGERIR, "--lote", "/tmp/a", "--drive"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    # origem + drive
    r = subprocess.run([BIN_INGERIR, "--origem", "gdrive:x", "--drive"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    # sem fonte
    r = subprocess.run([BIN_INGERIR, "--motor", "rag"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "informe --lote <pasta>, --origem <gdrive:pasta|url> ou --drive [<pasta>]" in r.stderr


def test_acervo_ingerir_dispatch_drive():
    # Testa que acervo ingerir repassa --drive sem tentar prefixar --lote
    r = subprocess.run([BIN_ACERVO, "ingerir", "--drive", "--lote", "x"], capture_output=True, text=True)
    assert r.returncode == 2
    assert "mutuamente exclusivos" in r.stderr

    r_obra = subprocess.run([BIN_ACERVO, "ingerir", "obra", "--drive", "--lote", "x"], capture_output=True, text=True)
    assert r_obra.returncode == 2
    assert "mutuamente exclusivos" in r_obra.stderr


def test_portao_1_divergencia_aborta(tmp_path):
    # Cria binário fake do rclone no PATH que simula cópia incompleta
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    rclone_script = fake_bin / "rclone"
    
    # O mock do rclone:
    # - 'copy': cria 2 arquivos no destino
    # - 'lsf': devolve 3 arquivos (simula que faltou 1 arquivo)
    rclone_content = """#!/usr/bin/env bash
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
"""
    rclone_script.write_text(rclone_content)
    rclone_script.chmod(rclone_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ.get('PATH', '')}")
    r = subprocess.run([BIN_INGERIR, "--drive", "Teste/lote", "--motor", "rag"], env=env, capture_output=True, text=True)
    assert r.returncode == 1
    assert "PORTÃO 1: contagem de rclone lsf (3) diverge do staging (2) — lote incompleto" in r.stderr


def test_portao_1_aprovado(tmp_path):
    # Cria binário fake do rclone onde a contagem bate perfeitamente
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    rclone_script = fake_bin / "rclone"
    
    rclone_content = """#!/usr/bin/env bash
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
"""
    rclone_script.write_text(rclone_content)
    rclone_script.chmod(rclone_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    env = dict(os.environ, PATH=f"{fake_bin}:{os.environ.get('PATH', '')}")
    # Chama dry-run sem servidor do motor rodando (vai passar pelo portão 1)
    r = subprocess.run([BIN_INGERIR, "--drive", "--motor", "rag"], env=env, capture_output=True, text=True)
    assert "PORTÃO 1 aprovado: 2 arquivo(s) conferidos no staging" in r.stderr
