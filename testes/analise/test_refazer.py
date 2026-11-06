"""Comparação em três camadas separa a origem da diferença."""
import pytest
from analise.comparacao import comparar
from analise import Falha
from analise.ambiente import construir

@pytest.mark.parametrize("chave,camada",[("ambiente","ambiente"),("receita","ambiente"),("entradas","entrada"),("saidas","calculo")])
def test_camada_da_divergencia(chave,camada):
    original={"receita":{"sha":"a"},"ambiente":{"python":"3.12.3"},
        "entradas":{"x":{"sha256":"a"}},"saidas":{"y":{"sha256":"b"}}}
    nova={**original,chave:{"x":{"sha256":"z"}}}
    assert comparar(original,nova)==(1,camada)

def test_dependencia_ausente_sai_3(tmp_path):
    (tmp_path/"pyproject.toml").write_text("[project]\nname=\"sem-lock\"\nversion=\"1\"\nrequires-python=\">=3.12\"\ndependencies=[]\n")
    with pytest.raises(Falha) as e:construir(tmp_path,tmp_path/"cache")
    assert e.value.exit==3
