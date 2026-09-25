"""Testes de contrato para stdin JSON (dict/list) na porta (#3124).

O cliente MCP desserializa um stdin que é JSON válido ANTES de chegar ao servidor: a
tool de verbo gerada por `_faz_tool_verbo` declarava `stdin: str | None`, e o pydantic
recusava o pedido inteiro, sem rodar nada ("Input should be a valid string"). Dois
efeitos irmãos batiam o mesmo caminho: no lote por tool e no item de `run_command`
(`_item_de_lote` / o laço de injeção), um stdin dict caía sempre como pipe malformado
`{"de": n}`, com mensagem enganosa.

Cobre os três pontos de entrada nomeados no card, cada um "simulado" — chamando a
função por baixo do FastMCP, sem subir servidor de verdade (mesmo padrão de
`test_run_command_lote_injecao.py`; a validação de schema do pydantic não é testável
sem um servidor real, então a assinatura em si também é conferida por introspecção):

- top-level da tool de verbo (`_faz_tool_verbo` -> `_tool`);
- lote por tool (`_tool(lote=[...])`);
- item de `run_command` (`_item_de_lote` e o laço de injeção em `run_command`).

E a invariante que não pode regredir: `{"de": <int>}` dentro de um item de
`run_command` continua sendo lido como referência de pipe ao item anterior, não como
conteúdo.
"""
from __future__ import annotations

