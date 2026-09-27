"""Reidratação de `sessao:{id}` a partir de `sessao.sessao` (Postgres, durável) quando
a chave efêmera some do msg-mem (card #3145, Onda 1 Frente E; decisão 1 do plano).

Cobre:
1. `sessao ver`: chave presente -> não consulta o "banco" (reidratar não é chamado).
2. `bin/_sessao/reidratar.reidratar`: ausente + linha aberta e válida -> reidrata,
   regrava `sessao:{id}` com o TTL que resta.
3. ausente + sem linha (nunca existiu) -> não existe.
4. ausente + linha vencida (fora da janela de TTL_SESSAO_S contada de `aberta_em`,
   arq:0091 §3) -> não existe.
5. ausente + linha com `encerrada_em` preenchida (migração 0092 -- decisão do
   planejador sobre o item 5: sessão encerrada de propósito não reidrata) -> não
   existe, mesmo dentro do TTL.
6. ausente + coluna `encerrada_em` ainda não existe (migração 0092 não aplicada
   depois da promoção) -> tolera, comportamento de antes da 0092 (reidrata igual).
7. `sessao ver` integra a reidratação: ausente+válida reidrata (exit 0); ajudante
   ausente preserva o comportamento atual (exit 1, "não existe").
8. `sessao encerrar`/`sessao limpar` gravam `encerrada_em=now()` em `sessao.sessao`
   (melhor esforço, via `_marca_encerrada`) além do DEL de sempre no msg-mem; banco
   mudo não trava o ato.
9. `sessao longjob <args>` -> execve de `bin/_sessao/longjob` (card #3145, item 5).

Isolado pelo conftest (redis-cli/psql são delatores): tudo por camadas falsas
injetáveis, como os testes atuais de sessao (testes/test_sessao_limpar.py).
"""
from __future__ import annotations

import importlib.util
import io
import json
import sys
import types
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

_loader = SourceFileLoader("sessao", str(REPO_ROOT / "bin" / "sessao"))
_spec = importlib.util.spec_from_loader("sessao", _loader)
assert _spec and _spec.loader
sessao_mod = importlib.util.module_from_spec(_spec)
_loader.exec_module(sessao_mod)

_spec_r = importlib.util.spec_from_file_location(
    "reidratar", str(REPO_ROOT / "bin" / "_sessao" / "reidratar.py"))
assert _spec_r and _spec_r.loader
reidratar_mod = importlib.util.module_from_spec(_spec_r)
_spec_r.loader.exec_module(reidratar_mod)


class FakeMsgMem:
    """Dublê do Redis/msg-mem (mesmo shape de testes/test_sessao_limpar.py)."""

    def __init__(self, chaves: dict[str, str] | None = None):
        self.data: dict[str, str] = dict(chaves or {})
        self.ex_gravado: dict[str, int] = {}

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, val: str, ex: int | None = None):
        self.data[key] = val
        if ex is not None:
            self.ex_gravado[key] = ex

    def exists(self, key: str) -> bool:
        return key in self.data

    def delete(self, *keys: str) -> int:
        removidos = 0
        for k in keys:
            if k in self.data:
                del self.data[k]
                removidos += 1
        return removidos

    def scan_iter(self, match: str = "*", count: int = 500):
        prefix = match[:-1] if match.endswith("*") else match
        for k in list(self.data.keys()):
            if k.startswith(prefix):
                yield k


def _roda_seg_ok(argv, timeout=10, stdin=None):
    assert argv[:3] == ["seg", "segredo", "ler"]
    return 0, "senha-fake\n", ""


def _roda_seg_falha(argv, timeout=10, stdin=None):
    return 3, "", "segredo ausente"


def _fake_psycopg(row):
    """Módulo `psycopg` de mentira: `connect(...)` devolve um cursor cujo `fetchone`
    sempre devolve `row` (ou None). Suficiente para a única query que `reidratar` faz."""
    modulo = types.ModuleType("psycopg")

    class _Cursor:
        def execute(self, *a, **k):
            pass

        def fetchone(self):
            return row

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Conexao:
        def cursor(self):
            return _Cursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def connect(dsn, connect_timeout=3):
        return _Conexao()

    modulo.connect = connect
    return modulo


