"""Verbo tarefas: quadro de discovery/delivery e aposta com decisão (card #3619; R35 e R36 da
spec tarefas).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele): o teste prova o que o
VERBO faz — a rota que chama, a query que monta, o que imprime e o que recusa — e não a regra,
que é do rastreador e tem self-check lá (#3617, #3618). O verbo não guarda lista de estados de
quadro nenhuma: quem decide o recorte de cada quadro é a API.
"""
from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin" / "tarefas"


class _Stub(BaseHTTPRequestHandler):
    rotas: dict = {}
    chamadas: list = []

    def log_message(self, *a):  # silencioso
        pass

    def _atende(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}") if n else None
        partes = urlsplit(self.path)
        type(self).chamadas.append((self.command, self.path, corpo))
        r = type(self).rotas.get((self.command, partes.path))
        if r is None:
            status, payload = 404, {"erro": f"sem rota: {self.command} {partes.path}"}
        else:
            status, payload = r(corpo) if callable(r) else r
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    do_GET = do_POST = do_PATCH = do_DELETE = _atende


@pytest.fixture()
def stub():
    _Stub.rotas, _Stub.chamadas = {}, []
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base="http://127.0.0.1:9", **env_extra):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia", **env_extra)
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env)


def _caminhos(s, metodo=None):
    return [c for m, c, _ in s.chamadas if metodo is None or m == metodo]


def _cartao(id, estado_mostrado="priorizada", **resto):
    return {"id": id, "titulo": f"item {id}", "nivel": 1, "estado_mostrado": estado_mostrado,
            "cadeira": "engenharia", "executor": "engenharia", "pai": None,
            "motivo_parada": None, "posto": None, **resto}


# --- listar --quadro (R35) ----------------------------------------------------------------

def test_listar_quadro_chama_a_rota_do_quadro_e_nao_itens(stub):
    s, base = stub
    s.rotas[("GET", "/quadro/discovery")] = (
        200, {"itens": [_cartao(1, "captada")], "estados": [], "total": 1})
    p = _run(["listar", "--quadro", "discovery"], base)
    assert p.returncode == 0, p.stderr
    chamadas = _caminhos(s, "GET")
    caminho = chamadas[-1].split("?", 1)[0]
    assert caminho == "/quadro/discovery"
    assert not any(c.startswith("/itens") for c in chamadas)


def test_listar_quadro_sem_paradas_pede_exclusao_de_dormentes(stub):
    s, base = stub
    s.rotas[("GET", "/quadro/delivery")] = (
        200, {"itens": [_cartao(1, "em-execucao")], "estados": [], "total": 1,
              "dormentes_excluidos": 2})
    p = _run(["listar", "--quadro", "delivery"], base)
    assert p.returncode == 0, p.stderr
    assert "dormentes=excluir" in _caminhos(s, "GET")[-1]
    assert "2 dormente(s) escondida(s)" in p.stdout


def test_listar_quadro_com_paradas_nao_pede_exclusao_e_nao_avisa(stub):
    s, base = stub
    s.rotas[("GET", "/quadro/delivery")] = (
        200, {"itens": [_cartao(1, "em-execucao"), _cartao(2, "despriorizada")],
              "estados": [], "total": 2})
    p = _run(["listar", "--quadro", "delivery", "--paradas"], base)
    assert p.returncode == 0, p.stderr
    assert "dormentes" not in _caminhos(s, "GET")[-1]
    assert "escondida" not in p.stdout


def test_listar_quadro_imprime_id_estado_cadeira_executor_titulo(stub):
    s, base = stub
    s.rotas[("GET", "/quadro/discovery")] = (
        200, {"itens": [_cartao(7, "em-formalizacao", cadeira="dados", executor="dados",
                                 titulo="feature X")], "estados": [], "total": 1})
    p = _run(["listar", "--quadro", "discovery"], base)
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "#7\tem-formalizacao\tdados\tdados\tfeature X"


def test_listar_quadro_json_imprime_o_corpo_como_veio(stub):
    s, base = stub
    corpo = {"itens": [_cartao(1)], "estados": [{"estado": "priorizada", "nome": "Priorizada"}],
             "total": 1}
    s.rotas[("GET", "/quadro/discovery")] = (200, corpo)
    p = _run(["listar", "--quadro", "discovery", "--json"], base)
    assert p.returncode == 0, p.stderr
    assert json.loads(p.stdout) == corpo


def test_listar_quadro_tipo_desconhecido_e_recusa_da_api_nao_do_verbo(stub):
    s, base = stub
    s.rotas[("GET", "/quadro/kanban")] = (
        400, {"erro": "tipo de quadro desconhecido: `kanban` (válidos: discovery, delivery)"})
    p = _run(["listar", "--quadro", "kanban"], base)
    assert p.returncode == 1
    assert "válidos: discovery, delivery" in p.stderr


def test_listar_quadro_opcao_desconhecida_e_uso(stub):
    s, base = stub
    p = _run(["listar", "--quadro", "discovery", "--estado", "captada"], base)
    assert p.returncode == 2
    assert not s.chamadas


def test_bin_tarefas_nao_guarda_lista_de_estados_de_quadro():
    """Confere de R35: a coluna virtual em-formalizacao só existe na API — o verbo que a
    citasse estaria recalculando o recorte do quadro por fora."""
    texto = BIN.read_text(encoding="utf-8")
    assert "em-formalizacao" not in texto


# --- mover --decisao (R36) ----------------------------------------------------------------

def test_mover_com_decisao_manda_o_numero_do_comentario(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/40")] = (200, {"id": 40, "titulo": "feature", "estado_nome": "Priorizada",
                                              "estado_derivado": None, "pai": None})
    p = _run(["mover", "40", "priorizada", "--decisao", "12"], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas[-1][2] == {"estado": "priorizada", "decisao": 12}


def test_mover_sem_decisao_nao_manda_o_campo(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/40")] = (200, {"id": 40, "titulo": "feature", "estado_nome": "Priorizada",
                                              "estado_derivado": None, "pai": None})
    p = _run(["mover", "40", "priorizada"], base)
    assert p.returncode == 0, p.stderr
    assert "decisao" not in s.chamadas[-1][2]


def test_mover_sem_decisao_imprime_a_recusa_da_api_com_a_forma_certa(stub):
    s, base = stub
    s.rotas[("PATCH", "/itens/40")] = (
        400, {"erro": "a aposta para `priorizada` exige o número de um comentário de decisão "
                      "do PRÓPRIO item (R19, D3 da arq:0127): informe `decisao`"})
    p = _run(["mover", "40", "priorizada"], base)
    assert p.returncode == 1
    assert "informe `decisao`" in p.stderr


def test_uso_cita_mover_decisao_e_listar_quadro():
    p = _run(["--ajuda"])
    assert p.returncode == 0
    assert "--decisao" in p.stdout and "--quadro discovery|delivery" in p.stdout


def test_listar_ajuda_mostra_quadro():
    p = _run(["listar", "--ajuda"])
    assert p.returncode == 0
    assert "--quadro" in p.stdout
