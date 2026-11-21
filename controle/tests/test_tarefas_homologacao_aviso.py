# componente: componente:verbo-tarefas
"""Teste do DT-35: aviso de feature em homologação não repete o envio (transição única, re-movimento terminal e pai já em homologação)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "bin" / "tarefas"

if not shutil.which("jq") or not shutil.which("bash"):
    pytest.skip("tarefas precisa de bash e jq reais", allow_module_level=True)


class _Estado:
    def __init__(self) -> None:
        self.itens = {
            3114: {
                "id": 3114,
                "chave": "3114",
                "nivel": 1,
                "nivel_nome": "feature",
                "titulo": "Feature 3114",
                "estado": "priorizada",
                "estado_nome": "Em execução",
                "estado_fase": "execucao",
                "estado_natureza": "aberta",
                "estado_derivado": "em-execucao",
                "cadeira": "gestao-estrategica",
                "pai": None,
                "filhas": [],
            },
            3115: {
                "id": 3115,
                "chave": "3115",
                "nivel": 2,
                "nivel_nome": "story",
                "titulo": "Story 3115",
                "estado": "em-execucao",
                "estado_nome": "Em execução",
                "estado_fase": "execucao",
                "estado_natureza": "aberta",
                "estado_derivado": None,
                "cadeira": "engenharia",
                "pai": 3114,
                "filhas": [],
            },
            3116: {
                "id": 3116,
                "chave": "3116",
                "nivel": 2,
                "nivel_nome": "story",
                "titulo": "Story 3116",
                "estado": "em-execucao",
                "estado_nome": "Em execução",
                "estado_fase": "execucao",
                "estado_natureza": "aberta",
                "estado_derivado": None,
                "cadeira": "engenharia",
                "pai": 3114,
                "filhas": [],
            },
        }


def _faz_handler(estado: _Estado):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _json(self, obj, code: int = 200):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            p = urlparse(self.path).path
            if p == "/registro":
                return self._json({
                    "estados": [
                        {"estado": "em-execucao", "fase": "execucao", "natureza": "aberta"},
                        {"estado": "entregue", "fase": "terminal", "natureza": "terminal"},
                        {"estado": "englobada", "fase": "terminal", "natureza": "terminal"},
                    ]
                })
            if p.startswith("/itens/"):
                iid = int(p.split("/")[2])
                if iid in estado.itens:
                    return self._json(estado.itens[iid])
            return self._json({"erro": "nao encontrado"}, 404)

        def do_PATCH(self):
            n = int(self.headers.get("Content-Length", 0))
            corpo = json.loads(self.rfile.read(n).decode("utf-8") or "{}")
            p = urlparse(self.path).path
            iid = int(p.split("/")[2])
            item = estado.itens[iid]
            if corpo.get("estado") in ("entregue", "englobada"):
                item["estado"] = corpo["estado"]
                item["estado_nome"] = corpo["estado"]
                item["estado_fase"] = "terminal"
                item["estado_natureza"] = "terminal"
                estado.itens[3114]["estado_derivado"] = "em-homologacao"
            return self._json(item)

    return Handler


def _run_mover(base_url: str, fila_bin: Path, item_id: int, destino: str):
    env = {
        **os.environ,
        "TAREFAS_BASE": base_url,
        "PF_CADEIRA": "engenharia",
        "PF_FILA_BIN": str(fila_bin),
    }
    return subprocess.run(
        ["bash", str(SCRIPT), "mover", str(item_id), destino],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def test_dt35_aviso_homologacao_nao_repete(tmp_path: Path):
    estado = _Estado()
    srv = HTTPServer(("127.0.0.1", 0), _faz_handler(estado))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base_url = f"http://127.0.0.1:{srv.server_port}"

    envios_log = tmp_path / "fila_envios.log"
    fila_fake = tmp_path / "fila"
    fila_fake.write_text(
        f'#!/usr/bin/env bash\nprintf "%s\\n" "$*" >> "{envios_log}"\necho "20261115T160000-engenharia-1"\n',
        encoding="utf-8",
    )
    fila_fake.chmod(0o755)

    try:
        # 1) Transição real: 3115 fecha e 3114 entra em em-homologacao -> envia 1 vez.
        r1 = _run_mover(base_url, fila_fake, 3115, "entregue")
        assert r1.returncode == 0, r1.stderr
        assert "aviso de conferência enviado: gestao-estrategica" in r1.stdout
        assert len(envios_log.read_text(encoding="utf-8").splitlines()) == 1

        # 2) Re-mover filha já terminal (3115 -> englobada) -> não reenvia.
        r2 = _run_mover(base_url, fila_fake, 3115, "englobada")
        assert r2.returncode == 0, r2.stderr
        assert "aviso de conferência enviado" not in r2.stdout
        assert len(envios_log.read_text(encoding="utf-8").splitlines()) == 1

        # 3) Mover outra filha (3116 -> entregue) quando pai já estava em em-homologacao -> não reenvia.
        r3 = _run_mover(base_url, fila_fake, 3116, "entregue")
        assert r3.returncode == 0, r3.stderr
        assert "aviso de conferência enviado" not in r3.stdout
        assert len(envios_log.read_text(encoding="utf-8").splitlines()) == 1
    finally:
        srv.shutdown()
