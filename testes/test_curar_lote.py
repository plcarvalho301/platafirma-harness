"""#3193: os atos de lote do `curar` (spec espelho-de-leitura §4.2 e §9 caso 8) e o `acervo listar obra
metodos` lendo a tabela única do conversor.

O servidor falso (http.server em thread, loopback, porta livre) responde às rotas do motor como o
contrato do card: POST /acervo/reextracoes/lote (plano e aplicar), GET /acervo/reextracoes/lote/{id},
POST /acervo/espelhos/rejulgamento e POST /acervo/obras/{id}/reextracoes (selada, ou 422 com o
relatório de todos os portões). `curar` roda como subprocesso, como em test_curar_bancada.py.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CURAR = RAIZ / "bin" / "curar"
LISTAR = RAIZ / "bin" / "_acervo" / "listar"
OBRA = "0000de1c-0000-4000-8000-000000000000"
LOTE = "11111111-0000-4000-8000-000000000000"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()

PLANO = {
    "modo": "plano", "ato": "reextrair-lote", "metodo": None, "ordem": [], "corte": "blocos-1", "n": 2,
    "itens": [
        {"posicao": 1, "obra_id": OBRA, "titulo": "Lei 14.133", "tipo": "application/pdf", "bytes": 2097152,
         "marcacao": "transcrita e indexada", "metodo_atual": "perfil", "metodo_alvo": "combinado",
         "servindo_da_fonte": 1},
        {"posicao": 2, "obra_id": "0000beef-0000-4000-8000-000000000000", "titulo": "Manual", "tipo": "DOCX",
         "bytes": 1048576, "marcacao": "transcrita", "metodo_atual": "sem espelho", "metodo_alvo": "docling",
         "servindo_da_fonte": 2},
    ],
    "totais": [{"tipo": "DOCX", "n": 1, "bytes": 1048576}, {"tipo": "application/pdf", "n": 1, "bytes": 2097152}],
    "fora_do_lote": {"XLSX": 3, "PPTX": 2}, "inteiras": 4, "em_dia": 5, "seladas_a_promover": 1,
}

RELATORIO_REPROVADO = {
    "portoes": [
        {"portao": "blocos", "bloqueante": True, "ok": True, "causa": None, "criterio": None},
        {"portao": "pagina_calada", "bloqueante": True, "ok": True, "causa": None, "criterio": None},
        {"portao": "detectores", "bloqueante": True, "ok": False,
         "causa": "§4.5: PDF sem detectores — o método 'perfil' não grava `sinais.tabelas`", "criterio": None},
    ],
}


class Falso:
    def __init__(self):
        self.chamadas = []
        falso = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _resp(self, status, obj):
                dados = json.dumps(obj, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(dados)))
                self.end_headers()
                self.wfile.write(dados)

            def do_GET(self):
                falso.chamadas.append(("GET", self.path, None))
                if self.path.startswith(f"/acervo/reextracoes/lote/{LOTE}"):
                    return self._resp(200, {
                        "lote": LOTE, "estado": "concluido", "criado_em": "2026-10-01T12:00:00+00:00",
                        "autor": "dados", "concluido_em": "2026-10-01T13:00:00+00:00",
                        "por_estado": {"selada": 1, "reprovada": 1},
                        "por_tipo": [{"tipo": "application/pdf", "n": 2, "conversao_ms": 90000, "corte_ms": 3000}],
                        "reprovadas": [{"obra_id": OBRA, "titulo": "Lei 14.133",
                                        "causas": ["§4.5: página calada p. 4"]}],
                        "prazo_insuficiente": [], "falha_de_maquina_repetida": [], "itens": []})
                return self._resp(404, {"title": "LoteNaoEncontrado", "detail": "não há"})

            def do_POST(self):
                corpo = json.loads(self.rfile.read(int(self.headers.get("content-length") or 0)) or b"{}")
                falso.chamadas.append(("POST", self.path, corpo))
                if self.path == "/acervo/reextracoes/lote":
                    if corpo.get("aplicar"):
                        resumo = {k: v for k, v in PLANO.items() if k != "itens"}
                        return self._resp(200, {**resumo, "modo": "aplicado", "lote": LOTE,
                                                "acompanhar": f"acervo curar biblioteca --reextrair --lote --relatorio {LOTE}"})
                    return self._resp(200, PLANO)
                if self.path == "/acervo/espelhos/rejulgamento":
                    item = {"impressao": "imp-1", "obra_id": OBRA, "titulo": "Lei 14.133", "estado": "servindo",
                            "regua_atual": 1, "qualidade_atual": "boa"}
                    if corpo.get("aplicar"):
                        return self._resp(200, {"modo": "aplicado", "regua": 2, "n": 1, "falhas": [],
                                                "itens": [{**item, "qualidade": "suspeita",
                                                           "motivo": ["substituições 3"]}]})
                    return self._resp(200, {"modo": "plano", "regua": 2, "n": 1, "itens": [item]})
                if self.path == f"/acervo/obras/{OBRA}/reextracoes":
                    if corpo.get("metodo") == "perfil":
                        return self._resp(422, {"type": "about:blank", "title": "ReextracaoReprovada",
                                                "detail": RELATORIO_REPROVADO["portoes"][2]["causa"],
                                                "criterio": None, "relatorio": RELATORIO_REPROVADO})
                    return self._resp(200, {
                        "modo": "aplicado", "ato": "reextrair", "obra_id": OBRA, "titulo": "Lei 14.133",
                        "objeto": "acervo/abc", "impressao_atual": "imp-velha", "espelho_atual": "d" * 64,
                        "metodo_alvo": "combinado", "metodo": "combinado", "regenerar": False, "trechos": 12,
                        "impressao_nova": "imp-nova", "selada": True, "ja_selada": False, "ja_existia": False,
                        "promover": f"acervo curar biblioteca --promover {OBRA} --impressao imp-nova",
                        "espelho": {"digest": "e" * 64, "qualidade": "boa", "motivo": [],
                                    "conversor": {"nome": "combinado", "versao": "1"}}})
                return self._resp(404, {"title": "Nada", "detail": self.path})

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()


@pytest.fixture
def falso():
    f = Falso()
    yield f
    f.fechar()


def _curar(falso, *argv):
    env = {**os.environ, "MOTOR_ACERVO_URL": falso.url, "RAG_API_TOKEN": "tok-teste", "PF_CADEIRA": "dados"}
    return subprocess.run([PY, str(CURAR), *argv], capture_output=True, text=True, env=env, timeout=60, check=False)


precisa_requests = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


@precisa_requests
def test_lote_plano_e_o_portao_1_com_a_contagem_por_tipo(falso):
    r = _curar(falso, "--reextrair", "--lote")
    assert r.returncode == 0, r.stderr
    assert "PORTÃO 1" in r.stdout
    assert "application/pdf" in r.stdout and "DOCX" in r.stdout
    assert "fora do lote" in r.stdout and "XLSX 3" in r.stdout
    assert "plano seco" in r.stdout
    verbo, caminho, corpo = falso.chamadas[-1]
    assert (verbo, caminho) == ("POST", "/acervo/reextracoes/lote")
    assert corpo["aplicar"] is False and corpo["metodo"] is None and corpo["ordem"] == []


@precisa_requests
def test_lote_apply_devolve_o_id_e_como_acompanhar(falso):
    r = _curar(falso, "--reextrair", "--lote", "--ordem", "de1c6e97,514d9c80", "--apply")
    assert r.returncode == 0, r.stderr
    assert LOTE in r.stdout and f"--relatorio {LOTE}" in r.stdout
    corpo = falso.chamadas[-1][2]
    assert corpo["aplicar"] is True and corpo["ordem"] == ["de1c6e97", "514d9c80"]


@precisa_requests
def test_lote_de_medida_leva_replicas_e_a_lista(falso):
    r = _curar(falso, "--reextrair", "--lote", "--medida", "--replicas", "2", "--ordem", "de1c6e97", "--apply")
    assert r.returncode == 0, r.stderr
    corpo = falso.chamadas[-1][2]
    assert corpo["medida"] is True and corpo["replicas"] == 2 and corpo["ordem"] == ["de1c6e97"]


@precisa_requests
def test_lote_de_medida_sem_lista_recusa_antes_de_chamar(falso):
    antes = len(falso.chamadas)
    r = _curar(falso, "--reextrair", "--lote", "--medida", "--replicas", "2", "--apply")
    assert r.returncode == 2 and "--ordem" in r.stderr
    assert len(falso.chamadas) == antes


@precisa_requests
def test_relatorio_do_lote_lista_as_reprovadas_com_a_causa(falso):
    r = _curar(falso, "--reextrair", "--lote", "--relatorio", LOTE)
    assert r.returncode == 0, r.stderr
    assert falso.chamadas[-1][:2] == ("GET", f"/acervo/reextracoes/lote/{LOTE}")
    assert "reprovadas (1)" in r.stdout and "página calada p. 4" in r.stdout


@precisa_requests
def test_rejulgar_lote_plano_e_apply(falso):
    r = _curar(falso, "--rejulgar", "--lote")
    assert r.returncode == 0, r.stderr
    assert "Plano: 1 espelho(s)" in r.stdout and falso.chamadas[-1][2]["aplicar"] is False
    r = _curar(falso, "--rejulgar", "--lote", "--apply")
    assert r.returncode == 0, r.stderr
    assert "rejulgado(s) pela régua 2" in r.stdout and "suspeita (substituições 3)" in r.stdout


@precisa_requests
@pytest.mark.parametrize("argv", [["--rejulgar"], ["--lote"], ["--reextrair", "--lote", "--bancada", "/tmp/x"],
                                  ["--rejulgar", "--lote", "--reextrair"]])
def test_combinacoes_de_lote_que_nao_valem_saem_2(falso, argv):
    r = _curar(falso, *argv)
    assert r.returncode == 2, (r.stdout, r.stderr)
    assert not [c for c in falso.chamadas if c[0] == "POST"]


@precisa_requests
def test_reextrair_termina_na_selada_e_traz_o_promover(falso):
    r = _curar(falso, "--reextrair", OBRA, "--apply")
    assert r.returncode == 0, r.stderr
    assert "imp-nova selada" in r.stdout and "imp-velha segue servindo" in r.stdout
    assert f"--promover {OBRA} --impressao imp-nova" in r.stdout
    assert "servindo ·" not in r.stdout and "aposentada" not in r.stdout
    assert falso.chamadas[-1][2]["metodo"] is None  # sem --metodo, o padrão do tipo decide no servidor


@precisa_requests
def test_reextrair_reprovada_mostra_todos_os_portoes(falso):
    r = _curar(falso, "--reextrair", OBRA, "--metodo", "perfil", "--apply")
    assert r.returncode == 1
    assert "Reextração reprovada" in r.stdout and "PDF sem detectores" in r.stdout
    linhas = [linha.split() for linha in r.stdout.splitlines() if linha.startswith("    ")]
    assert [(linha[0], linha[1]) for linha in linhas] == [
        ("REPROVA", "detectores"), ("ok", "blocos"), ("ok", "pagina_calada")]


def test_listar_obra_metodos_le_a_tabela_do_conversor(tmp_path):
    pacote = tmp_path / "conversor" / "conversor"
    pacote.mkdir(parents=True)
    (pacote / "__init__.py").write_text("")
    (pacote / "padrao.py").write_text(
        "def linhas():\n"
        "    return [{'tipo': 'application/pdf', 'rotulo': 'PDF', 'metodo': 'combinado',\n"
        "             'conversor': 'docling-slim', 'versao': '==2.126.0', 'desde': '2026-10-01', 'lote': True},\n"
        "            {'tipo': 'XLSX', 'rotulo': 'XLSX', 'metodo': 'perfil', 'conversor': 'openpyxl',\n"
        "             'versao': '>=3.1.5', 'desde': '2026-09-28', 'lote': False}]\n")
    env = {**os.environ, "PF_CONHECIMENTO_DIR": str(tmp_path)}
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "metodos", "--json"], capture_output=True,
                       text=True, env=env, timeout=60, check=False)
    assert r.returncode == 0, r.stderr
    itens = json.loads(r.stdout)
    assert itens[0] == {"tipo": "PDF", "mime": "application/pdf", "metodo": "combinado",
                        "conversor": "docling-slim", "versao": "==2.126.0", "desde": "2026-10-01", "lote": True}
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "metodos"], capture_output=True,
                       text=True, env=env, timeout=60, check=False)
    assert r.returncode == 0, r.stderr
    assert "combinado" in r.stdout and "2026-10-01" in r.stdout and "fora (inteira)" in r.stdout
