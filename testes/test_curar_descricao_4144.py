"""4144: os comandos públicos entregam a descrição à API em plano e aplicação."""
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
OBRA = "11111111-1111-4111-8111-111111111111"


@pytest.fixture
def api():
    chamadas = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def responde(self, obj):
            b = json.dumps(obj).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            self.responde({"id": OBRA, "titulo": "Título", "itens": []})

        def do_PATCH(self):
            corpo = json.loads(self.rfile.read(int(self.headers["content-length"])))
            chamadas.append((self.path, corpo))
            if self.path == "/acervo/obras":
                self.responde({"modo": "plano", "n": 1, "itens": []})
            else:
                self.responde({"modo": "aplicado", "aprovado": True})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    from test_acervo_atos_classificar import _acha_python
    py = _acha_python()
    assert py, "o teste do comando exige Python com requests"
    env = {**os.environ, "MOTOR_ACERVO_URL": url, "RAG_API_URL": url, "RAG_API_BASE": url,
           "PATH": str(Path(py).parent) + os.pathsep + os.environ.get("PATH", "")}
    try:
        yield chamadas, env
    finally:
        srv.shutdown()
        srv.server_close()
        thread.join()


def rodar(env, *args):
    return subprocess.run(["bash", str(RAIZ / "bin/acervo"), *args, "--json", "--autor", "dados"],
                          env=env, capture_output=True, text=True, timeout=30)


@pytest.mark.parametrize("aplicar", [False, True])
def test_catalogar_passa_resumo_emissor_publicacao_e_dominio(api, aplicar):
    chamadas, env = api
    r = rodar(env, "catalogar", "biblioteca", "obra", OBRA,
              "--resumo", "Descrição conferida", "--emitido-por", "Autora; Editora",
              "--publicacao", "2026", "--dominio", "direito", *(["--apply"] if aplicar else []))
    assert r.returncode == 0, r.stderr
    path, corpo = chamadas[-1]
    alteracao = corpo if aplicar else corpo["alteracao"]
    assert alteracao["resumo"] == "Descrição conferida"
    assert alteracao["emitido_por"] == ["Autora", "Editora"]
    assert alteracao["publicacao"] == "2026" and alteracao["dominio"] == "direito"
    assert path == (f"/acervo/obras/{OBRA}" if aplicar else "/acervo/obras")


@pytest.mark.parametrize("aplicar", [False, True])
def test_definir_edita_descricao_de_conceito_existente(api, aplicar):
    chamadas, env = api
    r = rodar(env, "definir", "biblioteca", "conceito", "conceito",
              "--rotulo", "Rótulo conferido", "--definicao", "Definição conferida",
              "--motivo", "Correção bibliográfica", *(["--apply"] if aplicar else []))
    assert r.returncode == 0, r.stderr
    path, corpo = chamadas[-1]
    assert path == "/acervo/conceitos/conceito"
    assert corpo["rotulo"] == "Rótulo conferido" and corpo["definicao"] == "Definição conferida"
    assert corpo["aplicar"] is aplicar
