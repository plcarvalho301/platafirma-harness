"""#3191: `curar --apagar <obra> [--apply]` tira do acervo, sem volta, a obra já retirada (arq:0119 §9.2).

O servidor falso responde POST /acervo/obras/{id}/apagar como o motor: plano sem `aplicar`, o
resultado com o balde quando aplica, e 409 para obra que não foi retirada. `curar` roda como
subprocesso, como em test_curar_lote.py.
"""

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
CURAR = RAIZ / "bin" / "curar"
FOSSIL = "0000f055-0000-4000-8000-000000000000"
VIVA = "0000a1fe-0000-4000-8000-000000000000"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()

PLANO = {"obra_id": FOSSIL, "titulo": "Fóssil", "objeto": "acervo/sha-arq", "objeto_compartilhado": False,
         "espelhos": 1, "impressoes": 2, "ligacoes_conceito": 3, "ligacoes_frente": 0,
         "itens_lote_reextracao": 1, "itens_lote_ingestao": 0, "obras_fichadas_nela": 0, "derivacoes": 0,
         "lastros_de_aresta": 1}


class Falso:
    def __init__(self, falha_no_balde=False):
        self.chamadas = []
        falso = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _resp(self, status, obj):
                dados = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                corpo = json.loads(self.rfile.read(n) or b"{}")
                falso.chamadas.append(("POST", self.path, corpo))
                if self.path == f"/acervo/obras/{VIVA}/apagar":
                    return self._resp(409, {"title": "ObraNaoExpurgada",
                                            "detail": f"Obra {VIVA} não está retirada"})
                if self.path != f"/acervo/obras/{FOSSIL}/apagar":
                    return self._resp(404, {"title": "Nada", "detail": self.path})
                if not corpo.get("aplicar"):
                    return self._resp(200, {"modo": "plano", **PLANO})
                balde = {"bucket": "acervo", "apagados": ["sha-arq", "espelho/x/espelho.md"],
                         "ausentes": [], "mantidos": [],
                         "falhas": ["espelho/x/indice.json: S3Error: boom"] if falha_no_balde else []}
                return self._resp(200, {"modo": "aplicado", **PLANO, "indices_apagados": ["i1", "i2"],
                                        "balde": balde})

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def falso():
    f = Falso()
    yield f
    f.fechar()


def _curar(falso, *argv):
    env = {**os.environ, "MOTOR_ACERVO_URL": falso.url, "RAG_API_TOKEN": "tok-teste", "PF_CADEIRA": "dados"}
    return subprocess.run([PY, str(CURAR), *argv], capture_output=True, text=True, env=env, timeout=60, check=False)


precisa_requests = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


@precisa_requests
def test_sem_apply_e_plano_seco(falso):
    r = _curar(falso, "--apagar", FOSSIL)
    assert r.returncode == 0, r.stderr
    assert "SEM VOLTA" in r.stdout and "plano seco" in r.stdout and "acervo/sha-arq" in r.stdout
    verbo, caminho, corpo = falso.chamadas[-1]
    assert (verbo, caminho) == ("POST", f"/acervo/obras/{FOSSIL}/apagar")
    assert corpo == {"autor": "dados", "aplicar": False}


@precisa_requests
def test_apply_apaga_e_relata_o_balde(falso):
    r = _curar(falso, "--apagar", FOSSIL, "--apply")
    assert r.returncode == 0, r.stderr
    assert f"Obra {FOSSIL} apagada" in r.stdout and "2 índice(s)" in r.stdout and "2 objeto(s)" in r.stdout
    assert falso.chamadas[-1][2]["aplicar"] is True


@precisa_requests
def test_objeto_que_nao_saiu_do_balde_sai_1():
    f = Falso(falha_no_balde=True)
    try:
        r = _curar(f, "--apagar", FOSSIL, "--apply")
    finally:
        f.fechar()
    assert r.returncode == 1
    assert "NÃO saíram do balde" in r.stdout


@precisa_requests
def test_obra_viva_recusa(falso):
    r = _curar(falso, "--apagar", VIVA, "--apply")
    assert r.returncode == 1
    assert "ObraNaoExpurgada" in r.stdout
