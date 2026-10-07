"""I13 no `release conferir acervo` (#3323, #3332): nenhum derivado anterior depois da promoção.

Três faces: impressão aposentada de obra ou casa viva, índice do motor de impressão que não existe
mais (caso real de 07/10/2026: dois índices da casa sobraram do expurgo 084) e espelho no balde sem
dono. Sem banco nem balde: as portas de leitura são trocadas por dublês.
"""

from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "bin" / "_release" / "conferir"))

import predicados_acervo as pa  # noqa: E402

LIMPO = {"obra": [], "casa": [], "existentes": ["imp-1", "imp-2"]}


def test_limpo_e_conforme():
    assert pa.predicado_13(LIMPO, ["imp-1", "imp-2"], 0).estado == "conforme"


def test_aposentada_de_obra_viva_diverge():
    v = pa.predicado_13({**LIMPO, "obra": ["imp-velha"]}, ["imp-1"], 0)
    assert v.estado == "divergente" and "aposentada(s) de obra viva" in v.motivo


def test_aposentada_de_casa_viva_diverge():
    v = pa.predicado_13({**LIMPO, "casa": ["ci-velha"]}, [], 0)
    assert v.estado == "divergente" and "casa viva" in v.motivo


def test_indice_de_impressao_que_nao_existe_diverge():
    v = pa.predicado_13(LIMPO, ["imp-1", "13ac7f68-orfa"], 0)
    assert v.estado == "divergente" and "1 índice(s) do motor" in v.motivo and "13ac7f68" in v.motivo


def test_espelho_sem_dono_diverge():
    v = pa.predicado_13(LIMPO, ["imp-1"], 3)
    assert v.estado == "divergente" and "3 espelho(s)" in v.motivo


def _ler(rag, motor):
    def ler(banco, sql):
        if sql is pa.SQL_I13_RAG:
            return rag
        if sql is pa.SQL_I13_MOTOR:
            return motor
        raise pa.Indeterminavel("fora do I13")  # os outros itens não são deste teste
    return ler


def _i13(itens):
    return dict(itens)[pa.NOME_I13]


def test_medir_traz_o_i13():
    itens, _, _ = pa.medir(regua_raiz="/nao/existe", ler=_ler(LIMPO, ["imp-1"]),
                           orfaos_do_balde=lambda: 0)
    assert _i13(itens).estado == "conforme"


def test_balde_que_nao_responde_e_indeterminavel():
    def balde():
        raise pa.Indeterminavel("balde: HTTP 401")

    itens, _, _ = pa.medir(regua_raiz="/nao/existe", ler=_ler(LIMPO, []), orfaos_do_balde=balde)
    v = _i13(itens)
    assert v.estado == "indeterminavel" and "401" in v.motivo
