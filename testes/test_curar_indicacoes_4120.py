"""#4120, U7: `acervo curar conceitos --indicacoes <lote>` — a curadoria em lote das indicações.

O classificador indica o conceito candidato com a obra como garantia (item 19). Este ato junta as indicações do
lote e cria cada conceito uma vez. Sem --apply mostra o plano; quem cria conceito no tesauro é a cadeira conhecimento,
então o --apply de outra cadeira recusa antes de falar com o servidor.
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
LOTE = "22222222-2222-4222-8222-222222222222"

PLANO = {"plano": True, "lote_id": LOTE, "total_termos": 2, "itens": [
    {"termo": "Governança de dados", "slug": "governanca-de-dados", "obras_contagem": 3,
     "obras": ["o1", "o2", "o3"], "indicacao_ids": ["i1", "i2", "i3"]},
    {"termo": "Catálogo", "slug": "catalogo", "obras_contagem": 1, "obras": ["o4"], "indicacao_ids": ["i4"]},
]}
APLICADO = {"aplicado": True, "lote_id": LOTE, "indicacoes_admitidas": 4, "criados": [
    {"id": "c1", "slug": "governanca-de-dados", "rotulo": "Governança de dados"},
    {"id": "c2", "slug": "catalogo", "rotulo": "Catálogo", "ja_existia": True},
]}


class _Handler(BaseHTTPRequestHandler):
    falso: "Falso"

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        corpo = json.loads(self.rfile.read(n) or b"null")
        self.falso.chamadas.append((self.path, corpo))
        if self.path != "/acervo/indicacoes":
            status, obj = 404, {"title": "NaoEncontrado", "detail": self.path}
        else:
            status, obj = (201, APLICADO) if corpo.get("aplicar") else (200, PLANO)
        dados = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


class Falso:
    def __init__(self):
        self.chamadas = []
        handler = type("H", (_Handler,), {"falso": self})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()

    def rodar(self, *argv, cadeira="conhecimento"):
        env = {**os.environ, "MOTOR_ACERVO_URL": self.url, "RAG_API_URL": "", "RAG_API_BASE": "",
               "RAG_API_TOKEN": "tok-ind", "PF_CADEIRA": cadeira, "PF_SESSAO_ID": f"t-{uuid.uuid4().hex}"}
        return subprocess.run(["bash", str(ACERVO), *argv], capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, timeout=60, check=False)


@pytest.fixture
def servidor():
    f = Falso()
    try:
        yield f
    finally:
        f.fechar()


def test_sem_apply_mostra_o_plano_e_nao_cria_nada(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE)
    assert r.returncode == 0, r.stderr
    assert "plano: 2 conceito(s) a criar" in r.stdout
    assert "Governança de dados -> governanca-de-dados · 3 obra(s) de garantia" in r.stdout
    assert "plano seco" in r.stdout
    assert servidor.chamadas == [("/acervo/indicacoes", {"lote_id": LOTE, "aplicar": False})]


def test_apply_da_cadeira_conhecimento_cria_cada_conceito_uma_vez(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE, "--apply")
    assert r.returncode == 0, r.stderr
    assert "governanca-de-dados: criado" in r.stdout
    assert "catalogo: já existia" in r.stdout
    assert "indicações admitidas: 4" in r.stdout
    assert servidor.chamadas == [("/acervo/indicacoes", {"lote_id": LOTE, "aplicar": True})]


def test_apply_de_outra_cadeira_recusa_sem_falar_com_o_servidor(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE, "--apply", cadeira="engenharia")
    assert r.returncode == 4
    assert "quem cria conceito no tesauro é a cadeira conhecimento" in r.stderr
    assert servidor.chamadas == []


def test_apply_da_cadeira_dados_recusa_porque_o_ato_e_de_conhecimento(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE, "--apply", cadeira="dados")
    assert r.returncode == 4
    assert "quem cria conceito no tesauro é a cadeira conhecimento" in r.stderr
    assert servidor.chamadas == []


def test_todas_as_indicacoes_e_termos_escolhidos_vao_no_corpo(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", "todas", "--termos", "catalogo, governanca-de-dados")
    assert r.returncode == 0, r.stderr
    assert servidor.chamadas == [("/acervo/indicacoes", {
        "lote_id": None, "aplicar": False, "termos": ["catalogo", "governanca-de-dados"]})]


def test_a_forma_pela_particao_biblioteca_chega_ao_mesmo_ato(servidor):
    r = servidor.rodar("curar", "biblioteca", "conceitos", "--indicacoes", LOTE)
    assert r.returncode == 0, r.stderr
    assert "plano: 2 conceito(s) a criar" in r.stdout


def test_sem_indicacoes_sai_2(servidor):
    r = servidor.rodar("curar", "conceitos")
    assert r.returncode == 2 and "uso: acervo curar conceitos --indicacoes" in r.stderr
    assert servidor.chamadas == []


def test_json_devolve_o_corpo_do_servidor(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE, "--json")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["total_termos"] == 2
