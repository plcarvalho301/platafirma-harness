"""Contrato de `lint diagrama` e do bloqueio no pre-commit (card #3096).

O Kroki é um servidor HTTP de fixture no loopback (o mesmo padrão de
`test_conferir_diagrama_kroki.py`, card #3099): recusa (400) diagrama cujo corpo traz a
marca `QUEBRA`, aceita (200, `<svg/>`) o resto. Prova: um diagrama bom compila (exit 0); um
quebrado reprova (exit 1) nomeando arquivo e linha; Kroki fora de alcance é indeterminavel
(exit 5), nunca defeito; o pre-commit recusa o commit com o stage tendo diagrama quebrado,
nomeando o arquivo, e passa quando ele é corrigido; Kroki fora do ar no pre-commit avisa e
NÃO barra (a trava desta story). Não prova: o Kroki real nem a rede da conta.
"""
from __future__ import annotations

import http.server
import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[2]
LINT = HARNESS / "bin" / "lint"
PRE_COMMIT = HARNESS / "bin" / "_lint" / "pre_commit.py"

IDENT = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
         "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}

MMD_BOM = "graph TD\n  a-->b\n"
MMD_QUEBRADO = "graph TD\n  QUEBRA linha 2\n"


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={**os.environ, **IDENT})


def _kroki():
    class H(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            corpo = self.rfile.read(n).decode("utf-8", errors="replace")
            if "QUEBRA" in corpo:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Error 400: Parse error on line 2: token QUEBRA")
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"<svg/>")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def _porta_livre():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _kroki_url(porta):
    return f"http://127.0.0.1:{porta}"


# --- `lint diagrama <repo> <alvo>` ----------------------------------------------------

def _bancada(tmp_path):
    bancada = tmp_path / "bancada"
    wt = bancada / "wt" / "demo-diag" / "ti" / "fixture"
    wt.mkdir(parents=True)
    (wt / "bom.mmd").write_text(MMD_BOM, encoding="utf-8")
    (wt / "quebrado.mmd").write_text(MMD_QUEBRADO, encoding="utf-8")
    _git(wt, "init", "-q", "-b", "main")
    _git(wt, "add", "-A")
    _git(wt, "commit", "-q", "-m", "fixture")
    return bancada


