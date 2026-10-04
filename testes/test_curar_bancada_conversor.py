"""#3276: `curar --reextrair <arquivo> --bancada <pasta>` com ARQUIVO local vai direto ao serviço do
conversor (POST /conversoes, spec conversor-pdf-combinado §3.3), sem a rag-api e sem credencial.

Servidor falso do serviço em thread (loopback, porta livre), apontado por PF_CONVERSOR_URL. A rag-api
(MOTOR_ACERVO_URL) aponta para uma porta morta: se o verbo a procurasse, a obra sairia `erro`.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CURAR = RAIZ / "bin" / "curar"


def _acha_python():
    for cand in dict.fromkeys([sys.executable, shutil.which("python3"), "/usr/bin/python3"]):
        if cand and os.path.exists(cand) and subprocess.run(
                [cand, "-c", "import requests"], capture_output=True, check=False).returncode == 0:
            return cand
    return None


PY = _acha_python()
pytestmark = pytest.mark.skipif(PY is None, reason="nenhum python com `requests` (curar precisa)")


def _resposta(corpo_pdf: bytes, metodo: str, status: int = 200, **over):
    md = f"# espelho\n\n{len(corpo_pdf)} bytes recebidos\n"
    indice = json.dumps({"secoes": []}) + "\n"
    rel = {"versao_relatorio": 2, "metodo": metodo, "aplicavel": True, "classe": "B",
           "reprovado": False, "erro": None, "erro_tipo": None, "paginas": 3, "prazo_s": 150,
           "cabecalho": {"blocos": 7}, "fidelidade": {"perda": {"paragrafo": 1}, "erro": None},
           "tempos_ms": {"total": 900},
           "sha256_md": hashlib.sha256(md.encode()).hexdigest(), "bytes_md": len(md.encode()),
           "sha256_indice": hashlib.sha256(indice.encode()).hexdigest(), "bytes_indice": len(indice.encode())}
    rel.update(over)
    arquivos = {"espelho.md": md, "indice.json": indice} if status == 200 else None
    return status, {"relatorio": rel, "arquivos": arquivos}


class Servico:
    def __init__(self, ocupado_vezes: int = 0, status: int = 200, **over):
        self.chamadas = []
        self.ocupado = ocupado_vezes
        servico = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                dados = self.rfile.read(n)
                u = urlparse(self.path)
                servico.chamadas.append({"caminho": u.path, "params": parse_qs(u.query), "bytes": dados,
                                         "cab": {k.lower(): v for k, v in self.headers.items()}})
                if u.path != "/conversoes":
                    return self._resp(404, {"title": "RotaInexistente"})
                if servico.ocupado > 0:
                    servico.ocupado -= 1
                    self.send_response(409)
                    self.send_header("Retry-After", "0")
                    self.send_header("content-length", "2")
                    self.end_headers()
                    self.wfile.write(b"{}")
                    return
                st, obj = _resposta(dados, parse_qs(u.query)["metodo"][0], status, **over)
                self._resp(st, obj)

            def _resp(self, status, obj):
                b = json.dumps(obj).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(b)))
                self.end_headers()
                self.wfile.write(b)

        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()

    def parar(self):
        self.srv.shutdown()
        self.srv.server_close()


def _curar(url, *args):
    env = {k: v for k, v in os.environ.items() if k != "RAG_API_TOKEN"}
    env.update({"PF_CONVERSOR_URL": url, "MOTOR_ACERVO_URL": "http://127.0.0.1:9", "PYTHONDONTWRITEBYTECODE": "1"})
    return subprocess.run([PY, str(CURAR), *args], capture_output=True, text=True, env=env, timeout=60, check=False)


@pytest.fixture
def pdf(tmp_path):
    p = tmp_path / "DMBOK v2.pdf"
    p.write_bytes(b"%PDF-1.7 corpo de teste")
    return p


def test_arquivo_local_vai_direto_ao_servico_sem_credencial(tmp_path, pdf):
    s = Servico()
    try:
        r = _curar(s.url, "--reextrair", str(pdf), "--bancada", str(tmp_path / "saida"),
                   "--metodo", "combinado", "--timeout-s", "300")
    finally:
        s.parar()
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(s.chamadas) == 1
    c = s.chamadas[0]
    assert c["bytes"] == pdf.read_bytes()
    assert c["params"]["metodo"] == ["combinado"] and c["params"]["modo"] == ["bancada"]
    assert c["params"]["extensao"] == ["pdf"] and c["params"]["prazo_s"] == ["300"]
    assert "authorization" not in c["cab"]
    pasta = tmp_path / "saida" / "combinado" / "DMBOK_v2"
    assert (pasta / "espelho.md").exists() and (pasta / "indice.json").exists()
    rel = json.loads((pasta / "relatorio.json").read_text(encoding="utf-8"))
    assert rel["arquivo"] == "DMBOK v2.pdf"
    assert r.stdout.startswith("ok")


def test_ocupado_espera_e_tenta_de_novo(tmp_path, pdf):
    s = Servico(ocupado_vezes=2)
    try:
        r = _curar(s.url, "--reextrair", str(pdf), "--bancada", str(tmp_path / "saida"), "--metodo", "combinado")
    finally:
        s.parar()
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(s.chamadas) == 3


def test_prazo_estourado_e_dado(tmp_path, pdf):
    s = Servico(status=504, erro="prazo de 150 s", erro_tipo="timeout", sha256_md=None, bytes_md=None,
                sha256_indice=None, bytes_indice=None)
    try:
        r = _curar(s.url, "--reextrair", str(pdf), "--bancada", str(tmp_path / "saida"), "--metodo", "combinado")
    finally:
        s.parar()
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.startswith("falha")


def test_servico_fora_do_ar_e_erro(tmp_path, pdf):
    r = _curar("http://127.0.0.1:9", "--reextrair", str(pdf), "--bancada", str(tmp_path / "saida"),
               "--metodo", "combinado")
    assert r.returncode == 1
    assert "127.0.0.1:9" in r.stdout
