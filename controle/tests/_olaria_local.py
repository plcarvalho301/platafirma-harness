"""Servidor HTTP local da Olaria para testes de release e teste (card #4417)."""
from __future__ import annotations

import http.server
import json
import threading


def _yaml_de_terceiros(terceiros: dict | None) -> str:
    if not terceiros:
        return "classe: stack\nfichas: []\n"
    linhas = ["classe: stack", "fichas:", "- chave: stack:teste", "  ligacoes:", "    depende-de:"]
    for nome, item in terceiros.items():
        if str(nome).startswith("_") or not isinstance(item, dict):
            continue
        sha = item.get("sha256", "")
        fam = item.get("familia", "platafirma-harness")
        dest = item.get("destino", f"terceiros/{nome}")
        url = item.get("url", "")
        linhas.append(f"    - alvo: dependencia-externa:teste:{nome}")
        linhas.append(f"      nome: {nome}")
        linhas.append(f"      familia: {fam}")
        linhas.append(f"      destino: {dest}")
        linhas.append(f"      pino: sha256:{sha}")
        if url:
            linhas.append(f"      url: {url}")
    return "\n".join(linhas) + "\n"


def subir_olaria_local(terceiros: dict | None = None) -> tuple[http.server.ThreadingHTTPServer, dict[str, str]]:
    yaml_txt = _yaml_de_terceiros(terceiros)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            tam = int(self.headers.get("Content-Length", "0"))
            _ = self.rfile.read(tam)
            raw = json.dumps({"yaml": yaml_txt}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def log_message(self, *args):
            return

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, {"OLARIA_URL": f"http://127.0.0.1:{srv.server_address[1]}", "OLARIA_CHAVE": "chave-teste"}
