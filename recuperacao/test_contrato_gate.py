"""Contrato do gate de procedência (#2310). Spec §10.1–5.

O caso que este arquivo existe para travar: citação legítima de impressão aposentada
reprovando como chave fabricada.
"""

from __future__ import annotations

import pytest

from .adaptadores.base import monta_envelope
from .envelope import Cobertura, Item, LinhaFonte, Procedencia, Sinal, Versao, VersaoTipo
from .fontes import Fonte
from .gate import Gate, Julgamento, extrai_chaves, fontes_citadas
from .resolvedor import Resolvedor, Secao
from .adaptadores.base import Resultado

SHA = "df70f05c9a1b4e2d8c3f6a7b0e1d2c3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d"
CHAVE = f"acervo:{SHA}#in-memory-caching"


def _secao(**kw) -> Secao:
    base = dict(
        obra="Nygard, Release It! (2007)", ancora="in-memory-caching", impressao="4b6f610a",
        titulo="In-Memory Caching", hierarquia=("Stability Patterns",), pagina=208,
    )
    base.update(kw)
    return Secao(**base)


def _envelope_com(chave: str) -> object:
    proc = Procedencia(
        fonte=Fonte("acervo"), chave=chave,
        versao=Versao(tipo=VersaoTipo.DIGEST, valor="4b6f610a"),
    )
    # `acervo` é semântica: cobertura contra piso EXIGE sinal (§3, inv. 2).
    linha = LinhaFonte(
        fonte=Fonte("acervo"), cobertura=Cobertura.COBERTA,
        sinal=Sinal(medida="sim", valor=0.72, piso=0.55),
    )
    return monta_envelope([Resultado(linha=linha, itens=[Item(procedencia=proc, conteudo="…")])])


def _envelope_vazio() -> object:
    return monta_envelope([Resultado(linha=LinhaFonte(fonte=Fonte("acervo"), cobertura=Cobertura.VAZIA))])


def _gate(servindo: bool = True, historico: bool = True) -> Gate:
    def recuperar_real(chave, servindo=True):  # noqa: FBT002
        if servindo:
            return _envelope_com(chave) if globals()["_SERVINDO"] else _envelope_vazio()
        return _envelope_com(chave) if globals()["_HISTORICO"] else _envelope_vazio()

    globals()["_SERVINDO"], globals()["_HISTORICO"] = servindo, historico
    return Gate(recuperar_real, Resolvedor(lambda _: _secao()))


# ------------------------------------------------------------------ extração

def test_extrai_chave_de_cada_uma_das_seis_fontes():
    texto = (
        f"Ver {CHAVE}, o item:447, a carta caixa:claudinho-IA/1692-0, "
        "a decisão adr:0064, a página wiki:1204#recuperador e mem:ia:harness#107."
    )
    achadas = extrai_chaves(texto)
    assert len(achadas) == 6
    assert CHAVE in achadas
    assert "item:447" in achadas


def test_pontuacao_final_nao_entra_na_chave():
    assert extrai_chaves("a decisão adr:0064.") == ["adr:0064"]


def test_chave_repetida_sai_uma_vez_so():
    assert extrai_chaves(f"{CHAVE} e de novo {CHAVE}") == [CHAVE]


def test_fontes_citadas_alimenta_o_eixo_2():
    assert fontes_citadas(f"{CHAVE} e item:447") == {Fonte("acervo"), Fonte("board")}


# ------------------------------------------------- predicado em dois passos

def test_chave_servindo_e_citavel():
    v = _gate(servindo=True).confere(CHAVE)
    assert v.julgamento is Julgamento.CITAVEL
    assert not v.recusa


def test_impressao_aposentada_nao_reprova():
    """§10.3: citação legítima de impressão aposentada não é chave fabricada."""
    v = _gate(servindo=False, historico=True).confere(CHAVE)
    assert v.julgamento is Julgamento.APOSENTADA
    assert not v.recusa
    assert v.coordenada is not None


def test_chave_que_nao_resolve_em_impressao_nenhuma_e_recusada():
    v = _gate(servindo=False, historico=False).confere(CHAVE)
    assert v.julgamento is Julgamento.FABRICADA
    assert v.recusa


def test_recusa_traz_falta_e_proximo():
    """§10.4 e `arq:0064` §6: recusar sem dizer o que falta gasta o giro."""
    v = _gate(servindo=False, historico=False).confere(CHAVE)
    assert v.falta
    assert v.proximo.startswith("recuperar")


# --------------------------------------------------------- o gate não cava

def test_o_gate_nao_abre_conexao_propria():
    """§10.2: tudo passa por `recuperar`. Uma chave, no máximo duas chamadas."""
    chamadas = []

    def recuperar(chave, servindo=True):  # noqa: FBT002
        chamadas.append(servindo)
        return _envelope_com(chave)

    Gate(recuperar, Resolvedor(lambda _: _secao())).confere(CHAVE)
    assert chamadas == [True]


def test_so_consulta_o_historico_quando_o_servindo_falha():
    chamadas = []

    def recuperar(chave, servindo=True):  # noqa: FBT002
        chamadas.append(servindo)
        return _envelope_vazio() if servindo else _envelope_com(chave)

    Gate(recuperar, Resolvedor(lambda _: _secao())).confere(CHAVE)
    assert chamadas == [True, False]


def test_recuperar_que_devolve_outra_coisa_falha_o_build():
    with pytest.raises(TypeError):
        Gate(lambda c, servindo=True: {"itens": []}, Resolvedor(lambda _: _secao())).confere(CHAVE)


def test_chave_de_outra_secao_no_envelope_nao_confirma_a_citada():
    outra = f"acervo:{SHA}#circuit-breaker"
    gate = Gate(lambda c, servindo=True: _envelope_com(outra), Resolvedor(lambda _: _secao()))
    assert gate.confere(CHAVE).julgamento is Julgamento.FABRICADA


# ---------------------------------------------------------- grava e é idempotente

def test_grava_a_coordenada_humana_no_artefato():
    p = _gate().julga(f"Como argumenta {CHAVE}, o cache em memória…")
    assert "Nygard, Release It! (2007) › Stability Patterns › In-Memory Caching, p. 208" in p.texto
    assert p.aprovado


def test_gravar_duas_vezes_nao_duplica():
    gate = _gate()
    uma = gate.julga(f"Ver {CHAVE}.").texto
    assert gate.julga(uma).texto == uma


def test_artefato_com_chave_fabricada_nao_e_aprovado():
    p = _gate(servindo=False, historico=False).julga(f"Ver {CHAVE}.")
    assert not p.aprovado
    assert p.recusadas[0].chave == CHAVE


def test_chave_recusada_nao_e_reescrita_no_texto():
    """Recusa não fabrica coordenada: o texto sai como entrou."""
    texto = f"Ver {CHAVE}."
    assert _gate(servindo=False, historico=False).julga(texto).texto == texto
