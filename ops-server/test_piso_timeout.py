"""Piso de timeout por verbo+ato (balde #2856, linha 185).

Medido em 04/10/2026: `repo sincronizar` leva ~127 s no pre-push e o padrao de 120 s da
assinatura matava o processo no meio. O piso so sobe o timeout; nunca o encurta.

Cobre:
- _timeout_com_piso: o ato com piso sobe o padrao; o pedido maior vale; verbo e ato sem
  piso ficam como vieram.
- _run_verbo_blocking: o `communicate` recebe o timeout com piso (fiacao, sem rodar o verbo).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
PDP_CODE_DIR = HARNESS_DIR / "politica-acesso"
for d in (OPS_SERVER_DIR, PDP_CODE_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

os.environ["PF_HARNESS"] = str(HARNESS_DIR)
import server as s

IDENT = {"sessao_id": "-", "ordem_id": "-", "cadeira": ""}


def test_piso_sobe_o_padrao_do_ato_listado():
    assert s._timeout_com_piso(["/opt/bin/repo", "sincronizar", "x"], 120) == 600


def test_piso_nao_encurta_pedido_maior_nem_toca_o_resto():
    assert s._timeout_com_piso(["/opt/bin/repo", "sincronizar"], 900) == 900
    assert s._timeout_com_piso(["/opt/bin/repo", "estado"], 120) == 120
    assert s._timeout_com_piso(["/opt/bin/release", "sincronizar"], 120) == 120
    assert s._timeout_com_piso(["/opt/bin/repo"], 120) == 120
    assert s._timeout_com_piso([], 120) == 120


class _FakePopen:
    def __init__(self, *a, **kw):
        self.pid = 1
        self.returncode = 0
        self.vistos = []

    def communicate(self, input=None, timeout=None):
        _FakePopen.timeout_visto = timeout
        return b"ok", b""


def _roda(argv, timeout):
    with patch("server.subprocess.Popen", _FakePopen):
        return s._run_verbo_blocking(argv, None, timeout, IDENT, None)


def test_run_verbo_blocking_passa_o_timeout_com_piso():
    r = _roda(["/opt/bin/repo", "sincronizar", "x"], 120)
    assert r["exit_code"] == 0
    assert _FakePopen.timeout_visto == 600


def test_run_verbo_blocking_sem_piso_fica_no_pedido():
    _roda(["/opt/bin/repo", "estado"], 120)
    assert _FakePopen.timeout_visto == 120