import inspect
import json
import os
import sys
import typing
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
PDP_CODE_DIR = HARNESS_DIR / "politica-acesso"
for d in (OPS_SERVER_DIR, PDP_CODE_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

os.environ["PF_HARNESS"] = str(HARNESS_DIR)
import server as s


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _rc_vazio() -> MagicMock:
    """Mock do cliente Valkey/Redis que não sabe de sessão nenhuma — evita que o
    autospec do MagicMock devolva um objeto truthy onde o código espera None/str."""
    m = MagicMock()
    m.get.return_value = None
    m.hget.return_value = None
    m.hgetall.return_value = {}
    return m


# --- _stdin_texto: normalização pura -----------------------------------------------

def test_stdin_texto_none_e_str_passam_intactos():
    assert s._stdin_texto(None) is None
    assert s._stdin_texto("já é texto") == "já é texto"


def test_stdin_texto_dict_vira_json_dumps():
    payload = {"mensagem": "commit", "arquivos": ["a.py", "b.py"], "n": 2}
    assert s._stdin_texto(payload) == json.dumps(payload, ensure_ascii=False)


def test_stdin_texto_list_vira_json_dumps():
    payload = [{"a": 1}, "b", 3]
    assert s._stdin_texto(payload) == json.dumps(payload, ensure_ascii=False)


def test_stdin_texto_bytes_decodifica():
    assert s._stdin_texto(b"conteudo") == "conteudo"


def test_stdin_texto_string_com_json_nao_e_reserializada():
    """Uma string que por acaso É JSON não passa por json.dumps de novo — string
    já satisfaz o contrato, e reserializar mudaria o byte a byte (aspas, espaço)."""
    texto = '{"a": 1, "b": [2, 3]}'
    assert s._stdin_texto(texto) == texto


# --- _eh_pipe_stdin: só {"de": <int>} exato -----------------------------------------

def test_eh_pipe_stdin_aceita_so_de_int_exato():
    assert s._eh_pipe_stdin({"de": 0}) is True
    assert s._eh_pipe_stdin({"de": 3}) is True


def test_eh_pipe_stdin_recusa_forma_diferente():
    assert s._eh_pipe_stdin({"de": "0"}) is False          # de como string
    assert s._eh_pipe_stdin({"de": 0, "extra": 1}) is False  # chave extra
    assert s._eh_pipe_stdin({"outro": 1}) is False
    assert s._eh_pipe_stdin({}) is False
    assert s._eh_pipe_stdin([0]) is False
    assert s._eh_pipe_stdin("de") is False
    assert s._eh_pipe_stdin(None) is False
    assert s._eh_pipe_stdin({"de": True}) is False          # bool é int em Python


# --- ponto de entrada 1: _item_de_lote (item de run_command, ~962) -----------------

def test_item_de_lote_stdin_dict_vira_texto():
    with patch("server.SLUGS_SERVIDOS", {"repo"}), \
         patch("server.BINARIOS", {"repo": "/opt/bin/repo"}):
        payload = {"mensagem": "commit", "arquivos": ["a.py"]}
        argv, stdin, recusa = s._item_de_lote(
            {"verbo": "repo", "ato": "commitar", "args": [], "stdin": payload})
        assert recusa is None
        assert stdin == json.dumps(payload, ensure_ascii=False)


def test_item_de_lote_stdin_list_vira_texto():
    with patch("server.SLUGS_SERVIDOS", {"repo"}), \
         patch("server.BINARIOS", {"repo": "/opt/bin/repo"}):
        payload = ["a.py", "b.py"]
        argv, stdin, recusa = s._item_de_lote(
            {"verbo": "repo", "ato": "commitar", "args": [], "stdin": payload})
        assert recusa is None
        assert stdin == json.dumps(payload, ensure_ascii=False)


def test_item_de_lote_stdin_string_json_passa_intacta():
    with patch("server.SLUGS_SERVIDOS", {"repo"}), \
         patch("server.BINARIOS", {"repo": "/opt/bin/repo"}):
        texto = '{"a": 1}'
        argv, stdin, recusa = s._item_de_lote(
            {"verbo": "repo", "ato": "ler", "args": [], "stdin": texto})
        assert recusa is None
        assert stdin == texto


def test_item_de_lote_stdin_pipe_de_int_nao_vira_texto():
    """A invariante que não pode regredir: {"de": n} continua marcador de pipe,
    intocado por _item_de_lote — quem resolve o valor é o laço de run_command."""
    with patch("server.SLUGS_SERVIDOS", {"repo"}), \
         patch("server.BINARIOS", {"repo": "/opt/bin/repo"}):
        argv, stdin, recusa = s._item_de_lote(
            {"verbo": "repo", "ato": "ler", "args": [], "stdin": {"de": 0}})
        assert recusa is None
        assert stdin == {"de": 0}


# --- ponto de entrada 2: laço de injeção de run_command (~1014) --------------------

@pytest.mark.anyio
async def test_run_command_lote_stdin_de_continua_pipe():
    chamadas = []

    def fake_run_verbo_blocking(argv, stdin, timeout, ident):
        chamadas.append(stdin)
        if len(chamadas) == 1:
            out = "saida-do-item-0"
            return {"exit_code": 0, "stdout": {"texto": out, "bytes_total": len(out), "truncado": False}}
        return {"exit_code": 0, "stdout": {"texto": "ok", "bytes_total": 2, "truncado": False}}

    novos_slugs = set(s.SLUGS_SERVIDOS) | {"repo"}
    novos_bins = dict(s.BINARIOS)
    novos_bins["repo"] = "/opt/bin/repo"

    with patch("server.SLUGS_SERVIDOS", novos_slugs), \
         patch("server.BINARIOS", novos_bins), \
         patch("server._autoriza", return_value=None), \
         patch("server._rc", return_value=_rc_vazio()), \
         patch("server._audit"), \
         patch("server._run_verbo_blocking", side_effect=fake_run_verbo_blocking):

        res = await s.run_command(commands=[
            {"verbo": "repo", "ato": "estado", "args": []},
            {"verbo": "repo", "ato": "ler", "args": [], "stdin": {"de": 0}},
        ])

    assert len(chamadas) == 2
    assert chamadas[1] == "saida-do-item-0"
    assert "lote" in res


@pytest.mark.anyio
async def test_run_command_lote_stdin_dict_nao_pipe_vira_texto_sem_recusa():
    chamadas = []

    def fake_run_verbo_blocking(argv, stdin, timeout, ident):
        chamadas.append(stdin)
        return {"exit_code": 0, "stdout": {"texto": "ok", "bytes_total": 2, "truncado": False}}

    novos_slugs = set(s.SLUGS_SERVIDOS) | {"repo"}
    novos_bins = dict(s.BINARIOS)
    novos_bins["repo"] = "/opt/bin/repo"
    payload = {"mensagem": "ola", "n": 2}

    with patch("server.SLUGS_SERVIDOS", novos_slugs), \
         patch("server.BINARIOS", novos_bins), \
         patch("server._autoriza", return_value=None), \
         patch("server._rc", return_value=_rc_vazio()), \
         patch("server._audit"), \
         patch("server._run_verbo_blocking", side_effect=fake_run_verbo_blocking):

        res = await s.run_command(commands=[
            {"verbo": "repo", "ato": "commitar", "args": [], "stdin": payload},
        ])

    assert len(chamadas) == 1
    assert chamadas[0] == json.dumps(payload, ensure_ascii=False)
    item = res if "lote" not in res else res["lote"][0]
    assert item.get("recusado") is not True


# --- ponto de entrada 3: top-level e lote da tool de verbo (_faz_tool_verbo, ~1978, ~1994) ---

@pytest.mark.anyio
async def test_faz_tool_verbo_stdin_dict_top_level_vira_texto():
    chamadas = []

    def fake_run_verbo_blocking(argv, stdin, timeout, ident):
        chamadas.append(stdin)
        return {"exit_code": 0, "stdout": {"texto": "ok", "bytes_total": 2, "truncado": False}}

    tool_fn = s._faz_tool_verbo("repo", "/opt/bin/repo", "descrição qualquer")
    payload = {"mensagem": "commit", "arquivos": ["a.py", "b.py"]}

    with patch("server._autoriza", return_value=None), \
         patch("server._rc", return_value=_rc_vazio()), \
         patch("server._audit"), \
         patch("server._run_verbo_blocking", side_effect=fake_run_verbo_blocking):

        res = await tool_fn(ato="commitar", args=[], stdin=payload)

    assert len(chamadas) == 1
    assert chamadas[0] == json.dumps(payload, ensure_ascii=False)
    assert res.get("exit_code") == 0


@pytest.mark.anyio
async def test_faz_tool_verbo_stdin_list_lote_vira_texto():
    chamadas = []

    def fake_run_verbo_blocking(argv, stdin, timeout, ident):
        chamadas.append(stdin)
        return {"exit_code": 0, "stdout": {"texto": "ok", "bytes_total": 2, "truncado": False}}

    tool_fn = s._faz_tool_verbo("repo", "/opt/bin/repo", "descrição qualquer")
    payload = ["a.py", "b.py"]

    with patch("server.PF_TOOLS_LOTE", True), \
         patch("server._autoriza", return_value=None), \
         patch("server._rc", return_value=_rc_vazio()), \
         patch("server._audit"), \
         patch("server._run_verbo_blocking", side_effect=fake_run_verbo_blocking):

        res = await tool_fn(lote=[{"ato": "commitar", "args": [], "stdin": payload}])

    assert len(chamadas) == 1
    assert chamadas[0] == json.dumps(payload, ensure_ascii=False)
    assert res["lote"][0].get("exit_code") == 0


# --- raiz do bug: a anotação de tipo é o que o pydantic vê no schema da tool -------

def test_faz_tool_verbo_assinatura_aceita_dict_e_list():
    """A anotação velha (`stdin: str | None`) é o que fazia o pydantic da tool MCP
    recusar um stdin dict/list ANTES de rodar qualquer coisa — o efeito real do bug
    não é testável sem subir um servidor de verdade, mas a causa (o schema derivado
    desta anotação) é, por introspecção direta da assinatura."""
    tool_fn = s._faz_tool_verbo("repo", "/opt/bin/repo", "descrição qualquer")
    anot = inspect.signature(tool_fn).parameters["stdin"].annotation
    args = typing.get_args(anot)
    assert dict in args
    assert list in args
    assert str in args


def test_run_verbo_blocking_assinatura_aceita_dict_e_list():
    anot = inspect.signature(s._run_verbo_blocking).parameters["stdin"].annotation
    args = typing.get_args(anot)
    assert dict in args
    assert list in args
    assert str in args
