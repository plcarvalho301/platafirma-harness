"""Verbo tarefas: `editar --trecho`, o corpo do card trocado só num ponto (card #4110).

O rastreador é um stub HTTP em loopback (TAREFAS_BASE aponta para ele): o teste prova o que o
VERBO faz — o pedido que envia, as recusas de forma, a recusa da API que sobe — sem tocar no
board. Quem confere se o `antes` ocorre uma vez só no corpo gravado é a API
(`platafirma-rastreador@api/tests/test_descricao_trecho.py`); aqui se prova que o verbo leva só
o trecho, converte o texto como o corpo é gravado (HTML) e não chama a API quando a forma é ruim.
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

BIN = Path(__file__).resolve().parents[1] / "bin" / "tarefas"

ITEM = {"id": 42, "titulo": "card de teste", "estado": "em-execucao",
        "estado_nome": "Em execução", "pai": None}


class _Stub(BaseHTTPRequestHandler):
    chamadas: list = []
    recusa: str | None = None
    item_desc: str | None = None
    rotulos: list | None = None

    def log_message(self, *a):  # silencioso
        pass

    def _json(self, payload, status=200):
        b = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_PATCH(self):
        n = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(n) or b"{}")
        type(self).chamadas.append(("PATCH", self.path, corpo))
        if self.recusa:
            return self._json({"erro": self.recusa}, 400)
        m = re.match(r"^/itens/(\d+)$", self.path)
        return self._json(ITEM if m else {"erro": "rota"}, 200 if m else 404)

    def do_GET(self):
        type(self).chamadas.append(("GET", self.path, None))
        m = re.match(r"^/itens/(\d+)$", self.path)
        if m and type(self).item_desc is not None:
            it = dict(ITEM)
            it["descricao"] = type(self).item_desc
            return self._json(it, 200)
        if self.path == "/modelo" and type(self).rotulos is not None:
            return self._json({"rotulos_da_conversao": type(self).rotulos}, 200)
        self._json({"erro": "o trecho não precisa de leitura nem da lista de rótulos"}, 404)


@pytest.fixture()
def stub():
    _Stub.chamadas, _Stub.recusa = [], None
    _Stub.item_desc, _Stub.rotulos = None, None
    srv = HTTPServer(("127.0.0.1", 0), _Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield _Stub, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def _run(args, base):
    env = dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia")
    return subprocess.run([str(BIN)] + args, capture_output=True, text=True, env=env, timeout=30)


def test_trecho_manda_um_patch_que_leva_so_o_trecho(stub):
    s, base = stub
    p = _run(["editar", "#42", "--trecho", "--antes", "sai 0", "--depois", "sai 1"], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas == [("PATCH", "/itens/42",
                           {"descricao_trecho": {"antes": "sai 0", "depois": "sai 1"}})]
    assert "item 42 editado: card de teste" in p.stdout and "(inalterado)" in p.stdout


def test_trecho_sai_com_o_mesmo_escape_do_corpo_e_a_mesma_quebra(stub):
    s, base = stub
    antes = "a < b & \"c\" 'd'\nsegunda linha\n\nnovo parágrafo"
    p = _run(["editar", "42", "--trecho", "--antes", antes, "--depois", "x<y"], base)
    assert p.returncode == 0, p.stderr
    enviado = s.chamadas[0][2]["descricao_trecho"]
    assert enviado["antes"] == ("a &lt; b &amp; &quot;c&quot; &#x27;d&#x27;<br>segunda linha"
                                "</p><p>novo parágrafo")
    assert enviado["depois"] == "x&lt;y"


def test_depois_vazio_apaga_o_trecho(stub):
    s, base = stub
    p = _run(["editar", "42", "--trecho", "--antes", "<br>- um", "--depois", ""], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas[0][2] == {"descricao_trecho": {"antes": "&lt;br&gt;- um", "depois": ""}}


def test_bruto_manda_o_trecho_como_esta_para_quem_escreve_o_html(stub):
    s, base = stub
    p = _run(["editar", "42", "--trecho", "--bruto", "--antes", "<strong>Aceite:</strong> x",
              "--depois", "<strong>Aceite:</strong> y"], base)
    assert p.returncode == 0, p.stderr
    assert s.chamadas[0][2] == {"descricao_trecho": {"antes": "<strong>Aceite:</strong> x",
                                                    "depois": "<strong>Aceite:</strong> y"}}


def test_trecho_nao_chama_nada_alem_do_patch(stub):
    """Sem GET do corpo e sem GET /modelo: o pedido leva só o trecho."""
    s, base = stub
    assert _run(["editar", "42", "--trecho", "--antes", "a", "--depois", "b"], base).returncode == 0
    assert [c[0] for c in s.chamadas] == ["PATCH"]


def test_trecho_junto_de_titulo_e_um_patch_so(stub):
    s, base = stub
    p = _run(["editar", "42", "--titulo", "novo", "--trecho", "--antes", "a", "--depois", "b"], base)
    assert p.returncode == 0, p.stderr
    assert len(s.chamadas) == 1
    assert s.chamadas[0][2] == {"titulo": "novo", "descricao_trecho": {"antes": "a", "depois": "b"}}


@pytest.mark.parametrize("args", [
    ["--trecho"],                                              # sem antes nem depois
    ["--trecho", "--antes", "a"],                              # sem depois
    ["--trecho", "--depois", "b"],                             # sem antes
    ["--trecho", "--antes", "", "--depois", "b"],              # antes vazio casaria em todo lugar
    ["--antes", "a", "--depois", "b"],                         # sem --trecho
    ["--bruto"],                                               # sem --trecho
    ["--trecho", "--antes", "a", "--depois", "b", "--desc", "corpo"],       # trecho e corpo inteiro
    ["--trecho", "--antes", "a"] + ["--depois"],               # --depois sem valor
])
def test_forma_ruim_sai_2_sem_chamar_a_api(stub, args):
    s, base = stub
    p = _run(["editar", "42", *args], base)
    assert p.returncode == 2, (p.returncode, p.stderr)
    assert s.chamadas == []


def test_recusa_da_api_sobe_com_a_contagem(stub):
    s, base = stub
    s.recusa = "descricao_trecho: `antes` ocorre 2 vezes no corpo do item; tem de ocorrer exatamente uma"
    p = _run(["editar", "42", "--trecho", "--antes", "igual", "--depois", "x"], base)
    assert p.returncode == 1
    assert "ocorre 2 vezes" in p.stderr


def test_corpo_inteiro_continua_pedindo_a_lista_de_rotulos_e_nao_manda_trecho(stub):
    """A troca inteira segue como era: `--desc` sozinho não leva `descricao_trecho`."""
    s, base = stub
    _run(["editar", "42", "--desc", "corpo"], base)  # o stub não serve /modelo: recusa antes do PATCH
    assert all("descricao_trecho" not in (c[2] or {}) for c in s.chamadas)


def test_o_ajuda_do_verbo_diz_o_trecho():
    ajuda = subprocess.run([str(BIN)], capture_output=True, text=True,
                           env=dict(os.environ, TAREFAS_BASE="http://127.0.0.1:9"))
    texto = ajuda.stdout + ajuda.stderr
    assert "--trecho --antes" in texto and "UMA vez" in texto


def test_editar_desc_stdin_nao_dobra_barra_invertida(stub):
    s, base = stub
    s.rotulos = ["Tarefas", "Aceite"]
    texto_com_barra = 'Aceite:\nrepo procurar platafirma-harness "acervo ler casa\\|planilha" skills/prosa\n'
    p = subprocess.run([str(BIN), "editar", "42", "--desc-stdin"], input=texto_com_barra,
                       capture_output=True, text=True,
                       env=dict(os.environ, TAREFAS_BASE=base, PF_CADEIRA="engenharia"), timeout=30)
    assert p.returncode == 0, p.stderr
    patch_chamada = [c for c in s.chamadas if c[0] == "PATCH"][0]
    descricao_recebida = patch_chamada[2]["descricao"]
    assert 'acervo ler casa\\|planilha' in descricao_recebida
    assert 'acervo ler casa\\\\|planilha' not in descricao_recebida


def test_o_ato_riscar_saiu_do_verbo(stub):
    # R37 (#4223): a task é filha da story, com estado; riscar linha de `Tarefas:` não existe mais
    s, base = stub
    p = _run(["riscar", "42", "1"], base)
    assert p.returncode != 0
    assert not s.chamadas
    assert "riscar" not in BIN.read_text(encoding="utf-8")
