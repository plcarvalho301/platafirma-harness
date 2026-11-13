"""Verbo tarefas: a task se chama pela chave da story, `<story>.t<n>` (incidente #4245).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele). Prova o que o VERBO faz:
a chave que a pessoa digita vira o id que a rota endereça (`GET /itens/chave/<chave>`), o `#`
continua aceito, o id de card segue como era, a chave que não existe sobe como a recusa do
rastreador, e as telas do verbo (`criar`, `mover`, a leitura da story) mostram a chave e nunca o id
interno da task. Quem numera e quem guarda a chave é o rastreador
(`platafirma-rastreador@api/tests/test_task_chave_por_story.py`, sql/029).
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
    {"estado": "entregue", "fase": "terminal", "natureza": "terminal"},
]}

# o id interno da task: longe da sequência dos cards, e nunca aparece na tela
ID_INTERNO = 1000000003


def _item(id_, chave, nivel, nome, **extra):
    return {"id": id_, "chave": chave, "titulo": f"item {chave}", "nivel": nivel,
            "nivel_nome": nome, "estado": "em-execucao", "estado_nome": "Em execução",
            "estado_fase": "delivery", "estado_natureza": "ativo", "estado_derivado": None,
            "cadeira": "engenharia", "ancestrais": [], "sign_offs": [], "descricao": "corpo",
            "filhas": [], **extra}


class _Stub(BaseHTTPRequestHandler):
    itens: dict = {}
    chamadas: list = []

    def log_message(self, *a):
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        type(self).chamadas.append(("GET", self.path))
        if self.path == "/registro":
            return self._json(REGISTRO)
        m = re.match(r"^/itens/chave/(.+)$", self.path)
        if m:
            for it in self.itens.values():
                if it["chave"] == m.group(1):
                    return self._json({"id": it["id"], "chave": it["chave"]})
            return self._json({"erro": f"item {m.group(1)} não existe"}, 404)
        m = re.match(r"^/itens/(\d+)$", self.path)
        if m and int(m.group(1)) in self.itens:
            return self._json(self.itens[int(m.group(1))])
        self._json({"erro": "nao existe"}, 404)

    def do_PATCH(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        type(self).chamadas.append(("PATCH", self.path, corpo))
        m = re.match(r"^/itens/(\d+)", self.path)
        if m and int(m.group(1)) in self.itens:
            return self._json({**self.itens[int(m.group(1))], "estado": corpo["estado"],
                               "estado_nome": "Entregue", "estado_natureza": "terminal"})
        self._json({"erro": "nao existe"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        type(self).chamadas.append(("POST", self.path, corpo))
        if corpo.get("nivel") == 3:
            return self._json({"id": ID_INTERNO, "chave": "7.t3", "titulo": corpo["titulo"]}, 201)
        return self._json({"id": 9001, "chave": "9001", "titulo": corpo["titulo"]}, 201)


@pytest.fixture()
def stub():
    _Stub.itens, _Stub.chamadas = {}, []
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env, timeout=30)


def test_ler_pela_chave_da_task_resolve_para_o_id_e_le_o_item(stub):
    s, base = stub
    s.itens[ID_INTERNO] = _item(ID_INTERNO, "7.t3", 3, "task")
    p = _run(["ler", "7.t3"], base)
    assert p.returncode == 0, p.stderr
    assert ("GET", "/itens/chave/7.t3") in s.chamadas
    assert ("GET", f"/itens/{ID_INTERNO}") in s.chamadas
    # o nome exibido é só t3, e o id interno não aparece
    assert "t3 · task ·" in p.stdout and "#7.t3" not in p.stdout
    assert str(ID_INTERNO) not in p.stdout


def test_o_sustenido_antes_da_chave_e_aceito(stub):
    s, base = stub
    s.itens[ID_INTERNO] = _item(ID_INTERNO, "7.t3", 3, "task")
    p = _run(["ler", "#7.t3"], base)
    assert p.returncode == 0, p.stderr
    assert ("GET", "/itens/chave/7.t3") in s.chamadas


def test_id_de_card_segue_sem_resolver_chave(stub):
    s, base = stub
    s.itens[7] = _item(7, "7", 2, "story")
    p = _run(["ler", "7"], base)
    assert p.returncode == 0, p.stderr
    assert not any(c[1].startswith("/itens/chave/") for c in s.chamadas)
    p = _run(["ler", "#7"], base)
    assert p.returncode == 0, p.stderr
    assert not any(c[1].startswith("/itens/chave/") for c in s.chamadas)


def test_chave_que_nao_existe_sobe_a_recusa_do_rastreador(stub):
    s, base = stub
    p = _run(["ler", "7.t9"], base)
    assert p.returncode != 0
    assert "7.t9 não existe" in p.stdout + p.stderr


def test_mover_a_task_pela_chave_patcha_o_id_e_mostra_a_chave(stub):
    s, base = stub
    s.itens[ID_INTERNO] = _item(ID_INTERNO, "7.t3", 3, "task")
    p = _run(["mover", "7.t3", "entregue"], base)
    assert p.returncode == 0, p.stderr
    assert any(c[0] == "PATCH" and c[1].startswith(f"/itens/{ID_INTERNO}") for c in s.chamadas)
    assert "item t3 →" in p.stdout
    assert str(ID_INTERNO) not in p.stdout


def test_criar_task_mostra_a_chave_e_nao_o_id_interno(stub):
    s, base = stub
    p = _run(["criar", "task de prova", "--nivel", "task", "--pai", "7"], base)
    assert p.returncode == 0, p.stderr
    assert "item t3 criado: task de prova" in p.stdout
    assert str(ID_INTERNO) not in p.stdout


def test_criar_card_segue_mostrando_o_numero_do_card(stub):
    s, base = stub
    p = _run(["criar", "story de prova", "--nivel", "story"], base)
    assert p.returncode == 0, p.stderr
    assert "item 9001 criado: story de prova" in p.stdout


def test_a_leitura_da_story_lista_as_tasks_pela_chave(stub):
    s, base = stub
    s.itens[7] = _item(7, "7", 2, "story", filhas=[
        {"id": 11, "chave": "7.t1", "titulo": "task concluída", "estado": "entregue", "cadeira": "engenharia"},
        {"id": ID_INTERNO, "chave": "7.t2", "titulo": "task aberta", "estado": "em-execucao",
         "cadeira": "engenharia"},
    ])
    p = _run(["ler", "7"], base)
    assert p.returncode == 0, p.stderr
    linhas = p.stdout.splitlines()
    i = linhas.index("tasks (1 abertas de 2):")
    assert linhas[i + 1].startswith("  1. t1\t") and "concluída" in linhas[i + 1]
    assert linhas[i + 2].startswith("  2. t2\t") and "aberta" in linhas[i + 2]
    assert "7.t" not in p.stdout and str(ID_INTERNO) not in p.stdout


def test_os_vinculos_da_task_exibem_t_n_e_os_do_card_seguem_com_sustenido(stub):
    s, base = stub
    s.itens[ID_INTERNO] = _item(
        ID_INTERNO, "7.t3", 3, "task",
        bloqueia=[{"id": 1000000004, "chave": "7.t4", "titulo": "x", "estado": "em-execucao"}],
        bloqueado_por=[{"id": 11, "chave": "7.t1", "titulo": "y", "estado": "em-execucao"},
                       {"id": 40, "chave": "40", "titulo": "z", "estado": "em-execucao"}])
    p = _run(["ler", "7.t3"], base)
    assert p.returncode == 0, p.stderr
    assert "bloqueia: t4 (em-execucao)" in p.stdout
    assert "bloqueado por: t1 (em-execucao), #40 (em-execucao)" in p.stdout
    assert "travada por: t1 (em-execucao), #40 (em-execucao)" in p.stdout
    assert "1000000004" not in p.stdout
