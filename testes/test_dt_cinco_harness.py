"""Testes de regressão para os 5 débitos técnicos resolvidos no harness:
- DT 83: tarefas estados filtra estados retirados (retirado != true)
- DT 204: tarefas sub <pai> com 1 argumento lista as filhas
- DT 252: release migrar aplicar recusa com exit 2 quando stdin vem vazio
- DT 270: tarefas criar e editar passam corpo ao jq sem --arg para evitar estouro de exec
- DT 1: repo resolve <repo>@<card> casando <card>-<slug>
"""
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN_TAREFAS = REPO_ROOT / "bin" / "tarefas"
BIN_REPO = REPO_ROOT / "bin" / "repo"
BIN_MIGRAR = REPO_ROOT / "bin" / "_release" / "migrar"


class _MockRastreador(BaseHTTPRequestHandler):
    pedidos: ClassVar[list] = []
    registro_estados: ClassVar[list] = [
        {"estado": "captada", "nome": "Captada", "fase": "funil", "retirado": False},
        {"estado": "refinada", "nome": "Refinada", "fase": "delivery", "retirado": True},
        {"estado": "em-execucao", "nome": "Em execução", "fase": "delivery", "retirado": False},
    ]
    item_resposta: ClassVar[dict] = {
        "id": 100,
        "titulo": "Item pai",
        "filhas": [
            {"id": 101, "estado": "em-execucao", "cadeira": "engenharia", "titulo": "Filha 1"},
            {"id": 102, "estado": "captada", "cadeira": "arquiteto", "titulo": "Filha 2"},
        ]
    }

    def log_message(self, *a):
        pass

    def _envia_json(self, payload, status=200):
        corpo = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/registro":
            return self._envia_json({"estados": self.registro_estados})
        if self.path.startswith("/itens/"):
            return self._envia_json(self.item_resposta)
        self._envia_json({"erro": "nao encontrado"}, 404)

    def do_POST(self):
        tam = int(self.headers.get("Content-Length", 0))
        dados = json.loads(self.rfile.read(tam) or b"{}")
        type(self).pedidos.append(("POST", self.path, dados))
        if self.path == "/itens":
            return self._envia_json({"id": 200, "titulo": dados.get("titulo", "")}, 201)
        self._envia_json({"erro": "nao encontrado"}, 404)

    def do_PATCH(self):
        tam = int(self.headers.get("Content-Length", 0))
        dados = json.loads(self.rfile.read(tam) or b"{}")
        type(self).pedidos.append(("PATCH", self.path, dados))
        if self.path.startswith("/itens/"):
            return self._envia_json({"id": 100, "titulo": "Item editado", "estado_nome": "Captada"}, 200)
        self._envia_json({"erro": "nao encontrado"}, 404)


@pytest.fixture()
def rastreador_mock():
    _MockRastreador.pedidos = []
    srv = HTTPServer(("127.0.0.1", 0), _MockRastreador)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_dt83_estados_filtra_retirados(rastreador_mock):
    env = dict(os.environ, TAREFAS_BASE=rastreador_mock, PF_CADEIRA="engenharia")
    p = subprocess.run([str(BIN_TAREFAS), "estados"], capture_output=True, text=True, env=env, timeout=30, check=False)
    assert p.returncode == 0, p.stderr
    assert "refinada" not in p.stdout
    assert "captada\tfunil\tCaptada" in p.stdout
    assert "em-execucao\tdelivery\tEm execução" in p.stdout


def test_dt204_sub_com_um_arg_lista_filhas(rastreador_mock):
    env = dict(os.environ, TAREFAS_BASE=rastreador_mock, PF_CADEIRA="engenharia")
    p = subprocess.run([str(BIN_TAREFAS), "sub", "100"], capture_output=True, text=True, env=env, timeout=30, check=False)
    assert p.returncode == 0, p.stderr
    assert "#101\tem-execucao\tengenharia\tFilha 1" in p.stdout
    assert "#102\tcaptada\tarquiteto\tFilha 2" in p.stdout


def test_dt270_criar_e_editar_passam_corpo_ao_jq_sem_arg(rastreador_mock):
    env = dict(os.environ, TAREFAS_BASE=rastreador_mock, PF_CADEIRA="engenharia")
    corpo_longo = "Parágrafo 1 com texto longo.\n\nParágrafo 2 com markdown e crases: `codigo`."

    p1 = subprocess.run(
        [str(BIN_TAREFAS), "criar", "Card Teste", "--desc", corpo_longo],
        capture_output=True, text=True, env=env, timeout=30, check=False
    )
    assert p1.returncode == 0, p1.stderr
    assert "item 200 criado: Card Teste" in p1.stdout

    p2 = subprocess.run(
        [str(BIN_TAREFAS), "editar", "100", "--desc", corpo_longo],
        capture_output=True, text=True, env=env, timeout=30, check=False
    )
    assert p2.returncode == 0, p2.stderr
    assert "item 100 editado:" in p2.stdout


def test_dt252_migrar_aplicar_recusa_sem_stdin():
    env = dict(os.environ, PF_SUJEITO="operador-teste@82b853de")
    p = subprocess.run(
        [str(BIN_MIGRAR), "aplicar", "rag"],
        input="", capture_output=True, text=True, env=env, timeout=30, check=False
    )
    assert p.returncode == 2, p.stdout
    assert "falta o SQL da migracao por STDIN" in p.stderr


def _monta_bancada_com_worktree(tmp_path: Path, repo: str, cadeira: str, pasta: str):
    bancada = tmp_path / "bancada"
    clone = bancada / repo
    clone.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main", str(clone)], check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-C", str(clone), "config", "user.name", "T"], check=True, timeout=30)
    subprocess.run(["git", "-C", str(clone), "config", "user.email", "t@t.org"], check=True, timeout=30)
    (clone / "f").write_text("x")
    subprocess.run(["git", "-C", str(clone), "add", "f"], check=True, timeout=30)
    subprocess.run(["git", "-C", str(clone), "commit", "-m", "i"], check=True, timeout=30)
    wt = bancada / "wt" / repo / cadeira / pasta
    wt.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(clone), "worktree", "add", "-b", f"{cadeira}/{pasta}", str(wt)], check=True, capture_output=True, timeout=30)
    return bancada


def test_dt1_bancada_de_com_card_num(tmp_path):
    bancada = _monta_bancada_com_worktree(tmp_path, "platafirma-teste", "engenharia", "3169-guia-operacao")
    env = dict(os.environ, PLATAFIRMA_BANCADA=str(bancada), PF_CADEIRA="engenharia")
    p = subprocess.run(
        [str(BIN_REPO), "estado", "platafirma-teste@3169"],
        capture_output=True, text=True, env=env, timeout=30, check=False
    )
    assert p.returncode == 0, p.stderr
    assert "3169-guia-operacao" in p.stdout
