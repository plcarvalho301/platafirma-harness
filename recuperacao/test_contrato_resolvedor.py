"""Contrato do resolvedor (#2311). O que falha o build quando violado.

Não é teste de unidade de conveniência: cada caso aqui é uma invariante escrita da
spec §10 ou de `arq:0064` §5. Teste que passa com a invariante quebrada não é teste.
"""

from __future__ import annotations

import pytest

from .envelope import ContratoViolado, Procedencia, Versao, VersaoTipo
from .fontes import Fonte
from .resolvedor import (
    Coordenada,
    Degrau,
    EstadoConceito,
    NaoResolve,
    Resolvedor,
    Secao,
    ancora_ruido,
    le_chave,
    tem_letra_latina,
)

SHA = "df70f05c9a1b4e2d8c3f6a7b0e1d2c3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d"


def _proc(chave: str, versao: str = "4b6f610a") -> Procedencia:
    return Procedencia(
        fonte=le_chave(chave).fonte,
        chave=chave,
        versao=Versao(tipo=VersaoTipo.SHA, valor=versao),
    )


def _secao(**kw) -> Secao:
    base = dict(
        obra="Nygard, Release It! (2007)",
        ancora="in-memory-caching",
        impressao="4b6f610a",
        titulo="In-Memory Caching",
        hierarquia=("Stability Patterns",),
        pagina=208,
    )
    base.update(kw)
    return Secao(**base)


# ------------------------------------------------------------- leitura da chave

def test_chave_de_acervo_separa_ancora_de_parte():
    lida = le_chave(f"acervo:{SHA}#in-memory-caching:p3")
    assert lida.fonte == Fonte("acervo")
    assert lida.objeto == SHA
    assert lida.ancora == "in-memory-caching"
    assert lida.parte == 3


def test_a_unidade_citavel_e_a_secao_nao_a_parte():
    """§4: `#âncora` é de SEÇÃO, `:p<idx>` é a parte."""
    lida = le_chave(f"acervo:{SHA}#in-memory-caching:p3")
    assert lida.chave_da_secao == f"acervo:{SHA}#in-memory-caching"


def test_ancora_com_sufixo_de_reaparicao_sobrevive():
    """`~<n>` marca a 2ª ocorrência do slug e é parte da âncora, não da parte."""
    assert le_chave(f"acervo:{SHA}#keyboard-interaction~13").ancora == "keyboard-interaction~13"


def test_chave_sem_prefixo_de_fonte_nao_passa():
    with pytest.raises(ContratoViolado):
        le_chave("in-memory-caching")


# --------------------------------------------------------------- âncora-ruído

@pytest.mark.parametrize("ancora", ["4", "7.1.", "645", "§3.2", "", None])
def test_ancora_sem_letra_latina_e_ruido(ancora):
    assert ancora_ruido(ancora)


@pytest.mark.parametrize("ancora", ["in-memory-caching", "ação-do-dono", "3-stability-patterns"])
def test_ancora_com_letra_nao_e_ruido(ancora):
    assert not ancora_ruido(ancora)


def test_acento_conta_como_letra_latina():
    """Normalização declarada ao caractere (§4-bis): `ação` é titulada."""
    assert tem_letra_latina("ação")


# ------------------------------------------------------- a chave nunca é reescrita

def test_chave_gravada_e_sempre_a_da_folha_mesmo_degradando():
    """`arq:0065` §7: gravar a chave do ancestral colapsa seções distintas."""
    chave = f"acervo:{SHA}#4"
    r = Resolvedor(lambda _: _secao(
        ancora="4", titulo=None, ancestrais=("Part III: Interaction Details",)
    ))
    c = r.resolve(_proc(chave))
    assert c.chave == chave
    assert c.degrau is Degrau.ANCESTRAL
    assert c.hierarquia == ("Part III: Interaction Details",)


def test_tres_ancoras_ruidosas_sob_o_mesmo_ancestral_nao_viram_a_mesma_chave():
    """O caso real do About Face: âncoras 2, 3 e 6 sob o mesmo título."""
    r = Resolvedor(lambda lida: _secao(
        obra="Cooper, About Face (2014)", ancora=lida.ancora, titulo=None,
        ancestrais=("Part III: Interaction Details",), pagina=None,
    ))
    chaves = {r.resolve(_proc(f"acervo:{SHA}#{n}")).chave for n in ("2", "3", "6")}
    assert len(chaves) == 3


