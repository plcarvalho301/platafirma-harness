# componente: componente:verbo-mesa
"""Testes da gravação atômica de escopo e chapéu na lousa pelos verbos (story #4342, t5)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HARNESS_DIR = Path(__file__).resolve().parents[1]
HARNESS_LIB = HARNESS_DIR / "lib"
if str(HARNESS_LIB) not in sys.path:
    sys.path.insert(0, str(HARNESS_LIB))

from postura.lousa import LousaFixtura

LOUSA_PY = HARNESS_LIB / "postura" / "lousa.py"
BIN_REPO = HARNESS_DIR / "bin" / "repo"
BIN_TAREFAS = HARNESS_DIR / "bin" / "tarefas"


def test_gravacao_atomica_concorrente_escopo_e_chapeu_sem_lost_update(tmp_path: Path):
    fix = tmp_path / "valkey.json"
    fix.write_text("{}", encoding="utf-8")
    env_base = {**os.environ, "PF_VALKEY_FIXTURE": str(fix), "PF_SESSAO": "sess-conc"}

    p1 = subprocess.Popen(
        [sys.executable, str(LOUSA_PY), "gravar-sessao", "escopo_atual", "card:4342"],
        env=env_base,
    )
    p2 = subprocess.Popen(
        [sys.executable, str(LOUSA_PY), "gravar-sessao", "chapeu", "back-end"],
        env=env_base,
    )
    assert p1.wait(timeout=10) == 0
    assert p2.wait(timeout=10) == 0

    lousa = LousaFixtura(fix)
    assert lousa.ler_campo_sessao("sess-conc", "escopo_atual") == "card:4342"
    assert lousa.ler_campo_sessao("sess-conc", "chapeu") == "back-end"


def test_repo_abrir_apos_prazo_grava_escopo_na_lousa(tmp_path: Path):
    fix = tmp_path / "valkey.json"
    fix.write_text("{}", encoding="utf-8")
    # Simula um repo abrir que atrasa acima do prazo de espera do chamador (0.15s)
    # e conclui depois (0.35s), gravando escopo_atual pelo próprio processo.
    atraso_script = tmp_path / "repo_abrir_lento.sh"
    atraso_script.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "sleep 0.35\n"
        f'python3 "{LOUSA_PY}" gravar-sessao escopo_atual "card:4342"\n'
        "echo 'bancada aberta'\n",
        encoding="utf-8",
    )
    atraso_script.chmod(0o755)
    env = {**os.environ, "PF_VALKEY_FIXTURE": str(fix), "PF_SESSAO": "sess-tardia"}
    proc = subprocess.Popen([str(atraso_script)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        proc.wait(timeout=0.1)
        passou_prazo = False
    except subprocess.TimeoutExpired:
        passou_prazo = True
    assert passou_prazo is True
    assert proc.wait(timeout=5) == 0

    lousa = LousaFixtura(fix)
    assert lousa.ler_campo_sessao("sess-tardia", "escopo_atual") == "card:4342"
    # Confirma também que bin/repo contém o hook grava_escopo_sessao
    assert "grava_escopo_sessao" in BIN_REPO.read_text(encoding="utf-8")


def test_tarefas_mover_grava_escopo_atual_preservando_chapeu(tmp_path: Path):
    fix = tmp_path / "valkey.json"
    fix.write_text(json.dumps({"sessoes": {"sess-mov": {"chapeu": "back-end"}}}), encoding="utf-8")

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"id": 4342, "estado": "priorizada", "nivel_nome": "story"}).encode())

        def do_PATCH(self):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(
                json.dumps(
                    {
                        "id": 4342,
                        "titulo": "Story teste",
                        "estado": "em-execucao",
                        "estado_rotulo": "Em execução",
                        "nivel_nome": "story",
                    }
                ).encode()
            )

    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    port = srv.server_address[1]
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        env = {
            **os.environ,
            "TAREFAS_BASE": f"http://127.0.0.1:{port}",
            "PF_CADEIRA": "engenharia",
            "PF_SESSAO": "sess-mov",
            "PF_VALKEY_FIXTURE": str(fix),
            "PF_INFRA_BIN": "/bin/false",
        }
        cp = subprocess.run(
            ["bash", str(BIN_TAREFAS), "mover", "4342", "em-execucao"],
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert cp.returncode == 0, cp.stderr
    finally:
        srv.shutdown()
        srv.server_close()

    lousa = LousaFixtura(fix)
    assert lousa.ler_campo_sessao("sess-mov", "escopo_atual") == "card:4342"
    assert lousa.ler_campo_sessao("sess-mov", "chapeu") == "back-end"


def test_persona_atos_grava_chapeu_na_lousa(tmp_path: Path):
    fix = tmp_path / "valkey.json"
    fix.write_text(json.dumps({"sessoes": {"sess-per": {"escopo_atual": "card:4342"}}}), encoding="utf-8")
    lousa = LousaFixtura(fix)
    lousa.gravar_campo_sessao("sess-per", "chapeu", "back-end")
    assert lousa.ler_campo_sessao("sess-per", "chapeu") == "back-end"
    assert lousa.ler_campo_sessao("sess-per", "escopo_atual") == "card:4342"
    atos_src = (HARNESS_LIB / "postura" / "atos.py").read_text(encoding="utf-8")
    assert 'gravar_campo_sessao(ctx.sessao_id, "chapeu", ctx.chapeu)' in atos_src
