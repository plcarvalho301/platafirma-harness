"""`sessao abrir --agente/--em-nome-de/--conta`: a sessao filha do agente guarda quem e ele (card #3156).

Hermetico, como test_sessao_origem.py: msg-mem, politica, vocabulario e Postgres sao dubles. O que se
trava: os tres atributos entram na chave e no retorno, vao juntos, so descrevem (nao travam nem concedem),
e nunca trocam os ja gravados.
"""

from __future__ import annotations

import importlib.util
import io
import json
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

ORQ = "11111111-1111-4111-8111-111111111111"
FILHA = "22222222-2222-4222-8222-222222222222"
AGENTE = ("--agente", "varredor", "--em-nome-de", "engenharia", "--conta", "claudinho")


class FakeMsgMem:
    def __init__(self, chaves: dict[str, str] | None = None):
        self.data: dict[str, str] = dict(chaves or {})

    def scan_iter(self, match: str = "*", count: int = 500):
        prefix = match[:-1] if match.endswith("*") else match
        for k in list(self.data):
            if k.startswith(prefix):
                yield k

    def get(self, key):
        return self.data.get(key)

    def set(self, key, val, ex=None):
        self.data[key] = val

    def exists(self, key):
        return key in self.data

    def delete(self, *keys):
        return sum(1 for k in keys if self.data.pop(k, None) is not None)


@pytest.fixture
def mem():
    return FakeMsgMem({f"sessao:{ORQ}": json.dumps({"sujeito": "suj-1", "cadeira": "engenharia", "ordem_id": "o1",
                                                   "origem": "sessao abrir"})})


@pytest.fixture
def abre(mem, monkeypatch):
    monkeypatch.setenv("PF_SUJEITO", "suj-1")

    def _abre(*argv):
        f = io.StringIO()
        with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
                patch.object(sessao_mod, "_vocabulario",
                             return_value=({"engenharia": {"alias": "Gabriel", "chapeus": []}}, None)), \
                patch.object(sessao_mod, "_decidir", return_value=(0, {"regra": "r", "plano": "p"}, "")), \
                patch.object(sessao_mod, "_registra_duravel", return_value=None), \
                redirect_stdout(f):
            rc = sessao_mod.main(["abrir", "engenharia", "--json", *argv])
        saida = f.getvalue().strip()
        return rc, (json.loads(saida) if saida else None)

    return _abre


def _chave(mem, sid):
    return json.loads(mem.data[f"sessao:{sid}"])


def test_atributos_do_agente_entram_na_chave_e_no_retorno(abre, mem):
    rc, out = abre("--origem", ORQ, *AGENTE)
    assert rc == 0
    for k, v in (("agente", "varredor"), ("em_nome_de", "engenharia"), ("conta_agente", "claudinho")):
        assert out[k] == v and _chave(mem, out["sessao_id"])[k] == v
    assert out["origem_sessao"] == ORQ
    assert _chave(mem, out["sessao_id"])["sujeito"] == "suj-1", "a pessoa segue sendo quem abriu"


def test_sem_os_flags_a_chave_fica_como_antes(abre, mem):
    rc, out = abre("--origem", ORQ)
    assert rc == 0
    assert not {"agente", "em_nome_de", "conta_agente"} & set(out)
    assert not {"agente", "em_nome_de", "conta_agente"} & set(_chave(mem, out["sessao_id"]))


@pytest.mark.parametrize("flags", [
    ("--agente", "varredor"),
    ("--agente", "varredor", "--em-nome-de", "engenharia"),
    ("--em-nome-de", "engenharia", "--conta", "claudinho"),
    ("--agente", "Varredor", "--em-nome-de", "engenharia", "--conta", "claudinho"),
    ("--agente", "a b", "--em-nome-de", "engenharia", "--conta", "claudinho"),
])
def test_atributos_incompletos_ou_fora_do_molde_saem_2_e_nao_gravam(abre, mem, flags):
    antes = set(mem.data)
    rc, out = abre("--origem", ORQ, *flags)
    assert rc == 2
    assert "vao juntos" in out["erro"]
    assert set(mem.data) == antes


def test_reabrir_nao_troca_os_atributos_ja_gravados(abre, mem):
    rc, out = abre("--sessao-id", FILHA, "--origem", ORQ, *AGENTE)
    assert rc == 0 and out["sessao_id"] == FILHA
    rc, _ = abre("--sessao-id", FILHA, "--origem", ORQ, "--agente", "outro", "--em-nome-de", "ia", "--conta", "jaiminho")
    assert rc == 0
    assert _chave(mem, FILHA)["agente"] == "varredor" and _chave(mem, FILHA)["conta_agente"] == "claudinho"


def test_dry_run_mostra_os_atributos_e_nao_grava(abre, mem):
    antes = dict(mem.data)
    rc, out = abre("--dry-run", "--origem", ORQ, *AGENTE)
    assert rc == 0 and out["agente"] == "varredor"
    assert mem.data == antes


def test_ver_mostra_os_atributos(abre, mem):
    _, out = abre("--origem", ORQ, *AGENTE)
    f = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), redirect_stdout(f):
        assert sessao_mod.main(["ver", out["sessao_id"]]) == 0
    texto = f.getvalue()
    assert "agente: varredor" in texto and "em_nome_de: engenharia" in texto and "conta_agente: claudinho" in texto