# ------------------------------------------------------------ escada de degrau

def test_secao_titulada_usa_o_proprio_titulo():
    c = Resolvedor(lambda _: _secao()).resolve(_proc(f"acervo:{SHA}#in-memory-caching"))
    assert c.degrau is Degrau.SECAO
    assert c.hierarquia == ("Stability Patterns", "In-Memory Caching")


def test_sem_ancestral_titulado_degrada_para_obra_mais_pagina():
    c = Resolvedor(lambda _: _secao(ancora="4", titulo=None, ancestrais=(), pagina=208)).resolve(
        _proc(f"acervo:{SHA}#4")
    )
    assert c.degrau is Degrau.PAGINA
    assert c.hierarquia == ()
    assert c.pagina == 208


def test_sem_ancestral_e_sem_pagina_degrada_para_obra_e_declara():
    c = Resolvedor(lambda _: _secao(ancora="4", titulo=None, ancestrais=(), pagina=None)).resolve(
        _proc(f"acervo:{SHA}#4")
    )
    assert c.degrau is Degrau.OBRA
    assert c.para_texto().startswith("Nygard, Release It! (2007) — acervo:")


def test_ancestral_tambem_ruidoso_nao_sustenta_ancestral():
    """Subir para um ancestral que também é número não é reparo, é o mesmo ruído."""
    c = Resolvedor(lambda _: _secao(
        ancora="4", titulo=None, ancestrais=("7.1.",), pagina=208
    )).resolve(_proc(f"acervo:{SHA}#4"))
    assert c.degrau is Degrau.PAGINA


def test_titulo_nunca_e_derivado_do_corpo():
    """Se a seção não tem título, o resolvedor degrada — não inventa rótulo."""
    c = Resolvedor(lambda _: _secao(titulo=None, ancora="4", ancestrais=(), pagina=12)).resolve(
        _proc(f"acervo:{SHA}#4")
    )
    assert "In-Memory" not in c.para_texto()


# ------------------------------------------------------------------- a forma

def test_forma_da_coordenada_e_a_do_paragrafo_5():
    c = Resolvedor(lambda _: _secao()).resolve(_proc(f"acervo:{SHA}#in-memory-caching"))
    assert c.para_texto() == (
        "Nygard, Release It! (2007) › Stability Patterns › In-Memory Caching, p. 208 "
        f"— acervo:{SHA}#in-memory-caching @ impressão 4b6f610a"
    )


def test_degrau_sem_hierarquia_falha_o_build():
    with pytest.raises(ContratoViolado):
        Coordenada(obra="X", chave="acervo:a#b", versao="1", degrau=Degrau.SECAO)


# ------------------------------------------------------- os cinco estados (§5)

@pytest.mark.parametrize(
    ("kw", "esperado"),
    [
        ({}, EstadoConceito.ANCORADO),
        ({"obras": 2, "obras_servindo": 0}, EstadoConceito.DECLARADO_NAO_SERVINDO),
        ({"obras": 0, "obras_servindo": 0}, EstadoConceito.SEM_OBRA_NAO_JULGADO),
        ({"classificado": False}, EstadoConceito.ORFAO),
        ({"lacuna": True, "obras": 0, "obras_servindo": 0}, EstadoConceito.LACUNA),
    ],
)
def test_tabela_de_estados(kw, esperado):
    assert Resolvedor.estado(_secao(**kw)) is esperado


def test_lacuna_nao_se_deriva_da_ausencia_de_obra():
    """Juízo não se deriva: sem obra e sem linha de lacuna é `sem-obra-não-julgado`."""
    assert Resolvedor.estado(_secao(obras=0, obras_servindo=0)) is not EstadoConceito.LACUNA


# ------------------------------------------------------------ erro que instrui

def test_chave_que_nao_resolve_traz_falta_e_proximo():
    with pytest.raises(NaoResolve) as e:
        Resolvedor(lambda _: None).resolve(_proc(f"acervo:{SHA}#fabricada"))
    assert e.value.para_json()["falta"]
    assert e.value.para_json()["proximo"].startswith("recuperar")