def _fake_psycopg_coluna_ausente(row_sem_encerrada_em):
    """Simula a migração 0092 ainda não aplicada: a query com `encerrada_em` levanta
    (coluna inexistente), a query antiga (4 colunas) funciona -- `reidratar()` precisa
    tolerar isso e cair na forma antiga."""
    modulo = types.ModuleType("psycopg")

    class _Cursor:
        def __init__(self):
            self.chamadas = 0

        def execute(self, sql, *a, **k):
            self.chamadas += 1
            if "encerrada_em" in sql and "SELECT" in sql:
                raise RuntimeError('column "encerrada_em" does not exist')

        def fetchone(self):
            return row_sem_encerrada_em

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Conexao:
        def __init__(self):
            self._cursor = _Cursor()

        def cursor(self):
            return self._cursor

        def rollback(self):
            pass

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def connect(dsn, connect_timeout=3):
        return _Conexao()

    modulo.connect = connect
    return modulo


def _fake_psycopg_update_capturado(capturas: list):
    """Módulo `psycopg` de mentira para `_marca_encerrada`: registra cada UPDATE
    (sql, params) em `capturas`."""
    modulo = types.ModuleType("psycopg")

    class _Cursor:
        def execute(self, sql, params=None):
            capturas.append((sql, params))

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class _Conexao:
        def cursor(self):
            return _Cursor()

        def commit(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def connect(dsn, connect_timeout=3):
        return _Conexao()

    modulo.connect = connect
    return modulo


# ---------------------------------------------------------------- reidratar() puro
def test_reidratar_ausente_linha_valida_regrava_com_ttl_restante(monkeypatch):
    sid = str(uuid.uuid4())
    aberta_em = datetime.now(timezone.utc) - timedelta(hours=1)  # 47h de TTL ainda restam
    # encerrada_em None -- nunca encerrada; sujeito presente (migracao 0094, card #3145)
    row = ("ti", "devops", "code", aberta_em, None, "user-abc")
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg(row))
    rc_mem = FakeMsgMem()

    ch = reidratar_mod.reidratar(sid, rc_mem, _roda_seg_ok)

    assert ch is not None
    assert ch["cadeira"] == "ti"
    assert ch["chapeu"] == "devops"
    assert ch["superficie"] == "code"
    assert ch["origem"] == "reidratada"
    assert ch["sujeito"] == "user-abc"
    # regravou sessao:{id} no msg-mem
    assert f"sessao:{sid}" in rc_mem.data
    gravado = json.loads(rc_mem.data[f"sessao:{sid}"])
    assert gravado["cadeira"] == "ti"
    assert gravado["sujeito"] == "user-abc"
    # TTL que resta: ~47h, nunca os 48h inteiros de novo (nao reinicia a janela)
    restante = rc_mem.ex_gravado[f"sessao:{sid}"]
    assert 46 * 3600 < restante < 48 * 3600


def test_reidratar_ausente_linha_valida_sem_sujeito_nao_inclui_chave(monkeypatch):
    """Linha durável gravada antes da migração 0094 (ou sessão sem sujeito):
    `sujeito IS NULL` -- `ch` sai SEM a chave `sujeito`, nunca com valor fabricado
    (decisão 9: nada de fallback para cadeira/USER/valor fixo)."""
    sid = str(uuid.uuid4())
    aberta_em = datetime.now(timezone.utc) - timedelta(hours=1)
    row = ("ti", "devops", "code", aberta_em, None, None)  # sujeito None
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg(row))
    rc_mem = FakeMsgMem()

    ch = reidratar_mod.reidratar(sid, rc_mem, _roda_seg_ok)

    assert ch is not None
    assert "sujeito" not in ch


def test_reidratar_ausente_sem_linha_nao_existe(monkeypatch):
    sid = str(uuid.uuid4())
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg(None))
    rc_mem = FakeMsgMem()

    ch = reidratar_mod.reidratar(sid, rc_mem, _roda_seg_ok)

    assert ch is None
    assert rc_mem.data == {}


def test_reidratar_ausente_vencida_nao_existe(monkeypatch):
    sid = str(uuid.uuid4())
    aberta_em = datetime.now(timezone.utc) - timedelta(hours=50)  # > TTL_SESSAO_S (48h)
    row = ("ti", None, "chat", aberta_em, None, "user-x")
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg(row))
    rc_mem = FakeMsgMem()

    ch = reidratar_mod.reidratar(sid, rc_mem, _roda_seg_ok)

    assert ch is None
    assert rc_mem.data == {}


def test_reidratar_ausente_encerrada_nao_existe(monkeypatch):
    """Linha aberta, dentro do TTL, mas `encerrada_em` preenchida (sessao encerrar|limpar
    já rodou): não reidrata -- decisão do planejador sobre o item 5."""
    sid = str(uuid.uuid4())
    aberta_em = datetime.now(timezone.utc) - timedelta(hours=1)  # bem dentro do TTL
    encerrada_em = datetime.now(timezone.utc) - timedelta(minutes=5)
    row = ("ti", None, "chat", aberta_em, encerrada_em, "user-x")
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg(row))
    rc_mem = FakeMsgMem()

    ch = reidratar_mod.reidratar(sid, rc_mem, _roda_seg_ok)

    assert ch is None
    assert rc_mem.data == {}


