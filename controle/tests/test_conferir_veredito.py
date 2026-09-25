# test_conferir_veredito — o Veredito comum (resultado.py) e as classes que ja o usam:
# card #3142. Stub de git/tarefas via monkeypatch de conferir.sh; nada toca rede ou disco
# fora de tmp_path/monkeypatch.
import importlib.machinery
import importlib.util
import json
from pathlib import Path

import pytest

CONFERIR_PATH = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "conferir.py"
RESULTADO_PATH = Path(__file__).resolve().parents[2] / "bin" / "_release" / "conferir" / "resultado.py"


def _carregar(caminho, nome):
    loader = importlib.machinery.SourceFileLoader(nome, str(caminho))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    modulo = importlib.util.module_from_spec(spec)
    loader.exec_module(modulo)
    return modulo


resultado = _carregar(RESULTADO_PATH, "resultado_teste")
conferir = _carregar(CONFERIR_PATH, "conferir_veredito_teste")


# --- resultado.py: o tipo Veredito --------------------------------------------

def test_veredito_conforme_nao_exige_motivo():
    v = resultado.conforme(desde="2026-09-20")
    assert v.estado == "conforme"
    assert v.motivo is None
    assert v.dict()["desde"] == "2026-09-20"


def test_veredito_divergente_e_indeterminavel_exigem_motivo():
    with pytest.raises(ValueError):
        resultado.Veredito("divergente")
    with pytest.raises(ValueError):
        resultado.Veredito("indeterminavel")


def test_veredito_desde_ausente_vira_string_indeterminavel_no_dict():
    v = resultado.divergente("motivo qualquer")
    assert v.dict()["desde"] == "indeterminavel"


@pytest.mark.parametrize("itens,exit_esperado", [
    ([("a", resultado.conforme())], 0),
    ([("a", resultado.conforme()), ("b", resultado.divergente("x"))], 1),
    ([("a", resultado.conforme()), ("b", resultado.indeterminavel("x"))], 5),
    ([("a", resultado.divergente("x")), ("b", resultado.indeterminavel("y"))], 1),
])
def test_agrega_prioriza_divergente_sobre_indeterminavel(itens, exit_esperado):
    exit_code, *_ = resultado.agrega(itens)
    assert exit_code == exit_esperado


def test_linha_ancora_tem_a_forma_do_card_3142():
    itens = [("a", resultado.conforme()), ("b", resultado.divergente("x"))]
    linha, exit_code = resultado.linha_ancora("servico", None, itens, "abc1234")
    assert linha == (
        "release conferir servico: 1 conforme · 1 divergente · 0 não consegui olhar "
        "— release abc1234"
    )
    assert exit_code == 1


# --- conferir_card (card #3142, passo 6) --------------------------------------

def _stub_sh(respostas):
    """respostas: lista de (predicado(args) -> bool, (rc, out, err)). Primeiro bate, vale."""
    def sh(args):
        for pred, resp in respostas:
            if pred(args):
                return resp
        raise AssertionError(f"sh() nao stubado para: {args}")
    return sh


def test_card_conforme_quando_nenhum_commit_cita(monkeypatch, capsys):
    monkeypatch.setattr(conferir, "sh", _stub_sh([
        (lambda a: a[:2] == ["git", "-C"] and "log" in a, (0, "", "")),
        (lambda a: a[:2] == ["git", "-C"] and "branch" in a, (0, "", "")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_card("9999", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["itens"][0]["estado"] == "conforme"


def test_card_divergente_quando_commit_cita_e_estado_nao_andou(monkeypatch, capsys):
    log_saida = "deadbeef1234 2026-09-24T10:00:00-03:00\n"
    monkeypatch.setattr(conferir, "sh", _stub_sh([
        (lambda a: a[:2] == ["git", "-C"] and "log" in a and "origin/main" in a,
         (0, log_saida, "")),
        (lambda a: a[:2] == ["git", "-C"] and "branch" in a, (0, "", "")),
        (lambda a: len(a) >= 2 and a[-2] == "ler",
         (0, "#42 story · Em refinamento técnico (delivery)\n", "")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_card("42", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 1
    dado = json.loads(saida.out)
    item = dado["itens"][0]
    assert item["estado"] == "divergente"
    assert "Em refinamento técnico" in item["motivo"]
    assert item["desde"] == "2026-09-24T10:00:00-03:00"


def test_card_conforme_quando_estado_ja_avancou(monkeypatch, capsys):
    log_saida = "deadbeef1234 2026-09-24T10:00:00-03:00\n"
    monkeypatch.setattr(conferir, "sh", _stub_sh([
        (lambda a: a[:2] == ["git", "-C"] and "log" in a and "origin/main" in a,
         (0, log_saida, "")),
        (lambda a: a[:2] == ["git", "-C"] and "branch" in a, (0, "", "")),
        (lambda a: len(a) >= 2 and a[-2] == "ler",
         (0, "#42 story · Em execução (delivery)\n", "")),
    ]))
    monkeypatch.setattr(conferir, "_sha_release", lambda: "abc1234")

    exit_code = conferir.conferir_card("42", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 0
    dado = json.loads(saida.out)
    assert dado["itens"][0]["estado"] == "conforme"


def test_card_sem_alvo_e_uso_incorreto(capsys):
    exit_code = conferir.conferir_card(None, como_json=True)
    saida = capsys.readouterr()
    assert exit_code == 2
    assert "uso" in json.loads(saida.out)["erro"]


# --- existe: indeterminavel sai 5, nao mais 2 (card #3142, passo 7) -----------

def test_existe_indeterminavel_sai_5(monkeypatch, capsys):
    monkeypatch.setattr(conferir, "sh", lambda args: (1, "", "tarefas: sem rede"))
    exit_code = conferir.conferir_existe("card", "999999", como_json=True)
    saida = capsys.readouterr()

    assert exit_code == 5
    dado = json.loads(saida.out)
    assert dado["existe"] is None
