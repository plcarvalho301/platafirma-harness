"""Regressivo #4378: contrato `sessao` em hash Valkey ↔ `longjob`, `reidratar`, `ver`, `abrir` e `limpar`.

Prova com dublê de hash Valkey (sem `get`/`set` string) que:
1. `sessao longjob run` herda `PF_AGENTE` e `PF_EM_NOME_DE` da chave hash `sessao:<id>`.
2. `sessao abrir` grava a chave como hash (via `hset` + `expire`) e `sessao ver` lê o hash.
3. `reidratar` regrava a sessão como hash com TTL restante e `sessao ver` a reidrata quando ausente.
4. `sessao limpar` remove sondas armazenadas como hash e preserva sessões reais.
"""
from __future__ import annotations

import importlib.util
import io
import json
import types
import uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]

_loader = SourceFileLoader("sessao_hash_reg", str(RAIZ / "bin" / "sessao"))
_spec = importlib.util.spec_from_loader("sessao_hash_reg", _loader)
assert _spec and _spec.loader
sessao_mod = importlib.util.module_from_spec(_spec)
_loader.exec_module(sessao_mod)

_spec_r = importlib.util.spec_from_file_location("reidratar_hash_reg", str(RAIZ / "bin" / "_sessao" / "reidratar.py"))
assert _spec_r and _spec_r.loader
reidratar_mod = importlib.util.module_from_spec(_spec_r)
_spec_r.loader.exec_module(reidratar_mod)


class _HashValkey:
    """Dublê estrito de hash Valkey: recusa `get`/`set` para provar que só usa hash."""

    def __init__(self, inicial: dict[str, dict[str, str]] | None = None):
        self.hashes: dict[str, dict[str, str]] = {k: dict(v) for k, v in (inicial or {}).items()}
        self.ttls: dict[str, int] = {}

    def get(self, *_a, **_k):
        raise AssertionError("contrato hash Valkey não deve chamar GET de string")

    def set(self, *_a, **_k):
        raise AssertionError("contrato hash Valkey não deve chamar SET de string")

    def hgetall(self, key: str) -> dict[str, str]:
        return dict(self.hashes.get(key) or {})

    def hset(self, key: str, mapping: dict[str, str] | None = None, **kwargs):
        bucket = self.hashes.setdefault(key, {})
        if mapping:
            bucket.update({str(k): str(v) for k, v in mapping.items()})
        if kwargs:
            bucket.update({str(k): str(v) for k, v in kwargs.items()})
        return len(bucket)

    def expire(self, key: str, ttl: int):
        self.ttls[key] = ttl
        return True

    def exists(self, key: str) -> bool:
        return key in self.hashes

    def delete(self, *keys: str) -> int:
        return sum(1 for k in keys if self.hashes.pop(k, None) is not None)

    def scan_iter(self, match: str = "*", count: int = 500):
        prefix = match[:-1] if match.endswith("*") else match
        for k in list(self.hashes):
            if k.startswith(prefix):
                yield k


def test_longjob_herda_agente_e_em_nome_de_de_hash_valkey(monkeypatch):
    sid = str(uuid.uuid4())
    mem = _HashValkey({
        f"sessao:{sid}": {
            "sujeito": "suj-1",
            "cadeira": "engenharia",
            "agente": "revisor",
            "em_nome_de": "engenharia",
            "conta_agente": "claudinho",
        }
    })
    for var in ("PF_AGENTE", "PF_EM_NOME_DE", "PF_CONTA_AGENTE", "PF_ORIGEM_SESSAO"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("PF_SUJEITO", "suj-1")
    monkeypatch.setenv("PF_SESSAO", sid)
    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod.os, "execve") as ex:
        sessao_mod.ato_longjob(["run", "prova", "true"])
    env = ex.call_args[0][2]
    assert env["PF_AGENTE"] == "revisor"
    assert env["PF_EM_NOME_DE"] == "engenharia"
    assert env["PF_CONTA_AGENTE"] == "claudinho"


def test_abrir_ver_e_limpar_operam_sobre_hash_valkey(monkeypatch):
    mem = _HashValkey()
    monkeypatch.setenv("PF_SUJEITO", "suj-1")
    monkeypatch.setenv("PF_SESSAO_AUTORIZADA_POR", "operador-plataforma")
    buf = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
         patch.object(sessao_mod, "_vocabulario", return_value=({"engenharia": {"alias": "Gabriel", "chapeus": []}}, None)), \
         patch.object(sessao_mod, "_registra_duravel", return_value=None), \
         redirect_stdout(buf):
        rc = sessao_mod.main(["abrir", "engenharia", "--json"])
    assert rc == 0
    aberto = json.loads(buf.getvalue())
    sid = aberto["sessao_id"]
    assert f"sessao:{sid}" in mem.hashes
    assert mem.hashes[f"sessao:{sid}"]["cadeira"] == "engenharia"
    assert mem.ttls[f"sessao:{sid}"] == sessao_mod.TTL_SESSAO_S

    # `sessao ver` lê do hash
    buf_ver = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), redirect_stdout(buf_ver):
        rc_ver = sessao_mod.main(["ver", sid, "--json"])
    assert rc_ver == 0
    visto = json.loads(buf_ver.getvalue())
    assert visto["cadeira"] == "engenharia"

    # Adiciona sonda em hash e limpa preservando a sessão real
    sid_sonda = str(uuid.uuid4())
    mem.hset(f"sessao:{sid_sonda}", mapping={"sujeito": "-", "cadeira": "ti", "ordem_id": "-"})
    buf_limp = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), redirect_stdout(buf_limp):
        rc_limp = sessao_mod.main(["limpar", "--json"])
    assert rc_limp == 0
    res = json.loads(buf_limp.getvalue())
    assert res["apagadas"] == 1
    assert res["preservadas"] == 1
    assert f"sessao:{sid}" in mem.hashes
    assert f"sessao:{sid_sonda}" not in mem.hashes


def test_reidratar_grava_hash_com_ttl_restante(monkeypatch):
    sid = str(uuid.uuid4())
    mem = _HashValkey()
    aberta_em = datetime.now(timezone.utc) - timedelta(hours=1)
    row = ("engenharia", "back-end", "agy", aberta_em, None, "suj-1", "o-1")

    modulo = types.ModuleType("psycopg")

    class _Cur:
        def execute(self, *_a, **_k):
            pass

        def fetchone(self):
            return row

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    class _Conn:
        def cursor(self):
            return _Cur()

        def rollback(self):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    modulo.connect = lambda *_a, **_k: _Conn()
    monkeypatch.setitem(__import__("sys").modules, "psycopg", modulo)

    dado = reidratar_mod.reidratar(sid, mem, lambda *_a, **_k: (0, "senha-fake", ""))
    assert dado and dado["cadeira"] == "engenharia"
    assert f"sessao:{sid}" in mem.hashes
    assert mem.hashes[f"sessao:{sid}"]["sujeito"] == "suj-1"
    assert 0 < mem.ttls[f"sessao:{sid}"] <= sessao_mod.TTL_SESSAO_S
