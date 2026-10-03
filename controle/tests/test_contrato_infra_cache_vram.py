"""#2856 linha 142: `infra cache vram` não sai mais 0 e vazio.

`vram` descarrega o modelo residente no ollama. Antes, sem modelo residente (ou com o ollama
fora) o ato não escrevia nada e saía 0, e quem queria medir a VRAM achava que o ato não existia.
O curl é um stub no PATH; o jq é o do host (o teste pula sem ele).
"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

INFRA = Path(__file__).resolve().parents[2] / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None or shutil.which("jq") is None,
                                reason="sem bash ou jq no PATH — bin/infra cache precisa dos dois")


def _curl(tmp_path, ps_json, ps_rc=0, generate_rc=0):
    d = tmp_path / "bin"
    d.mkdir()
    f = d / "curl"
    f.write_text(
        "#!/usr/bin/env bash\n"
        'case "$*" in\n'
        f"  *api/ps*) [ {ps_rc} -eq 0 ] && echo '{ps_json}'; exit {ps_rc} ;;\n"
        f"  *api/generate*) exit {generate_rc} ;;\n"
        "esac\nexit 9\n")
    f.chmod(f.stat().st_mode | stat.S_IEXEC)
    return d


def _vram(tmp_path, **kw):
    d = _curl(tmp_path, **kw)
    env = {**os.environ, "PATH": f"{d}{os.pathsep}{os.environ['PATH']}"}
    return subprocess.run([BASH, str(INFRA), "cache", "vram"], capture_output=True, text=True,
                          env=env, timeout=30)


def test_sem_modelo_residente_diz_que_nao_ha_nada_a_descarregar(tmp_path):
    r = _vram(tmp_path, ps_json='{"models":[]}')
    assert r.returncode == 0, r.stderr
    assert "nada residente em VRAM" in r.stdout and "infra cache ver" in r.stdout


def test_ollama_fora_sai_3_e_diz(tmp_path):
    r = _vram(tmp_path, ps_json="", ps_rc=7)
    assert r.returncode == 3 and r.stdout == ""
    assert "ollama nao respondeu" in r.stderr


def test_com_modelo_residente_descarrega_e_nomeia(tmp_path):
    r = _vram(tmp_path, ps_json='{"models":[{"name":"qwen2.5:7b"},{"name":"nomic"}]}')
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines() == ["descarregado: qwen2.5:7b", "descarregado: nomic"]


def test_descarga_que_falha_sai_3_e_nomeia_o_modelo(tmp_path):
    r = _vram(tmp_path, ps_json='{"models":[{"name":"qwen2.5:7b"}]}', generate_rc=22)
    assert r.returncode == 3 and "nao consegui descarregar qwen2.5:7b" in r.stderr