def _lint_diagrama(bancada, alvo, porta):
    env = {**os.environ, "PLATAFIRMA_BANCADA": str(bancada), "PF_CADEIRA": "ti",
           "KROKI_URL": _kroki_url(porta), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([str(LINT), "diagrama", "demo-diag", alvo],
                          capture_output=True, text=True, env=env, check=False)


def test_diagrama_bom_compila_sai_0(tmp_path):
    bancada = _bancada(tmp_path)
    srv = _kroki()
    try:
        r = _lint_diagrama(bancada, "bom.mmd", srv.server_address[1])
    finally:
        srv.shutdown()
    assert r.returncode == 0, r.stdout + r.stderr


def test_diagrama_quebrado_sai_1_com_arquivo_e_linha(tmp_path):
    bancada = _bancada(tmp_path)
    srv = _kroki()
    try:
        r = _lint_diagrama(bancada, "quebrado.mmd", srv.server_address[1])
    finally:
        srv.shutdown()
    assert r.returncode == 1, r.stdout + r.stderr
    assert "quebrado.mmd" in r.stdout
    # saida agrupada: o arquivo numa linha, a linha do erro embaixo do criterio
    assert "\n  quebrado.mmd\n" in r.stdout and "\n      2\n" in r.stdout, r.stdout


def test_diagrama_kroki_fora_de_alcance_sai_5_e_nao_reprova(tmp_path):
    bancada = _bancada(tmp_path)
    r = _lint_diagrama(bancada, "bom.mmd", _porta_livre())
    assert r.returncode == 5, r.stdout + r.stderr
    assert "nao consegui falar com o Kroki" in r.stdout + r.stderr


# --- `lint diagrama ... --json` (card #3096, revisao do PR #306) --------------------
# contrato de saida que muda pede teste de contrato (arq:0116 / guia portoes-do-codigo):
# nem test_contrato_diagrama.py (so testava texto puro) nem test_contrato_lint.py (so
# testa --json da classe 'codigo') mediam o {ancora, classe, alvo, chave, rev,
# apontamentos} que bin/lint monta para a classe 'diagrama'.

def _lint_diagrama_json(bancada, alvo, porta):
    env = {**os.environ, "PLATAFIRMA_BANCADA": str(bancada), "PF_CADEIRA": "ti",
           "KROKI_URL": _kroki_url(porta), "PYTHONDONTWRITEBYTECODE": "1"}
    return subprocess.run([str(LINT), "diagrama", "demo-diag", alvo, "--json"],
                          capture_output=True, text=True, env=env, check=False)


def test_diagrama_json_bom_tem_as_seis_chaves_e_lista_vazia(tmp_path):
    bancada = _bancada(tmp_path)
    srv = _kroki()
    try:
        r = _lint_diagrama_json(bancada, "bom.mmd", srv.server_address[1])
    finally:
        srv.shutdown()
    assert r.returncode == 0, r.stdout + r.stderr
    dado = json.loads(r.stdout)
    assert set(dado.keys()) == {"ancora", "classe", "alvo", "chave", "rev", "apontamentos"}
    assert dado["classe"] == "diagrama"
    assert dado["chave"] == "repositorio"
    assert dado["alvo"] == "demo-diag/bom.mmd"
    assert dado["rev"] is None
    assert dado["apontamentos"] == []
    assert "0 apontamentos" in dado["ancora"]


def test_diagrama_json_quebrado_nomeia_arquivo_e_linha_no_apontamento(tmp_path):
    bancada = _bancada(tmp_path)
    srv = _kroki()
    try:
        r = _lint_diagrama_json(bancada, "quebrado.mmd", srv.server_address[1])
    finally:
        srv.shutdown()
    assert r.returncode == 1, r.stdout + r.stderr
    dado = json.loads(r.stdout)
    assert dado["classe"] == "diagrama"
    assert dado["alvo"] == "demo-diag/quebrado.mmd"
    assert len(dado["apontamentos"]) == 1
    apontamento = dado["apontamentos"][0]
    assert apontamento["arquivo"] == "quebrado.mmd"
    assert apontamento["linha"] == 2
    assert apontamento["cura"]
    assert apontamento["o_que_fere"]


def test_diagrama_json_kroki_fora_de_alcance_sai_5_e_ainda_e_json_valido(tmp_path):
    """Indeterminavel (#3099) tambem passa pelo bloco --json comum (nao ha caminho de
    erro separado): o apontamento de aviso sobre o Kroki vai dentro de 'apontamentos'."""
    bancada = _bancada(tmp_path)
    r = _lint_diagrama_json(bancada, "bom.mmd", _porta_livre())
    assert r.returncode == 5, r.stdout + r.stderr
    dado = json.loads(r.stdout)
    assert dado["classe"] == "diagrama"
    assert len(dado["apontamentos"]) == 1
    assert "nao consegui falar com o Kroki" in dado["apontamentos"][0]["o_que_fere"]


# --- pre-commit: recusa o commit com diagrama quebrado no stage ----------------------

def _repo_com_diagrama(tmp_path, conteudo, nome="fig.mmd"):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / nome).write_text(conteudo, encoding="utf-8")
    _git(repo, "add", "-A")
    return repo


def _pre_commit(repo, porta):
    env = {**os.environ, "KROKI_URL": _kroki_url(porta)}
    return subprocess.run([sys.executable, str(PRE_COMMIT)], cwd=repo,
                          capture_output=True, text=True, env=env, check=False)


def test_pre_commit_recusa_diagrama_quebrado_nomeando_o_arquivo(tmp_path):
    repo = _repo_com_diagrama(tmp_path, MMD_QUEBRADO)
    srv = _kroki()
    try:
        r = _pre_commit(repo, srv.server_address[1])
    finally:
        srv.shutdown()
    assert r.returncode == 1, r.stdout + r.stderr
    assert "[diagrama] fig.mmd:2:" in r.stderr


def test_pre_commit_passa_com_diagrama_corrigido(tmp_path):
    repo = _repo_com_diagrama(tmp_path, MMD_BOM)
    srv = _kroki()
    try:
        r = _pre_commit(repo, srv.server_address[1])
    finally:
        srv.shutdown()
    assert r.returncode == 0, r.stdout + r.stderr


def test_pre_commit_kroki_fora_do_ar_avisa_e_nao_barra(tmp_path):
    repo = _repo_com_diagrama(tmp_path, MMD_QUEBRADO)
    r = _pre_commit(repo, _porta_livre())
    assert r.returncode == 0, r.stdout + r.stderr
    assert "Kroki fora de alcance" in r.stderr
