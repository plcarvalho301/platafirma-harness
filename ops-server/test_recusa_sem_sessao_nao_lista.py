"""Card #3475 (arq:0101 §1, emenda de 13/10/2026): a recusa por falta de `sessao_id` valido nao
lista sessao nem id de nenhuma cadeira.

Sem id valido o verbo nao sabe quem chamou; listar as sessoes dos outros e a porta inferindo
sessao, o que o §1 proibe, e foi o que o incidente #3236 mostrou (um chamador adotando o id de
outra cadeira). A recusa diz o que faltou e o ato que devolve o id.
"""
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

HARNESS_DIR = Path(__file__).resolve().parent.parent
_loader = SourceFileLoader("descansar_recusa_3475", str(HARNESS_DIR / "bin" / "descansar"))
_spec = importlib.util.spec_from_loader("descansar_recusa_3475", _loader)
assert _spec and _spec.loader
descansar = importlib.util.module_from_spec(_spec)
_loader.exec_module(descansar)

# Sessoes vivas de OUTRAS cadeiras, como o msg-mem as teria (`sessao:{id}`).
ALHEIAS = {
    "11111111-2222-4333-8444-555555555555": "ia",
    "66666666-7777-4888-8999-aaaaaaaaaaaa": "engenharia",
    "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff": "seguranca",
}


class _MsgMemQueNaoDeviaSerLido:
    """A recusa nao consulta o msg-mem: nem lista, nem resolve. Qualquer acesso reprova."""

    def __getattr__(self, nome):
        raise AssertionError(f"a recusa tocou o msg-mem ({nome}) para uma chamada sem cadeira")


@pytest.fixture()
def sem_cadeira(monkeypatch):
    monkeypatch.delenv("PF_CADEIRA", raising=False)
    monkeypatch.delenv("PF_SESSAO", raising=False)
    monkeypatch.setattr(descansar, "conn", lambda: _MsgMemQueNaoDeviaSerLido())


def _recusa() -> str:
    with pytest.raises(SystemExit) as saiu:
        descansar.cadeira()
    return str(saiu.value)


def _sem_id_alheio(texto: str):
    for sid, cad in ALHEIAS.items():
        assert sid not in texto, f"a recusa trouxe o id da sessao de {cad}"
    assert "sessoes vivas" not in texto
    assert "sessao listar" not in texto, "listar sessao e ato de quem ja tem cadeira"


def test_sem_sessao_id_a_recusa_nao_traz_id_de_outra_cadeira(sem_cadeira):
    texto = _recusa()
    _sem_id_alheio(texto)
    assert "PF_CADEIRA nao definida" in texto
    assert "nenhum sessao_id chegou" in texto


def test_sessao_id_torto_a_recusa_diz_o_que_faltou_sem_listar_ninguem(sem_cadeira, monkeypatch):
    torto = "019fac3d-902d-7075-82a9-8ff44a01f6ec"   # id do Project no lugar do sessao_id da fita
    monkeypatch.setenv("PF_SESSAO", torto)
    texto = _recusa()
    _sem_id_alheio(texto)
    assert torto in texto, "o id que o chamador mandou volta a ele, para ele ver o que mandou"
    assert "expirou" in texto and "uuid torto" in texto


def test_a_recusa_diz_o_ato_que_devolve_o_id(sem_cadeira):
    texto = _recusa()
    assert "sessao_id da propria fita" in texto
    assert "monta_sessao(cadeira=<slug>)" in texto


def test_com_cadeira_no_ambiente_nao_ha_recusa(monkeypatch):
    monkeypatch.setenv("PF_CADEIRA", "arquiteto")
    assert descansar.cadeira() == "arquiteto"


def test_a_lista_de_sessoes_vivas_nao_existe_mais():
    assert not hasattr(descansar, "_sessoes_vivas")
