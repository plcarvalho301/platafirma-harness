# Forma autorizada do referente da linha de Fontes (decisão do dono de 11/10/2026, #3408
# comentário #2085, item 4): casa «espécie chave — título, §», obra «autor, título», norma
# «id canônico». Sem banco: só as funções puras e o despacho de uso.
import importlib.machinery
import importlib.util
import os

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACERVO = os.path.join(REPO, "bin", "_acervo")


def _carrega(nome, arquivo):
    loader = importlib.machinery.SourceFileLoader(nome, os.path.join(ACERVO, arquivo))
    spec = importlib.util.spec_from_loader(nome, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


cit = _carrega("acervo_citacao", "citacao")


def test_forma_casa_com_e_sem_secao():
    assert cit.forma_casa("adr", "arq:0126", "0126 — Spec é a referência") == \
        "adr arq:0126 — 0126 — Spec é a referência"
    assert cit.forma_casa("spec", "espelho-de-leitura", "spec — espelho", "§3") == \
        "spec espelho-de-leitura — spec — espelho, §3"
    assert cit.forma_casa("guia", "publicar", "") == "guia publicar"


def test_forma_obra_autor_e_titulo():
    assert cit.forma_obra("Records and Information Management (2. ed.)", ["Patricia C. Franks"],
                          "ISBN 978-0-8389-1716-9", "academico-editorial", "livro") == (
        "Patricia C. Franks, Records and Information Management (2. ed.)", "obra", [])
    forma, regra, avisos = cit.forma_obra("Living Intelligence", ["Adam Roades", "Chris Rasmussen"],
                                          None, "academico-editorial", "apresentacao")
    assert forma == "Adam Roades; Chris Rasmussen, Living Intelligence" and not avisos


def test_forma_norma_e_o_id_canonico():
    assert cit.forma_obra("ICD 203: Analytic Standards", ["ODNI"], "ICD 203",
                          "ato-normativo", "norma-complementar") == ("ICD 203", "norma", [])
    assert cit.forma_obra("ISO 27001", [], "ISO/IEC 27001:2022", "padrao-tecnico",
                          "norma-tecnica")[0] == "ISO/IEC 27001:2022"


def test_norma_sem_id_e_obra_sem_autor_avisam():
    forma, regra, avisos = cit.forma_obra("Lei X", ["Congresso"], None, "ato-normativo", "lei")
    assert forma == "Congresso, Lei X" and regra == "obra" and "sem id canônico" in avisos[0]
    forma, _, avisos = cit.forma_obra("Sem autor", [], None, "academico-editorial", "paper")
    assert forma == "Sem autor" and "sem autor" in avisos[0]


@pytest.mark.parametrize("argv", [["casa", "spec"], ["biblioteca"], ["registro", "x"],
                                  ["biblioteca", "a", "b"], ["biblioteca", "x", "--secao", "§1"]])
def test_uso_errado_sai_2(argv):
    with pytest.raises(SystemExit) as e:
        cit.main(argv)
    assert e.value.code == 2
