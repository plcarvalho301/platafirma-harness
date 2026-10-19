"""O `motor` manda a credencial de escrita nos atos que escrevem no rag-api (card #3839; R25 da spec motor).

O verbo roda de verdade, como subprocesso, contra um rag-api falso em 127.0.0.1. O registro declara
`escrita_token_em` ao lado de `token_em`: o POST do plano e do lote de indexação e o POST da troca levam o
token de escrita; o GET do relatório leva o de leitura. Instância que não declara a credencial segue com o
token de leitura; declarada e ausente é falha alta, que diz o segredo a gravar.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

MOTOR = Path(__file__).resolve().parents[2] / "bin" / "motor"
LOTE = "0f0f0f0f-1111-4222-8333-444444444444"


class _API(BaseHTTPRequestHandler):
    pedidos: ClassVar[list] = []

    def log_message(self, *a):
        pass

    def _responde(self, status, corpo):
        dado = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]) or 0)
        self.pedidos.append(("POST", self.path, self.headers.get("Authorization")))
        return self._responde(200, {"modo": "plano", "n": 0, "a_indexar": 0, "trechos_a_embedar": 0,
                                    "prontas": 0, "fora_transcritas": 0, "indexadas": 0, "seladas": 0,
                                    "promover": False, "itens": []})

    def do_GET(self):
        self.pedidos.append(("GET", self.path, self.headers.get("Authorization")))
        return self._responde(200, {"lote": LOTE, "estado": "concluido", "por_estado": {}, "embedados": 0,
                                    "ms": 1, "itens": []})


def _monta(tmp_path, *, com_escrita: bool, grava_segredo_de_escrita: bool = True):
    servidor = HTTPServer(("127.0.0.1", 0), _API)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}"
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("leitura\n")
    if grava_segredo_de_escrita:
        (instancia / "segredos" / "rag" / "RAG_API_ESCRITA_TOKEN").write_text("escrita\n")
    inst = {"estado": "ativa", "container": None, "stack": "rag", "endpoint": f"{base}/search",
            "indexacao": f"{base}/motor/indexacoes/lote", "token_em": "rag/RAG_API_TOKEN",
            "facets": f"{base}/facets", "medicoes_em": "var/medicoes/rag", "ajustes": [], "nao_e_ajuste": {}}
    if com_escrita:
        inst["escrita_token_em"] = "rag/RAG_API_ESCRITA_TOKEN"
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": inst}))
    _API.pedidos = []

    def roda(*args):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_CADEIRA": "ia"}
        return subprocess.run([sys.executable, str(MOTOR), "rag", *args], capture_output=True, text=True,
                              env=env, timeout=60, check=False)

    return servidor, roda, _API.pedidos


@pytest.fixture
def com_escrita(tmp_path):
    servidor, roda, pedidos = _monta(tmp_path, com_escrita=True)
    yield roda, pedidos
    servidor.shutdown()


def test_o_plano_de_indexacao_manda_a_credencial_de_escrita(com_escrita):
    roda, pedidos = com_escrita
    r = roda("indexar", "biblioteca")
    assert r.returncode == 0, r.stderr
    assert pedidos[-1] == ("POST", "/motor/indexacoes/lote", "Bearer escrita")


def test_o_relatorio_do_lote_segue_com_o_token_de_leitura(com_escrita):
    roda, pedidos = com_escrita
    r = roda("indexar", "biblioteca", "--relatorio", LOTE)
    assert r.returncode == 0, r.stderr
    assert pedidos[-1] == ("GET", f"/motor/indexacoes/lote/{LOTE}", "Bearer leitura")


def test_sem_a_credencial_no_registro_vale_o_token_de_leitura(tmp_path):
    servidor, roda, pedidos = _monta(tmp_path, com_escrita=False, grava_segredo_de_escrita=False)
    try:
        r = roda("indexar", "biblioteca")
        assert r.returncode == 0, r.stderr
        assert pedidos[-1] == ("POST", "/motor/indexacoes/lote", "Bearer leitura")
    finally:
        servidor.shutdown()


def test_credencial_declarada_e_ausente_falha_alto_e_diz_o_segredo(tmp_path):
    servidor, roda, pedidos = _monta(tmp_path, com_escrita=True, grava_segredo_de_escrita=False)
    try:
        r = roda("indexar", "biblioteca")
        assert r.returncode == 1
        assert "seg segredo gravar rag/RAG_API_ESCRITA_TOKEN" in r.stderr
        assert pedidos == []  # nada saiu para a API
    finally:
        servidor.shutdown()
