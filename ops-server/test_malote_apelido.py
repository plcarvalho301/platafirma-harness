"""`malote` sem o apelido `run_command` (#3270, spec porta-so-verbo §3.7; #4117).

O apelido saiu da porta no #4117 (344 chamadas em 30 dias, 321 com erro): a porta serve só `malote`. A auditoria
grava `malote` em `tool` (na recusa e no lote encadeado) e em `via` (no item despachado). A ação do PDP segue
`run_command`: é a política da segurança, e o nome da tool não a muda. Quem ainda cita `run_command` ou
`read_file` volta recusado, com a sugestão que aponta `malote` e `ler_arquivo`. Falso de `_run_verbo_blocking`: o
que se prova é o transporte, não o verbo.
"""
from __future__ import annotations

import os
import sys
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


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _rc_vazio() -> MagicMock:
    m = MagicMock()
    m.get.return_value = None
    m.hget.return_value = None
    m.hgetall.return_value = {}
    return m


def _fake(argv, stdin, timeout, ident, prazo=None):
    ato = argv[1] if len(argv) > 1 else ""
    exit_code = 1 if ato == "falha" else 0
    texto = f"{ato} ok\n"
    return {"exit_code": exit_code, "stdout": {"texto": texto, "bytes_total": len(texto),
                                               "truncado": False}}


class _Lote:
    """SLUGS e BINARIOS com `repo`, PDP liberado (e espiado), redis vazio, auditoria espiada."""

    def __enter__(self):
        slugs = set(s.SLUGS_SERVIDOS) | {"repo"}
        bins = {**s.BINARIOS, "repo": "/opt/bin/repo"}
        self.autoriza = MagicMock(return_value=None)
        self.audit = MagicMock()
        self._p = [patch("server.SLUGS_SERVIDOS", slugs), patch("server.BINARIOS", bins),
                   patch("server._autoriza", self.autoriza),
                   patch("server._rc", return_value=_rc_vazio()),
                   patch("server._audit", self.audit),
                   patch("server._run_verbo_blocking", side_effect=_fake)]
        for p in self._p:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self._p):
            p.stop()

    def auditados(self, **filtro):
        return [c.kwargs for c in self.audit.call_args_list
                if all(c.kwargs.get(k) == v for k, v in filtro.items())]


# --- o catalogo -------------------------------------------------------------------

@pytest.mark.anyio
async def test_tools_list_serve_malote_com_o_texto_da_pagina_e_sem_os_apelidos():
    tools = {t.name: t for t in await s.mcp.list_tools()}
    assert "malote" in tools
    assert "run_command" not in tools and "read_file" not in tools, "os apelidos saíram da porta (#4117)"
    descricao = tools["malote"].description
    assert descricao.startswith("roda vários verbos numa chamada só · use para: SEMPRE que for chamar dois ou mais")
    assert "Lote entre verbos DISTINTOS" not in descricao and "Apelido de" not in descricao
    # a frase de saída do apelido não pode estar nem aqui: o Aceite procura por ela em ops-server (por isso a conta)
    frase_de_saida = "Sai quando " + "ninguém mais a chamar"
    assert frase_de_saida not in "".join(t.description for t in tools.values())


@pytest.mark.anyio
async def test_cada_tool_de_transporte_abre_pelo_texto_da_pagina():
    tools = {t.name: t for t in await s.mcp.list_tools()}
    abre = {"ler_arquivo": "lê arquivo pelo caminho · use para: texto por linhas, PDF, EPUB",
            "write_file": "grava arquivo na bancada ou no rascunho da fita · use para: escrever mudança"}
    for nome, inicio in abre.items():
        assert tools[nome].description.startswith(inicio), nome
    if "monta_sessao" in tools:
        assert tools["monta_sessao"].description.startswith(
            "abre o expediente da cadeira · use para: PRIMEIRA AÇÃO DA CONVERSA")


# --- a auditoria grava o nome chamado ----------------------------------------------

@pytest.mark.anyio
async def test_item_despachado_grava_via_malote():
    with _Lote() as lote:
        await s.malote(commands=["repo estado", "repo ler x"])
    itens = lote.auditados(evento="verbo", tool="repo")
    assert len(itens) == 2 and {kw["via"] for kw in itens} == {"malote"}


@pytest.mark.anyio
async def test_recusa_e_lote_encadeado_gravam_tool_malote():
    with _Lote() as lote:
        await s.malote(commands=["cat x", "repo estado"], encadeado=True)
    assert lote.auditados(evento="sem_verbo", tool="malote")
    assert lote.auditados(evento="lote_encadeado", tool="malote")
    assert not lote.auditados(tool="run_command")


@pytest.mark.anyio
async def test_acao_do_pdp_segue_run_command():
    with _Lote() as lote:
        await s.malote(command="repo estado")
    assert lote.autoriza.call_args.args[1] == "run_command"


@pytest.mark.anyio
async def test_ramo_legado_grava_tool_malote():
    with _Lote() as lote, patch("server.PF_RUN_SO_VERBO", False), patch("server.PF_GATE", False), \
            patch("server._run_blocking", return_value={"exit_code": 0, "stdout": {
                "texto": "ok", "bytes_total": 2, "truncado": False}}):
        await s.malote(command="true")
    fallback = lote.auditados(evento="fallback")
    assert fallback and {kw["tool"] for kw in fallback} == {"malote"}
    assert lote.autoriza.call_args.args[:2] == ("malote", "run_command")


# --- primeiro token e recusa -------------------------------------------------------

def test_primeiro_token_malote_e_desduplicado():
    with patch("server.SLUGS_SERVIDOS", {"repo"}), patch("server.BINARIOS", {"repo": "/opt/bin/repo"}):
        argv, _, rec = s._item_de_lote("malote repo estado")
        assert rec is None and argv == ["/opt/bin/repo", "estado"]
        argv, _, rec = s._item_de_lote({"verbo": "malote", "ato": "repo", "args": ["estado"]})
        assert rec is None and argv == ["/opt/bin/repo", "estado"]


@pytest.mark.anyio
async def test_item_que_cita_o_apelido_que_saiu_volta_recusado_com_a_sugestao():
    with _Lote():
        r = await s.malote(command="run_command repo estado")
    assert r["recusado"] is True and r["verbo"] == "run_command"
    assert r["sugestao"] == "saiu da porta: chame malote, a tool que você está chamando"


def test_recusa_do_nome_sozinho_aponta_a_tool_que_ficou():
    _, _, rec = s._item_de_lote("malote")
    assert rec["sugestao"] == "é a própria tool que você está chamando"
    _, _, rec = s._item_de_lote("run_command")
    assert rec["sugestao"] == "saiu da porta: chame malote, a tool que você está chamando"
    _, _, rec = s._item_de_lote("read_file")
    assert rec["sugestao"] == "saiu da porta: chame ler_arquivo(caminho=...)"
