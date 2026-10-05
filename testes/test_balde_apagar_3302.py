"""#3302: `balde apagar <sha256> --colecao <c> [--motivo <m>] [--apply]` — plano por padrão, que nomeia as
obras retiradas que perdem o apontamento; `--apply` apaga do balde e deixa a obra sem apontamento.

O servidor é falso: o que o teste prova é o corpo que o cliente manda e o que ele diz ao dono.
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
BALDE = RAIZ / "bin" / "_acervo" / "balde"
SHA = "a" * 64
OBRA = "0000f055-0000-4000-8000-000000000000"
MOTIVO = "coleção esvaziada por ordem do dono"


def _acha_python() -> str | None:
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, timeout=10, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
precisa_requests = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (balde precisa)")


def _plano(**kw):
    base = {"modo": "plano", "objeto": f"acervo/{SHA}", "no_balde": True,
            "obras_que_perdem_o_apontamento": [
                {"obra_id": OBRA, "titulo": "Obra Retirada", "retirada_motivo": MOTIVO}],
            "obras_sem_motivo": []}
    base.update(kw)
    return base


class _Handler(BaseHTTPRequestHandler):
    falso: Falso

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        corpo = json.loads(self.rfile.read(n) or b"{}")
        self.falso.chamadas.append((self.path, corpo))
        status, obj = self.falso.resposta(corpo)
        dados = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)


class Falso:
    def __init__(self, resposta=None):
        self.chamadas: list[tuple[str, dict]] = []
        self.resposta = resposta or (lambda corpo: (
            200, _plano() if not corpo["aplicar"] else {**_plano(), "modo": "aplicado", "apagado": f"acervo/{SHA}"}))
        cls = type("H", (_Handler,), {"falso": self})
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), cls)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def fechar(self):
        self.srv.shutdown()
        self.srv.server_close()

    def rodar(self, *argv: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [PY, str(BALDE), *argv], capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=30,
            check=False, env={**os.environ, "MOTOR_ACERVO_URL": self.url, "RAG_API_TOKEN": "tok",
                              "PF_CADEIRA": "dados"})


@pytest.fixture
def falso():
    f = Falso()
    try:
        yield f
    finally:
        f.fechar()


@precisa_requests
def test_sem_apply_e_plano_que_nomeia_a_obra_e_nao_aplica(falso):
    r = falso.rodar("apagar", SHA, "--colecao", "firma")
    assert r.returncode == 0, r.stderr
    assert falso.chamadas == [(f"/acervo/objetos/{SHA}/apagar",
                               {"autor": "dados", "colecao": "firma", "aplicar": False})]
    assert f"Plano: apagar acervo/{SHA} do balde, SEM VOLTA" in r.stdout
    assert f"obra   : {OBRA} «Obra Retirada» perde o apontamento — motivo da retirada: {MOTIVO}" in r.stdout
    assert "plano seco — repita com --apply para apagar" in r.stdout


@precisa_requests
def test_apply_aplica_e_diz_que_a_obra_ficou_sem_apontamento(falso):
    r = falso.rodar("apagar", SHA, "--colecao", "firma", "--apply")
    assert r.returncode == 0, r.stderr
    assert falso.chamadas[0][1]["aplicar"] is True
    assert f"Objeto acervo/{SHA} apagado do balde." in r.stdout
    assert f"obra {OBRA} «Obra Retirada» ficou sem apontamento (objeto nulo)" in r.stdout


@precisa_requests
def test_sim_antigo_vale_como_apply_com_aviso(falso):
    r = falso.rodar("apagar", SHA, "--colecao", "firma", "--sim")
    assert r.returncode == 0, r.stderr
    assert falso.chamadas[0][1]["aplicar"] is True
    assert "--sim e a forma antiga de --apply" in r.stderr


@precisa_requests
def test_motivo_vai_no_corpo_e_so_quando_dado(falso):
    falso.rodar("apagar", SHA, "--colecao", "firma", "--apply", "--motivo", f"  {MOTIVO}  ")
    falso.rodar("apagar", SHA, "--colecao", "firma", "--apply", "--motivo", "   ")
    assert falso.chamadas[0][1]["motivo"] == MOTIVO
    assert "motivo" not in falso.chamadas[1][1]


def test_obra_retirada_sem_motivo_o_plano_pede_o_motivo():
    if PY is None:
        pytest.skip("nenhum python com `requests`")
    f = Falso(lambda corpo: (200, _plano(
        obras_que_perdem_o_apontamento=[{"obra_id": OBRA, "titulo": "Obra Retirada", "retirada_motivo": None}],
        obras_sem_motivo=[OBRA])))
    try:
        r = f.rodar("apagar", SHA, "--colecao", "firma")
        assert r.returncode == 0, r.stderr
        assert "SEM MOTIVO: o plano pede --motivo" in r.stdout
        assert "falta  : --motivo" in r.stdout
        r2 = f.rodar("apagar", SHA, "--colecao", "firma", "--motivo", MOTIVO)
        assert "falta  :" not in r2.stdout
    finally:
        f.fechar()


def test_obra_viva_que_referencia_o_arquivo_sai_1_com_a_causa():
    if PY is None:
        pytest.skip("nenhum python com `requests`")
    f = Falso(lambda corpo: (409, {"title": "ObjetoEmUso", "detail": "referenciado por 1 obra(s) (viva-1)"}))
    try:
        r = f.rodar("apagar", SHA, "--colecao", "firma", "--apply")
        assert r.returncode == 1
        assert "ObjetoEmUso" in r.stdout + r.stderr
    finally:
        f.fechar()


@precisa_requests
def test_arquivo_que_ja_nao_esta_no_balde_so_tira_o_apontamento():
    f = Falso(lambda corpo: (200, {**_plano(no_balde=False), "modo": "aplicado", "apagado": None}
                             if corpo["aplicar"] else _plano(no_balde=False)))
    try:
        assert "o arquivo já não está no balde" in f.rodar("apagar", SHA, "--colecao", "firma").stdout
        r = f.rodar("apagar", SHA, "--colecao", "firma", "--apply")
        assert "já não estava no balde; só o apontamento saiu" in r.stdout
    finally:
        f.fechar()


@precisa_requests
def test_colecao_e_obrigatoria_e_validada(falso):
    assert falso.rodar("apagar", SHA).returncode == 2
    assert falso.rodar("apagar", SHA, "--colecao", "outra").returncode == 2
    assert falso.chamadas == []
