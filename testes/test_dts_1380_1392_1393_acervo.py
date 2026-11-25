# componente: componente:verbo-acervo
"""Testes dos DTs 1380, 1392 e 1393 do acervo no harness.

- DT 1380: limpeza idempotente do staging sob ~/AI/entrada/ após apply concluído sem falha.
- DT 1392: `acervo lote <id>` com total de obras, contagem de conceitos por obra e recorte `--pendentes`/`--curadas`.
- DT 1393: `acervo listar biblioteca indicacao` informa explicitamente quando `semantico = f`.
"""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "bin"))
from _ingerir.carga import limpar_staging_entrada  # noqa: E402

ACERVO = RAIZ / "bin" / "acervo"
LOTE_BIN = RAIZ / "bin" / "_acervo" / "lote"
LOTE_ID = "bbc55cf4-d4eb-4b4c-98d2-4f9709efb5f6"


# --- DT 1380 -----------------------------------------------------------------


def test_dt1380_limpar_staging_remove_subpasta_sob_entrada_e_e_idempotente(tmp_path):
    entrada = tmp_path / "entrada"
    staging = entrada / "drive-20261125-entrada"
    staging.mkdir(parents=True)
    (staging / "obra.pdf").write_bytes(b"%PDF-1.4")

    assert limpar_staging_entrada(staging, raiz_entrada=entrada) is True
    assert not staging.exists()
    assert entrada.is_dir()
    # Idempotência: chamar de novo não falha
    assert limpar_staging_entrada(staging, raiz_entrada=entrada) is False


def test_dt1380_limpar_staging_nunca_remove_raiz_nem_pasta_fora(tmp_path):
    entrada = tmp_path / "entrada"
    entrada.mkdir()
    fora = tmp_path / "outra_pasta"
    fora.mkdir()
    (fora / "importante.pdf").write_bytes(b"%PDF-1.4")

    assert limpar_staging_entrada(entrada, raiz_entrada=entrada) is False
    assert entrada.is_dir()

    assert limpar_staging_entrada(fora, raiz_entrada=entrada) is False
    assert fora.is_dir()
    assert (fora / "importante.pdf").is_file()


# --- DT 1392 -----------------------------------------------------------------


