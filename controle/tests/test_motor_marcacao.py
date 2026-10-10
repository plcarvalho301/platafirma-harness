"""`motor marcacao`: o cliente da marcacao-api (card #3349, feature #3340).

O verbo roda de verdade, como subprocesso, contra uma marcacao-api falsa em 127.0.0.1: registro, token e
instância apontam para um diretório temporário (PF_MOTOR_REG, PLATAFIRMA_INSTANCIA). Prova o que o verbo manda
e o exit de cada resposta; não prova a API, que tem a suíte dela (platafirma-motor, deploy/marcacao/tests).
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
LOTE = {"lote_id": "lote-t1", "gabarito_versao_id": "00000000-0000-4000-8000-000000000001", "criterio_versao": "v1",
        "passada": "primeira", "corpo": {"lote_id": "lote-t1", "criterio_versao": "v1", "passada": "primeira",
                                           "perguntas": []}, "respostas": []}


class _API(BaseHTTPRequestHandler):
    pedidos: ClassVar[list] = []
    status: ClassVar[int] = 200

    def log_message(self, *a):
        pass

    def _responde(self, status, corpo):
        dado = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def _atende(self, metodo):
        n = int(self.headers.get("Content-Length") or 0)
        corpo = json.loads(self.rfile.read(n)) if n else None
        self.pedidos.append((metodo, self.path, self.headers.get("Authorization"), corpo))
        if self.status != 200:
            return self._responde(self.status, {"erro": "recusado de teste"})
        if self.path == "/interno/lote" and metodo == "PUT":
            return self._responde(200, {"lote_id": corpo["lote_id"], "ativo": bool(corpo.get("ativo")),
                                        "perguntas": 2, "respostas": 6})
        if self.path.startswith("/interno/lote/") and self.path.endswith("/ativar"):
            return self._responde(200, {"lote_id": self.path.split("/")[3], "ativo": True})
        if self.path == "/interno/lote/desativar":
            return self._responde(200, {"lote_id": "lote-t1", "ativo": False})
        if self.path.startswith("/interno/lote/") and self.path.endswith("/desativar"):
            return self._responde(200, {"lote_id": self.path.split("/")[3], "ativo": False})
        if self.path.startswith("/interno/lote/"):
            if "com_braco=1" in self.path:
                return self._responde(200, {"lote_id": "lote-t1", "ativo": True, "respostas": [
                    {"resposta_id": "r1", "pergunta_id": "p1", "braco": "servido", "mapa": []},
                    {"resposta_id": "r2", "pergunta_id": "p1", "braco": "lexico", "mapa": []}]})
            return self._responde(200, {"lote_id": "lote-t1", "criterio_versao": "v1", "passada": "primeira",
                                        "perguntas": [{"pergunta_id": "p1"}]})
        if self.path.startswith("/interno/eventos"):
            return self._responde(200, {"lote_id": "lote-t1", "eventos": [{"tipo": "marca"}, {"tipo": "marca"},
                                                                          {"tipo": "preferencia"}]})
        if self.path == "/interno/juiz":
            return self._responde(200, {"gravadas": len(corpo["marcas"])})
        return self._responde(404, {"erro": "sem rota"})

    do_GET = lambda self: self._atende("GET")  # noqa: E731
    do_PUT = lambda self: self._atende("PUT")  # noqa: E731
    do_POST = lambda self: self._atende("POST")  # noqa: E731


@pytest.fixture
def api(tmp_path):
    servidor = HTTPServer(("127.0.0.1", 0), _API)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "marcacao-api").mkdir(parents=True)
    (instancia / "segredos" / "marcacao-api" / "MARCACAO_TOKEN").write_text("tok\n")
    registro = tmp_path / "motor-instancias.json"

    def escreve_registro(porta):
        registro.write_text(json.dumps({"marcacao": {
            "estado": "ativa", "tipo": "marcacao-api", "container": "marcacao-api", "stack": "marcacao-api",
            "endpoint": f"http://127.0.0.1:{porta}", "token_em": "marcacao-api/MARCACAO_TOKEN", "ajustes": []}}))

    escreve_registro(servidor.server_port)
    _API.pedidos = []
    _API.status = 200

    def roda(*args, stdin=None, porta=None):
        if porta:
            escreve_registro(porta)
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_CADEIRA": "ia"}
        return subprocess.run([sys.executable, str(MOTOR), "marcacao", *args], capture_output=True, text=True,
                              input=stdin, env=env, timeout=60, check=False)

    yield roda, _API, tmp_path
    servidor.shutdown()


def test_lote_gravar_manda_o_arquivo_com_o_token_e_ativar_liga_o_ativo(api):
    roda, srv, tmp = api
    arq = tmp / "lote.json"
    arq.write_text(json.dumps(LOTE))
    r = roda("lote", "gravar", str(arq), "--ativar")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "lote lote-t1 gravado · 2 perguntas · 6 respostas · ativo"
    metodo, caminho, auth, corpo = srv.pedidos[-1]
    assert (metodo, caminho, auth) == ("PUT", "/interno/lote", "Bearer tok")
    assert corpo["ativo"] is True and corpo["lote_id"] == "lote-t1"
    roda("lote", "gravar", str(arq))
    assert "ativo" not in srv.pedidos[-1][3]


def test_lote_gravar_le_do_stdin(api):
    roda, srv, _ = api
    r = roda("lote", "gravar", "-", "--json", stdin=json.dumps(LOTE))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["lote_id"] == "lote-t1"


def test_lote_ler_atual_com_braco_e_sem(api):
    roda, srv, _ = api
    r = roda("lote", "ler", "--atual", "--com-braco", "--json")
    assert r.returncode == 0, r.stderr
    assert srv.pedidos[-1][:2] == ("GET", "/interno/lote/atual?com_braco=1")
    assert [x["braco"] for x in json.loads(r.stdout)["respostas"]] == ["servido", "lexico"]
    r = roda("lote", "ler", "lote-t1")
    assert srv.pedidos[-1][:2] == ("GET", "/interno/lote/lote-t1")
    assert r.stdout.strip() == "lote lote-t1 · 1 perguntas"


def test_ativar_eventos_e_juiz(api):
    roda, srv, _ = api
    assert roda("lote", "ativar", "lote-t2").stdout.strip() == "lote lote-t2 ativo"
    assert srv.pedidos[-1][:2] == ("POST", "/interno/lote/lote-t2/ativar")
    assert roda("lote", "desativar", "lote-t2").stdout.strip() == "lote lote-t2 desativado"
    assert srv.pedidos[-1][:2] == ("POST", "/interno/lote/lote-t2/desativar")
    assert roda("lote", "desativar").stdout.strip() == "lote lote-t1 desativado"
    assert srv.pedidos[-1][:2] == ("POST", "/interno/lote/desativar")
    r = roda("eventos", "--lote", "lote-t1")
    assert srv.pedidos[-1][:2] == ("GET", "/interno/eventos?lote_id=lote-t1")
    assert r.stdout.strip() == "lote lote-t1 · 3 eventos · marca 2 · preferencia 1"
    corpo = {"lote_id": "lote-t1", "marcas": [{"resposta_id": "r1"}]}
    r = roda("juiz", "gravar", "-", stdin=json.dumps(corpo))
    assert r.stdout.strip() == "1 marca(s) do juiz gravada(s)" and srv.pedidos[-1][3] == corpo


@pytest.mark.parametrize("status,saida", [(404, 1), (409, 1), (422, 2), (401, 4), (503, 3), (500, 3)])
def test_exit_de_cada_resposta_da_api(api, status, saida):
    roda, srv, _ = api
    srv.status = status
    r = roda("lote", "ler", "--atual")
    assert r.returncode == saida, r.stderr
    assert "recusado de teste" in r.stderr or status == 401


def test_api_fora_do_ar_sai_3_e_diz_onde_olhar(api):
    roda, srv, _ = api
    r = roda("lote", "ler", "--atual", porta=9)
    assert r.returncode == 3 and "infra ps marcacao-api" in r.stderr


@pytest.mark.parametrize("args", [
    (), ("lote",), ("lote", "gravar"), ("lote", "ler"), ("lote", "ler", "--atual", "x"), ("eventos",),
    ("eventos", "--lote"), ("lote", "ler", "--atual", "--sem-isso"), ("coisa",),
])
def test_uso_errado_sai_2_sem_chamar_a_api(api, args):
    roda, srv, _ = api
    assert roda(*args).returncode == 2
    assert srv.pedidos == []


def test_arquivo_que_nao_e_json_sai_2(api):
    roda, srv, _ = api
    r = roda("lote", "gravar", "-", stdin="nao e json")
    assert r.returncode == 2 and srv.pedidos == []


def test_listar_mostra_a_instancia(api):
    roda, srv, _ = api
    env = {**os.environ, "PF_MOTOR_REG": str(api[2] / "motor-instancias.json")}
    r = subprocess.run([sys.executable, str(MOTOR), "listar"], capture_output=True, text=True, env=env, timeout=60)
    assert r.returncode == 0 and r.stdout.split()[:3] == ["marcacao", "ativa", "marcacao-api"]
