# componente: componente:verbo-tarefas
"""Verbo tarefas: o nível ideia (card #4339, classe `ideia` da Olaria, filha de `card`).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele): o teste prova o que o
VERBO faz — traduz o nome `ideia` para o nível 4 em `criar`, `listar` e `editar`, nasce em captada
só com o título, e sobe a recusa da API quando se tenta dar pai à ideia. Quem recusa o pai, o funil
e a troca de nível é a API (`platafirma-rastreador@api/tests/test_nivel_ideia.py`); o Aceite
contra o rastreador no ar é o do card.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parents[1] / "bin" / "tarefas"


class _Stub(BaseHTTPRequestHandler):
    posts: list = []
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

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        type(self).posts.append((self.path, corpo))
        if self.recusa_post:
            status, erro = self.recusa_post
            return self._json({"erro": erro}, status)
        return self._json({"id": 9002, "titulo": corpo["titulo"]}, 201)


@pytest.fixture()
def stub():
    _Stub.posts, _Stub.recusa_post = [], None
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="gestao-estrategica")
    env.pop("PF_ESTADO_INICIAL", None)
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env, timeout=30)


def test_criar_ideia_envia_nivel_4_em_captada_so_com_o_titulo(stub):
    s, base = stub
    p = _run(["criar", "tema de prova", "--nivel", "ideia"], base)
    assert p.returncode == 0, p.stderr
    assert "item 9002 criado: tema de prova" in p.stdout
    (caminho, corpo), = s.posts
    assert caminho == "/itens"
    assert corpo["nivel"] == 4 and corpo["estado"] == "captada"
    assert "descricao" not in corpo and "pai" not in corpo  # a ideia nasce só com o título


def test_criar_ideia_pelo_numero_do_nivel_tambem_funciona(stub):
    s, base = stub
    p = _run(["criar", "tema de prova", "--nivel", "4"], base)
    assert p.returncode == 0, p.stderr
    assert s.posts[0][1]["nivel"] == 4


def test_criar_ideia_com_pai_sobe_a_recusa_da_api(stub):
    s, base = stub
    s.recusa_post = (400, "a ideia não tem pai: ela guarda um tema sem compromisso")
    p = _run(["criar", "ideia com pai", "--nivel", "ideia", "--pai", "7"], base)
    assert p.returncode != 0
    assert "a ideia não tem pai" in p.stdout + p.stderr
    # o verbo leva o pedido como veio: quem sabe a regra é a API
    assert s.posts[0][1]["pai"] == 7 and s.posts[0][1]["nivel"] == 4


def test_nivel_desconhecido_lista_a_ideia_entre_os_niveis_validos(stub):
    s, base = stub
    for args in (["criar", "x", "--nivel", "zzz"], ["listar", "--nivel", "zzz"],
                 ["editar", "42", "--titulo", "t", "--nivel", "zzz"]):
        p = _run(args, base)
        assert p.returncode == 2, (args, p.stderr)
        assert "ideia" in p.stderr, (args, p.stderr)
    assert not s.posts


def test_a_ajuda_do_criar_diz_o_que_a_ideia_e_e_como_ela_sai(stub):
    s, base = stub
    p = _run(["--help"], base)
    texto = p.stdout + p.stderr
    assert "--nivel ideia" in texto
    assert "mover <id> englobada --englobado-em <card>" in texto
    assert 'mover <id> descartada --motivo' in texto
