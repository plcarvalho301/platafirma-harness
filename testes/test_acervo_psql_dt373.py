"""DT #373: acervo psql usa mktemp + trap em vez de /tmp/acervo-psql.err fixo."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ACERVO_PSQL = RAIZ / "bin" / "_acervo" / "psql"


def test_acervo_psql_nao_usa_tmp_fixo():
    texto = ACERVO_PSQL.read_text(encoding="utf-8")
    assert "/tmp/acervo-psql.err" not in texto
    assert "mktemp" in texto
    assert "trap " in texto


def test_chamadas_concorrentes_nao_se_pisam_nem_vazam_tmp(tmp_path):
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    tmpdir = tmp_path / "tmp"
    tmpdir.mkdir()

    docker_fake = fake_bin / "docker"
    docker_fake.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
if [ "${1:-}" = "inspect" ]; then
  echo "true"
  exit 0
fi
sql="$(cat)"
if [[ "$sql" == *"lenta"* ]]; then
  sleep 0.4
  echo "linha_lenta"
  echo "err_lenta" >&2
else
  echo "linha_rapida"
  echo "err_rapida" >&2
fi
""",
        encoding="utf-8",
    )
    docker_fake.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ.get('PATH', '')}",
        "TMPDIR": str(tmpdir),
    }

    p_lenta = subprocess.Popen(
        ["bash", str(ACERVO_PSQL), "--sql", "SELECT 'lenta'"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    p_rapida = subprocess.Popen(
        ["bash", str(ACERVO_PSQL), "--sql", "SELECT 'rapida'"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    out_rapida, err_rapida = p_rapida.communicate(timeout=10)
    out_lenta, err_lenta = p_lenta.communicate(timeout=10)

    assert p_rapida.returncode == 0, err_rapida
    assert p_lenta.returncode == 0, err_lenta
    assert out_rapida.strip() == "linha_rapida"
    assert err_rapida.strip() == "err_rapida"
    assert out_lenta.strip() == "linha_lenta"
    assert err_lenta.strip() == "err_lenta"
    assert "No such file or directory" not in err_rapida
    assert "No such file or directory" not in err_lenta
    assert list(tmpdir.iterdir()) == []