def _criar_psql_falso(tmp_path: Path, payload: dict) -> Path:
    script = tmp_path / "psql_falso.sh"
    json_str = json.dumps(payload, ensure_ascii=False)
    script.write_text(f"#!/usr/bin/env bash\nprintf '%s\\n' '{json_str}'\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


def test_dt1392_acervo_lote_devolve_total_conceitos_e_recorte_pendentes(tmp_path):
    dado = {
        "id": LOTE_ID,
        "estado": "concluido",
        "ate": "catalogar",
        "semantico": False,
        "itens": [
            {"posicao": 1, "obra_id": "o1", "titulo": "Obra Curada", "arquivo": "a.pdf",
             "veredito": "criar", "estado": "feito", "conceitos": 3},
            {"posicao": 2, "obra_id": "o2", "titulo": "Obra Pendente 1", "arquivo": "b.pdf",
             "veredito": "criar", "estado": "feito", "conceitos": 0},
            {"posicao": 3, "obra_id": "o3", "titulo": "Obra Pendente 2", "arquivo": "c.pdf",
             "veredito": "criar", "estado": "feito", "conceitos": 0},
        ],
    }
    psql_falso = _criar_psql_falso(tmp_path, dado)
    env = {**os.environ, "PF_ACERVO_PSQL": str(psql_falso)}

    r = subprocess.run([sys.executable, str(LOTE_BIN), LOTE_ID], capture_output=True, text=True, env=env, check=False)
    assert r.returncode == 0, r.stderr
    assert "obras: 3 total · 1 curada(s) · 2 pendente(s)" in r.stdout
    assert "o1 · 3 conceito(s) · Obra Curada" in r.stdout
    assert "o2 · 0 conceito(s) · Obra Pendente 1" in r.stdout

    r_pend = subprocess.run([sys.executable, str(LOTE_BIN), LOTE_ID, "--pendentes", "--json"],
                            capture_output=True, text=True, env=env, check=False)
    assert r_pend.returncode == 0, r_pend.stderr
    j = json.loads(r_pend.stdout)
    assert j["total_obras"] == 3
    assert j["curadas"] == 1
    assert j["pendentes"] == 2
    assert j["filtro"] == "pendentes"
    assert [o["obra_id"] for o in j["obras"]] == ["o2", "o3"]

    r_cur = subprocess.run([sys.executable, str(LOTE_BIN), LOTE_ID, "--curadas", "--json"],
                           capture_output=True, text=True, env=env, check=False)
    assert r_cur.returncode == 0, r_cur.stderr
    jc = json.loads(r_cur.stdout)
    assert [o["obra_id"] for o in jc["obras"]] == ["o1"]


# --- DT 1393 -----------------------------------------------------------------


class _HandlerInd(BaseHTTPRequestHandler):
    lote_resp: dict

    def log_message(self, *a):
        pass

    def _responder(self, status: int, obj: dict):
        dados = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        if self.path.startswith("/acervo/indicacoes"):
            self._responder(200, {"versao": "v0", "itens": []})
        elif self.path == f"/acervo/lotes/{LOTE_ID}":
            self._responder(200, self.lote_resp)
        else:
            self._responder(404, {"title": "NaoEncontrado"})

    def do_POST(self):
        n = int(self.headers.get("content-length") or 0)
        self.rfile.read(n)
        if self.path == "/acervo/indicacoes":
            self._responder(200, {"plano": True, "lote_id": LOTE_ID, "total_termos": 0, "itens": []})
        else:
            self._responder(404, {"title": "NaoEncontrado"})


def _rodar_listar_indicacao(lote_resp: dict, *extra_args: str) -> subprocess.CompletedProcess:
    handler = type("H", (_HandlerInd,), {"lote_resp": lote_resp})
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        env = {
            **os.environ,
            "MOTOR_ACERVO_URL": url,
            "RAG_API_URL": "",
            "RAG_API_BASE": "",
            "RAG_API_TOKEN": "tok-1393",
            "PF_CADEIRA": "engenharia",
            "PF_SESSAO_ID": f"t-{uuid.uuid4().hex}",
        }
        return subprocess.run(
            ["bash", str(ACERVO), "listar", "biblioteca", "indicacao", LOTE_ID, *extra_args],
            capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL, timeout=30, check=False,
        )
    finally:
        srv.shutdown()
        srv.server_close()


def test_dt1393_listar_indicacao_avisa_quando_lote_tem_semantico_falso():
    lote_sem_f = {"id": LOTE_ID, "estado": "concluido", "ate": "catalogar", "semantico": False}

    # Modo desagrupado (--estado todas)
    r = _rodar_listar_indicacao(lote_sem_f, "--estado", "todas")
    assert r.returncode == 0, r.stderr
    assert "0 itens" in r.stdout
    assert "semantico = f" in r.stdout
    assert "etapa semântica não rodou" in r.stdout

    # Modo --json
    r_json = _rodar_listar_indicacao(lote_sem_f, "--estado", "todas", "--json")
    assert r_json.returncode == 0, r_json.stderr
    dado = json.loads(r_json.stdout)
    assert dado["total"] == 0
    assert dado["lote_semantico"] is False
    assert dado["lote_ate"] == "catalogar"
    assert "etapa semântica não rodou" in dado["aviso"]

    # Modo agrupado (default)
    r_grp = _rodar_listar_indicacao(lote_sem_f)
    assert r_grp.returncode == 0, r_grp.stderr
    assert "semantico = f" in r_grp.stdout


def test_dt1393_listar_indicacao_sem_aviso_quando_semantico_verdadeiro():
    lote_sem_t = {"id": LOTE_ID, "estado": "concluido", "ate": "vetor", "semantico": True}
    r = _rodar_listar_indicacao(lote_sem_t, "--estado", "todas")
    assert r.returncode == 0, r.stderr
    assert "0 itens" in r.stdout
    assert "aviso:" not in r.stdout
