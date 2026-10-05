"""#3238: `curar --expurgar <obra> [--apply]` e `curar --restaurar <obra> [--apply]` com plano seco.
#3301: os dois exigem `--motivo`; sem ele saem 2, no plano e no --apply, sem falar com o servidor.

Sem --apply: mostram o plano (o que muda na obra e no export) e saem 0 sem gravar nada.
Com --apply: executam DELETE/PATCH e regeneram o export.
Sem pergunta interativa no terminal (input() removido).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CURAR = RAIZ / "bin" / "curar"
VIVA = "0000a1fe-0000-4000-8000-000000000000"
EXPURGADA = "0000f055-0000-4000-8000-000000000000"
MOTIVO = "substituída pela versão em Markdown"


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
        if self.path == f"/acervo/obras/{VIVA}":
            return self._resp(200, {
                "id": VIVA,
                "titulo": "Obra Viva",
                "expurgada_em": None,
                "dominio": "geral",
            })
        if self.path == f"/acervo/obras/{EXPURGADA}":
            return self._resp(200, {
                "id": EXPURGADA,
                "titulo": "Obra Expurgada",
                "expurgada_em": "2026-10-01T12:00:00Z",
                "dominio": "geral",
            })
        return self._resp(404, {"title": "NaoEncontrada", "detail": self.path})

    def do_DELETE(self):
        self.falso.chamadas.append(("DELETE", self.path, None))
        if self.path.startswith(f"/acervo/obras/{VIVA}") or self.path.startswith(f"/acervo/obras/{EXPURGADA}"):
            return self._resp(204)
        return self._resp(404, {"title": "NaoEncontrada", "detail": self.path})

    def do_PATCH(self):
        n = int(self.headers.get("content-length") or 0)
        corpo = json.loads(self.rfile.read(n) or b"{}")
        self.falso.chamadas.append(("PATCH", self.path, corpo))
        if self.path in (f"/acervo/obras/{EXPURGADA}", f"/acervo/obras/{VIVA}"):
            oid = EXPURGADA if EXPURGADA in self.path else VIVA
            tit = "Obra Expurgada" if oid == EXPURGADA else "Obra Viva"
            return self._resp(200, {
                "id": oid,
                "titulo": tit,
                "expurgada": False,
                "expurgada_em": None,
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


@pytest.fixture
def servidor_falso():
    f = Falso()
    try:
        yield f
    finally:
        f.fechar()


precisa_requests = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


@precisa_requests
def test_expurgar_sem_apply_e_plano_seco_sem_prompt(servidor_falso):
    r = servidor_falso.rodar("--expurgar", VIVA, "--motivo", MOTIVO)
    assert r.returncode == 0, r.stderr
    assert "Plano: expurgar a obra" in r.stdout
    assert f"motivo   : {MOTIVO}" in r.stdout
    assert "expurgada_em: None -> now()" in r.stdout
    assert "sai de ontologia/acervo/obra.jsonl" in r.stdout
    assert "plano seco — repita com --apply para gravar" in r.stdout

    metodos = [metodo for metodo, _, _ in servidor_falso.chamadas]
    assert "DELETE" not in metodos
    assert ("GET", f"/acervo/obras/{VIVA}", None) in servidor_falso.chamadas


@precisa_requests
def test_expurgar_com_apply_executa_e_relata(servidor_falso):
    r = servidor_falso.rodar("--expurgar", VIVA, "--motivo", MOTIVO, "--apply")
    assert r.returncode == 0, r.stderr
    assert f"Obra {VIVA} expurgada com sucesso" in r.stdout

    deletes = [(m, p) for m, p, _ in servidor_falso.chamadas if m == "DELETE"]
    assert len(deletes) == 1
    assert deletes[0][1].startswith(f"/acervo/obras/{VIVA}?autor=")
    assert f"motivo={urllib.parse.quote(MOTIVO)}" in deletes[0][1]


@precisa_requests
def test_restaurar_sem_apply_e_plano_seco(servidor_falso):
    r = servidor_falso.rodar("--restaurar", EXPURGADA, "--motivo", MOTIVO)
    assert r.returncode == 0, r.stderr
    assert "Plano: restaurar a obra" in r.stdout
    assert f"motivo   : {MOTIVO}" in r.stdout
    assert "2026-10-01T12:00:00Z -> None" in r.stdout
    assert "entra em ontologia/acervo/obra.jsonl" in r.stdout
    assert "plano seco — repita com --apply para gravar" in r.stdout

    metodos = [metodo for metodo, _, _ in servidor_falso.chamadas]
    assert "PATCH" not in metodos
    assert ("GET", f"/acervo/obras/{EXPURGADA}", None) in servidor_falso.chamadas


@precisa_requests
def test_restaurar_com_apply_executa_e_relata(servidor_falso):
    r = servidor_falso.rodar("--restaurar", EXPURGADA, "--motivo", MOTIVO, "--apply")
    assert r.returncode == 0, r.stderr
    assert f"Obra {EXPURGADA} restaurada com sucesso" in r.stdout

    patches = [(m, p, c) for m, p, c in servidor_falso.chamadas if m == "PATCH"]
    assert len(patches) == 1
    assert patches[0][1] == f"/acervo/obras/{EXPURGADA}"
    assert patches[0][2] == {"autor": "dados", "expurgada": False, "motivo": MOTIVO}


@precisa_requests
def test_expurgar_restaurar_json_modo(servidor_falso):
    r_exp_plano = servidor_falso.rodar("--expurgar", VIVA, "--motivo", MOTIVO, "--json")
    assert r_exp_plano.returncode == 0
    d_exp_plano = json.loads(r_exp_plano.stdout)
    assert d_exp_plano["modo"] == "plano"
    assert d_exp_plano["ato"] == "expurgar"
    assert d_exp_plano["motivo"] == MOTIVO
    assert d_exp_plano["antes"]["expurgada"] is False
    assert d_exp_plano["depois"]["expurgada"] is True

    r_res_plano = servidor_falso.rodar("--restaurar", EXPURGADA, "--motivo", MOTIVO, "--json")
    assert r_res_plano.returncode == 0
    d_res_plano = json.loads(r_res_plano.stdout)
    assert d_res_plano["modo"] == "plano"
    assert d_res_plano["ato"] == "restaurar"
    assert d_res_plano["motivo"] == MOTIVO
    assert d_res_plano["antes"]["expurgada"] is True
    assert d_res_plano["depois"]["expurgada"] is False

    r_exp_app = servidor_falso.rodar("--expurgar", VIVA, "--motivo", MOTIVO, "--apply", "--json")
    assert r_exp_app.returncode == 0
    d_exp_app = json.loads(r_exp_app.stdout)
    assert d_exp_app["modo"] == "aplicado"
    assert d_exp_app["expurgada"] is True
    assert d_exp_app["motivo"] == MOTIVO

    r_res_app = servidor_falso.rodar("--restaurar", EXPURGADA, "--motivo", MOTIVO, "--apply", "--json")
    assert r_res_app.returncode == 0
    d_res_app = json.loads(r_res_app.stdout)
    assert d_res_app["modo"] == "aplicado"
    assert d_res_app["expurgada"] is False


@precisa_requests
def test_idempotencia_plano_obra_ja_expurgada(servidor_falso):
    r = servidor_falso.rodar("--expurgar", EXPURGADA, "--motivo", MOTIVO)
    assert r.returncode == 0
    assert "já estava expurgada" in r.stdout
    assert "já ausente" in r.stdout


@precisa_requests
def test_idempotencia_plano_obra_ja_ativa(servidor_falso):
    r = servidor_falso.rodar("--restaurar", VIVA, "--motivo", MOTIVO)
    assert r.returncode == 0
    assert "já estava ativa" in r.stdout
    assert "já presente" in r.stdout


@precisa_requests
@pytest.mark.parametrize("ato,obra", [("--expurgar", VIVA), ("--restaurar", EXPURGADA)])
@pytest.mark.parametrize("extra", [[], ["--apply"], ["--json"]])
def test_sem_motivo_sai_2_com_a_cura_e_nao_toca_o_servidor(servidor_falso, ato, obra, extra):
    r = servidor_falso.rodar(ato, obra, *extra)
    assert r.returncode == 2, r.stdout + r.stderr
    assert f"{ato} exige --motivo" in r.stderr
    assert "cura: repita com --motivo" in r.stderr
    assert servidor_falso.chamadas == []


@precisa_requests
@pytest.mark.parametrize("motivo", ["", "   "])
def test_motivo_em_branco_vale_como_sem_motivo(servidor_falso, motivo):
    r = servidor_falso.rodar("--expurgar", VIVA, "--motivo", motivo, "--apply")
    assert r.returncode == 2
    assert servidor_falso.chamadas == []
