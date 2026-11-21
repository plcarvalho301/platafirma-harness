# componente: componente:verbo-curar
"""#2856 linha 141: `curar` assume `time-platafirma` para cadeira de construção e orienta no 422."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CURAR = RAIZ / "bin" / "curar"
OBRA = "0000a1fe-0000-4000-8000-000000000000"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
precisa_requests = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


def _sobe_servidor(handler_cls):
    srv = HTTPServer(("127.0.0.1", 0), handler_cls)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv


@precisa_requests
def test_cadeira_de_construcao_assume_time_platafirma_no_reextrair():
    capturado = []

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            tam = int(self.headers.get("Content-Length", "0"))
            corpo = json.loads(self.rfile.read(tam).decode("utf-8"))
            capturado.append((self.path, corpo))
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "modo": "seco",
                "titulo": "Obra",
                "obra_id": OBRA,
                "objeto": "obj",
                "metodo": "pymupdf",
                "espelho_atual": None,
            }).encode("utf-8"))

    srv = _sobe_servidor(H)
    try:
        env = {**os.environ, "MOTOR_ACERVO_URL": f"http://127.0.0.1:{srv.server_port}",
               "RAG_API_TOKEN": "t", "PF_CADEIRA": "engenharia"}
        r = subprocess.run([PY, str(CURAR), "--reextrair", OBRA],
                           capture_output=True, text=True, env=env, timeout=30, check=False)
        assert r.returncode == 0, r.stdout + r.stderr
        assert capturado and capturado[0][1]["autor"] == "time-platafirma"
    finally:
        srv.shutdown()


@precisa_requests
def test_curador_desconhecido_nomeia_time_platafirma():
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.send_response(422)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "title": "CuradorDesconhecido",
                "detail": "Curador 'fulano' desconhecido",
            }).encode("utf-8"))

    srv = _sobe_servidor(H)
    try:
        env = {**os.environ, "MOTOR_ACERVO_URL": f"http://127.0.0.1:{srv.server_port}",
               "RAG_API_TOKEN": "t", "PF_CADEIRA": "dados"}
        r = subprocess.run([PY, str(CURAR), "--reextrair", OBRA, "--autor", "fulano"],
                           capture_output=True, text=True, env=env, timeout=30, check=False)
        assert r.returncode == 1
        assert "--autor time-platafirma" in r.stderr
    finally:
        srv.shutdown()
