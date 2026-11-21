# componente: componente:verbo-curar
"""#4120, U7: `acervo curar conceitos --indicacoes <lote>` — a curadoria em lote das indicações.

O classificador indica o conceito candidato com a obra como garantia (item 19). Este ato leva cada termo a um
destino: liga as obras ao conceito que já existe, cria o conceito uma vez, ou deixa pendente o termo sem obra
viva de garantia, que só sai por --descartar (DT 806). Sem --apply mostra o plano; com --apply, qualquer cadeira
que roda o pipeline grava, em nome do curador dela.
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

PLANO = {"plano": True, "lote_id": LOTE, "total_termos": 3, "itens": [
    {"termo": "Governança de dados", "slug": "governanca-de-dados", "obras_contagem": 3,
     "obras": ["o1", "o2", "o3"], "indicacao_ids": ["i1", "i2", "i3"], "de_obra_retirada": [],
     "acao": "criar", "conceito": "governanca-de-dados"},
    {"termo": "Catálogo", "slug": "catalogo", "obras_contagem": 1, "obras": ["o4"], "indicacao_ids": ["i4", "i5"],
     "de_obra_retirada": ["i5"], "acao": "ligar_existente", "conceito_id": "c2", "conceito": "catalogo"},
    {"termo": "Licença", "slug": "licenca", "obras_contagem": 0, "obras": [], "indicacao_ids": ["i6"],
     "de_obra_retirada": ["i6"], "acao": "sem_garantia", "motivo": "nenhuma obra viva sustenta o termo; descarte-o"},
], "descartes": []}
APLICADO = {"aplicado": True, "lote_id": LOTE, "indicacoes_admitidas": 4, "indicacoes_descartadas": 1,
            "criados": [{"id": "c1", "slug": "governanca-de-dados", "rotulo": "Governança de dados"}],
            "ligados_a_existente": [{"id": "c2", "slug": "catalogo", "termo": "Catálogo"}],
            "sem_garantia": [{"termo": "Licença", "motivo": "nenhuma obra viva sustenta o termo; descarte-o"}]}


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


def test_sem_apply_mostra_o_destino_de_cada_termo_e_nao_grava(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE)
    assert r.returncode == 0, r.stderr
    assert "plano: 3 termo(s) a admitir, 0 a descartar" in r.stdout
    assert "Governança de dados -> criar governanca-de-dados · 3 obra(s) viva(s) de garantia" in r.stdout
    assert "Catálogo -> ligar ao existente catalogo · 1 obra(s) viva(s) de garantia · 1 de obra retirada" in r.stdout
    assert "Licença -> sem garantia" in r.stdout
    assert "plano seco" in r.stdout
    assert servidor.chamadas == [("/acervo/indicacoes", {"lote_id": LOTE, "aplicar": False,
                                                          "autor": "conhecimento"})]


def test_apply_cria_liga_ao_existente_e_deixa_o_sem_garantia(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE, "--apply")
    assert r.returncode == 0, r.stderr
    assert "governanca-de-dados: criado" in r.stdout
    assert "catalogo: já existia; obras ligadas" in r.stdout
    assert "Licença: segue pendente" in r.stdout
    assert "indicações admitidas: 4 · descartadas: 1" in r.stdout
    assert servidor.chamadas == [("/acervo/indicacoes", {"lote_id": LOTE, "aplicar": True,
                                                          "autor": "conhecimento"})]


def test_apply_de_qualquer_cadeira_grava_em_nome_do_curador_dela(servidor):
    for cadeira, autor in (("engenharia", "time-platafirma"), ("dados", "dados")):
        servidor.chamadas.clear()
        r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE, "--apply", cadeira=cadeira)
        assert r.returncode == 0, r.stderr
        assert servidor.chamadas == [("/acervo/indicacoes", {"lote_id": LOTE, "aplicar": True, "autor": autor})]


def test_todas_as_indicacoes_termos_e_descartes_vao_no_corpo(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", "todas", "--termos", "catalogo, governanca-de-dados",
                       "--descartar", "Licença")
    assert r.returncode == 0, r.stderr
    assert servidor.chamadas == [("/acervo/indicacoes", {
        "lote_id": None, "aplicar": False, "termos": ["catalogo", "governanca-de-dados"],
        "descartar": ["Licença"], "autor": "conhecimento"})]


def test_a_forma_pela_particao_biblioteca_chega_ao_mesmo_ato(servidor):
    r = servidor.rodar("curar", "biblioteca", "conceitos", "--indicacoes", LOTE)
    assert r.returncode == 0, r.stderr
    assert "plano: 3 termo(s) a admitir" in r.stdout


def test_sem_indicacoes_sai_2(servidor):
    r = servidor.rodar("curar", "conceitos")
    assert r.returncode == 2 and "uso: acervo curar conceitos --indicacoes" in r.stderr
    assert servidor.chamadas == []


def test_json_devolve_o_corpo_do_servidor(servidor):
    r = servidor.rodar("curar", "conceitos", "--indicacoes", LOTE, "--json")
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["total_termos"] == 3
