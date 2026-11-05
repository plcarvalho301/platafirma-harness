"""#4120, U13: o retrato devolve a diferença entre antes e depois (item 21).

A medida do card compara o primeiro lote que rodou pelo runbook de hoje com o primeiro por `acervo pipeline`.
O retrato de antes é o `--retrato --json` que se guardou em arquivo; `--diferenca <arquivo>` o compara com o de
agora e diz quem entrou e saiu, o que mudou em cada obra que ficou e a soma de cada entidade do rodapé.
Sem banco: os retratos são os do contrato (`retrato.montar`), editados à mão.
"""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "bin" / "_release" / "conferir"))
sys.path.insert(0, str(RAIZ / "bin" / "_acervo"))

import retrato  # noqa: E402
from test_acervo_retrato import _retrato  # noqa: E402

LISTAR = RAIZ / "bin" / "_acervo" / "listar"


@pytest.fixture
def par():
    antes = _retrato()
    depois = copy.deepcopy(antes)
    depois["cabecalho"]["tirado_em"] = "2026-11-06T10:00:00Z"
    # o2 passou a ser servida por trecho: viola menos e cobre mais
    o2 = depois["linhas"][1]
    o2.update(exposicao="trecho", cobertura="completa", invariantes=[])
    # o3 saiu do catálogo; o4 entrou
    o3 = depois["linhas"].pop(2)
    novo = copy.deepcopy(depois["linhas"][0])
    novo.update(obra_id="o4", titulo="Obra o4")
    depois["linhas"].append(novo)
    depois["rodape"]["obra"] = {"viva": 3}
    return antes, depois


def test_quem_entrou_e_quem_saiu(par):
    dif = retrato.diferenca(*par)
    assert [o["obra_id"] for o in dif["entraram"]] == ["o4"]
    assert [o["obra_id"] for o in dif["sairam"]] == ["o3"]
    assert dif["de"] == "2026-10-07T22:00:00Z" and dif["para"] == "2026-11-06T10:00:00Z"


def test_o_que_mudou_na_obra_que_ficou(par):
    dif = retrato.diferenca(*par)
    assert [o["obra_id"] for o in dif["mudaram"]] == ["o2"]
    mudancas = dif["mudaram"][0]["mudancas"]
    assert mudancas["exposicao"] == ["arquivo", "trecho"]
    assert mudancas["cobertura"] == ["sem índice", "completa"]
    assert mudancas["invariantes"] == [["I11"], []]
    assert "situacao" not in mudancas  # o que não mudou não entra


def test_o_rodape_so_traz_a_entidade_que_se_mexeu(par):
    dif = retrato.diferenca(*par)
    assert dif["rodape"]["obra"] == {"antes": {"retirada": 1, "viva": 2}, "depois": {"viva": 3}}
    assert "espelho_qualidade" not in dif["rodape"]


def test_retratos_iguais_dizem_que_nada_mudou():
    r = _retrato()
    dif = retrato.diferenca(r, copy.deepcopy(r))
    assert dif["entraram"] == dif["sairam"] == dif["mudaram"] == [] and dif["rodape"] == {}
    assert "nada mudou entre os dois retratos" in retrato.texto_diferenca(dif)


def test_o_texto_diz_o_antes_e_o_depois_de_cada_campo(par):
    texto = retrato.texto_diferenca(retrato.diferenca(*par))
    assert "obras: 3 -> 3 (entraram 1, saíram 1, mudaram 1)" in texto
    assert "entraram: o4" in texto and "saíram: o3" in texto
    assert "exposicao arquivo -> trecho" in texto and "cobertura sem índice -> completa" in texto
    assert "rodapé obra:" in texto


def test_o_texto_corta_a_lista_longa_e_aponta_o_json(par):
    antes, depois = par
    for i in range(retrato.MOSTRAR + 3):
        extra = copy.deepcopy(depois["linhas"][0])
        extra.update(obra_id=f"n{i:02d}", titulo=f"Nova {i}")
        depois["linhas"].append(extra)
    texto = retrato.texto_diferenca(retrato.diferenca(antes, depois))
    assert f"… +{3 + 1} que entraram" in texto
    assert "diferenca.entraram no --json" in texto


def test_executar_com_antes_junta_a_diferenca_ao_json(par, capsys):
    antes, depois = par
    ler = lambda sql: None  # noqa: E731  (não é chamado: `coletar` é trocado abaixo)
    original = retrato.pa.coletar
    try:
        retrato.pa.coletar = lambda ler, balde=None, orfaos=None: __import__("test_acervo_retrato")._dados()
        saida = retrato.executar(
            quero_json=True, ler=ler, balde=None, orfaos=None,
            projecao=lambda: __import__("test_acervo_retrato").PROJECAO,
            agora="2026-11-06T10:00:00Z", quem="t", antes=antes,
        )
    finally:
        retrato.pa.coletar = original
    corpo = json.loads(capsys.readouterr().out)
    assert "diferenca" in corpo and corpo["diferenca"]["para"] == "2026-11-06T10:00:00Z"
    assert corpo["diferenca"]["de"] == "2026-10-07T22:00:00Z"
    assert isinstance(saida, int)


def test_diferenca_sem_retrato_e_recusada_sem_tocar_em_banco():
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "--situacao", "--diferenca", "x.json"],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 2 and "--diferenca so vale com --retrato" in r.stderr


def test_arquivo_que_nao_e_retrato_e_recusado(tmp_path):
    ruim = tmp_path / "antes.json"
    ruim.write_text(json.dumps({"qualquer": "coisa"}))
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "--situacao", "--retrato", "--diferenca", str(ruim)],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 2 and "nao e um retrato" in r.stderr


def test_arquivo_ausente_e_recusado(tmp_path):
    r = subprocess.run([sys.executable, str(LISTAR), "obra", "--situacao", "--retrato", "--diferenca",
                        str(tmp_path / "nao-existe.json")],
                       capture_output=True, text=True, timeout=60, check=False)
    assert r.returncode == 2 and "nao li" in r.stderr
