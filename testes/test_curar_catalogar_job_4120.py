"""#4120, U7: `acervo catalogar biblioteca obra --job <id>` — a classificação pela sessão.

A classificadora é a própria sessão que roda a ingestão. O ato serve a ela o pedido do job (cabeçalho fixo na
parte 1, a ficha e a lista fechada de cada obra, o glossário) em partes de até 45 KB, e recebe dela a resposta
em JSON pelo stdin. A validação contra a lista fechada e o teto de 5 conceitos é do servidor; o cliente só
leva o pedido e traz o que ele recusou. Roda o ato de verdade, como subprocesso, contra um servidor falso.
"""

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
JOB = "11111111-1111-4111-8111-111111111111"

PEDIDO_PARTE_1 = {
    "job_id": JOB, "parte": 1, "total_partes": 2, "total_obras": 3,
    "cabecalho": {"instrucoes": "classifique", "teto_conceitos": 5, "especies": [{"slug": "livro"}]},
    "glossario": {"c1": {"rotulo": "C1", "definicao": "d1"}},
    "obras": [{"obra_id": "o1", "titulo": "Obra 1", "candidatos": ["c1"]}],
}
PEDIDO_PARTE_2 = {"job_id": JOB, "parte": 2, "total_partes": 2, "total_obras": 3,
                  "obras": [{"obra_id": "o2", "titulo": "Obra 2", "candidatos": ["c1"]}]}


class _Handler(BaseHTTPRequestHandler):
    falso: "Falso"

    def log_message(self, *a):
        pass

    def _resp(self, status, obj):
        dados = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        self.falso.chamadas.append(("GET", self.path, None, self.headers.get("authorization")))
        if self.path == f"/acervo/jobs/{JOB}/classificacao?parte=1":
            return self._resp(200, PEDIDO_PARTE_1)
        if self.path == f"/acervo/jobs/{JOB}/classificacao?parte=2":
            return self._resp(200, PEDIDO_PARTE_2)
        return self._resp(404, {"title": "NaoEncontrado", "detail": self.path})

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        corpo = json.loads(self.rfile.read(n) or b"null")
        self.falso.chamadas.append(("POST", self.path, corpo, self.headers.get("authorization")))
        if self.path == f"/acervo/jobs/{JOB}/classificacao":
            return self._resp(200, self.falso.resposta_do_post)
        return self._resp(404, {"title": "NaoEncontrado", "detail": self.path})


class Falso:
    def __init__(self):
        self.chamadas = []
        self.resposta_do_post = {"job_id": JOB, "total_aceitas": 1, "total_recusadas": 0, "aceitas": [], "recusadas": []}
        handler = type("H", (_Handler,), {"falso": self})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()

    def rodar(self, *argv, stdin=None, url=None):
        env = {**os.environ, "MOTOR_ACERVO_URL": url or self.url, "RAG_API_URL": "", "RAG_API_BASE": "",
               "RAG_API_TOKEN": "tok-job", "PF_CADEIRA": "engenharia",
               # o aviso de forma vigente sai uma vez por sessão: cada chamada leva uma nova
               "PF_SESSAO_ID": f"t-{uuid.uuid4().hex}"}
        return subprocess.run(["bash", str(ACERVO), *argv], capture_output=True, text=True, env=env,
                              input=stdin, stdin=None if stdin is not None else subprocess.DEVNULL,
                              timeout=60, check=False)


@pytest.fixture
def servidor():
    f = Falso()
    try:
        yield f
    finally:
        f.fechar()


def test_pedido_da_parte_1_traz_o_cabecalho_uma_vez_e_diz_quantas_partes_ha(servidor):
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB)
    assert r.returncode == 0, r.stderr
    pedido = json.loads(r.stdout)
    assert pedido["parte"] == 1 and pedido["total_partes"] == 2
    assert "cabecalho" in pedido and "glossario" in pedido
    assert "parte 1 de 2" in r.stderr
    assert servidor.chamadas == [("GET", f"/acervo/jobs/{JOB}/classificacao?parte=1", None, "Bearer tok-job")]


def test_parte_seguinte_vem_sem_cabecalho(servidor):
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB, "--parte", "2")
    assert r.returncode == 0, r.stderr
    pedido = json.loads(r.stdout)
    assert pedido["parte"] == 2 and "cabecalho" not in pedido and "glossario" not in pedido
    assert "parte 2 de 2" in r.stderr


def test_resposta_vai_ao_servidor_como_veio_e_sai_0_quando_nada_foi_recusado(servidor):
    resposta = [{"obra_id": "o1", "conceitos": ["c1"], "especie": "livro"}]
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB, "--resposta", stdin=json.dumps(resposta))
    assert r.returncode == 0, r.stderr
    assert servidor.chamadas == [("POST", f"/acervo/jobs/{JOB}/classificacao", resposta, "Bearer tok-job")]
    assert json.loads(r.stdout)["total_aceitas"] == 1
    assert "aceitas 1, recusadas 0" in r.stderr


def test_o_que_o_servidor_recusou_volta_dito_e_a_saida_e_1(servidor):
    servidor.resposta_do_post = {
        "job_id": JOB, "total_aceitas": 0, "total_recusadas": 1, "aceitas": [],
        "recusadas": [{"obra_id": "o1", "motivo": "conceitos fora da lista fechada de candidatos: ['x']"}],
    }
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB, "--resposta",
                       stdin=json.dumps([{"obra_id": "o1", "conceitos": ["x"]}]))
    assert r.returncode == 1
    assert "recusada o1: conceitos fora da lista fechada" in r.stderr
    assert json.loads(r.stdout)["total_recusadas"] == 1


def test_resposta_sem_stdin_ou_sem_json_sai_2_sem_falar_com_o_servidor(servidor):
    vazio = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB, "--resposta", stdin="")
    ruim = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB, "--resposta", stdin="isto não é json")
    assert vazio.returncode == 2 and "pelo stdin" in vazio.stderr
    assert ruim.returncode == 2 and "não é JSON" in ruim.stderr
    assert servidor.chamadas == []


@pytest.mark.parametrize("extra", [("--obra", "x"), ("--trata-de", "a"), ("--apply",), ("--dominio", "d")])
def test_job_nao_combina_com_a_obra_avulsa(servidor, extra):
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB, *extra)
    assert r.returncode == 2
    assert "não combina com" in r.stderr
    assert servidor.chamadas == []


def test_parte_invalida_sai_2(servidor):
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB, "--parte", "zero")
    assert r.returncode == 2 and "--parte pede um número" in r.stderr
    assert servidor.chamadas == []


def test_job_sem_id_sai_2(servidor):
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job")
    assert r.returncode == 2 and "falta o id do job" in r.stderr


def test_job_que_o_servidor_nao_conhece_sai_1_com_a_causa(servidor):
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", "00000000-0000-4000-8000-000000000000")
    assert r.returncode == 1
    assert "NaoEncontrado" in r.stderr


def test_servidor_fora_sai_3(servidor):
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB, url="http://127.0.0.1:9")
    assert r.returncode == 3
    assert "rota fora" in r.stderr


def test_o_ato_nao_traz_flag_que_bin_curar_recusaria(servidor):
    # antes desta entrega o verbo caía em bin/curar: «argumento que o verbo não lê: --job»
    r = servidor.rodar("catalogar", "biblioteca", "obra", "--job", JOB)
    assert "argumento que o verbo não lê" not in r.stderr
