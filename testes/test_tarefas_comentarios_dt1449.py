# componente: componente:verbo-tarefas
"""Regressão do DT 1449: separação de comentários/insumos e paginação em `bin/tarefas`."""
from __future__ import annotations

import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

RAIZ = Path(__file__).resolve().parents[1]
BIN_TAREFAS = RAIZ / "bin" / "tarefas"


def _subir_rastreador_duble(comentarios: list[dict], insumos: list[dict], filhas: list[dict] | None = None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def _responder(self, payload: dict) -> None:
            dados = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(dados)))
            self.end_headers()
            self.wfile.write(dados)

        def do_GET(self):
            caminho = self.path.split("?", 1)[0]
            if caminho == "/api/itens/100":
                self._responder(
                    {
                        "id": 100,
                        "titulo": "Card teste",
                        "nivel": 2,
                        "nivel_nome": "story",
                        "estado_nome": "em-execucao",
                        "estado_fase": "execucao",
                        "filhas": filhas or [],
                    }
                )
                return
            if caminho == "/api/itens/101":
                self._responder(
                    {
                        "id": 101,
                        "titulo": "Filha teste",
                        "nivel": 3,
                        "nivel_nome": "task",
                        "estado_nome": "em-execucao",
                        "estado_fase": "execucao",
                        "filhas": [],
                    }
                )
                return
            if caminho == "/api/itens/100/comentarios":
                self._responder({"item": 100, "comentarios": comentarios, "total": len(comentarios)})
                return
            if caminho == "/api/itens/101/comentarios":
                self._responder(
                    {
                        "item": 101,
                        "comentarios": [
                            {
                                "id": 900,
                                "autor": "engenharia",
                                "carimbo": "2026-11-28T10:00:00Z",
                                "tipo": "parecer",
                                "corpo": "Comentário na filha",
                            }
                        ],
                        "total": 1,
                    }
                )
                return
            if caminho == "/api/itens/100/insumos":
                self._responder({"item": 100, "insumos": insumos, "total": len(insumos)})
                return
            self.send_response(404)
            self.end_headers()

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    th = Thread(target=srv.serve_forever, daemon=True)
    th.start()
    env = {
        **os.environ,
        "TAREFAS_BASE": f"http://127.0.0.1:{srv.server_address[1]}/api",
        "PF_CADEIRA": "engenharia",
    }
    return srv, env


def _rodar(env: dict[str, str], *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(BIN_TAREFAS), *args],
        env=env,
        text=True,
        capture_output=True,
        timeout=15,
        check=False,
    )


def test_comentarios_separa_insumos_e_pagina_por_comentario() -> None:
    comentarios = [
        {
            "id": i,
            "autor": "engenharia",
            "carimbo": f"2026-11-28T10:{i:02d}:00Z",
            "tipo": "parecer",
            "corpo": f"Parecer número {i}",
        }
        for i in range(1, 13)
    ] + [
        {
            "id": 99,
            "autor": "produto",
            "carimbo": "2026-11-28T10:59:00Z",
            "tipo": "insumo",
            "corpo": "Insumo grande que não deve misturar",
        }
    ]
    srv, env = _subir_rastreador_duble(comentarios, [])
    try:
        r1 = _rodar(env, "comentarios", "100")
        assert r1.returncode == 0, r1.stderr
        assert "página 1 de 2 (comentários 1-10 de 12)" in r1.stdout
        assert "Parecer número 1" in r1.stdout
        assert "Parecer número 10" in r1.stdout
        assert "Parecer número 11" not in r1.stdout
        assert "Insumo grande" not in r1.stdout
        assert "insumos omitidos: 1" in r1.stdout
        assert "próxima: tarefas comentarios 100 --pagina 2" in r1.stdout

        r2 = _rodar(env, "comentarios", "100", "--pagina", "2")
        assert r2.returncode == 0, r2.stderr
        assert "página 2 de 2 (comentários 11-12 de 12)" in r2.stdout
        assert "Parecer número 11" in r2.stdout
        assert "Parecer número 12" in r2.stdout

        r_ins = _rodar(env, "comentarios", "100", "--tipo", "insumo")
        assert r_ins.returncode == 0, r_ins.stderr
        assert "Insumo grande" in r_ins.stdout
        assert "Parecer número 1" not in r_ins.stdout
    finally:
        srv.shutdown()
        srv.server_close()


def test_comentarios_arvore_e_insumo_listar_paginam() -> None:
    comentarios = [
        {
            "id": i,
            "autor": "engenharia",
            "carimbo": f"2026-11-28T10:{i:02d}:00Z",
            "tipo": "parecer",
            "corpo": f"Item {i}",
        }
        for i in range(1, 4)
    ]
    insumos = [
        {"id": i, "estado": "em-escrita", "vira": "politica", "titulo": f"Insumo {i}"}
        for i in range(1, 5)
    ]
    srv, env = _subir_rastreador_duble(comentarios, insumos, filhas=[{"id": 101}])
    try:
        r_arv = _rodar(env, "comentarios", "100", "--arvore", "--por-pagina", "2", "--pagina", "2")
        assert r_arv.returncode == 0, r_arv.stderr
        assert "página 2 de 2 (comentários 3-4 de 4)" in r_arv.stdout
        assert "Comentário na filha" in r_arv.stdout

        r_ins = _rodar(env, "insumo", "listar", "100", "--por-pagina", "2", "--pagina", "1")
        assert r_ins.returncode == 0, r_ins.stderr
        assert "página 1 de 2 (insumos 1-2 de 4)" in r_ins.stdout
        assert "Insumo 1" in r_ins.stdout
        assert "Insumo 3" not in r_ins.stdout
        assert "próxima: tarefas insumo listar 100 --pagina 2 --por-pagina 2" in r_ins.stdout
    finally:
        srv.shutdown()
        srv.server_close()
