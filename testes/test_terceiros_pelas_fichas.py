# componente: componente:terceiros
"""Testes de materialização e expurgo de terceiros pelas fichas da Olaria (card #4417)."""
from __future__ import annotations

import hashlib
import http.server
import json
import os
import subprocess
import sys
import threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "lib"))

import terceiros_olaria as to  # noqa: E402


def _servidor_http(handler_fn):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            tam = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(tam)
            status, ctype, payload = handler_fn("POST", self.path, raw)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            status, ctype, payload = handler_fn("GET", self.path, b"")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            return

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _rodar_materializar(familia: str, arvore: Path, cache: Path, env_extra: dict[str, str]):
    env = dict(os.environ)
    env.update(env_extra)
    cmd = f'. "{RAIZ}/lib/terceiros.sh" && materializar_terceiros_em "{familia}" "{arvore}" "{cache}"'
    return subprocess.run(["bash", "-c", cmd], env=env, capture_output=True, text=True, check=False)


def test_terceiro_materializado_pelas_fichas_com_download_e_cache(tmp_path):
    conteudo = b"conteudo-pinado-4417\n"
    sha = hashlib.sha256(conteudo).hexdigest()

    def srv_fn(method, path, _raw):
        if method == "GET" and path == "/artefato.bin":
            return 200, "application/octet-stream", conteudo
        if method == "POST" and path == "/ler":
            yaml_txt = (
                "classe: stack\nfichas:\n"
                "- chave: stack:harness\n"
                "  ligacoes:\n    depende-de:\n"
                "    - alvo: dependencia-externa:teste:artefato\n"
                "      nome: artefato-teste\n"
                "      familia: platafirma-harness\n"
                "      destino: terceiros/artefato.bin\n"
                f"      pino: sha256:{sha}\n"
                f"      url: {url_srv}/artefato.bin\n"
            )
            return 200, "application/json", json.dumps({"yaml": yaml_txt}).encode("utf-8")
        return 404, "text/plain", b"nao encontrado"

    srv, url_srv = _servidor_http(srv_fn)
    try:
        arvore = tmp_path / "arvore"
        arvore.mkdir()
        cache = tmp_path / "cache"
        proc = _rodar_materializar(
            "platafirma-harness",
            arvore,
            cache,
            {"OLARIA_URL": url_srv, "OLARIA_CHAVE": "chave-teste"},
        )
        assert proc.returncode == 0, proc.stderr
        assert (arvore / "terceiros/artefato.bin").read_bytes() == conteudo
        assert (cache / sha).read_bytes() == conteudo
        assert to.shas_declarados({"OLARIA_URL": url_srv, "OLARIA_CHAVE": "chave-teste"}) == {sha}
    finally:
        srv.shutdown()


def test_terceiro_com_sha256_diferente_do_pino_recusa_com_saida_4(tmp_path):
    sha_esperado = "a" * 64

    def srv_fn(method, path, _raw):
        if method == "GET" and path == "/adulterado.bin":
            return 200, "application/octet-stream", b"conteudo-adulterado\n"
        if method == "POST" and path == "/ler":
            yaml_txt = (
                "classe: stack\nfichas:\n"
                "- chave: stack:harness\n"
                "  ligacoes:\n    depende-de:\n"
                "    - alvo: dependencia-externa:teste:adulterado\n"
                "      nome: artefato-adulterado\n"
                "      familia: platafirma-harness\n"
                "      destino: terceiros/adulterado.bin\n"
                f"      pino: sha256:{sha_esperado}\n"
                f"      url: {url_srv}/adulterado.bin\n"
            )
            return 200, "application/json", json.dumps({"yaml": yaml_txt}).encode("utf-8")
        return 404, "text/plain", b"nao encontrado"

    srv, url_srv = _servidor_http(srv_fn)
    try:
        arvore = tmp_path / "arvore"
        arvore.mkdir()
        cache = tmp_path / "cache"
        proc = _rodar_materializar(
            "platafirma-harness",
            arvore,
            cache,
            {"OLARIA_URL": url_srv, "OLARIA_CHAVE": "chave-teste"},
        )
        assert proc.returncode == 4
        assert "current intacto" in proc.stderr
        assert not (arvore / "terceiros/adulterado.bin").exists()
    finally:
        srv.shutdown()


def test_olaria_fora_do_ar_sai_3_sem_tocar_arvore(tmp_path):
    arvore = tmp_path / "arvore"
    arvore.mkdir()
    cache = tmp_path / "cache"
    proc = _rodar_materializar(
        "platafirma-harness",
        arvore,
        cache,
        {"OLARIA_URL": "http://127.0.0.1:1", "OLARIA_CHAVE": "chave-teste"},
    )
    assert proc.returncode == 3
    assert "Olaria" in proc.stderr
    assert list(arvore.iterdir()) == []
