"""Guardas do incidente #4251 e da story 4120 migradas de ops-server/ (#4348).

O envelope de erro do ler_arquivo traz a chamada que resolve, e o oplog aceita tokens no
giro. O pareamento de tateio pelo malote (DT 875) já é guardado em test_metrica_transporte.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

_RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_RAIZ / "lib"))

import oplog  # noqa: E402
from leitura import leitura as L  # noqa: E402


# --- #4251: forma única e chamada que resolve -----------------------------------------------------
def test_envelope_erro_forma_unica_sem_proximo_vazio():
    r = L.envelope_erro(4, "negado pela política", None, recusado=True, motivo="x")
    assert r["exit_code"] == 4
    assert r["falta"] == "negado pela política"
    assert "proximo" not in r
    assert r["recusado"] is True and r["motivo"] == "x"


def test_ler_arquivo_sob_fila_recusa_e_aponta_o_verbo_fila(tmp_path):
    inst = tmp_path / "casa"
    alvo = inst / "var" / "fila" / "caixa.jsonl"
    alvo.parent.mkdir(parents=True)
    alvo.write_text("{}\n", encoding="utf-8")
    r = L.ler(alvo, instancia=inst)
    assert r["recusado"] is True
    assert r["exit_code"] == 4
    assert "fila" in r["motivo"]
    assert "fila(" in r["proximo"]


def test_linhas_invalida_traz_o_caminho_na_chamada_que_resolve(tmp_path):
    arq = tmp_path / "amostra.txt"
    arq.write_text("a\nb\n", encoding="utf-8")
    r = L.ler(arq, linhas="abc")
    assert r["exit_code"] == 2
    assert "…" not in r["proximo"]
    assert str(arq) in r["proximo"]


def test_termo_em_arquivo_devolve_erro_que_cita_diretorio(tmp_path):
    arq = tmp_path / "amostra.txt"
    arq.write_text("linha 1\n", encoding="utf-8")
    r = L.ler(arq, termo="linha")
    assert r["exit_code"] == 2
    assert "diretório" in r["falta"]


# --- 4120: tokens no giro -------------------------------------------------------------------------
def test_oplog_validar_aceita_tokens_no_giro():
    reg = {
        "ts": "2026-11-05T12:00:00.000+00:00",
        "evento_id": "0192f000-0000-7000-8000-000000000001",
        "schema_v": 1,
        "origem": "cadeira",
        "mapa_v": None,
        "tool": "teste",
        "sessao_id": "11111111-1111-4111-8111-111111111111",
        "cadeira": "engenharia",
        "ordem_id": "o1",
        "exit_code": 0,
        "classe": "ok",
        "classe_fonte": "verbo",
        "bytes_produzidos": 100,
        "bytes_servidos": 100,
        "lavado": [],
        "capacidade": "verificacao",
        "ferramenta": "teste",
        "escopo": "#4120",
        "turno_id": "t1",
        "turno_fonte": "declarado",
        "tokens": 42,
        "metodo_tokens": "tokenizador qwen2.5",
        "sujeito": "b6986be0",
        "sub": "b6986be0",
        "username": "megafone",
        "azp": "claudinho-mcp",
        "sid": "sid-login",
        "jti": "jti-1",
    }
    assert not oplog.validar(reg)