def test_reidratar_coluna_encerrada_em_ausente_comportamento_atual(monkeypatch):
    """Migrações 0092/0094 ainda não aplicadas (colunas `encerrada_em`/`sujeito` não
    existem): tolera o erro, cai na consulta antiga (4 colunas) e reidrata normalmente
    -- comportamento de antes das duas, nunca uma exceção. Sem a coluna, também sem
    sujeito no resultado -- nada de fabricar valor (decisão 9)."""
    sid = str(uuid.uuid4())
    aberta_em = datetime.now(timezone.utc) - timedelta(hours=1)
    row_sem_encerrada_em = ("ti", "devops", "code", aberta_em)
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_coluna_ausente(row_sem_encerrada_em))
    rc_mem = FakeMsgMem()

    ch = reidratar_mod.reidratar(sid, rc_mem, _roda_seg_ok)

    assert ch is not None
    assert ch["cadeira"] == "ti"
    assert "sujeito" not in ch
    assert f"sessao:{sid}" in rc_mem.data


def test_reidratar_sem_senha_nao_existe(monkeypatch):
    sid = str(uuid.uuid4())
    aberta_em = datetime.now(timezone.utc)
    row = ("ti", None, "chat", aberta_em, None)
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg(row))
    rc_mem = FakeMsgMem()

    ch = reidratar_mod.reidratar(sid, rc_mem, _roda_seg_falha)

    assert ch is None


def test_reidratar_sem_psycopg_nao_existe(monkeypatch):
    """psycopg ausente do venv (ex.: chamado por engano de um processo sem a
    dependência): o módulo não trava, devolve None -- mesmo shape de qualquer outro
    desvio."""
    sid = str(uuid.uuid4())
    monkeypatch.setitem(sys.modules, "psycopg", None)  # simula ImportError no import
    rc_mem = FakeMsgMem()

    ch = reidratar_mod.reidratar(sid, rc_mem, _roda_seg_ok)

    assert ch is None


# ---------------------------------------------------------------- reidratar_via_verbo()
def test_reidratar_via_verbo_devolve_json_do_sessao_ver():
    sid = str(uuid.uuid4())
    esperado = {"sessao_id": sid, "cadeira": "produto", "ordem_id": "-"}

    def fake_run(argv, capture_output, text, timeout, env):
        assert argv[1:3] == ["ver", sid]
        assert "--json" in argv
        import subprocess as _sp
        return _sp.CompletedProcess(argv, returncode=0, stdout=json.dumps(esperado), stderr="")

    with patch("subprocess.run", side_effect=fake_run):
        ch = reidratar_mod.reidratar_via_verbo(sid, "/bin/sessao", {})
    assert ch == esperado


def test_reidratar_via_verbo_exit_nao_zero_nao_existe():
    sid = str(uuid.uuid4())

    def fake_run(argv, capture_output, text, timeout, env):
        import subprocess as _sp
        return _sp.CompletedProcess(argv, returncode=1, stdout="", stderr="nao existe")

    with patch("subprocess.run", side_effect=fake_run):
        ch = reidratar_mod.reidratar_via_verbo(sid, "/bin/sessao", {})
    assert ch is None


# ---------------------------------------------------------------- `sessao ver` integrado
def test_ver_chave_presente_nao_consulta_o_banco():
    sid = str(uuid.uuid4())
    mem = FakeMsgMem({f"sessao:{sid}": json.dumps({"cadeira": "ti", "ordem_id": "o1"})})
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_reidratar_mod") as reidratar_espiao:
        with redirect_stdout(f):
            rc = sessao_mod.ato_ver(sid, saida)

    assert rc == 0
    reidratar_espiao.reidratar.assert_not_called()
    out = json.loads(f.getvalue())
    assert out["cadeira"] == "ti"


def test_ver_ausente_reidrata_e_sai_0():
    sid = str(uuid.uuid4())
    mem = FakeMsgMem()  # sessao:{sid} ausente
    reidratado = {"cadeira": "dados", "chapeu": None, "superficie": "code",
                  "ordem_id": "-", "aberto_em": "2026-09-25T10:00:00+00:00",
                  "origem": "reidratada"}
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_reidratar_mod") as reidratar_espiao:
        reidratar_espiao.reidratar.return_value = reidratado
        with redirect_stdout(f):
            rc = sessao_mod.ato_ver(sid, saida)

    assert rc == 0
    reidratar_espiao.reidratar.assert_called_once()
    out = json.loads(f.getvalue())
    assert out["cadeira"] == "dados"
    assert out["origem"] == "reidratada"


