"""`motor rag eleger`: medição só leitura da eleição de chapéu sobre o log (card #3368).

Lê acervo.evento_recuperacao (necessidade e chapéu não nulos), manda em lote à rota /eleger
do rag-api e imprime por cadeira e chapéu: total, frase_sem_conceito, chapeu_sem_casamento.
Não grava nada, não altera a busca.
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

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"

S = {
    "ia": "00000000-0000-4000-8000-000000000001",
    "dados": "00000000-0000-4000-8000-000000000002",
}

ROTULOS = [
    "Complexidade assintotica", "asymptotic complexity", "big-o", "Pipeline RAG", "rag",
    "retrieval-augmented generation", "Ranqueamento multiestágio", "reranking",
]

EVENTOS_EXEMPLO = [
    {
        "id": "10000000-0000-4000-8000-000000000001",
        "sessao_id": S["ia"],
        "criado_em": "2026-10-08 12:00:00+00",
        "necessidade": "Como podemos usar esta nota técnica para melhorar a capacidade absortiva do órgão?",
        "chapeu": "engenharia-de-harness",
    },
    {
        "id": "10000000-0000-4000-8000-000000000002",
        "sessao_id": S["ia"],
        "criado_em": "2026-10-08 14:00:00+00",
        "necessidade": "qual o protocolo de medição do rag?",
        "chapeu": "engenharia-de-harness",
    },
    {
        "id": "10000000-0000-4000-8000-000000000003",
        "sessao_id": S["dados"],
        "criado_em": "2026-10-09 10:00:00+00",
        "necessidade": "qual o catálogo de metadados da governança?",
        "chapeu": "governanca",
    },
]


class _API(BaseHTTPRequestHandler):
    chamadas: ClassVar[list] = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        if self.path == "/eleger":
            corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
            self.chamadas.append(corpo)
            itens_resp = []
            for item in corpo.get("itens", []):
                nec = item.get("necessidade", "")
                if "capacidade absortiva" in nec:
                    itens_resp.append({
                        "conceitos_da_frase": ["capacidade-absortiva"],
                        "eleito_do_chapeu": "capacidade-absortiva",
                        "sinais": [],
                    })
                elif "protocolo" in nec:
                    itens_resp.append({
                        "conceitos_da_frase": [],
                        "eleito_do_chapeu": None,
                        "sinais": ["frase_sem_conceito"],
                    })
                elif "catalogo" in nec or "metadados" in nec:
                    itens_resp.append({
                        "conceitos_da_frase": ["governanca-de-dados"],
                        "eleito_do_chapeu": None,
                        "sinais": ["chapeu_sem_casamento"],
                    })
                else:
                    itens_resp.append({
                        "conceitos_da_frase": [],
                        "eleito_do_chapeu": None,
                        "sinais": ["frase_sem_conceito"],
                    })
            dado = json.dumps({"itens": itens_resp}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dado)))
            self.end_headers()
            self.wfile.write(dado)
        else:
            self.send_response(404)
            self.end_headers()


DOCKER_FALSO = """#!{python}
import json, os, sys
a = sys.argv[1:]
container = a[2]
p = os.environ["FAKE_ESTADO"]
estado = json.load(open(p))
if container == "rag-extractor-pg":
    print(json.dumps(estado["eventos"]))
elif container == "harness-sessao-db":
    print(json.dumps(estado["cadeiras"]))
else:
    print("[]")
