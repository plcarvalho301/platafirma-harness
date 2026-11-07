"""Testes de regressão para os 5 débitos técnicos resolvidos no harness:
- DT 83: tarefas estados filtra estados retirados (retirado != true)
- DT 204: tarefas sub <pai> com 1 argumento lista as filhas
- DT 252: release migrar aplicar recusa com exit 2 quando stdin vem vazio
- DT 270: tarefas criar e editar passam corpo ao jq sem --arg para evitar estouro de exec
- DT 1: repo resolve <repo>@<card> casando <card>-<slug>
"""
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import ClassVar

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN_TAREFAS = REPO_ROOT / "bin" / "tarefas"
BIN_REPO = REPO_ROOT / "bin" / "repo"
BIN_MIGRAR = REPO_ROOT / "bin" / "_release" / "migrar"


class _MockRastreador(BaseHTTPRequestHandler):
    pedidos: ClassVar[list] = []
    registro_estados: ClassVar[list] = [
        {"estado": "captada", "nome": "Captada", "fase": "funil", "retirado": False},
        {"estado": "refinada", "nome": "Refinada", "fase": "delivery", "retirado": True},
        {"estado": "em-execucao", "nome": "Em execução", "fase": "delivery", "retirado": False},
    ]
    item_resposta: ClassVar[dict] = {
        "id": 100,
        "titulo": "Item pai",
        "filhas": [
            {"id": 101, "estado": "em-execucao", "cadeira": "engenharia", "titulo": "Filha 1"},
            {"id": 102, "estado": "captada", "cadeira": "arquiteto", "titulo": "Filha 2"},
        ]
    }

    def log_message(self, *a):
        pass

    def _envia_json(self, payload, status=200):
        corpo = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        if self.path == "/registro":
            return self._envia_json({"estados": self.registro_estados})
        # Card #4058: a conversão do corpo pega a lista de rótulos no molde da API.
        if self.path == "/modelo":
            return self._envia_json({"variantes": [], "rotulos_da_conversao": ["Problema"]})
        if self.path.startswith("/itens/"):
            return self._envia_json(self.item_resposta)
        self._envia_json({"erro": "nao encontrado"}, 404)

    def do_POST(self):
        tam = int(self.headers.get("Content-Length", 0))
        dados = json.loads(self.rfile.read(tam) or b"{}")
        type(self).pedidos.append(("POST", self.path, dados))
        if self.path == "/itens":
            return self._envia_json({"id": 200, "titulo": dados.get("titulo", "")}, 201)
        self._envia_json({"erro": "nao encontrado"}, 404)

    def do_PATCH(self):
        tam = int(self.headers.get("Content-Length", 0))
        dados = json.loads(self.rfile.read(tam) or b"{}")
        type(self).pedidos.append(("PATCH", self.path, dados))
        if self.path.startswith("/itens/"):
            return self._envia_json({"id": 100, "titulo": "Item editado", "estado_nome": "Captada"}, 200)
        self._envia_json({"erro": "nao encontrado"}, 404)


@pytest.fixture()
def rastreador_mock():
    _MockRastreador.pedidos = []
    srv = HTTPServer(("127.0.0.1", 0), _MockRastreador)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_dt83_estados_filtra_retirados(rastreador_mock):
    env = dict(os.environ, TAREFAS_BASE=rastreador_mock, PF_CADEIRA="engenharia")
    p = subprocess.run([str(BIN_TAREFAS), "estados"], capture_output=True, text=True, env=env, timeout=30, check=False)
    assert p.returncode == 0, p.stderr
    assert "refinada" not in p.stdout
    assert "captada\tfunil\tCaptada" in p.stdout
    assert "em-execucao\tdelivery\tEm execução" in p.stdout


def test_dt204_sub_com_um_arg_lista_filhas(rastreador_mock):
    env = dict(os.environ, TAREFAS_BASE=rastreador_mock, PF_CADEIRA="engenharia")
    p = subprocess.run([str(BIN_TAREFAS), "sub", "100"], capture_output=True, text=True, env=env, timeout=30, check=False)
    assert p.returncode == 0, p.stderr
    assert "#101\tem-execucao\tengenharia\tFilha 1" in p.stdout
    assert "#102\tcaptada\tarquiteto\tFilha 2" in p.stdout


