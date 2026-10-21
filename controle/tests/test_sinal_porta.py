"""`sinal --porta`: a medida da porta de fora, com o token do cliente da sonda (card #3919; spec eixos-do-host
R7 e R8).

Uma porta e um Keycloak de mentira, em loopback, no lugar dos de verdade: o Keycloak troca o segredo do cliente
da sonda por um token; a porta confere o token, responde ao MCP e, quando o teste manda, deixa a linha de giro no
bruto do dia. O que se prova: o ato leve (tool `sessao` sem ato, nunca `monta_sessao`, que abriria sessão),
o erro de transporte separado do erro de verbo, `nao_consegui_olhar` sem credencial, e o token que nunca se
imprime.
"""
import importlib.machinery
import importlib.util
import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

SINAL_PATH = Path(__file__).resolve().parents[2] / "bin" / "sinal"
SEGREDO = "segredo-da-sonda-0123456789"
TOKEN = "TOKEN.DA.SONDA.abcdef"


def _carregar_sinal():
    loader = importlib.machinery.SourceFileLoader("sinal_bin_porta", str(SINAL_PATH))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


sinal = _carregar_sinal()


class Mundo:
    """O que a porta e o Keycloak de mentira viram, e o que o teste manda eles fazerem."""

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir
        self.chamadas = []          # (metodo, nome da tool, argumentos) de cada tools/call
        self.autorizacoes = []
        self.deixa_linha = True     # a porta grava o giro no bruto
        self.classe = "ok"
        self.dur_ms = 41
        self.status_da_chamada = 200
        self.status_do_initialize = 200
        self.ato_da_linha = None    # None: giro da sonda; outro valor: giro de uma cadeira na mesma hora
        self.segredos_vistos = []


