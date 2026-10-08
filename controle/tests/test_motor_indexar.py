"""`motor rag indexar biblioteca` e a partição biblioteca no `motor` (card #3203; arq:0106 §3; arq:0119 §2).

O verbo roda de verdade, como subprocesso, contra um rag-api falso em 127.0.0.1: registro, token e log
apontam para um diretório temporário (PF_MOTOR_REG, PLATAFIRMA_INSTANCIA, OPS_LOG_DIR). Prova o que o
verbo manda à API e o que imprime; não prova o lote, que é do rag-api (platafirma-conhecimento,
rag/tests/test_indexacao.py).
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
OBRA = "de1c6e97-0000-4000-8000-000000000001"
LOTE = "0f0f0f0f-1111-4222-8333-444444444444"


class _API(BaseHTTPRequestHandler):
    pedidos: ClassVar[list] = []

    def log_message(self, *a):
        pass

    def _responde(self, status, corpo, tipo="application/json"):
        dado = json.dumps(corpo).encode()
        self.send_response(status)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        self.pedidos.append(("POST", self.path, self.headers.get("Authorization"), corpo))
        if self.path == "/search":
            pergunta = corpo.get("pergunta", "")
            if "negativa" in pergunta:
                return self._responde(200, {"fontes": [], "cobertura": "fraca", "tempos_ms": {"total": 5.0}})
            return self._responde(200, {"fontes": [{"obra": "Obra", "section_id": "sec-1",
                                                     "secao_id": "00000000-0000-0000-0000-000000000001"}],
                                        "cobertura": "boa", "tempos_ms": {"total": 5.0}})
        if corpo.get("aplicar"):
            return self._responde(200, {"modo": "aplicado", "lote": LOTE, "n": 1, "a_indexar": 1,
                                        "trechos_a_embedar": 3, "prontas": 0, "fora_transcritas": 0,
                                        "indexadas": 1, "seladas": 1, "promover": corpo.get("promover"),
                                        "acompanhar": f"motor rag indexar biblioteca --relatorio {LOTE}"})
        return self._responde(200, {"modo": "plano", "n": 1, "a_indexar": 1, "trechos_a_embedar": 3,
                                    "prontas": 0, "fora_transcritas": 0, "indexadas": 1, "seladas": 1,
                                    "promover": False, "itens": [
                                        {"posicao": 1, "obra_id": OBRA, "titulo": "Obra", "elegiveis": 3,
                                         "vetores": 0, "acao": "indexar"}]})

    def do_GET(self):
        self.pedidos.append(("GET", self.path, self.headers.get("Authorization"), None))
        if self.path == "/facets":
            return self._responde(200, {"indice": {"acervo_sha": "abc123456789", "embed_model": "model",
                                                   "embed_backend": "torch"}})
        if self.path.endswith(LOTE):
            return self._responde(200, {"lote": LOTE, "estado": "concluido", "por_estado": {"indexada": 1},
                                        "embedados": 3, "ms": 2000, "itens": [
                                            {"estado": "indexada", "obra_id": OBRA, "titulo": "Obra",
                                             "gate": {"aprovado": True, "vetores": 3, "elegiveis": 3}}]})
        return self._responde(404, {"type": "about:blank", "title": "LoteNaoEncontrado",
                                    "detail": "planeje de novo"}, "application/problem+json")


@pytest.fixture
def api(tmp_path):
    servidor = HTTPServer(("127.0.0.1", 0), _API)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{servidor.server_port}"
    instancia = tmp_path / "inst"
    (instancia / "segredos" / "rag").mkdir(parents=True)
    (instancia / "segredos" / "rag" / "RAG_API_TOKEN").write_text("tok\n")
    registro = tmp_path / "motor-instancias.json"
    registro.write_text(json.dumps({"rag": {
        "estado": "ativa", "container": None, "stack": "rag", "endpoint": f"{base}/search",
        "indexacao": f"{base}/motor/indexacoes/lote", "token_em": "rag/RAG_API_TOKEN",
        "facets": f"{base}/facets", "medicoes_em": "var/medicoes/rag",
        "ajustes": [], "nao_e_ajuste": {}}}))
    _API.pedidos = []

    def roda(*args, sem_instancia=False, ambiente=None):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(tmp_path / "ops"), "PF_CADEIRA": "ia", **(ambiente or {})}
        inicio = [] if sem_instancia else ["rag"]
        return subprocess.run([sys.executable, str(MOTOR), *inicio, *args], capture_output=True, text=True,
                              env=env, timeout=60, check=False)

    yield roda, _API.pedidos
    servidor.shutdown()


def test_o_plano_manda_as_obras_e_o_autor_e_nao_aplica(api):
    roda, pedidos = api
    r = roda("indexar", "biblioteca", "--obra", OBRA)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0].startswith("plano: 1 impressao(oes) · 1 a indexar (3 trechos a embedar)")
    assert OBRA in r.stdout and "para valer: o mesmo comando com --apply" in r.stdout
    metodo, caminho, auth, corpo = pedidos[-1]
    assert (metodo, caminho, auth) == ("POST", "/motor/indexacoes/lote", "Bearer tok")
    assert corpo == {"autor": "ia", "aplicar": False, "obras": [OBRA], "promover": False}


def test_apply_com_promover_abre_o_lote_e_devolve_como_acompanhar(api):
    roda, pedidos = api
    r = roda("indexar", "biblioteca", "--promover", "--apply", "--autor", "dados")
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0].startswith(f"lote {LOTE} aberto no rag-api")
    assert f"acompanhar: motor rag indexar biblioteca --relatorio {LOTE}" in r.stdout
    assert pedidos[-1][3] == {"autor": "dados", "aplicar": True, "obras": [], "promover": True}


def test_relatorio_le_o_lote_e_o_id_perdido_sai_1(api):
    roda, pedidos = api
    r = roda("indexar", "biblioteca", "--relatorio", LOTE)
    assert r.returncode == 0, r.stderr
    assert r.stdout.splitlines()[0].startswith(f"lote {LOTE}: concluido · indexada 1 · 3 vetores de trecho")
    assert pedidos[-1][:2] == ("GET", f"/motor/indexacoes/lote/{LOTE}")
    perdido = roda("indexar", "biblioteca", "--relatorio", "00000000-0000-4000-8000-000000000000")
    assert perdido.returncode == 1 and "LoteNaoEncontrado: planeje de novo" in perdido.stderr


def test_uso_errado_sai_2_sem_chamar_a_api(api):
    roda, pedidos = api
    assert roda("indexar", "casa").returncode == 2
    assert roda("indexar", "biblioteca", "--obra", "de1c6e97").returncode == 2  # prefixo não é uuid
    assert roda("indexar", "biblioteca", "--sem-isso").returncode == 2
    assert pedidos == []


def test_biblioteca_e_obra_sao_a_mesma_particao_e_a_api_recebe_biblioteca(api):
    roda, pedidos = api
    for nome in ("biblioteca", "obra"):
        r = roda("buscar", nome, "pergunta")
        assert r.returncode == 0, r.stderr
        assert pedidos[-1][1] == "/search" and pedidos[-1][3]["particao"] == "biblioteca"
        assert pedidos[-1][3]["pergunta"] == "pergunta"


# --- #3314: origem, sessao e fita no corpo da busca; particao e origem no evento do ops -------

SESSAO = "5a32558c-8b05-493a-a70c-7e752944cdb4"

def test_buscar_sem_flag_grava_origem_busca_e_leva_sessao_e_fita_do_ambiente(api):
    roda, pedidos = api
    r = roda("buscar", "biblioteca", "pergunta",
             ambiente={"PF_SESSAO": SESSAO, "PF_ORDEM_ID": "o20261007T200203-3049c8"})
    assert r.returncode == 0, r.stderr
    corpo = pedidos[-1][3]
    assert corpo["origem"] == "busca"
    assert corpo["particao"] == "biblioteca"
    assert corpo["sessao_id"] == SESSAO
    assert corpo["ordem_id"] == "o20261007T200203-3049c8"

def test_buscar_sem_sessao_no_ambiente_nao_manda_sessao_nem_fita(api):
    roda, pedidos = api
    r = roda("buscar", "biblioteca", "pergunta", ambiente={"PF_SESSAO": "-", "PF_ORDEM_ID": ""})
    assert r.returncode == 0, r.stderr
    assert "sessao_id" not in pedidos[-1][3] and "ordem_id" not in pedidos[-1][3]

def test_buscar_com_origem_declarada_manda_a_origem_e_a_ordem_do_argumento_vence(api):
    roda, pedidos = api
    r = roda("buscar", "casa", "pergunta", "--origem", "abertura", "--ordem-id", "o-do-argumento",
             ambiente={"PF_ORDEM_ID": "o-do-ambiente"})
    assert r.returncode == 0, r.stderr
    corpo = pedidos[-1][3]
    assert corpo["origem"] == "abertura" and corpo["particao"] == "casa"
    assert corpo["ordem_id"] == "o-do-argumento"

def test_buscar_com_origem_fora_da_lista_sai_2_sem_chamar_a_api(api):
    roda, pedidos = api
    r = roda("buscar", "biblioteca", "pergunta", "--origem", "manual")
    assert r.returncode == 2 and "--origem aceita" in r.stderr
    assert roda("buscar", "biblioteca", "pergunta", "--origem").returncode == 2
    assert pedidos == []

def test_o_evento_consulta_do_ops_grava_particao_e_origem(api, tmp_path):
    roda, _ = api
    r = roda("buscar", "casa", "pergunta", "--origem", "abertura")
    assert r.returncode == 0, r.stderr
    linhas = [json.loads(l) for f in (tmp_path / "ops").glob("ops-*.jsonl")
              for l in f.read_text().splitlines()]
    evento = [l for l in linhas if l.get("evento") == "consulta"][-1]
    assert evento["particao"] == "casa" and evento["origem_consulta"] == "abertura"
    # A consulta da abertura grava a mensagem do dono (ordem de 08/10) e so ela: o que a busca
    # devolveu (fontes, contexto) nao entra na linha. `origem` e de quem chamou.
    assert evento["query"] == "pergunta" and evento["query_bytes"] == len("pergunta")
    assert not {"fontes", "contexto", "resposta", "texto"} & set(evento)
    assert evento["origem"] == "cadeira" and evento["schema_v"] == 1 and evento["evento_id"]


def test_a_consulta_de_cadeira_tambem_grava_a_query(api, tmp_path):
    roda, _ = api
    r = roda("buscar", "casa", "o que e caderno", "--origem", "busca")
    assert r.returncode == 0, r.stderr
    linhas = [json.loads(l) for f in (tmp_path / "ops").glob("ops-*.jsonl")
              for l in f.read_text().splitlines()]
    evento = [l for l in linhas if l.get("evento") == "consulta"][-1]
    assert evento["origem_consulta"] == "busca" and evento["query"] == "o que e caderno"
    assert evento["query_bytes"] == len("o que e caderno")

def test_lote_pela_tool_com_instancia_e_ato_repetidos_busca_na_particao_pedida(api):
    # #2856 linha 23: `ato: buscar` com args [rag, buscar, casa, ...] chegava como
    # `motor buscar rag buscar casa ...`: buscava em biblioteca, com a pergunta «rag buscar casa ...».
    roda, pedidos = api
    r = roda("buscar", "rag", "buscar", "casa", "pergunta", sem_instancia=True)
    assert r.returncode == 0, r.stderr
    assert "sem particao" not in r.stderr
    assert pedidos[-1][3]["particao"] == "casa" and pedidos[-1][3]["pergunta"] == "pergunta"


def test_medir_calcula_abstencao_hit_k_e_t2_com_delta(api, tmp_path):
    roda, pedidos = api
    gab = tmp_path / "gabarito.jsonl"
    itens = [
        {"pergunta": "onde esta a obra?", "estrato": "T2-cadeiras", "alvo_obras": ["Obra"],
         "relevancia": "positiva", "pontuavel": True},
        {"pergunta": "pergunta negativa sem resposta", "estrato": "T2-cadeiras", "alvo_section_id": None,
         "alvo_obra_ids": [], "relevancia": "negativa", "pontuavel": True},
        {"pergunta": "pergunta multi-step", "estrato": "T3", "alvo_section_id": None,
         "alvo_obra_ids": [], "relevancia": "indeterminada", "pontuavel": True},
    ]
    gab.write_text("\n".join(json.dumps(x) for x in itens) + "\n", encoding="utf-8")

    # 1a rodada
    r = roda("medir", "biblioteca", "--gabarito", str(gab), "--k", "8", "--rotulo", "r1")
    assert r.returncode == 0, r.stderr
    assert "abstenção 1/1" in r.stdout
    assert "t2" in r.stdout
    assert "hit@8" in r.stdout
    assert "primeira medicao" in r.stdout

    # 2a rodada (avalia delta)
    r2 = roda("medir", "biblioteca", "--gabarito", str(gab), "--k", "8", "--rotulo", "r2")
    assert r2.returncode == 0, r2.stderr
    assert "abstenção 1/1" in r2.stdout
    assert "contra" in r2.stdout
    assert "t2" in r2.stdout
