"""`motor rag buscar` monta a consulta (card #3360; spec motor-do-conhecimento §2b): a fiação do verbo.

O verbo roda de verdade, como subprocesso, contra um rag-api falso em 127.0.0.1 (como test_motor_indexar.py).
O log da porta (OPS_LOG_DIR) é escrito pelo `oplog.emitir` real; rotas-chapeu.json tem a forma do arquivo da
abertura publicada. A lógica (lint, montagem, rótulos, pedido) está medida em test_motor_consulta.py; aqui se
prova o que o verbo manda à API, o que recusa antes de chamar e o que grava na linha de log da porta.
O rag-api de verdade (validação, eco do envelope, os campos do evento) está em rag/tests/test_api_consulta.py.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

RAIZ = Path(__file__).resolve().parents[2]
MOTOR = RAIZ / "bin" / "motor"
sys.path.insert(0, str(RAIZ / "lib"))

import oplog  # noqa: E402

SESSAO = "5a32558c-8b05-493a-a70c-7e752944cdb4"
PEDIDO = "mede o piso de abstenção da geração Nemotron e me diz se ele ainda vale"
NEC = "qual piso de abstenção a geração Nemotron usa?"
ROTULOS = ["Complexidade assintotica", "asymptotic complexity", "big-o", "Pipeline RAG", "rag",
           "retrieval-augmented generation", "Ranqueamento multiestágio", "reranking", "Juiz-modelo"]


class _API(BaseHTTPRequestHandler):
    pedidos: ClassVar[list] = []

    def log_message(self, *a):
        pass

    def do_POST(self):
        corpo = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        self.pedidos.append(corpo)
        p = corpo["pergunta"]
        n = len(p) if isinstance(p, list) else 1
        dado = json.dumps({"fontes": [], "cobertura": "fraca", "tempos_ms": {"total": 5.0, "n_perguntas": n},
                           **({"consulta": corpo["consulta"]} if "consulta" in corpo else {})}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)


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
        "token_em": "rag/RAG_API_TOKEN", "facets": f"{base}/facets", "medicoes_em": "var/medicoes/rag",
        "ajustes": [], "nao_e_ajuste": {}}}))
    abertura = tmp_path / "abertura-publicada" / "current" / "abertura"
    abertura.mkdir(parents=True)
    (abertura / "rotas-chapeu.json").write_text(json.dumps(
        {"ia": {"engenharia-de-harness": ROTULOS}}, ensure_ascii=False), encoding="utf-8")
    _API.pedidos = []
    ops = tmp_path / "ops"

    def roda(*args, ambiente=None):
        env = {**os.environ, "PF_MOTOR_REG": str(registro), "PLATAFIRMA_INSTANCIA": str(instancia),
               "OPS_LOG_DIR": str(ops), "PF_ABERTURA_DIR": str(tmp_path / "abertura-publicada"),
               "PF_CADEIRA": "ia", "PF_CHAPEU": "engenharia-de-harness", "PF_SESSAO": SESSAO,
               **(ambiente or {})}
        return subprocess.run([sys.executable, str(MOTOR), "rag", *args], capture_output=True, text=True,
                              env=env, timeout=60, check=False, stdin=subprocess.DEVNULL)

    def abertura_do_dono(pergunta=PEDIDO, chapeu="engenharia-de-harness", cadeira=None):
        oplog.emitir({"tool": "monta_sessao", "sessao_id": SESSAO, "pergunta": pergunta, "chapeu": chapeu},
                     diretorio_=ops, agora=datetime.now().astimezone())
        if cadeira:      # um giro da sessao, que e a linha do log que leva a cadeira
            oplog.emitir({"tool": "repo", "ato": "ler", "sessao_id": SESSAO, "cadeira": cadeira, "exit_code": 0},
                         diretorio_=ops, agora=datetime.now().astimezone())

    def linhas_do_ops():
        return [json.loads(l) for f in ops.glob("ops-*.jsonl") for l in f.read_text().splitlines()]

    yield roda, _API.pedidos, abertura_do_dono, linhas_do_ops
    servidor.shutdown()


def test_necessidade_monta_a_lista_de_tres_com_pedido_da_porta_e_rotulos(api):
    roda, pedidos, abertura, _ = api
    abertura()
    r = roda("buscar", "biblioteca", "--necessidade", NEC)
    assert r.returncode == 0, r.stderr
    corpo = pedidos[-1]
    assert corpo["pergunta"] == [NEC, PEDIDO, NEC + " — " + ", ".join(ROTULOS[:8])]
    c = corpo["consulta"]
    assert c["fonte_pedido"] == "porta" and c["pedido"] == PEDIDO and c["necessidade"] == NEC
    assert c["chapeu"] == "engenharia-de-harness" and c["rotulos"] == ROTULOS[:8]
    assert c["perguntas"] == corpo["pergunta"] and "lint" not in c
    assert corpo["origem"] == "busca" and corpo["sessao_id"] == SESSAO
    envelope = json.loads(r.stdout)
    assert envelope["tempos_ms"]["n_perguntas"] == 3 and envelope["consulta"]["fonte_pedido"] == "porta"


def test_sem_pf_chapeu_no_ambiente_o_chapeu_vem_da_abertura_no_log(api):
    """Medido no ar em 08/10: no claude.ai a porta nao poe PF_CHAPEU no verbo e a lista saia com 2 itens."""
    roda, pedidos, abertura, _ = api
    abertura()
    r = roda("buscar", "biblioteca", "--necessidade", NEC, ambiente={"PF_CHAPEU": ""})
    assert r.returncode == 0, r.stderr
    c = pedidos[-1]["consulta"]
    assert c["chapeu"] == "engenharia-de-harness" and c["rotulos"] == ROTULOS[:8]
    assert len(c["perguntas"]) == 3 and pedidos[-1]["pergunta"] == c["perguntas"]


def test_sem_pf_chapeu_nem_pf_cadeira_a_cadeira_vem_de_uma_linha_do_log(api):
    roda, pedidos, abertura, _ = api
    abertura(cadeira="ia")
    r = roda("buscar", "biblioteca", "--necessidade", NEC, ambiente={"PF_CHAPEU": "", "PF_CADEIRA": ""})
    assert r.returncode == 0, r.stderr
    c = pedidos[-1]["consulta"]
    assert c["chapeu"] == "engenharia-de-harness" and c["rotulos"] == ROTULOS[:8] and len(c["perguntas"]) == 3


def test_sem_cadeira_em_lugar_nenhum_o_chapeu_sai_mas_os_rotulos_nao(api):
    roda, pedidos, abertura, _ = api
    abertura()
    r = roda("buscar", "biblioteca", "--necessidade", NEC, ambiente={"PF_CHAPEU": "", "PF_CADEIRA": ""})
    assert r.returncode == 0, r.stderr
    c = pedidos[-1]["consulta"]
    assert c["chapeu"] == "engenharia-de-harness" and c["rotulos"] == [] and len(c["perguntas"]) == 2


def test_pf_chapeu_do_ambiente_vence_o_do_log(api):
    roda, pedidos, abertura, _ = api
    abertura(chapeu="agente")
    r = roda("buscar", "biblioteca", "--necessidade", NEC, ambiente={"PF_CHAPEU": "engenharia-de-harness"})
    assert r.returncode == 0, r.stderr
    assert pedidos[-1]["consulta"]["chapeu"] == "engenharia-de-harness"


def test_sem_pedido_alcancavel_declara_ausente_e_segue_com_necessidade_e_chapeu(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "--necessidade", NEC)
    assert r.returncode == 0, r.stderr
    c = pedidos[-1]["consulta"]
    assert c["fonte_pedido"] == "ausente" and c["pedido"] is None and len(c["perguntas"]) == 2


def test_sem_chapeu_sai_o_terceiro_item(api):
    roda, pedidos, abertura, _ = api
    abertura(chapeu="-")        # o roteador caiu em fallback: nem o ambiente nem a abertura tem chapeu
    r = roda("buscar", "biblioteca", "--necessidade", NEC, ambiente={"PF_CHAPEU": "-"})
    assert r.returncode == 0, r.stderr
    c = pedidos[-1]["consulta"]
    assert c["chapeu"] is None and c["rotulos"] == [] and c["perguntas"] == [NEC, PEDIDO]


def test_so_a_necessidade_vai_como_string_como_antes(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "--necessidade", NEC, ambiente={"PF_CHAPEU": "-"})
    assert r.returncode == 0, r.stderr
    assert pedidos[-1]["pergunta"] == NEC and pedidos[-1]["consulta"]["perguntas"] == [NEC]


def test_pedido_da_flag_sobrepoe_o_da_porta(api):
    roda, pedidos, abertura, _ = api
    abertura("o pedido da porta")
    r = roda("buscar", "biblioteca", "--necessidade", NEC, "--pedido", "o pedido da flag")
    assert r.returncode == 0, r.stderr
    c = pedidos[-1]["consulta"]
    assert c["fonte_pedido"] == "flag" and c["pedido"] == "o pedido da flag"


def test_pedido_e_cortado_em_600_caracteres(api):
    roda, pedidos, abertura, _ = api
    abertura("palavra " * 200)
    r = roda("buscar", "biblioteca", "--necessidade", NEC)
    assert r.returncode == 0, r.stderr
    assert len(pedidos[-1]["consulta"]["pedido"]) <= 600


def test_posicional_em_frase_passa_pelo_lint_e_vira_necessidade(api):
    roda, pedidos, _, _ = api
    texto = "como o log da porta grava o prompt do dono?"
    r = roda("buscar", "biblioteca", texto)
    assert r.returncode == 0, r.stderr
    assert pedidos[-1]["consulta"]["necessidade"] == texto


def test_tres_assuntos_com_ponto_e_virgula_sai_2_sem_chamar_a_api(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "SRE overload cascading failures; golden hammer lava flow; xUnit test smells")
    assert r.returncode == 2
    linhas = r.stderr.splitlines()
    assert linhas[0] == "consulta recusada: três assuntos em uma chamada"
    assert linhas[1].strip() == "uma necessidade por chamada; mande 3 chamadas no mesmo lote"
    assert pedidos == []


def test_saco_de_palavras_sai_2_sem_chamar_a_api(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "UTF-8 decoding truncated multibyte sequence byte boundary")
    assert r.returncode == 2
    assert r.stderr.splitlines()[0] == "consulta recusada: sem forma de frase"
    assert "escreva a necessidade em frase" in r.stderr.splitlines()[1]
    assert pedidos == []


def test_necessidade_em_ingles_com_pedido_em_portugues_sai_2(api):
    roda, pedidos, abertura, _ = api
    abertura()
    r = roda("buscar", "biblioteca", "--necessidade", "what is the abstention floor of the Nemotron generation?")
    assert r.returncode == 2
    assert r.stderr.splitlines()[0] == "consulta recusada: língua diferente da do pedido"
    assert pedidos == []


def test_sem_lint_deixa_passar_e_grava_desligado(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "--sem-lint", "UTF-8 decoding truncated multibyte sequence byte boundary")
    assert r.returncode == 0, r.stderr
    assert pedidos[-1]["consulta"]["lint"] == "desligado"


@pytest.mark.parametrize("origem", ["abertura", "bench", "sombra", "autoteste"])
def test_origem_literal_nao_passa_pelo_lint_nem_monta(api, origem):
    roda, pedidos, abertura, _ = api
    abertura()
    texto = "Respondi o gold set todo"
    saco = "UTF-8 decoding truncated multibyte sequence byte boundary; golden hammer"
    for t in (texto, saco):
        r = roda("buscar", "casa", t, "--origem", origem)
        assert r.returncode == 0, r.stderr
        assert pedidos[-1]["pergunta"] == t and "consulta" not in pedidos[-1]
        assert pedidos[-1]["origem"] == origem
    assert "consulta" not in json.loads(r.stdout)


def test_origem_literal_com_flag_de_montagem_sai_2(api):
    roda, pedidos, _, _ = api
    assert roda("buscar", "casa", "--origem", "abertura", "--necessidade", NEC).returncode == 2
    assert roda("buscar", "casa", "texto qualquer da abertura", "--origem", "bench", "--sem-lint").returncode == 2
    assert roda("buscar", "casa", "texto qualquer da abertura", "--origem", "sombra", "--pedido", "x").returncode == 2
    assert pedidos == []


def test_texto_posicional_e_necessidade_juntos_sai_2(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "uma frase qualquer aqui", "--necessidade", NEC)
    assert r.returncode == 2 and "use um so" in r.stderr
    assert pedidos == []


def test_origem_busca_explicita_tambem_passa_pelo_lint(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "a; b", "--origem", "busca")
    assert r.returncode == 2 and pedidos == []


def test_o_evento_consulta_do_ops_grava_a_necessidade_com_a_lista_enviada(api):
    """Regressão: com `pergunta` em lista, `pergunta.encode()` levantava e a linha sumia em silêncio."""
    roda, _, abertura, linhas = api
    abertura()
    r = roda("buscar", "biblioteca", "--necessidade", NEC)
    assert r.returncode == 0, r.stderr
    evento = [l for l in linhas() if l.get("evento") == "consulta"][-1]
    assert evento["query"] == NEC and evento["query_bytes"] == len(NEC.encode())
    assert evento["origem_consulta"] == "busca" and evento["particao"] == "biblioteca"
    assert evento["montagem"] == {"fonte_pedido": "porta", "pedido_bytes": len(PEDIDO.encode()),
                                  "n_rotulos": 8, "n_perguntas": 3, "lint": None}
    assert PEDIDO not in json.dumps(evento, ensure_ascii=False), "o pedido não é copiado para a linha da consulta"


def test_flag_desconhecida_continua_sai_2_e_lista_as_novas(api):
    roda, pedidos, _, _ = api
    r = roda("buscar", "biblioteca", "uma frase qualquer aqui", "--sem-isso", "x")
    assert r.returncode == 2 and "--necessidade" in r.stderr and "--sem-lint" in r.stderr
    assert pedidos == []