def test_ver_ausente_sem_ajudante_mantem_comportamento_atual():
    """Ajudante indisponível (import falhou lá no topo, `_reidratar_mod is None`):
    `ver` continua exatamente como hoje -- exit 1, "não existe"."""
    sid = str(uuid.uuid4())
    mem = FakeMsgMem()
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_reidratar_mod", None):
        with redirect_stdout(f):
            rc = sessao_mod.ato_ver(sid, saida)

    assert rc == 1
    out = json.loads(f.getvalue())
    assert "nao existe" in out["erro"]


def test_ver_ausente_reidratar_devolve_none_mantem_nao_existe():
    sid = str(uuid.uuid4())
    mem = FakeMsgMem()
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_reidratar_mod") as reidratar_espiao:
        reidratar_espiao.reidratar.return_value = None
        with redirect_stdout(f):
            rc = sessao_mod.ato_ver(sid, saida)

    assert rc == 1


# ---------------------------------------------------------------- _registra_duravel backfill de sujeito
def test_registra_duravel_grava_sujeito_em_linha_nova(monkeypatch):
    capturas: list = []
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_update_capturado(capturas))
    with patch.object(sessao_mod, "_senha_pg", return_value=("senha-fake", None)):
        motivo = sessao_mod._registra_duravel("sid-1", "ti", "jose-123")

    assert motivo is None
    assert len(capturas) == 1
    sql, params = capturas[0]
    assert "ON CONFLICT (sessao_id) DO UPDATE SET" in sql
    assert "COALESCE(sessao.sessao.sujeito, EXCLUDED.sujeito)" in sql
    assert params == ("sid-1", "ti", None, sessao_mod._superficie(), "jose-123")


def test_registra_duravel_backfill_nunca_sobrescreve_via_coalesce(monkeypatch):
    """A prova de que uma linha JA com sujeito nao troca de valor mora no SQL (COALESCE
    do lado da linha existente primeiro) -- aqui so confere que TODA chamada (mesmo
    reabertura, sujeito=None) manda o mesmo UPSERT, nunca um DO NOTHING que deixaria a
    linha antiga presa para sempre sem sujeito."""
    capturas: list = []
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_update_capturado(capturas))
    with patch.object(sessao_mod, "_senha_pg", return_value=("senha-fake", None)):
        sessao_mod._registra_duravel("sid-2", "ti", None)

    assert len(capturas) == 1
    sql, params = capturas[0]
    assert "DO NOTHING" not in sql
    assert params[-1] is None


# ---------------------------------------------------------------- ato_abrir: reabertura backfilla sujeito
def test_ato_abrir_reabertura_backfilla_sujeito_ausente(monkeypatch):
    """Chave viva reidratada de um registro anterior a migracao 0094 (sem sujeito):
    reabrir com PF_SUJEITO valido preenche a chave, sem tocar cadeira/ordem_id do
    jeito errado nem recunhar a sessao (card #3145, deadlock do bootstrap)."""
    sid = str(uuid.uuid4())
    mem = FakeMsgMem({
        f"sessao:{sid}": json.dumps({"cadeira": "ti", "ordem_id": "o-velho",
                                     "origem": "reidratada"}),
    })
    monkeypatch.setenv("PF_SUJEITO", "jose-123")
    capturas: list = []
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_update_capturado(capturas))
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_vocabulario", return_value=({"ti": {}}, None)), \
         patch.object(sessao_mod, "_decidir", return_value=(0, {"regra": "default", "plano": "p1"}, "")), \
         patch.object(sessao_mod, "_senha_pg", return_value=("senha-fake", None)):
        with redirect_stdout(f):
            rc = sessao_mod.ato_abrir("ti", sid, saida)

    assert rc == 0
    gravado = json.loads(mem.data[f"sessao:{sid}"])
    assert gravado["sujeito"] == "jose-123"
    assert gravado["cadeira"] == "ti"  # reabertura nao troca cadeira


