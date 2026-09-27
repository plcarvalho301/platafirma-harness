"""Contrato de `conferir diagrama` contra o Kroki (card #3099).

O Kroki e um servidor HTTP de fixture no loopback; `docker port` e um stub que devolve a
porta publicada dele. Prova: o endpoint sai de `docker port` (nunca do IP do conteiner, que
no docker rootless nao e roteavel do host); Kroki compila -> 0; Kroki recusa -> 1; Kroki
fora de alcance -> 5, nunca 0. Nao prova: o Kroki real nem a rede da conta.
"""
import http.server
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

CONFERIR = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "conferir.py"


def _kroki(status):
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", 0)))
            self.send_response(status)
            self.end_headers()
            self.wfile.write(b"<svg/>" if status == 200 else b"Error 400: syntax")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _porta_livre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _rodar(tmp_path, porta):
    stub = tmp_path / "stub"
    stub.mkdir()
    (stub / "docker").write_text(
        "#!/bin/sh\n"
        f'[ "$1 $2 $3" = "port plataforma-wiki-kroki-1 8000/tcp" ] && echo "127.0.0.1:{porta}" && exit 0\n'
        "exit 9\n")
    (stub / "docker").chmod(0o755)
    mmd = tmp_path / "f.mmd"
    mmd.write_text("graph TD\n  a-->b\n")
    env = {k: v for k, v in os.environ.items() if k != "KROKI_URL"}
    env.update(PATH=f"{stub}:{env.get('PATH', '/usr/bin:/bin')}", PF_AI_DIR=str(tmp_path / "AI"),
               PF_HARNESS_DIR=str(tmp_path / "nada"))
    return subprocess.run([sys.executable, str(CONFERIR), "diagrama", str(mmd)],
                          capture_output=True, text=True, env=env)


def test_compila_pela_porta_publicada(tmp_path):
    srv = _kroki(200)
    try:
        p = _rodar(tmp_path, srv.server_address[1])
    finally:
        srv.shutdown()
    assert p.returncode == 0, p.stdout + p.stderr


def test_kroki_recusa_sai_1(tmp_path):
    srv = _kroki(400)
    try:
        p = _rodar(tmp_path, srv.server_address[1])
    finally:
        srv.shutdown()
    assert p.returncode == 1, p.stdout + p.stderr


def test_kroki_fora_de_alcance_sai_5(tmp_path):
    p = _rodar(tmp_path, _porta_livre())
    assert p.returncode == 5, p.stdout + p.stderr
    assert "nao consegui falar com o Kroki" in p.stdout + p.stderr
