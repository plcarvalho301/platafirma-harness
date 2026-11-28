# componente: componente:verbo-ontologia
"""Contrato da ajuda do verbo `ontologia`: a ajuda geral lista as classes, e os campos da ficha saem pela classe pedida."""
from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

import pytest

RAIZ = Path(__file__).resolve().parents[2]
BIN = RAIZ / "bin"
if str(BIN) not in sys.path:
    sys.path.insert(0, str(BIN))

from _olaria.__main__ import executar  # noqa: E402

TETO_DA_AJUDA_GERAL = 16 * 1024


def _campo(nome: str, *, obrigatorio: bool = True) -> dict:
    return {"campo": nome, "tipo": "texto", "obrigatorio": obrigatorio, "minimo": 1 if obrigatorio else 0,
            "maximo": 1, "exemplo": f"exemplo de {nome}", "ensaiavel": True}


def _corpo(n_sinteticas: int = 3, campos_por_classe: int = 4) -> dict:
    classes = {
        "card": [_campo("titulo_do_card"), _campo("corpo_do_card")],
        "conta-de-sistema-operacional": [_campo("usuario_da_conta")],
        "verbo": [_campo("capacidade_do_verbo"), _campo("dono_do_verbo", obrigatorio=False)],
    }
    for i in range(n_sinteticas):
        classes[f"classe-sintetica-{i:03d}"] = [_campo(f"campo_{i:03d}_{j}") for j in range(campos_por_classe)]
    return {
        "envelope": ["classe", "classes", "fichas"],
        "catalogo": {"shape": {"obrigatorios": ["slug"], "opcionais": ["resumo"]}},
        "classes": classes,
    }


@pytest.fixture
def servico():
    estado = {"corpo": _corpo()}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            dados = json.dumps(estado["corpo"], ensure_ascii=False).encode("utf-8")
            self.send_response(200 if self.path == "/ajuda" else 404)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    Thread(target=srv.serve_forever, daemon=True).start()
    env = {
        "OLARIA_URL": f"http://127.0.0.1:{srv.server_address[1]}",
        "OLARIA_CHAVE": "chave-teste",
        "PF_CADEIRA": "engenharia",
    }
    try:
        yield env, estado
    finally:
        srv.shutdown()
        srv.server_close()


def test_ajuda_geral_lista_as_classes_sem_os_campos(servico):
    env, _ = servico
    saida = executar(["--help"], env=env)
    assert saida.codigo == 0
    assert "ontologia ler <classe>" in saida.stdout
    assert "classes gravadas (6); os campos da ficha de uma saem com `ontologia --help <classe>`:" in saida.stdout
    assert "conta-de-sistema-operacional" in saida.stdout
    assert "card, classe-sintetica-000" in saida.stdout
    assert "titulo_do_card ·" not in saida.stdout
    assert "capacidade_do_verbo ·" not in saida.stdout
    assert "campos dos itens de catálogo" in saida.stdout


def test_ajuda_da_classe_traz_so_os_campos_dela(servico):
    env, _ = servico
    saida = executar(["ler", "verbo", "--help"], env=env)
    assert saida.codigo == 0
    assert "campos da ficha de verbo (" in saida.stdout
    assert "capacidade_do_verbo · texto · obrigatório" in saida.stdout
    assert "dono_do_verbo · texto · opcional" in saida.stdout
    assert "titulo_do_card ·" not in saida.stdout
    assert "classes gravadas" not in saida.stdout
    assert "- classe: verbo" in saida.stdout


def test_ajuda_com_classe_que_nao_existe_cai_na_geral(servico):
    env, _ = servico
    saida = executar(["--help", "verbos"], env=env)
    assert saida.codigo == 0
    assert "classes gravadas (6)" in saida.stdout
    assert "(nome · tipo · obrigatoriedade" not in saida.stdout


def test_ajuda_geral_nao_cresce_com_o_catalogo(servico):
    env, estado = servico
    estado["corpo"] = _corpo(n_sinteticas=200, campos_por_classe=12)
    geral = executar(["--help"], env=env)
    uma = executar(["--help", "classe-sintetica-150"], env=env)
    assert geral.codigo == 0 and uma.codigo == 0
    assert len(geral.stdout.encode("utf-8")) < TETO_DA_AJUDA_GERAL
    assert len(uma.stdout.encode("utf-8")) < TETO_DA_AJUDA_GERAL
    assert "campo_150_11 ·" in uma.stdout
    assert "campo_149_0 ·" not in uma.stdout


def test_ajuda_sem_servico_sai_zero_com_a_gramatica():
    saida = executar(["--help"], env={"PF_CADEIRA": "engenharia", "OLARIA_URL": "http://127.0.0.1:9",
                                      "OLARIA_CHAVE": "chave-teste"})
    assert saida.codigo == 0
    assert "ontologia ler <classe>" in saida.stdout
    assert "a ajuda dos campos depende do serviço" in saida.stdout
