"""Verbo tarefas: moldes do two-pager, do comentário tipado e da story derivada, e o fecho
no próprio comentário (card #3410).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele): o teste prova o que
o VERBO faz — o molde que imprime, o corpo que envia, as recusas da forma do comentário —
sem tocar no board de verdade. A regra de transição é do rastreador e tem self-check lá.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BIN = REPO_ROOT / "bin" / "tarefas"


class _Stub(BaseHTTPRequestHandler):
    comentarios: list = []
    patches: list = []

    def log_message(self, *a):  # silencioso
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        m = re.match(r"^/itens/(\d+)/comentarios$", self.path)
        if m:
            return self._json({"item": int(m.group(1)), "comentarios": self.comentarios})
        self._json({"erro": "nao existe"}, 404)

    def do_PATCH(self):
        m = re.match(r"^/itens/(\d+)/comentarios/(\d+)$", self.path)
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        if not m:
            return self._json({"erro": "rota"}, 404)
        type(self).patches.append((int(m.group(2)), corpo))
        self._json({"id": int(m.group(2)), "item": int(m.group(1)), "corpo": corpo["corpo"]})


@pytest.fixture()
def stub():
    _Stub.comentarios, _Stub.patches = [], []
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base="http://127.0.0.1:9", stdin=None):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env,
                          input=stdin)


def _rotulos(texto):
    return [m.group(1) for m in re.finditer(r"(?m)^([A-ZÀ-Úa-zà-ú][^:\n]{0,30}):", texto)]


def test_modelo_feature_e_o_two_pager_na_ordem():
    p = _run(["modelo", "feature"])
    assert p.returncode == 0, p.stderr
    assert _rotulos(p.stdout) == ["Problema", "Solução", "Peças", "Fora", "Resultado", "Medida",
                                  "Apetite", "Aberto", "Produtos documentais", "Sai quando",
                                  "Quebra"]
    assert "Continuidade" not in p.stdout and "Fontes" not in p.stdout
    assert "título" in p.stderr


def test_modelo_epico_sem_indice_de_feature():
    p = _run(["modelo", "épico"])
    assert p.returncode == 0, p.stderr
    assert _rotulos(p.stdout) == ["Problema", "Solução", "Peças", "Fora", "Resultado", "Medida",
                                  "Apetite", "Aberto", "Quebra"]


@pytest.mark.parametrize("tipo,fixas", [
    ("insumo", ["Traz"]), ("pergunta", []), ("buraco", ["Caso", "Remendo"]),
    ("requisito", ["Confere"]), ("decisão", ["Descartado", "Substitui"]),
])
def test_modelo_comentario_topo_fixas_branco_argumento(tipo, fixas):
    p = _run(["modelo", "comentario", tipo])
    assert p.returncode == 0, p.stderr
    linhas = p.stdout.splitlines()
    assert linhas[0].startswith(tipo)
    assert [l.split(":")[0] for l in linhas[1:1 + len(fixas)]] == fixas
    assert linhas[1 + len(fixas)] == "" and linhas[2 + len(fixas)].startswith("<argumento")


def test_modelo_comentario_sem_tipo_e_uso():
    assert _run(["modelo", "comentario"]).returncode == 2


def test_modelo_story_derivada_aponta_o_item():
    p = _run(["modelo", "story", "derivada"])
    assert p.returncode == 0, p.stderr
    neg = next(l for l in p.stdout.splitlines() if l.startswith("Negócio:"))
    assert "R<a>" in neg and "D<n>" in neg and "Peça <n>" in neg
    assert "R<n> ou D<n>" in next(l for l in p.stdout.splitlines() if l.startswith("Aceite:"))


def test_fecha_escreve_a_ultima_linha(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "corpo": "<p>buraco: x</p><p><strong>Caso:</strong> a@b</p>"}]
    p = _run(["comentar", "3408", "--fecha", "7", "remendado — momento «No parecer»"], base)
    assert p.returncode == 0, p.stderr
    (cid, corpo), = s.patches
    assert cid == 7
    assert corpo["corpo"].startswith("<p>buraco: x</p>")
    assert corpo["corpo"].endswith("<p><strong>fecho:</strong> remendado — momento «No parecer»</p>")


def test_fecha_aceita_o_prefixo_fecho(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "corpo": "<p>pergunta (ti): x?</p>"}]
    p = _run(["comentar", "3408", "--fecha", "#7", "fecho: respondida — Solução"], base)
    assert p.returncode == 0, p.stderr
    assert s.patches[0][1]["corpo"].count("fecho:") == 1


def test_fecha_recusa_insumo(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "corpo": "<p>insumo: levantamento</p><p>Traz: x</p>"}]
    p = _run(["comentar", "3408", "--fecha", "7", "aceito — R3"], base)
    assert p.returncode == 4 and "insumo" in p.stderr and not s.patches


def test_fecha_recusa_resultado_fora_do_vocabulario(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "corpo": "<p>requisito: x</p><p>Confere: y</p>"}]
    p = _run(["comentar", "3408", "--fecha", "7", "remendado — R3"], base)
    assert p.returncode == 4 and "aceito" in p.stderr and not s.patches


def test_fecha_exige_destino(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "corpo": "<p>buraco: x</p>"}]
    p = _run(["comentar", "3408", "--fecha", "7", "remendado"], base)
    assert p.returncode == 2 and not s.patches


def test_fecha_ja_fechado_nao_muda(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "corpo": "<p>buraco: x</p><p><strong>fecho:</strong> cortado — Fora</p>"}]
    p = _run(["comentar", "3408", "--fecha", "7", "remendado — x"], base)
    assert p.returncode == 1 and "já está fechado" in p.stderr and not s.patches


def test_fecha_comentario_que_nao_existe(stub):
    s, base = stub
    p = _run(["comentar", "3408", "--fecha", "9", "remendado — x"], base)
    assert p.returncode == 1 and not s.patches


def test_fecha_sem_tipo_avisa_e_escreve(stub):
    s, base = stub
    s.comentarios = [{"id": 7, "corpo": "<p>comentário antigo sem etiqueta</p>"}]
    p = _run(["comentar", "3408", "--fecha", "7", "respondida — x"], base)
    assert p.returncode == 0 and "aviso" in p.stderr and len(s.patches) == 1


def test_para_html_separa_os_rotulos_do_two_pager(stub):
    """O achado do #3408: Solução e Peças caíam dentro de Medida e de Fora."""
    s, base = stub
    s.comentarios = [{"id": 1, "corpo": "<p>pergunta (x): y</p>"}]
    corpo = "Medida: m\nSolução:\n- Ao lapidar: a\nPeças:\n1. p\nAberto: z\nProdutos documentais:\n- d"
    p = subprocess.run(["bash", "-c", f'source <(sed -n "/^para_html()/,/^}}/p" {BIN}); para_html'],
                       input=corpo, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    for r in ("Medida", "Solução", "Peças", "Aberto", "Produtos documentais"):
        assert f"<p><strong>{r}:</strong>" in p.stdout, (r, p.stdout)
