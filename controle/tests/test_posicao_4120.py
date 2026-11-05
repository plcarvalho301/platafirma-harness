"""#4120, item 23: `acervo ler biblioteca posicao <obra>` — a obra está entre as k primeiras da busca pelo título?

A busca de verdade é trocada (PF_MOTOR) por um script que devolve o JSON combinado e guarda os argumentos que
recebeu; o serviço do acervo é falso e só diz o título da obra. Prova: o título vai literal à busca, em origem
`medida` (fora da série de cobertura), a posição conta obra e não trecho, e a obra fora das k primeiras sai 1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
POSICAO = RAIZ / "bin" / "_acervo" / "posicao"
ACERVO = RAIZ / "bin" / "acervo"
OBRA = "55555555-5555-4555-8555-555555555555"
TITULO = "Nota Técnica: Como elaborar modelo lógico de programa"


class _Handler(BaseHTTPRequestHandler):
    falso: "Falso"

    def log_message(self, *a):
        pass

    def do_GET(self):
        self.falso.chamadas.append(self.path)
        if self.path.endswith("/situacao") and (OBRA in self.path or "T%C3%ADtulo" in self.path or "Nota" in self.path):
            corpo, status = {"obra_id": OBRA, "titulo": TITULO}, 200
        else:
            corpo, status = {"title": "ObraNaoEncontrada", "detail": self.path}, 404
        dados = json.dumps(corpo, ensure_ascii=False).encode()
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


@pytest.fixture
def servidor():
    f = Falso()
    try:
        yield f
    finally:
        f.fechar()


def _motor(tmp_path, saida: str, codigo: int = 0):
    gravado = tmp_path / "args.json"
    script = tmp_path / "motor_falso.py"
    script.write_text(textwrap.dedent(f"""
        import json, sys
        json.dump(sys.argv[1:], open({str(gravado)!r}, "w"))
        sys.stdout.write({saida!r})
        sys.stderr.write("motor: erro de teste\\n" if {codigo} else "")
        sys.exit({codigo})
    """))
    return script, gravado


def _rodar(servidor, motor, *argv, via_acervo=False):
    env = {**os.environ, "MOTOR_ACERVO_URL": servidor.url, "RAG_API_URL": "", "RAG_API_BASE": "",
           "RAG_API_TOKEN": "t", "PF_MOTOR": str(motor)}
    cmd = ["bash", str(ACERVO), "ler", "biblioteca", "posicao", *argv] if via_acervo else [sys.executable, str(POSICAO), *argv]
    return subprocess.run(cmd, capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=60, check=False)


def _busca(*obras, por_trecho=False):
    itens = []
    for o in obras:
        itens.append({"obra_id": o, "trecho": "a"})
        if por_trecho:
            itens.append({"obra_id": o, "trecho": "b"})
    return json.dumps({"itens": itens})


def test_obra_na_terceira_posicao_sai_0_com_a_posicao(servidor, tmp_path):
    motor, gravado = _motor(tmp_path, _busca("x", "y", OBRA, "z"))
    r = _rodar(servidor, motor, OBRA)
    assert r.returncode == 0, r.stderr
    assert f"posicao: 3 de 10 · {TITULO} ({OBRA})" in r.stdout
    # o titulo vai literal, na origem de medida, e o k vai junto
    assert json.loads(gravado.read_text()) == ["rag", "buscar", "biblioteca", "--origem", "medida", "--k", "10", TITULO]


def test_a_posicao_conta_obra_e_nao_trecho(servidor, tmp_path):
    motor, _ = _motor(tmp_path, _busca("x", "y", OBRA, por_trecho=True))
    r = _rodar(servidor, motor, OBRA)
    assert "posicao: 3 de 10" in r.stdout  # x, x, y, y, OBRA, OBRA: a obra e a terceira, nao a quinta


def test_obra_fora_das_k_primeiras_sai_1_e_diz_quantas_vieram(servidor, tmp_path):
    motor, _ = _motor(tmp_path, _busca("a", "b", "c", OBRA))
    r = _rodar(servidor, motor, OBRA, "--k", "3")
    assert r.returncode == 1
    assert "fora das 3 primeiras (3 obra(s) vieram)" in r.stdout


def test_json_diz_posicao_e_se_esta_entre_as_k(servidor, tmp_path):
    motor, _ = _motor(tmp_path, _busca(OBRA))
    r = _rodar(servidor, motor, OBRA, "--json", "--k", "5")
    assert r.returncode == 0
    assert json.loads(r.stdout) == {"obra_id": OBRA, "titulo": TITULO, "k": 5, "posicao": 1,
                                    "entre_as_k_primeiras": True, "vieram": 1}


def test_a_resposta_com_obra_aninhada_tambem_se_le(servidor, tmp_path):
    corpo = json.dumps({"resultado": {"secoes": [{"obra": "x"}, {"documento": {"obra_id": OBRA}}]}})
    motor, _ = _motor(tmp_path, corpo)
    assert _rodar(servidor, motor, OBRA).returncode == 0


def test_busca_que_falha_sai_5_ou_3_com_a_causa(servidor, tmp_path):
    motor, _ = _motor(tmp_path, "", codigo=1)
    r = _rodar(servidor, motor, OBRA)
    assert r.returncode == 5 and "a busca saiu 1: motor: erro de teste" in r.stderr
    motor3, _ = _motor(tmp_path, "", codigo=3)
    assert _rodar(servidor, motor3, OBRA).returncode == 3


def test_saida_que_nao_e_json_sai_5(servidor, tmp_path):
    motor, _ = _motor(tmp_path, "nada de json")
    r = _rodar(servidor, motor, OBRA)
    assert r.returncode == 5 and "nao e JSON" in r.stderr


def test_obra_que_o_acervo_nao_conhece_sai_1(servidor, tmp_path):
    motor, gravado = _motor(tmp_path, _busca(OBRA))
    r = _rodar(servidor, motor, "00000000-0000-4000-8000-000000000000")
    assert r.returncode == 1 and "ObraNaoEncontrada" in r.stderr
    assert not gravado.exists()  # sem obra, nem busca


def test_servico_fora_sai_3(tmp_path):
    motor, _ = _motor(tmp_path, _busca(OBRA))
    env = {**os.environ, "MOTOR_ACERVO_URL": "http://127.0.0.1:9", "RAG_API_URL": "", "RAG_API_BASE": "", "PF_MOTOR": str(motor)}
    r = subprocess.run([sys.executable, str(POSICAO), OBRA], capture_output=True, text=True, env=env, timeout=60, check=False)
    assert r.returncode == 3 and "rota fora" in r.stderr


@pytest.mark.parametrize("argv, trecho", [
    ((), "falta a obra"),
    ((OBRA, "--k", "0"), "--k vai de 1 a 100"),
    ((OBRA, "--k", "101"), "--k vai de 1 a 100"),
    ((OBRA, "--semsentido"), "argumento que o ato nao le"),
])
def test_uso_errado_sai_2_sem_buscar(servidor, tmp_path, argv, trecho):
    motor, gravado = _motor(tmp_path, _busca(OBRA))
    r = _rodar(servidor, motor, *argv)
    assert r.returncode == 2 and trecho in r.stderr
    assert not gravado.exists()


def test_o_ato_esta_na_porta_do_acervo(servidor, tmp_path):
    motor, _ = _motor(tmp_path, _busca(OBRA))
    r = _rodar(servidor, motor, OBRA, via_acervo=True)
    assert r.returncode == 0, r.stderr
    assert "posicao: 1 de 10" in r.stdout
