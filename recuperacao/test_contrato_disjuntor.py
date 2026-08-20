"""Contrato do disjuntor. `python3 -m pytest recuperacao/ -q` da raiz do repo.

`spec_recuperador.md` §8. Relógio falso em todo teste: disjuntor testado com `sleep`
mede a paciência de quem roda a suíte, não o comportamento da peça.
"""

from __future__ import annotations

import time

import pytest

from recuperacao.disjuntor import Disjuntor, EstadoDisjuntor, Painel
from recuperacao.envelope import Causa, Cobertura, Envelope, Fonte


class Relogio:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def anda(self, s: float) -> None:
        self.t += s


@pytest.fixture
def rel() -> Relogio:
    return Relogio()


def disj(rel, **kw) -> Disjuntor:
    kw.setdefault("limiar_falhas", 3)
    kw.setdefault("espera_s", 30.0)
    return Disjuntor(fonte=Fonte.WIKI, relogio=rel, **kw)


# ============================================================== abertura por falha


def test_nasce_fechado_e_deixa_passar(rel):
    d = disj(rel)
    assert d.estado is EstadoDisjuntor.FECHADO
    assert d.permite()


def test_sucesso_zera_a_contagem(rel):
    d = disj(rel)
    d.registra_falha()
    d.registra_falha()
    d.registra_sucesso()
    d.registra_falha()
    d.registra_falha()
    assert d.estado is EstadoDisjuntor.FECHADO, "falha esparsa não é fonte caída"


def test_abre_no_limiar_de_falhas_consecutivas(rel):
    d = disj(rel)
    for _ in range(3):
        d.registra_falha()
    assert d.estado is EstadoDisjuntor.ABERTO
    assert not d.permite()


# ============================================== aberto responde em 0 ms, sem tocar


def test_aberto_recusa_sem_chamar_a_fonte(rel):
    d = disj(rel)
    d.abre()
    chamou = []

    inicio = time.perf_counter()
    with d.janela() as passa:
        if passa:
            chamou.append(1)
    gasto_ms = (time.perf_counter() - inicio) * 1000

    assert not chamou, "disjuntor aberto não pode deixar a chamada sair"
    assert gasto_ms < 1.0, f"recusa levou {gasto_ms:.3f} ms; a spec diz 0 ms"


def test_a_linha_da_recusa_e_fonte_nao_indexada_com_disjuntor_aberto(rel):
    d = disj(rel)
    d.abre()
    linha = d.linha_recusa()
    assert linha.cobertura is Cobertura.FONTE_NAO_INDEXADA
    assert linha.causa is Causa.DISJUNTOR_ABERTO
    env = Envelope(linhas=[linha])
    assert env.para_json()["aviso"] == [{"fonte": "wiki", "causa": "disjuntor-aberto"}]


# ================================ meia-abertura POR SONDAGEM, nunca por retentativa


def test_antes_da_espera_nao_sonda(rel):
    d = disj(rel)
    d.abre()
    rel.anda(29.9)
    assert not d.permite()
    assert d.estado is EstadoDisjuntor.ABERTO


def test_passada_a_espera_libera_UMA_sondagem(rel):
    d = disj(rel)
    d.abre()
    rel.anda(30.0)
    assert d.permite(), "vencida a espera, uma sondagem sai"
    assert not d.permite(), "a segunda não: sondagem, não retentativa imediata"
    assert not d.permite()


def test_sondagem_que_falha_reabre_e_reinicia_a_espera(rel):
    d = disj(rel)
    d.abre()
    rel.anda(30.0)
    assert d.permite()
    d.registra_falha()
    assert d.estado is EstadoDisjuntor.ABERTO
    rel.anda(29.9)
    assert not d.permite(), "a espera reiniciou; a fonte respondeu que não voltou"
    rel.anda(0.1)
    assert d.permite()


def test_sondagem_que_passa_fecha_o_disjuntor(rel):
    d = disj(rel)
    d.abre()
    rel.anda(30.0)
    with d.janela() as passa:
        assert passa
    assert d.estado is EstadoDisjuntor.FECHADO
    assert d.permite() and d.permite(), "fechado, a carga volta inteira"


def test_janela_registra_falha_na_excecao(rel):
    d = disj(rel, limiar_falhas=1)
    with pytest.raises(TimeoutError):
        with d.janela() as passa:
            assert passa
            raise TimeoutError("fonte não respondeu em 250 ms")
    assert d.estado is EstadoDisjuntor.ABERTO


# ==================================================== estado observável (§8 e §9)


def test_observavel_publica_o_que_a_operacao_precisa(rel):
    d = disj(rel)
    o = d.observavel()
    assert o["fonte"] == "wiki"
    assert o["disjuntor"] == "fechado"
    assert o["aberturas"] == 0
    assert o["aberto_ha_s"] is None

    d.abre()
    rel.anda(12.5)
    o = d.observavel()
    assert o["disjuntor"] == "aberto"
    assert o["aberturas"] == 1
    assert o["aberto_ha_s"] == 12.5


def test_leitura_de_estado_nao_consome_sondagem(rel):
    d = disj(rel)
    d.abre()
    rel.anda(30.0)
    assert d.estado is EstadoDisjuntor.MEIO_ABERTO
    assert d.estado is EstadoDisjuntor.MEIO_ABERTO
    assert d.permite(), "ler o estado não pode gastar a vaga da sondagem"


# ==================================================================== painel por fonte


def test_painel_da_um_disjuntor_por_fonte(rel):
    p = Painel(limiar_falhas=1, relogio=rel)
    assert p[Fonte.WIKI] is p[Fonte.WIKI]
    assert p[Fonte.WIKI] is not p[Fonte.ACERVO]


def test_fonte_caida_nao_derruba_as_outras(rel):
    p = Painel(limiar_falhas=1, relogio=rel)
    p[Fonte.WIKI].registra_falha()
    assert p.abertos == [Fonte.WIKI]
    assert p[Fonte.ACERVO].permite()
    assert p[Fonte.BOARD].permite()


def test_painel_observavel_lista_uma_linha_por_fonte(rel):
    p = Painel(relogio=rel)
    p[Fonte.WIKI], p[Fonte.ACERVO]
    assert [o["fonte"] for o in p.observavel()] == ["wiki", "acervo"]
