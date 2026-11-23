"""Regressivo #4436: `ontologia trocar <arquivo.yaml>` envia lote sem versão posicional."""
from __future__ import annotations

import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
BIN = RAIZ / "bin" / "ontologia"
CHAVE = "chave-teste-4436"


def _subir_servidor(respostas: list[tuple[int, dict]]):
    pedidos: list[dict] = []
    fila = list(respostas)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            tam = int(self.headers.get("Content-Length", "0"))
            bruto = self.rfile.read(tam) if tam else b"{}"
            pedidos.append({"caminho": self.path, "corpo": json.loads(bruto)})
            status, corpo = fila.pop(0) if len(fila) > 1 else fila[0]
            raw = json.dumps(corpo, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            return

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, pedidos


def _rodar(*args: str, url: str) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if not k.startswith(("OLARIA_", "PF_CADEIRA"))}
    env.update({
        "OLARIA_URL": url,
        "OLARIA_CHAVE": CHAVE,
        "PF_CADEIRA": "conhecimento",
        "PYTHONIOENCODING": "utf-8",
    })
    return subprocess.run(
        [sys.executable, str(BIN), *args], env=env, capture_output=True, text=True, timeout=30, check=False,
    )


def test_trocar_lote_envia_yaml_sem_versao_posicional(tmp_path: Path):
    srv, pedidos = _subir_servidor([
        (200, {"estado": "fez", "fornada": "019a83c4-7b12-7000-8000-000000000099", "uso": "catalogo", "gravadas": [], "removidas": []}),
    ])
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        arq = tmp_path / "lote.yaml"
        arq.write_text("classes:\n- slug: a\n  versao: 019a83c4-7b12-7000-8000-000000000001\n", encoding="utf-8")
        r = _rodar("trocar", str(arq), url=url)
        assert r.returncode == 0, r.stdout + r.stderr
        assert len(pedidos) == 1
        assert pedidos[0]["caminho"] == "/trocar"
        assert "versao" not in pedidos[0]["corpo"]
        assert "classe" not in pedidos[0]["corpo"]
        assert "chave" not in pedidos[0]["corpo"]
        assert "slug: a" in pedidos[0]["corpo"]["yaml"]
    finally:
        srv.shutdown()
        srv.server_close()


def test_trocar_sem_args_ou_sem_versao_continua_saindo_2(tmp_path: Path):
    srv, pedidos = _subir_servidor([(200, {"estado": "fez"})])
    try:
        url = f"http://127.0.0.1:{srv.server_address[1]}"
        arq = tmp_path / "m.yaml"
        arq.write_text("fichas: []\n", encoding="utf-8")
        assert _rodar("trocar", url=url).returncode == 2
        assert _rodar("trocar", "shape", url=url).returncode == 2
        assert _rodar("trocar", "shape", "deriva", "nao-v7", str(arq), url=url).returncode == 2
        assert pedidos == []
    finally:
        srv.shutdown()
        srv.server_close()
