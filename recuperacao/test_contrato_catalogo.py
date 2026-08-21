"""Contrato do catálogo de existência (#2315). Spec §12.

Duas invariantes que este arquivo existe para travar:
1. leitor de custo `varredura` não entra na abertura;
2. a peça servida cabe no teto, **medida** com o tokenizador do modelo servido.
"""

from __future__ import annotations

import pytest

from .catalogo import (
    TETO_TOKENS,
    Catalogo,
    Custo,
    CustoProibido,
    Leitor,
    LinhaCatalogo,
    Origem,
    conta_tokens,
    fontes_sem_leitor,
    monta,
)
from .fontes import Fonte


def _leitor(fonte: str, n: int = 10, carimbo: str = "bda62dd") -> Leitor:
    return Leitor(fonte=Fonte(fonte), ler=lambda: (n, carimbo))


def _todos() -> list[Leitor]:
    return [_leitor(str(f), n) for f, n in zip(Fonte, (2816, 681096, 4172, 1893, 447, 209))]


# ------------------------------------------------- §12: nunca COUNT na abertura

def test_leitor_de_varredura_e_recusado_no_construtor():
    with pytest.raises(CustoProibido):
        Leitor(fonte=Fonte("acervo"), ler=lambda: (1, "x"), custo=Custo.VARREDURA)


def test_o_catalogo_so_se_monta_de_leitor():
    """Aceitar uma função crua deixaria o custo passar sem ser declarado."""
    with pytest.raises(TypeError):
        monta([lambda: (10, "x")])


def test_cada_leitor_e_chamado_uma_vez_so():
    chamadas = []
    leitor = Leitor(fonte=Fonte("board"), ler=lambda: (chamadas.append(1), (1, "c"))[1])
    monta([leitor])
    assert len(chamadas) == 1


# --------------------------------------------- ausência declarada, nunca omitida

def test_fonte_que_levanta_vira_linha_declarada_nao_excecao():
    def quebrado():
        raise ConnectionError("sem socket")

    c = monta([Leitor(fonte=Fonte("acervo"), ler=quebrado)])
    assert c.linhas[0].origem is Origem.INDISPONIVEL
    assert c.linhas[0].itens is None
    assert "ConnectionError" in c.linhas[0].motivo


def test_uma_fonte_caida_nao_derruba_as_outras():
    def quebrado():
        raise TimeoutError

    c = monta([Leitor(fonte=Fonte("acervo"), ler=quebrado), _leitor("board", 447)])
    assert len(c.linhas) == 2
    assert len(c.indisponiveis) == 1


def test_zero_medido_e_contador_ausente_nao_se_confundem():
    c = monta([_leitor("board", 0), Leitor(fonte=Fonte("fila"), ler=lambda: 1 / 0)])
    texto = c.para_texto()
    assert " 0 " in texto or texto.splitlines()[0].split()[-2] == "0"
    assert "—" in texto
    assert c.linhas[0].itens == 0
    assert c.linhas[1].itens is None


def test_fonte_sem_leitor_sai_nomeada():
    assert "acervo" in fontes_sem_leitor([_leitor("board")])
    assert fontes_sem_leitor(_todos()) == ()


# --------------------------------------------------------- o teto, MEDIDO

def test_a_peca_servida_cabe_no_teto_medida_no_tokenizador_do_modelo():
    """§12: alvo ⚪ ≤ 250 tokens, fechado na medição — não na estimativa."""
    texto = monta(_todos()).para_texto()
    assert conta_tokens(texto) <= TETO_TOKENS


def test_o_teto_vale_com_as_seis_indisponiveis():
    """O pior caso é o de todas caídas: o motivo é texto e é ele que estoura."""
    def quebrado():
        raise ConnectionError("socket recusado no host, sem rota para o loopback")

    c = monta([Leitor(fonte=f, ler=quebrado) for f in Fonte])
    assert conta_tokens(c.para_texto()) <= TETO_TOKENS


def test_estimativa_por_bytes_nao_substitui_a_medicao():
    """Guarda contra alguém trocar a régua: bytes/4 e o tokenizador divergem."""
    texto = monta(_todos()).para_texto()
    assert conta_tokens(texto) != len(texto.encode()) // 4


# ------------------------------------------------------------------ a forma

def test_texto_tem_uma_linha_por_fonte():
    assert len(monta(_todos()).para_texto().splitlines()) == len(list(Fonte))


def test_json_traz_origem_em_toda_linha():
    d = monta(_todos()).para_json()
    assert all("origem" in p for p in d["pecas"])


def test_carimbo_viaja_na_linha():
    """§12: carimbo por evento ou sha — peça sem carimbo não é datável."""
    assert monta([_leitor("board", 447, "e-99182")]).linhas[0].carimbo == "e-99182"


def test_linha_sem_carimbo_nao_inventa_um():
    c = Catalogo(linhas=(LinhaCatalogo(fonte="board", itens=1),))
    assert "carimbo" not in c.para_json()["pecas"][0]
