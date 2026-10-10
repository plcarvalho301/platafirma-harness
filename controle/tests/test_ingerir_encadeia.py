"""`ingerir --ate vetor --apply` vai até o ar: cataloga, espelha, indexa e promove obra a obra.

Servidor do acervo falso (HTTP em thread) e verbos `acervo` e `motor` falsos (PF_BIN_ACERVO,
PF_BIN_MOTOR): a obra A passa em tudo; a obra B tem espelho não servível e para em Transcrever,
com o portão dito, sem derrubar a A."""
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BIN_INGERIR = os.path.join(REPO, "bin", "ingerir")

OBRA_A = "aaaaaaaa-0000-4000-8000-000000000001"
OBRA_B = "bbbbbbbb-0000-4000-8000-000000000002"
LOTE_MOTOR = "cccccccc-0000-4000-8000-000000000003"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (ingerir precisa)")


def _executavel(caminho, conteudo):
    caminho.write_text(conteudo)
    caminho.chmod(caminho.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


class _Acervo(BaseHTTPRequestHandler):
    pedidos = []

    def _json(self, codigo, corpo):
        dado = json.dumps(corpo).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(dado)))
        self.end_headers()
        self.wfile.write(dado)

    def _le(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def do_PUT(self):
        self._le()
        self._json(201, {})

    def do_POST(self):
        corpo = self._le()
        if self.path == "/acervo/lotes":
            _Acervo.pedidos.append(json.loads(corpo))
            self._json(201, {"id": "L1", "itens": [], "resumo": {}})
        else:
            self._json(202, {})

    def do_GET(self):
        self._json(200, {"id": "L1", "estado": "concluido", "resumo": {"feito": 2}, "itens": [
            {"posicao": 0, "obra_id": OBRA_A, "estado": "feito", "veredito": "criar", "titulo": "Obra A"},
            {"posicao": 1, "obra_id": OBRA_B, "estado": "feito", "veredito": "criar", "titulo": "Obra B"},
        ]})

    def log_message(self, *a):
        pass


@pytest.fixture
def servidor():
    _Acervo.pedidos = []
    srv = HTTPServer(("127.0.0.1", 0), _Acervo)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


def _ambiente(tmp_path, base):
    py = tmp_path / "py"
    py.mkdir()
    _executavel(py / "python3", f'#!/bin/sh\nexec {shlex.quote(PY)} "$@"\n')
    falsos = tmp_path / "falsos"
    falsos.mkdir()
    _executavel(falsos / "acervo", f"""#!/usr/bin/env bash
case "$4" in
  {OBRA_A}) echo "  novo      : combinado@1 · digest x · servível"
            echo "  impressão : dddddddd-0000-4000-8000-00000000000a selada" ;;
  {OBRA_B}) echo "  novo      : combinado@1 · digest y · não servível (sem medida)"
            echo "  impressão : dddddddd-0000-4000-8000-00000000000b selada" ;;
esac
""")
    _executavel(falsos / "motor", f"""#!/usr/bin/env bash
echo "$*" >> "{tmp_path}/motor.log"
if [[ " $* " == *" --relatorio "* ]]; then
  echo '{{"estado": "concluido", "itens": [{{"obra_id": "{OBRA_A}", "estado": "promovida", "gate": {{"aprovado": true}}}}]}}'
else
  echo '{{"lote": "{LOTE_MOTOR}", "modo": "aplicado"}}'
fi
""")
    home = tmp_path / "home"
    home.mkdir()
    return dict(os.environ, HOME=str(home), RAG_API_BASE=base, RAG_API_TOKEN="t",
                PF_BIN_ACERVO=str(falsos / "acervo"), PF_BIN_MOTOR=str(falsos / "motor"),
                PF_INGERIR_PASSO="0", PATH=f"{py}:{os.environ.get('PATH', '')}")


def _pasta(tmp_path):
    pasta = tmp_path / "lote"
    pasta.mkdir()
    (pasta / "a.md").write_text("# Obra A\n")
    (pasta / "b.md").write_text("# Obra B\n")
    return pasta


def test_ate_vetor_vai_ao_ar_e_para_a_obra_barrada_com_o_portao(tmp_path, servidor):
    env = _ambiente(tmp_path, servidor)
    r = subprocess.run([BIN_INGERIR, "--lote", str(_pasta(tmp_path)), "--ate", "vetor", "--apply"],
                       env=env, capture_output=True, text=True, check=False)
    assert _Acervo.pedidos[0]["ate"] == "catalogar"
    assert "Estágios depois de Incorporar: 1 de 2 no ar" in r.stdout
    linha_a = next(l for l in r.stdout.splitlines() if OBRA_A in l)
    linha_b = next(l for l in r.stdout.splitlines() if OBRA_B in l)
    assert linha_a.rstrip().endswith("no ar")
    assert "não servível (sem medida)" in linha_b
    motor = (tmp_path / "motor.log").read_text()
    assert f"--obra {OBRA_A} --promover" in motor and OBRA_B not in motor
    assert r.returncode == 1


def test_ate_chunk_para_na_selada_sem_chamar_o_motor(tmp_path, servidor):
    env = _ambiente(tmp_path, servidor)
    r = subprocess.run([BIN_INGERIR, "--lote", str(_pasta(tmp_path)), "--ate", "chunk", "--apply"],
                       env=env, capture_output=True, text=True, check=False)
    assert "1 de 2 selada" in r.stdout
    assert not (tmp_path / "motor.log").exists()


def test_sem_ate_nao_encadeia(tmp_path, servidor):
    env = _ambiente(tmp_path, servidor)
    r = subprocess.run([BIN_INGERIR, "--lote", str(_pasta(tmp_path)), "--apply"],
                       env=env, capture_output=True, text=True, check=False)
    assert r.returncode == 0
    assert "Estágios depois de Incorporar" not in r.stdout
    assert not (tmp_path / "motor.log").exists()