def test_ato_abrir_reabertura_nao_sobrescreve_sujeito_existente(monkeypatch):
    """Chave viva JA com sujeito: reabrir com um PF_SUJEITO diferente nao troca --
    identidade nao muda por reabertura (mesma regra que ja valia para cadeira)."""
    sid = str(uuid.uuid4())
    mem = FakeMsgMem({
        f"sessao:{sid}": json.dumps({"cadeira": "ti", "ordem_id": "o-velho",
                                     "sujeito": "sujeito-original"}),
    })
    monkeypatch.setenv("PF_SUJEITO", "outro-sujeito")
    capturas: list = []
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_update_capturado(capturas))
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_vocabulario", return_value=({"ti": {}}, None)), \
         patch.object(sessao_mod, "_decidir", return_value=(0, {"regra": "default", "plano": "p1"}, "")), \
         patch.object(sessao_mod, "_senha_pg", return_value=("senha-fake", None)):
        with redirect_stdout(f):
            rc = sessao_mod.ato_abrir("ti", sid, saida)

    assert rc == 0
    gravado = json.loads(mem.data[f"sessao:{sid}"])
    assert gravado["sujeito"] == "sujeito-original"


# ---------------------------------------------------------------- encerrar/limpar marcam encerrada_em
def test_ato_encerrar_marca_encerrada_em(monkeypatch):
    sid = str(uuid.uuid4())
    mem = FakeMsgMem({
        f"sessao:{sid}": json.dumps({"cadeira": "ti", "ordem_id": "o1"}),
        f"ledger:{sid}": "{}", f"giro:{sid}": "{}",
    })
    capturas: list = []
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_update_capturado(capturas))
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_senha_pg", return_value=("senha-fake", None)):
        with redirect_stdout(f):
            rc = sessao_mod.ato_encerrar(sid, saida)

    assert rc == 0
    assert len(capturas) == 1
    sql, params = capturas[0]
    assert "UPDATE sessao.sessao" in sql and "encerrada_em" in sql
    assert params == ([sid],)


def test_ato_limpar_marca_encerrada_em_so_para_apagadas(monkeypatch):
    sid_sonda = str(uuid.uuid4())
    sid_real = str(uuid.uuid4())
    mem = FakeMsgMem({
        f"sessao:{sid_sonda}": json.dumps({"sujeito": "-", "cadeira": "produto", "ordem_id": "-"}),
        f"sessao:{sid_real}": json.dumps({"sujeito": "user-1", "cadeira": "ti", "ordem_id": "o1"}),
    })
    capturas: list = []
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_update_capturado(capturas))
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_senha_pg", return_value=("senha-fake", None)):
        with redirect_stdout(f):
            rc = sessao_mod.ato_limpar(dry_run=False, saida=saida)

    assert rc == 0
    assert len(capturas) == 1
    _sql, params = capturas[0]
    assert params == ([sid_sonda],)  # só a sonda apagada, nunca a sessao real preservada


def test_ato_limpar_dry_run_nao_marca_encerrada_em(monkeypatch):
    sid_sonda = str(uuid.uuid4())
    mem = FakeMsgMem({
        f"sessao:{sid_sonda}": json.dumps({"sujeito": "-", "cadeira": "produto", "ordem_id": "-"}),
    })
    capturas: list = []
    monkeypatch.setitem(sys.modules, "psycopg", _fake_psycopg_update_capturado(capturas))
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)):
        with redirect_stdout(f):
            rc = sessao_mod.ato_limpar(dry_run=True, saida=saida)

    assert rc == 0
    assert capturas == []


def test_ato_encerrar_banco_mudo_nao_trava(monkeypatch, capsys):
    """`_marca_encerrada` falha (psycopg ausente): `encerrar` segue igual, só avisa em
    stderr -- nada de exit novo por isso (decisão do planejador)."""
    sid = str(uuid.uuid4())
    mem = FakeMsgMem({f"sessao:{sid}": json.dumps({"cadeira": "ti", "ordem_id": "o1"})})
    monkeypatch.setitem(sys.modules, "psycopg", None)  # ImportError simulado
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()

    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)):
        with redirect_stdout(f):
            rc = sessao_mod.ato_encerrar(sid, saida)

    assert rc == 0
    out = json.loads(f.getvalue())
    assert out["encerrada"] == sid
    assert "encerrada_em nao gravada" in capsys.readouterr().err


# ---------------------------------------------------------------- longjob (item 5)
def test_sessao_longjob_execve_caminho_novo():
    alvo_esperado = str(REPO_ROOT / "bin" / "_sessao" / "longjob")
    assert Path(alvo_esperado).is_file(), "bin/_sessao/longjob precisa existir (mv de bin/longjob)"

    with patch.object(sessao_mod.os, "execve") as execve_espiao:
        sessao_mod.ato_longjob(["run", "nome", "true"])

    execve_espiao.assert_called_once()
    argv_chamado = execve_espiao.call_args[0]
    assert argv_chamado[0] == alvo_esperado
    assert argv_chamado[1] == [alvo_esperado, "run", "nome", "true"]