def test_dt270_criar_e_editar_passam_corpo_ao_jq_sem_arg(rastreador_mock):
    env = dict(os.environ, TAREFAS_BASE=rastreador_mock, PF_CADEIRA="engenharia")
    corpo_longo = "Parágrafo 1 com texto longo.\n\nParágrafo 2 com markdown e crases: `codigo`."

    p1 = subprocess.run(
        [str(BIN_TAREFAS), "criar", "Card Teste", "--desc", corpo_longo],
        capture_output=True, text=True, env=env, timeout=30, check=False
    )
    assert p1.returncode == 0, p1.stderr
    assert "item 200 criado: Card Teste" in p1.stdout

    p2 = subprocess.run(
        [str(BIN_TAREFAS), "editar", "100", "--desc", corpo_longo],
        capture_output=True, text=True, env=env, timeout=30, check=False
    )
    assert p2.returncode == 0, p2.stderr
    assert "item 100 editado:" in p2.stdout


def test_dt252_migrar_aplicar_recusa_sem_stdin():
    env = dict(os.environ, PF_SUJEITO="operador-teste@82b853de")
    p = subprocess.run(
        [str(BIN_MIGRAR), "aplicar", "rag"],
        input="", capture_output=True, text=True, env=env, timeout=30, check=False
    )
    assert p.returncode == 2, p.stdout
    assert "falta o SQL da migracao por STDIN" in p.stderr


def _monta_bancada_com_worktree(tmp_path: Path, repo: str, cadeira: str, pasta: str):
    bancada = tmp_path / "bancada"
    clone = bancada / repo
    clone.mkdir(parents=True)
    subprocess.run(["git", "init", "-b", "main", str(clone)], check=True, capture_output=True, timeout=30)
    subprocess.run(["git", "-C", str(clone), "config", "user.name", "T"], check=True, timeout=30)
    subprocess.run(["git", "-C", str(clone), "config", "user.email", "t@t.org"], check=True, timeout=30)
    (clone / "f").write_text("x")
    subprocess.run(["git", "-C", str(clone), "add", "f"], check=True, timeout=30)
    subprocess.run(["git", "-C", str(clone), "commit", "-m", "i"], check=True, timeout=30)
    wt = bancada / "wt" / repo / cadeira / pasta
    wt.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "-C", str(clone), "worktree", "add", "-b", f"{cadeira}/{pasta}", str(wt)], check=True, capture_output=True, timeout=30)
    return bancada


def test_dt1_bancada_de_com_card_num(tmp_path):
    bancada = _monta_bancada_com_worktree(tmp_path, "platafirma-teste", "engenharia", "3169-guia-operacao")
    env = dict(os.environ, PLATAFIRMA_BANCADA=str(bancada), PF_CADEIRA="engenharia")
    p = subprocess.run(
        [str(BIN_REPO), "estado", "platafirma-teste@3169"],
        capture_output=True, text=True, env=env, timeout=30, check=False
    )
    assert p.returncode == 0, p.stderr
    assert "3169-guia-operacao" in p.stdout

