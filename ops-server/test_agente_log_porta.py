"""`agente`, `em_nome_de` e `conta_agente` no ops log (card #3156, spec agente §11.1).

A linha da sessao filha de um agente repete os atributos que `sessao abrir --agente` gravou na chave,
ao lado da `origem_sessao`. Vive em ops-server/ pela mesma razao de test_origem_sessao_porta.py: server.py
precisa do venv com `mcp`.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-agente-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import server as s  # noqa: E402

ORQ = "11111111-1111-4111-8111-111111111111"
FILHA = "22222222-2222-4222-8222-222222222222"
ATRIBUTOS = {"agente": "varredor", "em_nome_de": "engenharia", "conta_agente": "claudinho"}


@pytest.fixture(autouse=True)
def caches_limpos():
    s._ORIGENS.clear()
    s._AGENTES.clear()
    yield
    s._ORIGENS.clear()
    s._AGENTES.clear()


def _rc_com(chaves: dict[str, dict]):
    rc = MagicMock()
    rc.get.side_effect = lambda k: json.dumps(chaves[k]) if k in chaves else None
    return rc


def _audita(tmp_path, **campos) -> dict:
    with patch.object(s, "LOG_DIR", tmp_path):
        s._audit(tool="-", evento="teste", **campos)
    linhas = [json.loads(l) for f in tmp_path.glob("ops-*.jsonl") for l in f.read_text().splitlines()]
    assert len(linhas) == 1, linhas
    return linhas[0]


def test_audit_repete_os_atributos_do_agente_na_linha_da_filha(tmp_path):
    rc = _rc_com({f"sessao:{FILHA}": {"cadeira": "engenharia", "origem_sessao": ORQ, **ATRIBUTOS}})
    with patch.object(s, "_rc", return_value=rc):
        linha = _audita(tmp_path, sessao_id=FILHA)
    assert linha["origem_sessao"] == ORQ
    for k, v in ATRIBUTOS.items():
        assert linha[k] == v


def test_sessao_sem_origem_nao_paga_leitura_nova_nem_ganha_campos(tmp_path):
    rc = _rc_com({f"sessao:{ORQ}": {"cadeira": "engenharia"}})
    with patch.object(s, "_rc", return_value=rc):
        linha = _audita(tmp_path, sessao_id=ORQ)
    assert not set(ATRIBUTOS) & set(linha)
    assert rc.get.call_count == 1, "so a origem foi lida: sem origem, o agente nem e consultado"


def test_filha_que_nao_e_de_agente_nao_ganha_campos(tmp_path):
    rc = _rc_com({f"sessao:{FILHA}": {"cadeira": "engenharia", "origem_sessao": ORQ}})
    with patch.object(s, "_rc", return_value=rc):
        linha = _audita(tmp_path, sessao_id=FILHA)
    assert linha["origem_sessao"] == ORQ and not set(ATRIBUTOS) & set(linha)


def test_atributo_que_nao_e_texto_nao_entra():
    rc = _rc_com({f"sessao:{FILHA}": {"origem_sessao": ORQ, "agente": 7, "em_nome_de": "", "conta_agente": "claudinho"}})
    with patch.object(s, "_rc", return_value=rc):
        assert s._atributos_do_agente(FILHA) == {"conta_agente": "claudinho"}


def test_atributos_ficam_em_cache_e_o_vazio_vence_em_60s():
    rc = _rc_com({f"sessao:{FILHA}": {"origem_sessao": ORQ, **ATRIBUTOS}})
    with patch.object(s, "_rc", return_value=rc):
        assert s._atributos_do_agente(FILHA) == ATRIBUTOS
        leituras = rc.get.call_count
        assert s._atributos_do_agente(FILHA) == ATRIBUTOS
        assert rc.get.call_count == leituras
    vazio = _rc_com({f"sessao:{ORQ}": {"cadeira": "ia"}})
    with patch.object(s, "_rc", return_value=vazio):
        assert s._atributos_do_agente(ORQ) == {}
        vazio.get.side_effect = lambda k: json.dumps({"agente": "x"})
        assert s._atributos_do_agente(ORQ) == {}             # ainda dentro dos 60 s
        t, _ = s._AGENTES[ORQ]
        s._AGENTES[ORQ] = (t - s._ORIGEM_VAZIA_S - 1, {})
        assert s._atributos_do_agente(ORQ) == {"agente": "x"}


def test_msgmem_mudo_nao_derruba_a_auditoria(tmp_path):
    rc = MagicMock()
    rc.get.side_effect = ConnectionError("fora do ar")
    with patch.object(s, "_rc", return_value=rc):
        linha = _audita(tmp_path, sessao_id=FILHA)
        assert not set(ATRIBUTOS) & set(linha)
        assert s._atributos_do_agente(FILHA) == {}


def test_sem_sessao_nao_consulta_nada():
    rc = MagicMock()
    with patch.object(s, "_rc", return_value=rc):
        assert s._atributos_do_agente("-") == {} and s._atributos_do_agente(None) == {}
    rc.get.assert_not_called()