def _servidor(handler_cls):
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture
def mundo(tmp_path, monkeypatch):
    log_dir = tmp_path / "ops"
    log_dir.mkdir()
    m = Mundo(log_dir)

    class Keycloak(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            corpo = self.rfile.read(int(self.headers["Content-Length"])).decode()
            m.segredos_vistos.append(corpo)
            if f"client_secret={SEGREDO}" in corpo and "grant_type=client_credentials" in corpo and "client_id=sonda" in corpo:
                self._responde(200, {"access_token": TOKEN, "token_type": "Bearer"})
            else:
                self._responde(401, {"error": "unauthorized_client"})

        def _responde(self, status, corpo):
            dados = json.dumps(corpo).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

    class Porta(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            m.autorizacoes.append(self.headers.get("Authorization"))
            req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.headers.get("Authorization") != f"Bearer {TOKEN}":
                return self._responde(401, {})
            if req["method"] == "initialize":
                return self._responde(m.status_do_initialize, {"jsonrpc": "2.0", "id": 1, "result": {}},
                                      {"mcp-session-id": "sessao-mcp-1"})
            if req["method"] == "notifications/initialized":
                return self._responde(202, {})
            nome, args = req["params"]["name"], req["params"]["arguments"]
            m.chamadas.append((req["method"], nome, args))
            if m.deixa_linha:
                agora = datetime.now(timezone.utc).astimezone(ZoneInfo("America/Sao_Paulo"))
                linha = {"ts": agora.isoformat(), "tool": nome, "ato": m.ato_da_linha, "sessao_id": "-",
                         "dur_ms": m.dur_ms, "classe": m.classe, "origem": "sonda"}
                with open(m.log_dir / f"ops-{agora.strftime('%Y-%m-%d')}.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(linha) + "\n")
            self._responde(m.status_da_chamada, {"jsonrpc": "2.0", "id": 2, "result": {"content": []}})

        def _responde(self, status, corpo, extra=None):
            dados = json.dumps(corpo).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(dados)))
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(dados)

    kc, porta = _servidor(Keycloak), _servidor(Porta)
    instancia = tmp_path / "instancia"
    (instancia / "segredos" / "keycloak").mkdir(parents=True)
    (instancia / "segredos" / "keycloak" / "sonda").write_text(SEGREDO + "\n", encoding="utf-8")
    monkeypatch.setenv("PLATAFIRMA_INSTANCIA", str(instancia))
    monkeypatch.setenv("OPS_LOG_DIR", str(log_dir))
    monkeypatch.setenv("SINAL_SONDA_TOKEN_URL", f"http://127.0.0.1:{kc.server_port}/token")
    monkeypatch.setenv("SINAL_PORTA_URL", f"http://127.0.0.1:{porta.server_port}/mcp")
    monkeypatch.setenv("SINAL_PORTA_TIMEOUT", "3")
    m.instancia = instancia
    yield m
    kc.shutdown()
    porta.shutdown()


def test_porta_de_pe_devolve_latencia_de_fora_ao_lado_do_tempo_da_porta(mundo):
    m = sinal.medir_porta()
    assert m["estado_leitura"] == "lida" and m["causa"] is None
    assert m["latencia_externa_ms"] > 0
    assert m["dur_ms_porta"] == 41
    assert m["erros_transporte"] == 0 and m["erro_verbo"] is None


def test_o_ato_leve_e_a_tool_sessao_sem_ato_e_nunca_monta_sessao(mundo):
    sinal.medir_porta()
    assert mundo.chamadas == [("tools/call", "sessao", {})]
    assert all(a == f"Bearer {TOKEN}" for a in mundo.autorizacoes)


def test_erro_de_verbo_e_a_classe_do_giro_e_nao_conta_como_transporte(mundo):
    mundo.classe = "execucao"
    m = sinal.medir_porta()
    assert m["erro_verbo"] == "execucao"
    assert m["erros_transporte"] == 0


def test_requisicao_sem_linha_de_giro_e_erro_de_transporte(mundo):
    mundo.deixa_linha = False
    mundo.status_da_chamada = 502
    m = sinal.medir_porta(espera_s=0.2)
    assert m["estado_leitura"] == "lida"
    assert m["erros_transporte"] == 1 and m["erro_verbo"] is None
    assert m["dur_ms_porta"] is None


def test_giro_de_cadeira_na_mesma_hora_nao_e_o_giro_da_sonda(mundo):
    mundo.ato_da_linha = "ler"
    m = sinal.medir_porta(espera_s=0.2)
    assert m["erros_transporte"] == 1 and m["dur_ms_porta"] is None


def test_porta_fora_do_ar_e_erro_de_transporte_sem_latencia(mundo, monkeypatch):
    monkeypatch.setenv("SINAL_PORTA_URL", "http://127.0.0.1:9/mcp")
    m = sinal.medir_porta(espera_s=0.1)
    assert m["estado_leitura"] == "lida"
    assert m["erros_transporte"] == 1 and m["latencia_externa_ms"] is None


def test_sem_credencial_da_sonda_nao_consegui_olhar_e_nao_chama_ninguem(mundo):
    (mundo.instancia / "segredos" / "keycloak" / "sonda").unlink()
    m = sinal.medir_porta()
    assert m["estado_leitura"] == "nao_consegui_olhar"
    assert m["causa"] == "sem_credencial_da_sonda"
    assert m["fonte"] == "segredos/keycloak/sonda"
    assert m["latencia_externa_ms"] is None and mundo.segredos_vistos == [] and mundo.chamadas == []


def test_segredo_errado_sai_token_recusado(mundo):
    (mundo.instancia / "segredos" / "keycloak" / "sonda").write_text("outro-segredo\n", encoding="utf-8")
    m = sinal.medir_porta()
    assert (m["estado_leitura"], m["causa"]) == ("nao_consegui_olhar", "token_recusado")


def test_porta_que_recusa_o_token_nao_e_erro_de_transporte(mundo, monkeypatch):
    monkeypatch.setattr(sinal, "obter_token", lambda timeout: "token-que-a-porta-nao-aceita")
    m = sinal.medir_porta()
    assert (m["estado_leitura"], m["causa"]) == ("nao_consegui_olhar", "porta_recusou_o_token")
    assert m["erros_transporte"] == 0


def test_o_token_e_o_segredo_nunca_saem_em_nenhuma_saida(mundo, monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["sinal", "--porta", "--json"])
    assert sinal.main() == 0
    saida = capsys.readouterr()
    for texto in (saida.out, saida.err):
        assert TOKEN not in texto and SEGREDO not in texto
    assert json.loads(saida.out)["dur_ms_porta"] == 41


def test_sem_leitura_a_saida_e_5_e_sem_segredo(mundo, monkeypatch, capsys):
    (mundo.instancia / "segredos" / "keycloak" / "sonda").unlink()
    monkeypatch.setattr("sys.argv", ["sinal", "--porta"])
    assert sinal.main() == 5
    assert "sem_credencial_da_sonda" in capsys.readouterr().out
