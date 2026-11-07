"""Ajuda do ato custa só o catálogo pertinente (#2856 linha 502)."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def test_help_do_balde_e_curto_e_ajuda_continua_completa():
    def run(*args):
        return subprocess.run(["bash", str(ROOT / "bin/acervo"), *args],
                              text=True, capture_output=True)
    curto = run("balde", "--help")
    completo = run("--ajuda")
    assert curto.returncode == completo.returncode == 2
    assert "acervo balde" in curto.stderr
    assert "acervo espelhar" not in curto.stderr
    assert "acervo espelhar" in completo.stderr
    assert len(curto.stderr.encode()) < len(completo.stderr.encode()) / 4
