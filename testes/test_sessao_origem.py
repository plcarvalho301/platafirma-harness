"""`sessao abrir --origem`: a sessao filha guarda a sessao de quem chamou (card #3158).

Hermetico: msg-mem, politica (`acesso decidir`), vocabulario (`persona foto`) e Postgres sao
dubles. O que se trava: a origem entra na chave como `origem_sessao` (o campo `origem` da chave
e o marcador de como ela nasceu e nao muda), nao concede nada, nao trava a abertura, e nunca
troca uma origem ja gravada.
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

ORQ = "11111111-1111-4111-8111-111111111111"   # a sessao do orquestrador
FILHA = "22222222-2222-4222-8222-222222222222"  # a sessao portada de uma abertura anterior


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


def _chave_viva(cadeira="engenharia"):
    return json.dumps({"sujeito": "suj-1", "cadeira": cadeira, "ordem_id": "o1", "origem": "sessao abrir"})


@pytest.fixture
def mem():
    return FakeMsgMem({f"sessao:{ORQ}": _chave_viva()})


@pytest.fixture
def abre(mem, monkeypatch):
    """Abre uma sessao como o verbo abre, com tudo o que e de fora substituido."""
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


def test_origem_entra_na_chave_e_no_retorno(abre, mem):
    rc, out = abre("--origem", ORQ)
    assert rc == 0
    assert out["origem_sessao"] == ORQ
    ch = _chave(mem, out["sessao_id"])
    assert ch["origem_sessao"] == ORQ
    assert ch["origem"] == "sessao abrir", "o marcador de como a chave nasceu nao muda"
    assert out["avisos"] == []


def test_sem_origem_a_chave_fica_como_antes(abre, mem):
    rc, out = abre()
    assert rc == 0
    assert "origem_sessao" not in out
    assert "origem_sessao" not in _chave(mem, out["sessao_id"])


@pytest.mark.parametrize("invalida", ["", "nao-e-uuid", "1234"])
def test_origem_invalida_sai_2_e_nao_grava(abre, mem, invalida):
    antes = set(mem.data)
    rc, out = abre("--origem", invalida)
    assert rc == 2
    assert "RFC-4122" in out["erro"]
    assert set(mem.data) == antes


def test_origem_igual_ao_sessao_id_sai_2(abre, mem):
    rc, out = abre("--sessao-id", FILHA, "--origem", FILHA)
    assert rc == 2
    assert "de si mesma" in out["erro"]
    assert f"sessao:{FILHA}" not in mem.data


def test_origem_fora_do_ar_avisa_mas_abre(abre, mem):
    fantasma = str(uuid.uuid4())
    rc, out = abre("--origem", fantasma)
    assert rc == 0, "origem e linhagem, nunca trava a abertura"
    assert any(fantasma in a for a in out["avisos"])
    assert _chave(mem, out["sessao_id"])["origem_sessao"] == fantasma


def test_reabrir_nao_troca_a_origem_ja_gravada(abre, mem):
    rc, out = abre("--sessao-id", FILHA, "--origem", ORQ)
    assert rc == 0 and out["sessao_id"] == FILHA
    outra = str(uuid.uuid4())
    rc, _ = abre("--sessao-id", FILHA, "--origem", outra)
    assert rc == 0
    assert _chave(mem, FILHA)["origem_sessao"] == ORQ


def test_reabrir_sessao_sem_origem_aceita_a_primeira(abre, mem):
    mem.data[f"sessao:{FILHA}"] = _chave_viva()
    rc, _ = abre("--sessao-id", FILHA, "--origem", ORQ)
    assert rc == 0
    assert _chave(mem, FILHA)["origem_sessao"] == ORQ


def test_dry_run_mostra_a_origem_e_nao_grava(abre, mem):
    antes = dict(mem.data)
    rc, out = abre("--dry-run", "--origem", ORQ)
    assert rc == 0 and out["origem_sessao"] == ORQ
    assert mem.data == antes


def test_ver_e_listar_mostram_a_origem(abre, mem):
    _, out = abre("--origem", ORQ)
    sid = out["sessao_id"]
    f = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), redirect_stdout(f):
        assert sessao_mod.main(["ver", sid, "--json"]) == 0
    assert json.loads(f.getvalue())["origem_sessao"] == ORQ

    f = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), redirect_stdout(f):
        assert sessao_mod.main(["listar", "--json"]) == 0
    linhas = {l["sessao_id"]: l for l in json.loads(f.getvalue())["sessoes"]}
    assert linhas[sid]["origem_sessao"] == ORQ
    assert "origem_sessao" not in linhas[ORQ], "sessao sem origem nao ganha a chave"


def test_texto_do_abrir_traz_a_linha_da_origem(mem, monkeypatch):
    monkeypatch.setenv("PF_SUJEITO", "suj-1")
    f = io.StringIO()
    with patch.object(sessao_mod, "_msgmem", return_value=(mem, None)), \
            patch.object(sessao_mod, "_vocabulario",
                         return_value=({"engenharia": {"alias": "G", "chapeus": []}}, None)), \
            patch.object(sessao_mod, "_decidir", return_value=(0, {}, "")), \
            patch.object(sessao_mod, "_registra_duravel", return_value=None), \
            redirect_stdout(f):
        rc = sessao_mod.main(["abrir", "engenharia", "--origem", ORQ])
    assert rc == 0
    assert f"origem_sessao: {ORQ}" in f.getvalue()