# #2856: leitura compacta e correlação de eventos, sem serviços de produção.
def test_projecao_do_backlog(tmp_path):
    falso = tmp_path / "curl"
    corpo = {"itens": [{"id": 7, "pai": 3, "estado": "captada", "nivel": 2,
                        "estado_fase": "funil", "destinos": ["x" * 60000]}], "total": 1, "estados": []}
    falso.write_text("#!/bin/sh\ncat <<'JSON'\n" + json.dumps(corpo) + "\nJSON\n")
    falso.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + ":" + os.environ["PATH"])
    for ato in ("listar", "listar-tudo"):
        p = subprocess.run([str(BIN_TAREFAS), ato, "--json", "--campos", "id,pai,estado,nivel"],
                           env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        assert json.loads(p.stdout)["itens"] == [{"id": 7, "pai": 3, "estado": "captada", "nivel": 2}]
        assert len(p.stdout) < 500


def test_logs_filtram_antes_da_cauda(tmp_path):
    log = tmp_path / "args"
    docker = tmp_path / "docker"
    docker.write_text("""#!/bin/sh
if [ "$1" = ps ]; then echo alvo; exit 0; fi
printf '%s\\n' "$@" > "$CAPTURA"
printf 'antigo\\nerro recente\\noutro\\n'
""")
    docker.chmod(0o755)
    journal = tmp_path / "journalctl"
    journal.write_text("""#!/bin/sh
printf '%s\\n' "$@" > "$CAPTURA"
printf 'antigo\\nerro recente\\noutro\\n'
""")
    journal.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + ":" + os.environ["PATH"], CAPTURA=str(log))
    for alvo in ("alvo", "unit"):
        p = subprocess.run([str(REPO_ROOT / "bin/infra"), "logs", alvo, "1", "--desde",
                            "2026-11-01", "--until", "2026-11-07", "--grep", "erro"],
                           env=env, capture_output=True, text=True)
        assert p.returncode == 0, p.stderr
        assert p.stdout == "erro recente\n"
        assert "--since\n2026-11-01" in log.read_text()
        assert "--until\n2026-11-07" in log.read_text()
    p = subprocess.run([str(REPO_ROOT / "bin/infra"), "logs", "alvo", "--desconhecido"],
                       env=env, capture_output=True)
    assert p.returncode == 2


def _carrega_debito(nome, caminho):
    import importlib.machinery
    import importlib.util
    loader = importlib.machinery.SourceFileLoader(nome, str(REPO_ROOT / caminho))
    spec = importlib.util.spec_from_loader(nome, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def test_situacao_nao_le_corpo(monkeypatch, capsys):
    import sys
    monkeypatch.syspath_prepend(str(REPO_ROOT / "bin/_acervo"))
    monkeypatch.syspath_prepend(str(REPO_ROOT / "lib"))
    m = _carrega_debito("casa_dt222", "bin/_acervo/casa")
    monkeypatch.setattr(m, "normalizar", lambda *a: None)
    monkeypatch.setattr(m, "_especie", lambda *a: {})
    monkeypatch.setattr(m, "resolver", lambda *a: {"id": "a", "titulo": "Guia"})
    monkeypatch.setattr(m, "_fonte", lambda: {})
    monkeypatch.setattr(m, "_estado_espelho", lambda: {})
    monkeypatch.setattr(m, "_situacao", lambda *a: dict.fromkeys(
        ("fonte", "ingerido", "servido", "vetorizado", "status"), "ok"))
    monkeypatch.setattr(m, "marca_linha", lambda *a: "guia")
    monkeypatch.setattr(m, "ident", lambda *a: "guia")
    monkeypatch.setattr(m, "_q", lambda *a: pytest.fail("leu corpo"))
    assert m.ler("guia", "teste", False, situacao=True) == 0
    assert "servido: ok" in capsys.readouterr().out


def test_fita_integra_exclui_sonda_e_nao_inventa_fecho(monkeypatch):
    monkeypatch.syspath_prepend(str(REPO_ROOT / "lib"))
    m = _carrega_debito("fitas_dt44", "bin/_metrica/fitas.py")
    regs = [
        {"tool": "sessao", "sessao_id": "-", "ordem_id": "sonda"},
        {"tool": "monta_sessao", "sessao_id": "a", "ts": "2026-11-07T10:00:00+00:00"},
        {"tool": "monta_sessao", "sessao_id": "a", "ts": "2026-11-07T10:01:00+00:00"},
        {"tool": "descansar", "evento": "fecho", "sessao_id": "a", "ts": "2026-11-07T10:02:00+00:00"},
        {"tool": "acervo", "ato": "ler", "sessao_id": "b", "cadeira": "ia",
         "documento_especie": "guia", "documento_chave": "desenvolvimento"},
    ]
    r = m.medir(regs)
    assert r["total_fitas"] == 2 and r["fitas_integras"] == 1
    assert r["sondas_excluidas"] == 1
    assert r["fitas"][0]["duracao_s"] == 120
    assert r["fitas"][1]["abriu"] is None and not r["fitas"][1]["integra"]
    assert r["documentos"][0]["leituras"] == 1
