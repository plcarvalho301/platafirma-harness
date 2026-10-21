"""Card #3958: `curar --marcar-secoes --faixas-modelo <pasta>` lê o seccionamento feito fora daqui.

Prova só o lado do verbo: a pasta vira impressão → faixas de nível 1 em diante, com byte, título e
nível; o pré-âmbulo e o arquivo sem estrutura ficam de fora; nome que não é uuid recusa. A conferência
contra o espelho é da API (platafirma-conhecimento, test_segmentacao_modelo.py).
"""
import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

CURAR = Path(__file__).resolve().parents[2] / "bin" / "curar"
IMP = "a3e99e87-1fb9-4d35-9eeb-147b18444d0c"
VAZIA = "28a9887c-c3fa-4c4d-9118-06132f76b2b5"


@pytest.fixture(scope="module")
def curar():
    import sys
    import types
    try:
        import requests  # noqa: F401
    except ImportError:  # o ambiente do portão não tem requests; a função provada não fala HTTP
        class _SemRede(types.ModuleType):
            def __getattr__(self, nome):  # requests.Response, requests.exceptions… só como nome
                return type(nome, (Exception,), {})
        sys.modules.setdefault("requests", _SemRede("requests"))
    carregador = importlib.machinery.SourceFileLoader("curar_3958", str(CURAR))
    spec = importlib.util.spec_from_loader("curar_3958", carregador)
    modulo = importlib.util.module_from_spec(spec)
    carregador.exec_module(modulo)
    return modulo


def _grava(pasta, impressao, faixas):
    (pasta / f"{impressao}.json").write_text(json.dumps({"impressao": impressao, "faixas": faixas}))


def test_pasta_vira_impressao_e_faixas_de_nivel_1_em_diante(curar, tmp_path):
    _grava(tmp_path, IMP, [
        {"ordem": 0, "ancora": "_preambulo", "titulo": None, "nivel": 0, "byte_ini": 0, "byte_fim": 425},
        {"ordem": 1, "ancora": "adi-6428", "titulo": "ADI 6428", "nivel": 1, "byte_ini": 425, "byte_fim": 685},
        {"ordem": 2, "ancora": "ementa", "titulo": "Ementa", "nivel": 2, "byte_ini": 685, "byte_fim": 4517}])
    _grava(tmp_path, VAZIA, [{"ordem": 0, "ancora": "_preambulo", "titulo": None, "nivel": 0,
                              "byte_ini": 0, "byte_fim": 4376}])
    (tmp_path / IMP).mkdir()  # a pasta irmã que o Gemini deixou não conta
    assert curar._faixas_modelo_da_pasta(str(tmp_path)) == {IMP: [
        {"byte_ini": 425, "titulo": "ADI 6428", "nivel": 1},
        {"byte_ini": 685, "titulo": "Ementa", "nivel": 2}]}


def test_nome_que_nao_e_uuid_recusa(curar, tmp_path):
    _grava(tmp_path, "nao-e-uuid", [{"nivel": 1, "byte_ini": 1, "titulo": "x"}])
    with pytest.raises(ValueError):
        curar._faixas_modelo_da_pasta(str(tmp_path))


def test_caminho_que_nao_e_pasta_recusa(curar, tmp_path):
    with pytest.raises(ValueError):
        curar._faixas_modelo_da_pasta(str(tmp_path / "nao-existe"))
