"""`infra limpeza logs`: nenhum dia do bruto da porta sai por idade (card #3343, arq:0123 §12).

O bruto em var/log/ops é só de acréscimo e o dia cortado não volta; quem o corta é o timer
com portão (#3354). A poda por -mtime segue só em var/log/jobs. Estes testes rodam o
bin/infra de verdade contra uma instância montada em tmp_path.
"""
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
INFRA = RAIZ / "bin" / "infra"
BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="sem bash no PATH")

CEM_DIAS = 100


def _velho(p, dias=CEM_DIAS):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("x\n")
    t = time.time() - dias * 86400
    os.utime(p, (t, t))
    return p


def _limpar(tmp_path):
    env = {k: v for k, v in os.environ.items()
           if k not in ("OPS_LOG_DIR", "LONGJOB_LOGDIR", "OPS_LOG_RETENCAO_DIAS")}
    env["PLATAFIRMA_INSTANCIA"] = str(tmp_path)
    return subprocess.run([BASH, str(INFRA), "limpeza", "logs"], capture_output=True,
                          text=True, env=env, timeout=30)


def test_ops_velho_fica_e_jobs_velho_sai(tmp_path):
    ops = _velho(tmp_path / "var" / "log" / "ops" / "ops-2026-01-01.jsonl")
    job = _velho(tmp_path / "var" / "log" / "jobs" / "velho.log")
    r = _limpar(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert ops.exists(), "o bruto da porta não sai por idade"
    assert not job.exists(), "jobs segue cortado por -mtime"


def test_linha_de_vida_conta_o_retido(tmp_path):
    _velho(tmp_path / "var" / "log" / "ops" / "ops-2026-01-01.jsonl")
    r = _limpar(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    marca = tmp_path / "var" / "log" / "poda.log"
    assert marca.exists(), "o teste tem de escrever o poda.log do tmp, não o real"
    texto = marca.read_text()
    assert "poda ok — retencao=90d removidos=0" in texto
    assert "ops retido: 1 dias" in texto


def test_sai_zero_sem_pasta_de_ops(tmp_path):
    r = _limpar(tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ops retido: 0 dias" in (tmp_path / "var" / "log" / "poda.log").read_text()
