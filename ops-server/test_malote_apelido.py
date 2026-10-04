"""`malote` e o apelido `run_command` (#3270, spec porta-so-verbo §3.7).

A porta serve as duas tools com a mesma assinatura e o mesmo retorno; a auditoria grava o
nome chamado (`tool` na recusa e no lote encadeado, `via` no item despachado), porque a
regra de saida do apelido conta os dois. A acao do PDP segue `run_command`. Falso de
`_run_verbo_blocking`: o que se prova e o transporte, nao o verbo.
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


def _sem_volatil(r):
    """O retorno sem o que muda de chamada para chamada: `lote_id` e o giro da poda."""
    if isinstance(r, dict):
        return {k: _sem_volatil(v) for k, v in r.items() if k not in ("lote_id", "giro")}
    if isinstance(r, list):
        return [_sem_volatil(x) for x in r]
    return r


# --- o catalogo -------------------------------------------------------------------

@pytest.mark.anyio
async def test_tools_list_serve_malote_e_o_apelido_com_o_mesmo_schema():
    tools = {t.name: t for t in await s.mcp.list_tools()}
    assert "malote" in tools and "run_command" in tools
    # `title` do schema e o nome da funcao (`maloteArguments`); o resto e o contrato.
    sem_titulo = lambda t: {k: v for k, v in t.inputSchema.items() if k != "title"}  # noqa: E731
    assert sem_titulo(tools["malote"]) == sem_titulo(tools["run_command"])
    assert "Apelido de `malote`" in tools["run_command"].description
    assert "Lote entre verbos DISTINTOS" in tools["malote"].description


# --- o retorno ----------------------------------------------------------------------

@pytest.mark.anyio
@pytest.mark.parametrize("encadeado", [False, True])
async def test_mesmo_lote_mesmo_retorno(encadeado):
    itens = ["repo estado", {"verbo": "repo", "ato": "ler", "args": ["x"]}, "cat x"]
    with _Lote():
        a = await s.malote(commands=itens, encadeado=encadeado)
    with _Lote():
        b = await s.run_command(commands=itens, encadeado=encadeado)
    assert _sem_volatil(a) == _sem_volatil(b)


# --- a auditoria grava o nome chamado ----------------------------------------------

@pytest.mark.anyio
@pytest.mark.parametrize("nome", ["malote", "run_command"])
async def test_item_despachado_grava_via_com_o_nome_chamado(nome):
    with _Lote() as lote:
        await getattr(s, nome)(commands=["repo estado", "repo ler x"])
    itens = lote.auditados(evento="verbo", tool="repo")
    assert len(itens) == 2 and {kw["via"] for kw in itens} == {nome}


@pytest.mark.anyio
@pytest.mark.parametrize("nome", ["malote", "run_command"])
async def test_recusa_e_lote_encadeado_gravam_tool_com_o_nome_chamado(nome):
    with _Lote() as lote:
        await getattr(s, nome)(commands=["cat x", "repo estado"], encadeado=True)
    assert lote.auditados(evento="sem_verbo", tool=nome)
    assert lote.auditados(evento="lote_encadeado", tool=nome)
    outro = "run_command" if nome == "malote" else "malote"
    assert not lote.auditados(tool=outro)


@pytest.mark.anyio
@pytest.mark.parametrize("nome", ["malote", "run_command"])
async def test_acao_do_pdp_segue_run_command(nome):
    with _Lote() as lote:
        await getattr(s, nome)(command="repo estado")
    assert lote.autoriza.call_args.args[1] == "run_command"


@pytest.mark.anyio
@pytest.mark.parametrize("nome", ["malote", "run_command"])
async def test_ramo_legado_grava_tool_com_o_nome_chamado(nome):
    with _Lote() as lote, patch("server.PF_RUN_SO_VERBO", False), patch("server.PF_GATE", False), \
            patch("server._run_blocking", return_value={"exit_code": 0, "stdout": {
                "texto": "ok", "bytes_total": 2, "truncado": False}}):
        await getattr(s, nome)(command="true")
    fallback = lote.auditados(evento="fallback")
    assert fallback and {kw["tool"] for kw in fallback} == {nome}
    assert lote.autoriza.call_args.args[:2] == (nome, "run_command")


# --- primeiro token e recusa -------------------------------------------------------

@pytest.mark.parametrize("token", ["malote", "run_command"])
def test_primeiro_token_com_qualquer_dos_nomes_e_desduplicado(token):
    with patch("server.SLUGS_SERVIDOS", {"repo"}), patch("server.BINARIOS", {"repo": "/opt/bin/repo"}):
        argv, _, rec = s._item_de_lote(f"{token} repo estado")
        assert rec is None and argv == ["/opt/bin/repo", "estado"]
        argv, _, rec = s._item_de_lote({"verbo": token, "ato": "repo", "args": ["estado"]})
        assert rec is None and argv == ["/opt/bin/repo", "estado"]


@pytest.mark.anyio
async def test_aviso_de_desduplicacao_cita_a_tool_e_o_token():
    with _Lote():
        r = await s.malote(command="run_command repo estado")
    assert r["aviso"] == "malote: primeiro token 'run_command' desduplicado com aviso"


def test_recusa_do_nome_sozinho_diz_que_e_a_propria_tool():
    _, _, rec = s._item_de_lote("malote")
    assert rec["sugestao"] == "é a própria tool que você está chamando"
    _, _, rec = s._item_de_lote("run_command")
    assert rec["sugestao"] == "é apelido de malote, a tool que você está chamando"
