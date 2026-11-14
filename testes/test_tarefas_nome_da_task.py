"""Verbo tarefas: fora do banco, a task se chama só `t<n>` (incidente #4250, ordem do dono de 13/11/2026).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele), com uma story e três tasks de
ids da sequência dos cards, como as da 4216. O teste prova o que o VERBO imprime em cada ato que mostra
item: o nome da task é `t<n>`, e o id dela não aparece em linha nenhuma. O card segue pelo id.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin" / "tarefas"

STORY = 9216
IDS_DAS_TASKS = ("9230", "9239", "9240")
ESTADOS = [
    {"estado": "priorizada", "nome": "Priorizada", "fase": "funil", "natureza": "fila"},
    {"estado": "em-execucao", "nome": "Em execução", "fase": "delivery", "natureza": "ativo"},
    {"estado": "entregue", "nome": "Entregue", "fase": "terminal", "natureza": "terminal"},
]


def _task(id_, n, titulo, **extra):
    return {"id": id_, "chave": f"{STORY}.t{n}", "nivel": 3, "nivel_nome": "task", "pai": STORY,
            "titulo": titulo, "estado": "priorizada", "estado_nome": "Priorizada",
            "estado_fase": "funil", "estado_derivado": None, "cadeira": "conhecimento",
            "executor": "engenharia", "ancestrais": [], "bloqueia": [], "bloqueado_por": [],
            "descricao": "", "sign_offs": [], **extra}


def _filha(t, travada=False, bloqueada_por=()):
    return {"id": t["id"], "chave": t["chave"], "titulo": t["titulo"], "estado": t["estado"],
            "estado_derivado": None, "cadeira": t["cadeira"], "travada": travada,
            "bloqueada_por": list(bloqueada_por)}


T1 = _task(9230, 1, "Dar código às regras duras")
T4 = _task(9239, 4, "Pôr a organização no lote",
           bloqueado_por=[{"id": 9247, "chave": "9247", "titulo": "Trocar a ligação", "estado": "entregue"}])
T5 = _task(9240, 5, "Atualizar o documento do verbo",
           bloqueado_por=[{"id": 9230, "chave": f"{STORY}.t1", "titulo": T1["titulo"], "estado": "priorizada"}])
T1["bloqueia"] = [{"id": 9240, "chave": f"{STORY}.t5", "titulo": T5["titulo"], "estado": "priorizada"}]
TASKS = {9230: T1, 9239: T4, 9240: T5}

STORY_JSON = {
    "id": STORY, "chave": str(STORY), "nivel": 2, "nivel_nome": "story", "pai": 9205,
    "titulo": "Gravar a primeira fornada", "estado": "em-execucao", "estado_nome": "Em execução",
    "estado_fase": "delivery", "estado_derivado": None, "cadeira": "conhecimento",
    "ancestrais": [{"id": 9205, "titulo": "Ontologia", "nivel": 1}], "bloqueia": [], "bloqueado_por": [],
    "descricao": "<p>corpo</p>", "sign_offs": [],
    # a API manda o bloqueador da filha só com id, título e estado, sem a chave
    "filhas": [_filha(T1), _filha(T4),
               _filha(T5, travada=True, bloqueada_por=[{"id": 9230, "titulo": T1["titulo"], "estado": "priorizada"},
                                                     {"id": 9247, "titulo": "Trocar a ligação", "estado": "priorizada"}])],
}


class _Rastreador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _item(self, id_):
        if id_ == STORY:
            return STORY_JSON
        return TASKS.get(id_)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/registro":
            return self._json({"estados": ESTADOS})
        if url.path == "/modelo":  # a lista de rótulos que `comentar` pede para converter o corpo
            return self._json({"rotulos_da_conversao": ["Negócio"]})
        if url.path == "/itens":
            return self._json({"itens": [{**t, "estado_mostrado": t["estado"]} for t in TASKS.values()],
                               "estados": ESTADOS, "total": len(TASKS)})
        m = re.match(r"^/itens/chave/(\d+)\.t(\d+)$", url.path)
        if m:
            for t in TASKS.values():
                if t["chave"] == f"{m.group(1)}.t{m.group(2)}":
                    return self._json(t)
            return self._json({"erro": "chave"}, 404)
        m = re.match(r"^/itens/(\d+)$", url.path)
        if m and self._item(int(m.group(1))):
            return self._json(self._item(int(m.group(1))))
        self._json({"erro": "rota"}, 404)

    def do_PATCH(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        m = re.match(r"^/itens/(\d+)$", urlparse(self.path).path)
        item = self._item(int(m.group(1))) if m else None
        if not item:
            return self._json({"erro": "rota"}, 404)
        resp = {**item, **{k: v for k, v in corpo.items() if k in ("titulo", "pai")}}
        if corpo.get("estado"):
            resp.update(estado=corpo["estado"], estado_nome=corpo["estado"],
                        propagacao={"movidas": [{"id": 9230}, {"id": 9239}]})
        return self._json(resp)

    def do_DELETE(self):
        m = re.match(r"^/itens/(\d+)(?:/bloqueia/(\d+))?$", urlparse(self.path).path)
        if m and m.group(2):
            return self._json({"bloqueia": [], "bloqueado_por": []})
        if m:
            t = TASKS[int(m.group(1))]
            return self._json({"quantos": 1, "apagados": [{"id": t["id"], "estado": t["estado"],
                                                            "titulo": t["titulo"]}]})
        self._json({"erro": "rota"}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        self.rfile.read(n)
        p = urlparse(self.path).path
        if re.match(r"^/itens/\d+/bloqueia$", p):
            return self._json({"bloqueia": [{"id": 9240}], "bloqueado_por": []})
        if re.match(r"^/itens/\d+/comentarios$", p):
            return self._json({"id": 77, "item": 9230}, 201)
        if re.match(r"^/itens/\d+/posto$", p):
            return self._json({"id": 9230, "chave": f"{STORY}.t1", "posto": "zz", "titulo": T1["titulo"]})
        self._json({"erro": "rota"}, 404)


@pytest.fixture(scope="module")
def base():
    srv = HTTPServer(("127.0.0.1", 0), _Rastreador)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(base, *args):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="conhecimento",
               PF_FILA_BIN="/nao/existe")
    r = subprocess.run(["bash", str(BIN), *args], capture_output=True, text=True, env=env, timeout=60)
    return r.returncode, r.stdout + r.stderr


def _sem_id_de_task(saida):
    for id_ in IDS_DAS_TASKS:
        assert id_ not in saida, f"o id {id_} da task apareceu na saída:\n{saida}"


@pytest.mark.parametrize("args, esperado", [
    (("sub", str(STORY)), ["t1", "t4", "t5"]),
    (("listar", "--nivel", "task"), ["t1", "t4", "t5", f"story #{STORY}"]),
    (("listar-tudo", "--nivel", "task"), ["t1", "t4", "t5"]),
    (("ler", str(STORY)), ["t1", "t5", "[travada por t1, #9247]"]),
    (("ler", f"{STORY}.t5"), ["t5 · task", "bloqueado por: t1"]),
    (("editar", f"{STORY}.t1", "--titulo", "novo"), ["item t1 editado"]),
    (("mover", str(STORY), "em-execucao"), ["filhas movidas junto: t1, t4"]),
    (("apagar", f"{STORY}.t4"), ["  t4 [priorizada]"]),
    (("bloquear", f"{STORY}.t1", f"{STORY}.t5"), ["t1 bloqueia: t5"]),
    (("comentar", f"{STORY}.t1", "texto"), ["criado no item t1"]),
    (("ordenar", f"{STORY}.t1", "--antes-de", f"{STORY}.t5"), ["item t1 ficou antes de t5"]),
    (("sub", str(STORY), f"{STORY}.t1"), ["item t1 agora é filho de 9216"]),
])
def test_a_task_sai_so_como_t_n(base, args, esperado):
    rc, saida = _run(base, *args)
    assert rc == 0, saida
    for trecho in esperado:
        assert trecho in saida, f"faltou «{trecho}» em:\n{saida}"
    _sem_id_de_task(saida)