"""


@pytest.fixture
def api(tmp_path):
    servidor = HTTPServer(("127.0.0.1", 0), _API)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}"
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\\n")

    (tmp_path / "bin").mkdir()
    docker = tmp_path / "bin" / "docker"
    docker.write_text(DOCKER_FALSO.format(python=sys.executable))
    docker.chmod(0o755)

    estado = tmp_path / "estado.json"
    estado.write_text(json.dumps({
        "eventos": EVENTOS_EXEMPLO,
        "cadeiras": [{"sessao_id": v, "cadeira": k} for k, v in S.items()],
    }))

    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": None, "stack": "rag",
        "endpoint": f"{base}/search",
        "token_em": "rag/RAG_API_TOKEN",
        "banco": {"container": "rag-extractor-pg", "db": "rag_extractor", "user": "rag"},
        "bancos": {
            "motor": {"container": "motor-pg", "db": "motor", "user": "motor"},
            "sessao": {"container": "harness-sessao-db", "db": "sessao", "user": "sessao"},
        },
        "ajustes": [], "nao_e_ajuste": {},
    }}))

    abertura = tmp_path / "abertura-publicada" / "current" / "abertura"
    abertura.mkdir(parents=True)
    (abertura / "rotas-chapeu.json").write_text(json.dumps({
        "ia": {"engenharia-de-harness": ROTULOS},
        "dados": {"governanca": ["Governança de dados"]},
    }, ensure_ascii=False), encoding="utf-8")

    _API.chamadas = []

    def roda(*args, eventos=None):
        if eventos is not None:
            e = json.loads(estado.read_text())
            e["eventos"] = eventos
            estado.write_text(json.dumps(e))
        env = {
            **os.environ,
            "PF_MOTOR_REG": str(registro),
            "PLATAFIRMA_INSTANCIA": str(instancia),
            "OPS_LOG_DIR": str(tmp_path / "ops"),
            "PF_ABERTURA_DIR": str(tmp_path / "abertura-publicada"),
            "PF_CADEIRA": "ia",
            "FAKE_ESTADO": str(estado),
            "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}",
        }
        return subprocess.run(
            [sys.executable, str(MOTOR), "rag", "eleger", *args],
            capture_output=True, text=True, env=env, timeout=60, check=False,
        )

    yield roda, _API.chamadas, estado
    servidor.shutdown()


def test_eleger_json_devolve_tabela_e_totais(api):
    roda, chamadas, _ = api
    r = roda("--json")
    assert r.returncode == 0, r.stderr
    assert len(chamadas) == 1
    assert len(chamadas[0]["itens"]) == 3
    dados = json.loads(r.stdout)
    assert dados["eventos"] == 3
    assert len(dados["tabela"]) == 2
    # ia / engenharia-de-harness: 2 eventos (1 com eleito, 1 frase_sem_conceito)
    ia_row = dados["por_cadeira_chapeu"]["ia/engenharia-de-harness"]
    assert ia_row["total"] == 2
    assert ia_row["frase_sem_conceito"] == 1
    assert ia_row["chapeu_sem_casamento"] == 0
    assert ia_row["eleito"] == 1

    # dados / governanca: 1 evento (chapeu_sem_casamento)
    dados_row = dados["por_cadeira_chapeu"]["dados/governanca"]
    assert dados_row["total"] == 1
    assert dados_row["frase_sem_conceito"] == 0
    assert dados_row["chapeu_sem_casamento"] == 1
    assert dados_row["eleito"] == 0

    assert dados["totais"] == {
        "total": 3,
        "frase_sem_conceito": 1,
        "chapeu_sem_casamento": 1,
        "eleito": 1,
    }


def test_eleger_tabela_impressa(api):
    roda, _, _ = api
    r = roda()
    assert r.returncode == 0, r.stderr
    assert "eleicao de chapeu sobre 3 eventos do log" in r.stdout
    assert "cadeira" in r.stdout and "chapeu" in r.stdout
    assert "frase_sem_conceito" in r.stdout and "chapeu_sem_casamento" in r.stdout
    assert "ia" in r.stdout and "engenharia-de-harness" in r.stdout
    assert "dados" in r.stdout and "governanca" in r.stdout
    assert "total" in r.stdout


def test_eleger_filtro_desde(api):
    roda, chamadas, _ = api
    r = roda("--desde", "2026-10-09", "--json")
    assert r.returncode == 0, r.stderr
    dados = json.loads(r.stdout)
    assert dados["eventos"] == 1
    assert dados["desde"] == "2026-10-09"
    assert "dados/governanca" in dados["por_cadeira_chapeu"]
    assert "ia/engenharia-de-harness" not in dados["por_cadeira_chapeu"]


def test_eleger_sem_eventos(api):
    roda, chamadas, _ = api
    r = roda("--json", eventos=[])
    assert r.returncode == 0, r.stderr
    dados = json.loads(r.stdout)
    assert dados["eventos"] == 0
    assert dados["tabela"] == []
    assert dados["totais"]["total"] == 0
    assert chamadas == []

    r_txt = roda(eventos=[])
    assert r_txt.returncode == 0
    assert "nenhum evento encontrado" in r_txt.stdout


@pytest.mark.parametrize("args", [
    ("--desconhecido",),
    ("--desde",),
    ("--sem-isso", "x"),
])
def test_eleger_flags_invalidas_sai_2(api, args):
    roda, _, _ = api
    r = roda(*args)
    assert r.returncode == 2
