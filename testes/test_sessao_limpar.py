"""Suíte de testes herméticos para `sessao abrir --dry-run` e `sessao limpar` (Card #3089).

Verifica:
1. `sessao abrir --dry-run` não requer PF_SUJEITO, não toca no msg-mem nem Postgres, e retorna 0.
2. `sessao limpar --dry-run` identifica sondas (sujeito ausente ou '-') e preserva sessões reais sem apagar nada.
3. `sessao limpar` apaga chaves de sonda acumuladas (sessao, ledger, giro) e preserva estritamente sessões reais.
4. `sessao limpar` falha com exit 3 quando msg-mem está ausente.
5. Invocação via CLI (main) com `--json` e `--dry-run`.
"""

from __future__ import annotations

import importlib.util
import io
import json
import uuid
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
loader = SourceFileLoader("sessao", str(REPO_ROOT / "bin" / "sessao"))
spec = importlib.util.spec_from_loader("sessao", loader)
assert spec and spec.loader
sessao_mod = importlib.util.module_from_spec(spec)
loader.exec_module(sessao_mod)


class FakeMsgMem:
    """Dublê do Redis/msg-mem para testes herméticos."""

    def __init__(self, chaves: dict[str, str] | None = None):
        self.data: dict[str, str] = dict(chaves or {})

    def scan_iter(self, match: str = "*", count: int = 500):
        prefix = match[:-1] if match.endswith("*") else match
        for k in list(self.data.keys()):
            if k.startswith(prefix):
                yield k

    def get(self, key: str) -> str | None:
        return self.data.get(key)

    def set(self, key: str, val: str, ex: int | None = None):
        self.data[key] = val

    def exists(self, key: str) -> bool:
        return key in self.data

    def delete(self, *keys: str) -> int:
        removidos = 0
        for k in keys:
            if k in self.data:
                del self.data[k]
                removidos += 1
        return removidos


def test_sessao_abrir_dry_run_sem_sujeito():
    """`sessao abrir <cadeira> --dry-run` funciona sem PF_SUJEITO e não grava no msg-mem."""
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()
    with redirect_stdout(f):
        rc = sessao_mod.ato_abrir("fabrica", None, saida, dry_run=True)
    assert rc == 0
    out = json.loads(f.getvalue())
    assert out["registrada"] is False
    assert out["duravel"] is False
    assert out["duravel_motivo"] == "dry-run: nao gravado"
    assert out["sujeito"] == "sonda"
    assert "sessao_id" in out


def test_sessao_limpar_dry_run():
    """`sessao limpar --dry-run` apenas relata sondas e preservadas sem deletar."""
    sid_real = str(uuid.uuid4())
    sid_sonda1 = str(uuid.uuid4())
    sid_sonda2 = str(uuid.uuid4())

    mem_data = {
        f"sessao:{sid_real}": json.dumps({"sujeito": "user-1234", "cadeira": "ti", "ordem_id": "o1"}),
        f"sessao:{sid_sonda1}": json.dumps({"sujeito": "-", "cadeira": "produto", "ordem_id": "-"}),
        f"sessao:{sid_sonda2}": json.dumps({"cadeira": "ia", "ordem_id": "-"}),
        f"ledger:{sid_sonda1}": "{}",
        f"giro:{sid_sonda1}": "{}",
    }
    fake_mem = FakeMsgMem(mem_data)

    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(fake_mem, None)):
        with redirect_stdout(f):
            rc = sessao_mod.ato_limpar(dry_run=True, saida=saida)

    assert rc == 0
    res = json.loads(f.getvalue())
    assert res["dry_run"] is True
    assert res["sondas_encontradas"] == 2
    assert res["preservadas"] == 1
    assert res["apagadas"] == 0

    # Nenhuma chave foi apagada
    assert f"sessao:{sid_real}" in fake_mem.data
    assert f"sessao:{sid_sonda1}" in fake_mem.data
    assert f"sessao:{sid_sonda2}" in fake_mem.data
    assert f"ledger:{sid_sonda1}" in fake_mem.data


def test_sessao_limpar_efetivo():
    """`sessao limpar` remove chaves-sonda e preserva a chave real."""
    sid_real = str(uuid.uuid4())
    sid_sonda1 = str(uuid.uuid4())
    sid_sonda2 = str(uuid.uuid4())

    mem_data = {
        f"sessao:{sid_real}": json.dumps({"sujeito": "user-1234", "cadeira": "ti", "ordem_id": "o1"}),
        f"sessao:{sid_sonda1}": json.dumps({"sujeito": "-", "cadeira": "produto", "ordem_id": "-"}),
        f"sessao:{sid_sonda2}": json.dumps({"cadeira": "ia", "ordem_id": "-"}),
        f"ledger:{sid_sonda1}": "{}",
        f"giro:{sid_sonda1}": "{}",
    }
    fake_mem = FakeMsgMem(mem_data)

    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(fake_mem, None)):
        with redirect_stdout(f):
            rc = sessao_mod.ato_limpar(dry_run=False, saida=saida)

    assert rc == 0
    res = json.loads(f.getvalue())
    assert res["dry_run"] is False
    assert res["sondas_encontradas"] == 2
    assert res["preservadas"] == 1
    assert res["apagadas"] == 2

    # Chaves de sonda apagadas
    assert f"sessao:{sid_sonda1}" not in fake_mem.data
    assert f"sessao:{sid_sonda2}" not in fake_mem.data
    assert f"ledger:{sid_sonda1}" not in fake_mem.data
    assert f"giro:{sid_sonda1}" not in fake_mem.data

    # Chave real preservada
    assert f"sessao:{sid_real}" in fake_mem.data


def test_sessao_limpar_msgmem_ausente():
    """Se msg-mem estiver ausente, ato_limpar retorna exit 3 com mensagem de cura."""
    saida = sessao_mod.Saida(como_json=True)
    f = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(None, "ConnectionRefused")):
        with redirect_stdout(f):
            rc = sessao_mod.ato_limpar(dry_run=False, saida=saida)
    assert rc == 3
    res = json.loads(f.getvalue())
    assert "msg-mem: ausente" in res["erro"]


def test_sessao_cli_limpar_e_abrir():
    """Testa invocação de `main` com argumentos de CLI."""
    # sessao abrir --dry-run --json
    f1 = io.StringIO()
    with redirect_stdout(f1):
        rc1 = sessao_mod.main(["abrir", "fabrica", "--dry-run", "--json"])
    assert rc1 == 0
    out1 = json.loads(f1.getvalue())
    assert out1["registrada"] is False

    # sessao limpar --dry-run --json
    fake_mem = FakeMsgMem()
    f2 = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(fake_mem, None)):
        with redirect_stdout(f2):
            rc2 = sessao_mod.main(["limpar", "--dry-run", "--json"])
    assert rc2 == 0
    out2 = json.loads(f2.getvalue())
    assert out2["dry_run"] is True
