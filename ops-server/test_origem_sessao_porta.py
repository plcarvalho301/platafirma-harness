"""`origem_sessao` no ops log (card #3158): toda linha da sessao filha carrega a origem.

O Aceite do card e medido nesse log: as chamadas de verbo dos sub-agentes trazem a
`origem_sessao` igual ao `sessao_id` do orquestrador. Vive em ops-server/ porque server.py
precisa do venv com `mcp` (mesma fronteira de test_sessao_reidratar_porta.py).
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

_TMP = Path(tempfile.mkdtemp(prefix="ops-origem-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import server as s  # noqa: E402

ORQ = "11111111-1111-4111-8111-111111111111"
FILHA = "22222222-2222-4222-8222-222222222222"


@pytest.fixture(autouse=True)
def cache_limpo():
    s._ORIGENS.clear()
    yield
    s._ORIGENS.clear()


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


def test_resolve_traz_a_origem_da_chave_viva():
    rc = _rc_com({f"sessao:{FILHA}": {"cadeira": "engenharia", "ordem_id": "o1", "origem_sessao": ORQ}})
    with patch.object(s, "_rc", return_value=rc):
        out = s._sessao_resolve(FILHA)
    assert out["origem_sessao"] == ORQ
    assert out["cadeira"] == "engenharia"


def test_resolve_sem_origem_devolve_vazio():
    rc = _rc_com({f"sessao:{ORQ}": {"cadeira": "engenharia", "ordem_id": "o1"}})
    with patch.object(s, "_rc", return_value=rc):
        assert s._sessao_resolve(ORQ)["origem_sessao"] == ""


def test_origem_que_nao_e_uuid_nao_entra():
    rc = _rc_com({f"sessao:{FILHA}": {"cadeira": "ia", "origem_sessao": "lixo"}})
    with patch.object(s, "_rc", return_value=rc):
        assert s._sessao_resolve(FILHA)["origem_sessao"] == ""


def test_audit_grava_a_origem_na_linha_da_sessao_filha(tmp_path):
    rc = _rc_com({f"sessao:{FILHA}": {"cadeira": "engenharia", "origem_sessao": ORQ}})
    with patch.object(s, "_rc", return_value=rc):
        linha = _audita(tmp_path, sessao_id=FILHA)
    assert linha["sessao_id"] == FILHA
    assert linha["origem_sessao"] == ORQ


def test_audit_da_sessao_sem_origem_nao_ganha_o_campo(tmp_path):
    rc = _rc_com({f"sessao:{ORQ}": {"cadeira": "engenharia"}})
    with patch.object(s, "_rc", return_value=rc):
        linha = _audita(tmp_path, sessao_id=ORQ)
    assert "origem_sessao" not in linha


def test_audit_sem_sessao_nao_consulta_o_msgmem(tmp_path):
    rc = MagicMock()
    with patch.object(s, "_rc", return_value=rc):
        linha = _audita(tmp_path)
    assert linha["sessao_id"] == "-" and "origem_sessao" not in linha
    rc.get.assert_not_called()


def test_resolve_ja_povoa_o_cache_e_o_audit_nao_le_de_novo(tmp_path):
    rc = _rc_com({f"sessao:{FILHA}": {"cadeira": "engenharia", "ordem_id": "o1", "origem_sessao": ORQ}})
    with patch.object(s, "_rc", return_value=rc):
        s._sessao_resolve(FILHA)
        leituras = rc.get.call_count
        linha = _audita(tmp_path, sessao_id=FILHA)
    assert linha["origem_sessao"] == ORQ
    assert rc.get.call_count == leituras, "o ops log nao faz ida nova ao msg-mem no caminho comum"


def test_msgmem_mudo_nao_derruba_nem_repete_a_espera(tmp_path):
    rc = MagicMock()
    rc.get.side_effect = ConnectionError("fora do ar")
    with patch.object(s, "_rc", return_value=rc):
        linha = _audita(tmp_path, sessao_id=FILHA)
        assert "origem_sessao" not in linha
        antes = rc.get.call_count
        assert s._origem_da_sessao(FILHA) is None
        assert rc.get.call_count == antes, "falha cacheada por 60 s: a auditoria nao espera de novo"


def test_vazio_do_cache_vence_depois_de_60s():
    rc = _rc_com({f"sessao:{FILHA}": {"cadeira": "ia"}})
    with patch.object(s, "_rc", return_value=rc):
        assert s._origem_da_sessao(FILHA) is None
        rc.get.side_effect = lambda k: json.dumps({"cadeira": "ia", "origem_sessao": ORQ})
        assert s._origem_da_sessao(FILHA) is None            # ainda dentro dos 60 s
        t, _ = s._ORIGENS[FILHA]
        s._ORIGENS[FILHA] = (t - s._ORIGEM_VAZIA_S - 1, None)
        assert s._origem_da_sessao(FILHA) == ORQ             # venceu: le de novo e acha
    assert s._ORIGENS[FILHA][1] == ORQ


def test_cache_tem_teto():
    with patch.object(s, "_ORIGENS_TETO", 3):
        for i in range(5):
            s._guarda_origem(f"sid-{i}", None)
    assert len(s._ORIGENS) <= 3
