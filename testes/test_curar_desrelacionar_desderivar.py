"""# DT #85 e #137: `curar --desderivar` e `curar --desrelacionar` com plano seco e --apply sem input().

Sem --apply: mostram o plano e saem 0 sem mutação (plano seco).
Com --apply (ou --sim para compatibilidade): executam o DELETE na API sem pergunta interativa.
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
ARESTA_ID = "0000a1fe-0000-4000-8000-000000000001"
OBRA_ID = "0000a1fe-0000-4000-8000-000000000002"
ORIGEM_ID = "0000a1fe-0000-4000-8000-000000000003"


def _acha_python() -> str | None:
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, timeout=10, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()


class _FalsoHandler(BaseHTTPRequestHandler):
    falso: Falso

    def log_message(self, *a):
        pass

    def _resp(self, status: int, obj: dict | None = None):
        self.send_response(status)
        if obj is not None:
            dados = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)
        else:
            self.send_header("content-length", "0")
            self.end_headers()

    def do_GET(self):
        self.falso.chamadas.append(("GET", self.path, None))
        if self.path == f"/acervo/conceitos/relacoes/{ARESTA_ID}":
            return self._resp(200, {
                "id": ARESTA_ID,
                "de": "conceito-a",
                "para": "conceito-b",
                "tipo": "generica",
                "garantia": "formal",
            })
        if self.path == f"/acervo/obras/{OBRA_ID}/derivacoes":
            return self._resp(200, {
                "obra": {"id": OBRA_ID, "titulo": "Obra Derivada"},
                "origens": [{"id": ORIGEM_ID, "titulo": "Obra Origem"}],
                "derivadas": [],
            })
        if self.path == f"/acervo/obras/{OBRA_ID}/situacao":
            return self._resp(200, {"obra_id": OBRA_ID, "titulo": "Obra Derivada"})
        if self.path == f"/acervo/obras/{ORIGEM_ID}/situacao":
            return self._resp(200, {"obra_id": ORIGEM_ID, "titulo": "Obra Origem"})
        return self._resp(404, {"title": "NaoEncontrada", "detail": self.path})

    def do_DELETE(self):
        self.falso.chamadas.append(("DELETE", self.path, None))
        if self.path.startswith(f"/acervo/conceitos/relacoes/{ARESTA_ID}"):
            return self._resp(200, {
                "desfeita": {
                    "id": ARESTA_ID,
                    "de": "conceito-a",
                    "para": "conceito-b",
                    "tipo": "generica",
                    "garantia": "formal",
                }
            })
        if self.path.startswith(f"/acervo/obras/{OBRA_ID}/derivacoes/{ORIGEM_ID}"):
            return self._resp(200, {
                "desfeita": {
                    "obra": {"id": OBRA_ID, "titulo": "Obra Derivada"},
                    "origem": {"id": ORIGEM_ID, "titulo": "Obra Origem"},
                }
            })
        return self._resp(404, {"title": "NaoEncontrada", "detail": self.path})


class Falso:
    def __init__(self):
        self.chamadas = []
        handler_cls = type("Handler", (_FalsoHandler,), {"falso": self})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()

    def rodar(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PY, str(CURAR), *argv],
            capture_output=True,
            text=True,
            env={**os.environ, "MOTOR_ACERVO_URL": self.url, "RAG_API_TOKEN": "tok-curar", "PF_CADEIRA": "dados"},
            stdin=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )

    def escritas(self) -> list[tuple[str, str, dict | None]]:
        return [c for c in self.chamadas if c[0] == "DELETE"]


@pytest.fixture
def servidor_falso():
    f = Falso()
    try:
        yield f
    finally:
        f.fechar()


precisa_requests = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


@precisa_requests
def test_desrelacionar_sem_apply_plano_seco_sem_input(servidor_falso):
    r = servidor_falso.rodar("--desrelacionar", ARESTA_ID)
    assert r.returncode == 0, r.stderr
    assert f"Plano: desfazer a aresta {ARESTA_ID}" in r.stdout
    assert "conceito-a -generica-> conceito-b" in r.stdout
    assert "plano seco — repita com --apply para gravar" in r.stdout
    assert servidor_falso.escritas() == []


@precisa_requests
def test_desrelacionar_com_apply_executa_sem_input(servidor_falso):
    r = servidor_falso.rodar("--desrelacionar", ARESTA_ID, "--apply")
    assert r.returncode == 0, r.stderr
    assert f"Aresta desfeita: conceito-a -generica-> conceito-b [formal] ({ARESTA_ID})" in r.stdout
    assert len(servidor_falso.escritas()) == 1


@precisa_requests
def test_desrelacionar_com_sim_executa_sem_input(servidor_falso):
    r = servidor_falso.rodar("--desrelacionar", ARESTA_ID, "--sim")
    assert r.returncode == 0, r.stderr
    assert f"Aresta desfeita: conceito-a -generica-> conceito-b [formal] ({ARESTA_ID})" in r.stdout
    assert len(servidor_falso.escritas()) == 1


@precisa_requests
def test_desrelacionar_json(servidor_falso):
    r = servidor_falso.rodar("--desrelacionar", ARESTA_ID, "--json")
    assert r.returncode == 0, r.stderr
    data = json.loads(r.stdout)
    assert data.get("modo") == "plano"
    assert data.get("ato") == "desrelacionar"


@precisa_requests
def test_desderivar_sem_apply_plano_seco_sem_input(servidor_falso):
    r = servidor_falso.rodar("--desderivar", OBRA_ID, "--de", ORIGEM_ID)
    assert r.returncode == 0, r.stderr
    assert "Plano: desfazer a derivação Obra Derivada" in r.stdout
    assert "plano seco — repita com --apply para gravar" in r.stdout
    assert servidor_falso.escritas() == []


@precisa_requests
def test_desderivar_com_apply_executa_sem_input(servidor_falso):
    r = servidor_falso.rodar("--desderivar", OBRA_ID, "--de", ORIGEM_ID, "--apply")
    assert r.returncode == 0, r.stderr
    assert "Derivação desfeita: Obra Derivada <- Obra Origem" in r.stdout
    assert len(servidor_falso.escritas()) == 1


@precisa_requests
def test_desderivar_com_sim_executa_sem_input(servidor_falso):
    r = servidor_falso.rodar("--desderivar", OBRA_ID, "--de", ORIGEM_ID, "--sim")
    assert r.returncode == 0, r.stderr
    assert "Derivação desfeita: Obra Derivada <- Obra Origem" in r.stdout
    assert len(servidor_falso.escritas()) == 1
