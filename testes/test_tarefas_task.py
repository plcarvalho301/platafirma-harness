"""Verbo tarefas: a task como passo da story (card #4223, R37 da spec tarefas).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele): o teste prova o que o
VERBO faz — o pedido que `criar --nivel task` envia, a recusa antes de chamar a API quando falta
o pai, a recusa da API que sobe, e a leitura da story com as tasks dela, abertas e concluídas, na
ordem. Quem recusa o pai que não é story é a API (`platafirma-rastreador@api/tests/
test_task_passo_da_story.py`); o Aceite contra o rastreador no ar é o do card.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "bin" / "tarefas"

REGISTRO = {"estados": [
    {"estado": "em-execucao", "fase": "delivery", "natureza": "ativo"},
    {"estado": "priorizada", "fase": "funil", "natureza": "fila"},
    {"estado": "entregue", "fase": "terminal", "natureza": "terminal"},
    {"estado": "cancelada", "fase": "terminal", "natureza": "terminal"},
]}


def _item(id_, nivel, nome, filhas=None, **extra):
    return {"id": id_, "titulo": f"item {id_}", "nivel": nivel, "nivel_nome": nome,
            "estado": "em-execucao", "estado_nome": "Em execução", "estado_fase": "delivery",
            "estado_derivado": None, "cadeira": "engenharia", "ancestrais": [],
            "sign_offs": [], "descricao": "corpo", "filhas": filhas or [], **extra}


class _Stub(BaseHTTPRequestHandler):
    posts: list = []
    itens: dict = {}
    recusa_post: tuple | None = None

    def log_message(self, *a):  # silencioso
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path == "/registro":
            return self._json(REGISTRO)
        m = re.match(r"^/itens/(\d+)$", self.path)
        if m and int(m.group(1)) in self.itens:
            return self._json(self.itens[int(m.group(1))])
        self._json({"erro": "nao existe"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        type(self).posts.append((self.path, corpo))
        if self.recusa_post:
            status, erro = self.recusa_post
            return self._json({"erro": erro}, status)
        return self._json({"id": 9001, "titulo": corpo["titulo"]}, 201)


@pytest.fixture()
def stub():
    _Stub.posts, _Stub.itens, _Stub.recusa_post = [], {}, None
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env, timeout=30)


def test_criar_task_sem_pai_diz_o_comando_e_nao_chama_a_api(stub):
    s, base = stub
    p = _run(["criar", "task de prova", "--nivel", "task"], base)
    assert p.returncode == 2
    assert "--nivel task --pai <story>" in p.stderr and "dt admitir" in p.stderr
    assert not s.posts


def test_criar_task_com_story_como_pai_envia_nivel_3_e_o_pai(stub):
    s, base = stub
    p = _run(["criar", "task de prova", "--nivel", "task", "--pai", "7"], base)
    assert p.returncode == 0, p.stderr
    assert "item 9001 criado: task de prova" in p.stdout
    (caminho, corpo), = s.posts
    assert caminho == "/itens"
    assert corpo["nivel"] == 3 and corpo["pai"] == 7 and corpo["titulo"] == "task de prova"
    assert "descricao" not in corpo  # a task nasce só com o título


def test_criar_task_com_pai_que_a_api_recusa_sobe_a_recusa(stub):
    s, base = stub
    s.recusa_post = (400, "o pai da task é de nível 1, e o pai da task tem de ser uma story")
    p = _run(["criar", "x", "--nivel", "task", "--pai", "4219"], base)
    assert p.returncode != 0
    assert "tem de ser uma story" in p.stdout + p.stderr


def test_ler_a_story_traz_todas_as_tasks_na_ordem_com_o_estado_de_cada_uma(stub):
    s, base = stub
    s.itens[7] = _item(7, 2, "story", filhas=[
        {"id": 11, "titulo": "task concluída", "estado": "entregue", "cadeira": "engenharia"},
        {"id": 12, "titulo": "task aberta", "estado": "em-execucao", "cadeira": "engenharia"},
        {"id": 13, "titulo": "task seguinte", "estado": "priorizada", "cadeira": "engenharia",
         "travada": True, "bloqueada_por": [12]},
    ])
    p = _run(["ler", "7"], base)
    assert p.returncode == 0, p.stderr
    linhas = p.stdout.splitlines()
    i = linhas.index("tasks (2 abertas de 3):")
    assert linhas[i + 1].startswith("  1. #11") and "concluída" in linhas[i + 1]
    assert linhas[i + 2].startswith("  2. #12") and "aberta" in linhas[i + 2]
    assert linhas[i + 3].startswith("  3. #13") and "[travada por #12]" in linhas[i + 3]
    assert "filhas (abertas)" not in p.stdout


def test_ler_a_story_sem_task_nao_imprime_lista(stub):
    s, base = stub
    s.itens[7] = _item(7, 2, "story")
    p = _run(["ler", "7"], base)
    assert p.returncode == 0, p.stderr
    assert "tasks (" not in p.stdout


def test_ler_a_feature_segue_com_as_filhas_abertas(stub):
    s, base = stub
    s.itens[4] = _item(4, 1, "feature", filhas=[
        {"id": 7, "titulo": "story aberta", "estado": "em-execucao", "cadeira": "engenharia"},
        {"id": 8, "titulo": "story fechada", "estado": "entregue", "cadeira": "engenharia"},
    ])
    p = _run(["ler", "4"], base)
    assert p.returncode == 0, p.stderr
    assert "filhas (abertas):" in p.stdout and "#7" in p.stdout and "#8" not in p.stdout
    assert "tasks (" not in p.stdout
