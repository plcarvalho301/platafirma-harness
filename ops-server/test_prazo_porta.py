"""Prazo da chamada na porta (#3249).

Quem corta em ~60 s e o cliente MCP, nao a porta (medido em 03/10/2026 no ops log): o
verbo seguia no host e o retorno se perdia. Passado o prazo, a chamada devolve
`em_andamento` com o caminho do resultado, e o verbo segue ate o timeout pedido. Em lote
o prazo e da chamada inteira. Processo de verdade (`sh -c`) onde o que se prova e o
processo; falso de `_run_verbo_blocking` onde o que se prova e o lote.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

os.environ["PF_HARNESS"] = str(HARNESS_DIR)
import server as s

IDENT = {"sessao_id": "-", "ordem_id": "-", "cadeira": "", "sujeito": "", "origem_sessao": ""}


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def resultado_dir(tmp_path):
    with patch("server.RESULTADO_DIR", tmp_path), patch("server._audit") as audit:
        yield tmp_path, audit


def _espera_fim(caminho: Path, teto: float = 10.0) -> dict:
    fim = time.monotonic() + teto
    while time.monotonic() < fim:
        d = json.loads(caminho.read_text(encoding="utf-8"))
        if not d.get("em_andamento"):
            return d
        time.sleep(0.05)
    raise AssertionError(f"{caminho} ainda em andamento depois de {teto}s")


# --- o processo -------------------------------------------------------------------

def test_verbo_que_cabe_no_prazo_volta_como_sempre(resultado_dir):
    r = s._run_verbo_blocking(["sh", "-c", "echo oi"], None, 10, IDENT, 5)
    assert r["exit_code"] == 0
    assert r["stdout"]["texto"] == "oi\n"
    assert not r.get("em_andamento")


def test_passou_do_prazo_devolve_em_andamento_e_grava_o_final(resultado_dir):
    pasta, audit = resultado_dir
    # O verbo espera um portao que so o teste abre, depois que a chamada voltou: a ordem
    # (devolveu antes de o verbo acabar) se prova pelo estado, nao por uma janela de tempo,
    # que falhava com a CPU do host ocupada.
    portao = pasta / "liberar"
    espera = 'while [ ! -e "$1" ]; do sleep 0.02; done; echo fim'
    r = s._run_verbo_blocking(["sh", "-c", espera, "sh", str(portao)], None, 10, IDENT, 0.2)
    assert r.get("em_andamento") is True and r["id"], r   # portao fechado: o verbo nao acabou
    caminho = Path(r["resultado"])
    assert caminho.parent == pasta
    assert json.loads(caminho.read_text())["em_andamento"] is True
    portao.touch()
    final = _espera_fim(caminho)
    assert final["exit_code"] == 0
    assert final["stdout"]["texto"] == "fim\n"
    assert final["id"] == r["id"] and final["dur_ms"] >= 200     # viveu alem do prazo de 0,2 s
    eventos = [c.kwargs.get("evento") for c in audit.call_args_list]
    assert "verbo_concluido_apos_prazo" in eventos


def test_stdin_chega_inteiro_mesmo_passando_do_prazo(resultado_dir):
    r = s._run_verbo_blocking(["sh", "-c", "sleep 0.5; cat"], "abc", 10, IDENT, 0.1)
    assert r["em_andamento"] is True
    assert _espera_fim(Path(r["resultado"]))["stdout"]["texto"] == "abc"


def test_timeout_pedido_menor_que_o_prazo_mata_como_antes(resultado_dir):
    r = s._run_verbo_blocking(["sh", "-c", "sleep 5"], None, 1, IDENT, 5)
    assert "timeout (1s)" in r["erro"]
    assert not r.get("em_andamento")


def test_timeout_que_estoura_depois_do_prazo_vai_ao_resultado(resultado_dir):
    r = s._run_verbo_blocking(["sh", "-c", "sleep 5"], None, 1, IDENT, 0.2)
    assert r["em_andamento"] is True
    final = _espera_fim(Path(r["resultado"]))
    assert "timeout (1s)" in final["erro"]


def test_sem_prazo_e_o_comportamento_de_antes(resultado_dir):
    r = s._run_verbo_blocking(["sh", "-c", "sleep 0.3; echo ok"], None, 10, IDENT, None)
    assert r["exit_code"] == 0


def test_prazo_zero_desliga():
    with patch("server.PRAZO_S", 0):
        assert s._prazo_da_chamada() is None
        assert s._prazo_esgotado(None) is None


def test_porta_reiniciada_fecha_o_resultado_pendente(resultado_dir):
    pasta, _ = resultado_dir
    pendente = pasta / "abc.json"
    pendente.write_text(json.dumps({"em_andamento": True, "id": "abc", "verbo": "acervo curar"}))
    pronto = pasta / "def.json"
    pronto.write_text(json.dumps({"id": "def", "exit_code": 0}))
    velho = pasta / "velho.json"
    velho.write_text(json.dumps({"id": "velho", "exit_code": 0}))
    antigo = time.time() - s.RESULTADO_RETENCAO_S - 60
    os.utime(velho, (antigo, antigo))
    s._fecha_orfaos_do_prazo()
    d = json.loads(pendente.read_text())
    assert d["interrompido"] is True and "em_andamento" not in d and d["id"] == "abc"
    assert json.loads(pronto.read_text()) == {"id": "def", "exit_code": 0}
    assert not velho.exists()


# --- o lote: prazo da chamada inteira ---------------------------------------------

def _rc_vazio() -> MagicMock:
    m = MagicMock()
    m.get.return_value = None
    m.hget.return_value = None
    m.hgetall.return_value = {}
    return m


def _patches_do_lote():
    slugs = set(s.SLUGS_SERVIDOS) | {"repo"}
    bins = {**s.BINARIOS, "repo": "/opt/bin/repo"}
    return (patch("server.SLUGS_SERVIDOS", slugs), patch("server.BINARIOS", bins),
            patch("server._autoriza", return_value=None),
            patch("server._rc", return_value=_rc_vazio()), patch("server._audit"))


@pytest.mark.anyio
async def test_lote_reparte_o_prazo_e_o_item_sem_prazo_nao_roda():
    prazos = []

    def fake(argv, stdin, timeout, ident, prazo=None):
        prazos.append(prazo)
        time.sleep(0.2)
        return {"exit_code": 0, "stdout": {"texto": "ok", "bytes_total": 2, "truncado": False}}

    a, b, c, d, e = _patches_do_lote()
    with a, b, c, d, e, patch("server.PRAZO_S", 0.3), \
            patch("server._run_verbo_blocking", side_effect=fake):
        res = await s.run_command(commands=["repo estado", "repo estado", "repo estado"])

    assert len(prazos) == 2
    assert prazos[0] > prazos[1]                 # o segundo item herda o que sobrou
    assert res["lote"][2]["nao_rodou"] is True
    assert "prazo da chamada" in res["lote"][2]["motivo"]


@pytest.mark.anyio
async def test_encadeado_para_no_item_em_andamento():
    def fake(argv, stdin, timeout, ident, prazo=None):
        return {"em_andamento": True, "id": "x1", "resultado": "/tmp/x1.json",
                "motivo": "em andamento: repo passou do prazo da chamada"}

    a, b, c, d, e = _patches_do_lote()
    with a, b, c, d, e, patch("server._run_verbo_blocking", side_effect=fake):
        res = await s.run_command(commands=["repo commitar", "repo empurrar"], encadeado=True)

    assert res["cadeia"]["parou_em"] == 0
    assert res["cadeia"]["itens"][0]["linha"].startswith("em andamento")
    assert res["lote"][1]["nao_rodou"] is True


@pytest.mark.anyio
async def test_pipe_de_item_em_andamento_recusa():
    def fake(argv, stdin, timeout, ident, prazo=None):
        return {"em_andamento": True, "id": "x2", "resultado": "/tmp/x2.json"}

    a, b, c, d, e = _patches_do_lote()
    with a, b, c, d, e, patch("server._run_verbo_blocking", side_effect=fake):
        res = await s.run_command(commands=[
            {"verbo": "repo", "ato": "estado", "args": []},
            {"verbo": "repo", "ato": "ler", "args": [], "stdin": {"de": 0}},
        ])

    assert res["lote"][1]["recusado"] is True
    assert "em andamento" in res["lote"][1]["motivo"]


@pytest.mark.anyio
async def test_tool_de_verbo_passa_o_prazo_ao_verbo():
    recebidos = []

    def fake(argv, stdin, timeout, ident, prazo=None):
        recebidos.append(prazo)
        return {"exit_code": 0, "stdout": {"texto": "ok", "bytes_total": 2, "truncado": False}}

    tool_fn = s._faz_tool_verbo("repo", "/opt/bin/repo", "descricao")
    with patch("server.PRAZO_S", 50), patch("server._autoriza", return_value=None), \
            patch("server._rc", return_value=_rc_vazio()), patch("server._audit"), \
            patch("server._run_verbo_blocking", side_effect=fake):
        await tool_fn(ato="estado")
    assert 49 < recebidos[0] <= 50
