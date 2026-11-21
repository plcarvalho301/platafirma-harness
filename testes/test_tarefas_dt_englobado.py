# componente: componente:verbo-tarefas
"""Verbo tarefas: DTs 278 (ler item englobado mostra resolvido_de) e 449 (dica de registro)."""
from __future__ import annotations

import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin" / "tarefas"

ESTADOS = [
    {"estado": "captada", "nome": "Captada", "fase": "funil", "natureza": "fila"},
    {"estado": "priorizada", "nome": "Priorizada", "fase": "funil", "natureza": "fila"},
    {"estado": "entregue", "nome": "Entregue", "fase": "terminal", "natureza": "terminal"},
]


class _Rastreador(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        caminho = urlparse(self.path).path
        if caminho == "/api/estados":
            return self._json({"estados": ESTADOS})
        if caminho == "/api/itens/3531":
            return self._json({
                "id": 3513, "chave": "3513", "resolvido_de": 3531,
                "nivel": 2, "nivel_nome": "story", "pai": 3497,
                "titulo": "Item absorvedor", "estado": "entregue",
                "estado_nome": "Entregue", "estado_fase": "terminal",
                "estado_derivado": None, "cadeira": "ia",
                "ancestrais": [], "bloqueia": [], "bloqueado_por": [],
                "descricao": "<p>corpo</p>", "sign_offs": [],
            })
        return self._json({"erro": f"nao esperado: {caminho}"}, status=404)

    def do_POST(self):
        caminho = urlparse(self.path).path
        if caminho == "/api/itens":
            return self._json({
                "erro": "story sem pai exige `registro-de-negocio` para ir a `priorizada` (R16, arq:0127 D8)",
                "exige": "registro-de-negocio",
            }, status=400)
        return self._json({"erro": f"nao esperado: {caminho}"}, status=404)


def _rodar(*args: str):
    srv = HTTPServer(("127.0.0.1", 0), _Rastreador)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        env = {**os.environ, "TAREFAS_BASE": f"http://127.0.0.1:{srv.server_port}/api"}
        return subprocess.run([str(BIN), *args], capture_output=True, text=True, env=env)
    finally:
        srv.shutdown()
        srv.server_close()


def test_dt_278_ler_item_englobado_recusa_e_aponta_o_englobante():
    """Ordem do dono, 17/11/2026: o englobado está fora do funil e não aparece em leitura; a recusa
    nomeia o englobante, que é o que se lê, e não traz título nem corpo."""
    for args in (("ler", "3531", "--cabecalho"), ("ler", "3531")):
        r = _rodar(*args)
        assert r.returncode == 1, r.stdout
        assert r.stdout == ""
        assert "#3531 está fora do funil (englobada em #3513)" in r.stderr
        assert "Item absorvedor" not in r.stderr


def test_dt_449_recusa_de_registro_nao_forca_estado_priorizada():
    r = _rodar("criar", "Ajuste", "--cadeira", "dados")
    assert r.returncode != 0
    assert '--registro "<porquê>"' in r.stderr
    assert '--estado priorizada --registro' not in r.stderr


def test_dt_943_story_com_estado_captada_recusa_explicando_regra():
    """DT 943: story e task não têm captada (regra do dono, 20/10/2026). Pedir `--estado captada`
    em story recusa com exit 4 explicando a regra e os níveis de captura, em vez de deixar a API
    promover silenciosamente para priorizada e acusar falta de registro de negócio."""
    r = _rodar("criar", "Revisar custódia", "--estado", "captada", "--cadeira", "seguranca")
    assert r.returncode == 4, (r.returncode, r.stdout, r.stderr)
    assert "não têm 'captada'" in r.stderr
    assert "--nivel ideia" in r.stderr
