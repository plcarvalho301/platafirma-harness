"""`motor rag indexar biblioteca` e a partição biblioteca no `motor` (card #3203; arq:0106 §3; arq:0119 §2).

O verbo roda de verdade, como subprocesso, contra um rag-api falso em 127.0.0.1: registro, token e log
apontam para um diretório temporário (PF_MOTOR_REG, PLATAFIRMA_INSTANCIA, OPS_LOG_DIR). Prova o que o
verbo manda à API e o que imprime; não prova o lote, que é do rag-api (platafirma-conhecimento,
rag/tests/test_indexacao.py).
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
OBRA = "de1c6e97-0000-4000-8000-000000000001"
LOTE = "0f0f0f0f-1111-4222-8333-444444444444"


class _API(BaseHTTPRequestHandler):
    pedidos: ClassVar[list] = []

    def log_message(self, *a):
        pass

    def _responde(self, status, corpo, tipo="application/json"):
        dado = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        self.pedidos.append(("POST", self.path, self.headers.get("Authorization"), corpo))
        if self.path == "/search":
            return self._responde(200, {"fontes": []})
        if corpo.get("aplicar"):
            return self._responde(200, {"modo": "aplicado", "lote": LOTE, "n": 1, "a_indexar": 1,
                                        "trechos_a_embedar": 3, "prontas": 0, "fora_transcritas": 0,
                                        "indexadas": 1, "seladas": 1, "promover": corpo.get("promover"),
                                        "acompanhar": f"motor rag indexar biblioteca --relatorio {LOTE}"})
        return self._responde(200, {"modo": "plano", "n": 1, "a_indexar": 1, "trechos_a_embedar": 3,
                                    "prontas": 0, "fora_transcritas": 0, "indexadas": 1, "seladas": 1,
                                    "promover": False, "itens": [
                                        {"posicao": 1, "obra_id": OBRA, "titulo": "Obra", "elegiveis": 3,
                                         "vetores": 0, "acao": "indexar"}]})

    def do_GET(self):
        self.pedidos.append(("GET", self.path, self.headers.get("Authorization"), None))
        if self.path.endswith(LOTE):
            return self._responde(200, {"lote": LOTE, "estado": "concluido", "por_estado": {"indexada": 1},
                                        "embedados": 3, "ms": 2000, "itens": [
                                            {"estado": "indexada", "obra_id": OBRA, "titulo": "Obra",
                                             "gate": {"aprovado": True, "vetores": 3, "elegiveis": 3}}]})
        return self._responde(404, {"type": "about:blank", "title": "LoteNaoEncontrado",
                                    "detail": "planeje de novo"}, "application/problem+json")


@pytest.fixture
def api(tmp_path):
    servidor = HTTPServer(("127.0.0.1", 0), _API)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}"
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": None, "stack": "rag", "endpoint": f"{base}/search",
        "indexacao": f"{base}/motor/indexacoes/lote", "token_em": "rag/RAG_API_TOKEN",
        "ajustes": [], "nao_e_ajuste": {}}}))
    _API.pedidos = []

    def roda(*args, sem_instancia=False):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_CADEIRA": "ia"}
        inicio = [] if sem_instancia else ["rag"]
        return subprocess.run([sys.executable, str(MOTOR), *inicio, *args], capture_output=True, text=True,
                              env=env, timeout=60, check=False)

    yield roda, _API.pedidos
    servidor.shutdown()


def test_o_plano_manda_as_obras_e_o_autor_e_nao_aplica(api):
    roda, pedidos = api
    r = roda("indexar", "biblioteca", "--obra", OBRA)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0].startswith("plano: 1 impressao(oes) · 1 a indexar (3 trechos a embedar)")
    assert OBRA in r.stdout and "para valer: o mesmo comando com --apply" in r.stdout
    metodo, caminho, auth, corpo = pedidos[-1]
    assert (metodo, caminho, auth) == ("POST", "/motor/indexacoes/lote", "Bearer tok")
    assert corpo == {"autor": "ia", "aplicar": False, "obras": [OBRA], "promover": False}


def test_apply_com_promover_abre_o_lote_e_devolve_como_acompanhar(api):
    roda, pedidos = api
    r = roda("indexar", "biblioteca", "--promover", "--apply", "--autor", "dados")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0].startswith(f"lote {LOTE} aberto no rag-api")
    assert f"acompanhar: motor rag indexar biblioteca --relatorio {LOTE}" in r.stdout
    assert pedidos[-1][3] == {"autor": "dados", "aplicar": True, "obras": [], "promover": True}


def test_relatorio_le_o_lote_e_o_id_perdido_sai_1(api):
    roda, pedidos = api
    r = roda("indexar", "biblioteca", "--relatorio", LOTE)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0].startswith(f"lote {LOTE}: concluido · indexada 1 · 3 vetores de trecho")
    assert pedidos[-1][:2] == ("GET", f"/motor/indexacoes/lote/{LOTE}")
    perdido = roda("indexar", "biblioteca", "--relatorio", "00000000-0000-4000-8000-000000000000")
    assert perdido.returncode == 1 and "LoteNaoEncontrado: planeje de novo" in perdido.stderr


def test_uso_errado_sai_2_sem_chamar_a_api(api):
    roda, pedidos = api
    assert roda("indexar", "casa").returncode == 2
    assert roda("indexar", "biblioteca", "--obra", "de1c6e97").returncode == 2  # prefixo não é uuid
    assert roda("indexar", "biblioteca", "--sem-isso").returncode == 2
    assert pedidos == []


def test_biblioteca_e_obra_sao_a_mesma_particao_e_a_api_recebe_obra(api):
    roda, pedidos = api
    for nome in ("biblioteca", "obra"):
        r = roda("buscar", nome, "pergunta")
        assert r.returncode == 0, r.stderr
        assert pedidos[-1][1] == "/search" and pedidos[-1][3]["particao"] == "obra"
        assert pedidos[-1][3]["pergunta"] == "pergunta"


def test_lote_pela_tool_com_instancia_e_ato_repetidos_busca_na_particao_pedida(api):
    # #2856 linha 23: `ato: buscar` com args [rag, buscar, casa, ...] chegava como
    # `motor buscar rag buscar casa ...`: buscava em biblioteca, com a pergunta «rag buscar casa ...».
    roda, pedidos = api
    r = roda("buscar", "rag", "buscar", "casa", "pergunta", sem_instancia=True)
    assert r.returncode == 0, r.stderr
    assert "sem particao" not in r.stderr
    assert pedidos[-1][3]["particao"] == "casa" and pedidos[-1][3]["pergunta"] == "pergunta"
