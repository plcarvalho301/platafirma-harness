"""`tarefas espera-dono` exibe stories em refinamento com regras pendentes (card #4096).

O rastreador é um stub HTTP em loopback (`TAREFAS_BASE` aponta para ele): o teste prova que
o verbo lista as stories em refinamento cujas regras novas não possuem marca de validação,
preservando as perguntas legadas abertas e a saída `--json`.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN = REPO_ROOT / "bin" / "tarefas"


class _Stub(BaseHTTPRequestHandler):
    espera: dict = {}

    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path == "/espera-dono":
            b = json.dumps(self.espera).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
            return
        self.send_response(404)
        self.end_headers()


@pytest.fixture()
def stub():
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    finally:
        srv.shutdown()
        srv.server_close()


def _run(args, base):
    env = {**os.environ, "TAREFAS_BASE": base}
    return subprocess.run(
        ["bash", str(BIN), *args],
        text=True, capture_output=True, env=env, timeout=15,
    )


def test_espera_dono_exibe_regras_pendentes_e_perguntas_legadas(stub):
    s, base = stub
    s.espera = {
        "do_dono": {
            "regras_pendentes": [
                {
                    "id": 4096,
                    "titulo": "Ler a validação das Regras novas no corpo",
                    "cadeira": "gestao-estrategica",
                    "regras": ["1. story com regra sem marca → recusa com 400"],
                }
            ],
            "perguntas": [
                {
                    "id": 77,
                    "item": 500,
                    "titulo": "pergunta legada",
                    "cadeira": "engenharia",
                    "primeira_linha": "pergunta (dono): segue no ar?",
                    "carimbo": "2026-11-01T00:00:00Z",
                }
            ],
            "prontos_para_aposta": [],
            "em_homologacao": [],
            "total": 2,
        },
        "com_cadeiras": {"abertos": 0, "orfaos": 0, "cards": []},
        "gerado_em": "2026-11-13T12:00:00Z",
    }
    p = _run(["espera-dono"], base)
    assert p.returncode == 0, p.stderr
    assert "do dono (2):" in p.stdout
    assert "regra pendente · #4096 [gestao-estrategica] Ler a validação das Regras novas no corpo" in p.stdout
    assert "    - 1. story com regra sem marca → recusa com 4096" not in p.stdout
    assert "    - 1. story com regra sem marca → recusa com 400" in p.stdout
    assert "pergunta #77 · #500 pergunta legada [engenharia] — pergunta (dono): segue no ar?" in p.stdout

    pj = _run(["espera-dono", "--json"], base)
    assert pj.returncode == 0, pj.stderr
    assert json.loads(pj.stdout) == s.espera
