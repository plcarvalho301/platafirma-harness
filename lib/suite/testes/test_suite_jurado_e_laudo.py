# componente: componente:suite
# verifica: ato:verificar
"""Contrato do executor de testes (jurado) e da suíte de testes (motor) — card #4454."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

LIB_DIR = Path(__file__).resolve().parents[2]
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

from suite import (  # noqa: E402
    ErroExecutorTestes,
    ErroLaudoSuite,
    OpcoesExecucaoTeste,
    julgar_ficha,
    julgar_laudo,
)
from suite.coletor import LinhaBalde  # noqa: E402
from suite.esteira import DubleExecutorIsolado  # noqa: E402


def _criar_arquivo_teste(raiz: Path, rel: str, componente: str, verifica: str | None, funcoes: list[str]) -> Path:
    arq = raiz / rel
    arq.parent.mkdir(parents=True, exist_ok=True)
    linhas = [f"# componente: {componente}"]
    if verifica:
        linhas.append(f"# verifica: {verifica}")
    linhas.append("")
    for fn in funcoes:
        linhas.append(f"def {fn}():")
        linhas.append("    assert True")
        linhas.append("")
    arq.write_text("\n".join(linhas), encoding="utf-8")
    return arq


def test_ficha_verde_retorna_sim_conforme(tmp_path: Path):
    _criar_arquivo_teste(tmp_path, "tests/test_alfa.py", "componente:alfa", None, ["test_ok_1", "test_ok_2"])
    duble = DubleExecutorIsolado(
        {
            "tests/test_alfa.py::test_ok_1": True,
            "tests/test_alfa.py::test_ok_2": True,
        }
    )

    veredito = julgar_ficha(
        "teste:alfa",
        tmp_path,
        opcoes=OpcoesExecucaoTeste(alvo="componente:alfa", executor_isolado=duble),
    )

    assert veredito.resultado == "sim"
    assert veredito.constatacao == "conforme"
    assert veredito.modo == "enquadrou"
    assert veredito.motor == "servico:harness:executor-de-testes"
    assert veredito.apontamentos == ()
    assert veredito.casos_total == 2
    assert len(duble.chamadas) == 1


def test_ficha_vermelha_retorna_nao_divergente_com_apontamento(tmp_path: Path):
    _criar_arquivo_teste(tmp_path, "tests/test_beta.py", "componente:beta", None, ["test_bom", "test_quebrado"])

    def exec_fn(_arvore: Path, ids: list[str]):
        return {
            cid: (
                {"aprovado": True, "saida": ""}
                if cid.endswith("test_bom")
                else {"aprovado": False, "saida": "AssertionError: valor esperado 1, obtido 2"}
            )
            for cid in ids
        }

    veredito = julgar_ficha(
        "teste:beta",
        tmp_path,
        opcoes=OpcoesExecucaoTeste(alvo="componente:beta", executor_isolado=exec_fn),
    )

    assert veredito.resultado == "nao"
    assert veredito.constatacao == "divergente"
    assert len(veredito.apontamentos) == 1
    ap = veredito.apontamentos[0]
    assert ap.item == "test_quebrado"
    assert ap.lugar == "tests/test_beta.py"
    assert ap.severidade == "bloqueante"
    assert "AssertionError" in ap.cura


def test_ficha_sem_caso_retorna_nao_sei_inconclusivo(tmp_path: Path):
    _criar_arquivo_teste(tmp_path, "tests/test_vazio.py", "componente:vazio", None, [])

    veredito = julgar_ficha(
        "teste:vazio",
        tmp_path,
        opcoes=OpcoesExecucaoTeste(alvo="componente:vazio", executor_isolado=DubleExecutorIsolado()),
    )

    assert veredito.resultado == "nao-sei"
    assert veredito.constatacao == "inconclusivo"
    assert veredito.casos_total == 0


def test_ficha_ausente_sem_confirmacao_levanta_saida_1(tmp_path: Path):
    with pytest.raises(ErroExecutorTestes) as exc_info:
        julgar_ficha(
            "teste:fantasma",
            tmp_path,
            opcoes=OpcoesExecucaoTeste(executor_isolado=DubleExecutorIsolado()),
        )

    assert exc_info.value.saida == 1
    assert exc_info.value.codigo == "regua-inexistente"


def test_caso_em_quarentena_ativa_nao_conta_para_divergente(tmp_path: Path):
    _criar_arquivo_teste(
        tmp_path,
        "tests/test_gama.py",
        "componente:gama",
        None,
        ["test_verde", "test_erratico"],
    )
    duble = DubleExecutorIsolado(
        {
            "tests/test_gama.py::test_verde": True,
            "tests/test_gama.py::test_erratico": False,
        }
    )
    quarentena = [
        LinhaBalde(
            numero=1,
            idade_dias=5,
            stack="harness",
            texto="errático: tests/test_gama.py::test_erratico",
        )
    ]

    veredito = julgar_ficha(
        "teste:gama",
        tmp_path,
        opcoes=OpcoesExecucaoTeste(
            alvo="componente:gama",
            executor_isolado=duble,
            abertas_quarentena=quarentena,
        ),
    )

    assert veredito.resultado == "sim"
    assert veredito.constatacao == "conforme"
    assert veredito.casos_quarentena == 1
    assert veredito.apontamentos == ()


def test_laudo_de_duas_fichas_combina_vereditos_e_preserva_individuais(tmp_path: Path):
    _criar_arquivo_teste(tmp_path, "tests/test_f1.py", "componente:delta", None, ["test_a"])
    _criar_arquivo_teste(tmp_path, "tests/test_f2.py", "componente:delta", "politica:0011", ["test_b"])
    duble = DubleExecutorIsolado(
        {
            "tests/test_f1.py::test_a": True,
            "tests/test_f2.py::test_b": False,
        }
    )

    laudo = julgar_laudo(
        ["teste:delta", "teste:delta--politica-0011"],
        tmp_path,
        opcoes=OpcoesExecucaoTeste(alvo="componente:delta", executor_isolado=duble),
    )

    assert laudo.motor == "motor:harness:suite-de-testes"
    assert laudo.resultado == "nao"
    assert laudo.constatacao == "divergente"
    assert len(laudo.vereditos) == 2
    assert laudo.vereditos[0].resultado == "sim"
    assert laudo.vereditos[1].resultado == "nao"


def test_laudo_falha_na_segunda_ficha_preserva_primeira_parcial(tmp_path: Path):
    _criar_arquivo_teste(tmp_path, "tests/test_ok.py", "componente:eps", None, ["test_ok"])
    duble = DubleExecutorIsolado({"tests/test_ok.py::test_ok": True})

    with pytest.raises(ErroLaudoSuite) as exc_info:
        julgar_laudo(
            ["teste:eps", "teste:inexistente"],
            tmp_path,
            opcoes=OpcoesExecucaoTeste(alvo="componente:eps", executor_isolado=duble),
        )

    assert exc_info.value.saida == 1
    assert exc_info.value.codigo == "regua-inexistente"
    assert len(exc_info.value.vereditos_parciais) == 1
    assert exc_info.value.vereditos_parciais[0].resultado == "sim"
