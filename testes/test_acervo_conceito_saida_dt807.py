"""DT 807: `acervo retirar biblioteca conceito` chega às rotas de retirada e de fusão; conceito não se restaura."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ACERVO = RAIZ / "bin" / "acervo"


class _Handler(BaseHTTPRequestHandler):
    chamadas: list

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        corpo = json.loads(self.rfile.read(n) or b"null")
        self.chamadas.append((self.path, corpo))
        obj = {"modo": "aplicado" if corpo.get("aplicar") else "plano", "aprovado": True}
        dados = json.dumps(obj).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


@pytest.fixture
def servidor():
    chamadas: list = []
    srv = ThreadingHTTPServer(("127.0.0.1", 0), type("H", (_Handler,), {"chamadas": chamadas}))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    env = {**os.environ, "MOTOR_ACERVO_URL": url, "RAG_API_URL": "", "RAG_API_BASE": "", "RAG_API_TOKEN": "t",
           "PF_CADEIRA": "conhecimento", "PF_SESSAO_ID": f"t-{uuid.uuid4().hex}"}

    def rodar(*argv):
        return subprocess.run(["bash", str(ACERVO), *argv], capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, timeout=60, check=False)
    try:
        yield chamadas, rodar
    finally:
        srv.shutdown()
        srv.server_close()


def test_retirar_conceito_vai_a_retirada_em_plano_seco(servidor):
    chamadas, rodar = servidor
    r = rodar("retirar", "biblioteca", "conceito", "efeito-de-real", "--motivo", "sem lastro")
    assert r.returncode == 0, r.stderr
    assert chamadas == [("/acervo/conceitos/efeito-de-real/retirada",
                         {"motivo": "sem lastro", "autor": "conhecimento", "aplicar": False})]


def test_retirar_com_em_vai_a_fusao(servidor):
    chamadas, rodar = servidor
    r = rodar("retirar", "biblioteca", "conceito", "analise-de-vinculos", "--em", "analise-de-redes-sociais",
              "--motivo", "mesmo conceito")
    assert r.returncode == 0, r.stderr
    assert chamadas == [("/acervo/conceitos/analise-de-vinculos/fusao",
                         {"motivo": "mesmo conceito", "autor": "conhecimento", "aplicar": False,
                          "em": "analise-de-redes-sociais"})]


def test_restaurar_conceito_nao_existe(servidor):
    chamadas, rodar = servidor
    r = rodar("restaurar", "biblioteca", "conceito", "efeito-de-real", "--motivo", "volta")
    assert r.returncode == 2 and "acervo restaurar biblioteca obra" in r.stderr
    assert chamadas == []


def test_sem_motivo_sai_2_sem_chamar(servidor):
    chamadas, rodar = servidor
    r = rodar("retirar", "biblioteca", "conceito", "x")
    assert r.returncode == 2 and "falta --motivo" in r.stderr
    assert chamadas == []
