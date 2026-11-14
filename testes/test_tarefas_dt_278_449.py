"""Verbo tarefas: DTs 278 (ler item englobado mostra resolvido_de) e 449 (dica de registro)."""
from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin" / "tarefas"

ESTADOS = [
    {"estado": "captada", "nome": "Captada", "fase": "funil", "natureza": "fila"},
    {"estado": "priorizada", "nome": "Priorizada", "fase": "funil", "natureza": "fila"},
    {"estado": "entregue", "nome": "Entregue", "fase": "terminal", "natureza": "terminal"},
]


class _Rastreador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        caminho = urlparse(self.path).path
        if caminho == "/api/estados":
            return self._json({"estados": ESTADOS})
        if caminho == "/api/itens/3531":
            return self._json({
                "id": 3513, "chave": "3513", "resolvido_de": 3531,
                "nivel": 2, "nivel_nome": "story", "pai": 3497,
                "titulo": "Item absorvedor", "estado": "entregue",
                "estado_nome": "Entregue", "estado_fase": "terminal",
                "estado_derivado": None, "cadeira": "ia",
                "ancestrais": [], "bloqueia": [], "bloqueado_por": [],
                "descricao": "<p>corpo</p>", "sign_offs": [],
            })
        return self._json({"erro": f"nao esperado: {caminho}"}, status=404)

    def do_POST(self):
        caminho = urlparse(self.path).path
        if caminho == "/api/itens":
            return self._json({
                "erro": "story sem pai exige `registro-de-negocio` para ir a `priorizada` (R16, arq:0127 D8)",
                "exige": "registro-de-negocio",
            }, status=400)
        return self._json({"erro": f"nao esperado: {caminho}"}, status=404)


def _rodar(*args: str):
    srv = HTTPServer(("127.0.0.1", 0), _Rastreador)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        env = {**os.environ, "TAREFAS_BASE": f"http://127.0.0.1:{srv.server_port}/api"}
        return subprocess.run([str(BIN), *args], capture_output=True, text=True, env=env)
    finally:
        srv.shutdown()
        srv.server_close()


def test_dt_278_ler_mostra_resolvido_de_em_cabecalho_e_completo():
    r_cab = _rodar("ler", "3531", "--cabecalho")
    assert r_cab.returncode == 0, r_cab.stderr
    assert "#3513" in r_cab.stdout
    assert "resolvido de: #3531 (englobado neste item; use --direto para ler o original)" in r_cab.stdout

    r_full = _rodar("ler", "3531")
    assert r_full.returncode == 0, r_full.stderr
    assert "resolvido de: #3531 (englobado neste item; use --direto para ler o original)" in r_full.stdout


def test_dt_449_recusa_de_registro_nao_forca_estado_priorizada():
    r = _rodar("criar", "Ajuste", "--cadeira", "dados")
    assert r.returncode != 0
    assert '--registro "<porquê>"' in r.stderr
    assert '--estado priorizada --registro' not in r.stderr
