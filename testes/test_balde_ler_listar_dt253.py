"""DT 253: `balde ler` explicita que só mede existência e tamanho (stat); `balde listar` avisa quando trunca."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BALDE = RAIZ / "bin" / "_acervo" / "balde"
SHA = "b" * 64


def _acha_python() -> str | None:
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, timeout=10, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
precisa_requests = pytest.mark.skipif(PY is None, reason="nenhum python com `requests`")


class _Handler(BaseHTTPRequestHandler):
    falso: Falso

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == f"/acervo/objetos/{SHA}":
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "objeto": f"acervo/{SHA}",
                "bytes": 1234,
                "content_type": "application/pdf",
                "obras": ["obra-1"],
            }).encode())
        elif self.path.startswith("/acervo/baldes/firma/objetos"):
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            # Devolve 1000 itens para forçar truncamento
            itens = [{"objeto": f"acervo/obj-{i}", "bytes": 10, "modificado_em": "2026-11-08"} for i in range(1000)]
            self.wfile.write(json.dumps({"itens": itens, "proximo": None}).encode())
        else:
            self.send_response(404)
            self.end_headers()


class Falso:
    def __init__(self):
        _Handler.falso = self
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.porta = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def parar(self):
        self.httpd.shutdown()


@pytest.fixture
def servidor():
    s = Falso()
    try:
        yield s
    finally:
        s.parar()


@precisa_requests
def test_balde_ler_explicita_que_so_mede_existencia_e_tamanho(servidor):
    env = os.environ.copy()
    env["MOTOR_ACERVO_URL"] = f"http://127.0.0.1:{servidor.porta}"
    res = subprocess.run([PY, str(BALDE), "ler", SHA], capture_output=True, text=True, env=env, check=False)
    assert res.returncode == 0
    assert "este ato só mede existência e tamanho (stat); não lê bytes" in res.stdout


@precisa_requests
def test_balde_listar_avisa_truncamento_quando_atinge_limite(servidor):
    env = os.environ.copy()
    env["MOTOR_ACERVO_URL"] = f"http://127.0.0.1:{servidor.porta}"
    res = subprocess.run([PY, str(BALDE), "listar", "firma"], capture_output=True, text=True, env=env, check=False)
    assert res.returncode == 0
    assert "balde: listagem truncada em 1000 itens" in res.stderr
