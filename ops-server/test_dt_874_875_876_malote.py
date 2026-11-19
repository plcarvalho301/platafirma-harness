"""Regressão dos DTs 874, 875 e 876 do verbo malote (schema plano, inteiro, auditoria/tateio/isError, brutos e pipe)."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

RAIZ = Path(__file__).resolve().parents[1]
os.environ.setdefault("PF_HARNESS", str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import lote as _lote  # noqa: E402
import server as s  # noqa: E402


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _carrega_metrica():
    caminho = RAIZ / "bin" / "metrica"
    spec = importlib.util.spec_from_loader(
        "metrica_dt875",
        importlib.machinery.SourceFileLoader("metrica_dt875", str(caminho)),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _LoteFake:
    def __init__(self, fake_run=None, fake_serve=None):
        self.audits: list[dict] = []
        self.serve_calls: list[dict] = []
        self.fake_run = fake_run or (
            lambda argv, stdin, timeout, ident, prazo=None: {
                "exit_code": 0,
                "stdout": {"texto": "ok\n", "bytes_total": 3, "truncado": False},
            }
        )
        self.fake_serve = fake_serve

    def __enter__(self):
        def _record_audit(**kw):
            self.audits.append(kw)

        def _record_serve(r, **kw):
            self.serve_calls.append(kw)
            if self.fake_serve:
                return self.fake_serve(r, **kw)
            return r

        self._patches = [
            patch("server.SLUGS_SERVIDOS", {"repo", "release"}),
            patch("server.BINARIOS", {"repo": "/opt/bin/repo", "release": "/opt/bin/release"}),
            patch("server._autoriza", return_value=None),
            patch("server._audit", side_effect=_record_audit),
            patch("server._serve", side_effect=_record_serve),
            patch("server._run_verbo_blocking", side_effect=self.fake_run),
        ]
        for p in self._patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in reversed(self._patches):
            p.stop()


# --------------------------------------------------------------------------- DT-874
@pytest.mark.anyio
async def test_dt874_schema_malote_plano_tipado_sem_cwd_e_com_inteiro():
    tools = {t.name: t for t in await s.mcp.list_tools()}
    esquema = s._esquema_plano(tools["malote"].inputSchema)
    props = esquema["properties"]
    assert "cwd" not in props
    assert props["inteiro"]["type"] == "boolean"
    cmd_items = props["commands"]["items"]
    assert cmd_items["type"] == "object"
    assert "anyOf" not in cmd_items
    for campo in ("verbo", "ato", "args", "stdin", "stdin_de", "inteiro"):
        assert campo in cmd_items["properties"]


@pytest.mark.anyio
async def test_dt874_malote_propaga_inteiro_para_serve_esquece():
    with _LoteFake() as lote:
        await s.malote(
            commands=[
                {"verbo": "repo", "ato": "estado"},
                {"verbo": "repo", "ato": "ler", "args": ["x"], "inteiro": True},
            ]
        )
    assert [c["esquece"] for c in lote.serve_calls] == [False, True]

    with _LoteFake() as lote2:
        await s.malote(commands=["repo estado"], inteiro=True)
    assert lote2.serve_calls[0]["esquece"] is True


# --------------------------------------------------------------------------- DT-875
@pytest.mark.anyio
async def test_dt875_malote_nao_encadeado_audita_evento_lote():
    with _LoteFake() as lote:
        await s.malote(commands=["repo estado", "repo ler x"])
    ev_lote = [a for a in lote.audits if a.get("evento") == "lote" and a.get("tool") == "malote"]
    ev_itens = [a for a in lote.audits if a.get("evento") == "verbo" and a.get("via") == "malote"]
    assert len(ev_lote) == 1
    assert ev_lote[0]["exit_code"] == 0
    assert ev_lote[0]["lote_n"] == 2
    assert len(ev_itens) == 2


def test_dt875_deve_marcar_erro_em_lote_100pct_falho_e_em_andamento():
    # Lote não encadeado 100% falho => isError=True
    assert s._deve_marcar_erro({"lote": [{"exit_code": 2}, {"recusado": True}]}) is True
    # Lote não encadeado com sucesso parcial => isError=False
    assert s._deve_marcar_erro({"lote": [{"exit_code": 0}, {"exit_code": 2}]}) is False
    # Lote encadeado parado por em_andamento => isError=False
    cadeia = _lote.resumo_cadeia(
        [{"em_andamento": True, "motivo": "segue no host"}, {"nao_rodou": True}],
        parou_em=0,
    )
    assert cadeia["em_andamento"] is True
    assert cadeia["exit"] is None
    assert s._deve_marcar_erro({"cadeia": cadeia}) is False


def test_dt875_metrica_tateio_pareia_acerto_de_malote_sem_null():
    m = _carrega_metrica()
    linhas = [
        {"ts": "2026-11-19T10:00:01Z", "ordem_id": "o1", "cadeira": "engenharia",
         "tool": "malote", "evento": "sem_verbo", "verbo": "cat", "lote_id": "l1"},
        {"ts": "2026-11-19T10:00:02Z", "ordem_id": "o1", "cadeira": "engenharia",
         "tool": "repo", "ato": "ler", "via": "malote", "evento": "verbo", "exit_code": 0, "lote_id": "l2"},
        {"ts": "2026-11-19T10:00:02Z", "ordem_id": "o1", "cadeira": "engenharia",
         "tool": "malote", "evento": "lote", "exit_code": 0, "lote_id": "l2"},
    ]

    class _Fonte:
        def linhas(self, _dia):
            return linhas

    giros = m.giros_do_dia(_Fonte(), "2026-11-19")
    res = m.tateio(giros, m._por_par(giros))
    gasto = res["gramatica"]["gasto_ate_acerto"]
    assert len(gasto) == 1
    assert gasto[0]["tool"] == "malote"
    assert gasto[0]["acertou_em"] is not None
    assert "l2" in gasto[0]["acertou_em"]


# --------------------------------------------------------------------------- DT-876
@pytest.mark.anyio
async def test_dt876_nao_le_arquivo_cru_sem_pipe_fontes(tmp_path):
    cru = tmp_path / "grande.txt"
    cru.write_text("X" * 60000, encoding="utf-8")

    def fake_run(argv, stdin, timeout, ident, prazo=None):
        return {
            "exit_code": 0,
            "stdout": {"texto": "X" * 100, "bytes_total": 60000, "truncado": True, "cru": str(cru)},
        }

    with _LoteFake(fake_run=fake_run), patch.object(Path, "read_text", side_effect=AssertionError("nao deveria ler cru")):
        r = await s.malote(commands=["repo estado", "repo ler a"])
    assert len(r["lote"]) == 2
    assert r["lote"][0]["exit_code"] == 0


@pytest.mark.anyio
async def test_dt876_pipe_recusa_excesso_de_teto_de_memoria(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "PIPE_BRUTO_MAX", 100)
    cru = tmp_path / "enorme.txt"
    cru.write_text("A" * 200, encoding="utf-8")

    def fake_run(argv, stdin, timeout, ident, prazo=None):
        return {
            "exit_code": 0,
            "stdout": {"texto": "A" * 50, "bytes_total": 200, "truncado": True, "cru": str(cru)},
        }

    with _LoteFake(fake_run=fake_run):
        r = await s.malote(commands=[
            {"verbo": "repo", "ato": "ler", "args": ["a"]},
            {"verbo": "release", "ato": "migrar", "stdin_de": 0},
        ])
    assert r["lote"][1]["recusado"] is True
    assert "teto de pipe" in r["lote"][1]["motivo"]


@pytest.mark.anyio
async def test_dt876_stdin_de_em_nao_encadeado_recusa_produtor_falho_ou_interrompido():
    def fake_run_exit2(argv, stdin, timeout, ident, prazo=None):
        if argv[0].endswith("repo"):
            return {"exit_code": 2, "stdout": {"texto": "", "bytes_total": 0, "truncado": False}}
        raise AssertionError("consumidor nao deveria rodar quando produtor saiu 2")

    with _LoteFake(fake_run=fake_run_exit2):
        r = await s.malote(commands=[
            {"verbo": "repo", "ato": "ler", "args": ["x"]},
            {"verbo": "release", "ato": "migrar", "stdin": {"de": 0}},
        ], encadeado=False)
    assert r["lote"][1]["recusado"] is True
    assert "falhou com exit 2" in r["lote"][1]["motivo"]

    def fake_run_sigterm(argv, stdin, timeout, ident, prazo=None):
        if argv[0].endswith("repo"):
            return {
                "exit_code": -15,
                "interrompido": True,
                "stdout": {"texto": "parcial", "bytes_total": 7, "truncado": False},
            }
        raise AssertionError("consumidor nao deveria rodar quando produtor foi interrompido")

    with _LoteFake(fake_run=fake_run_sigterm):
        r2 = await s.malote(commands=[
            {"verbo": "repo", "ato": "ler", "args": ["x"]},
            {"verbo": "release", "ato": "migrar", "stdin": {"de": 0}},
        ], encadeado=False)
    assert r2["lote"][1]["recusado"] is True
    assert "interrompido" in r2["lote"][1]["motivo"]
