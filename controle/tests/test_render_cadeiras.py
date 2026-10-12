"""Bloco Cadeiras da recepcao contra o pacote que a abertura de hoje serve (#3472).

A coluna Manifesto media a peca `oficio`, que `expediente montar` nao serve mais (o #3078 ja
tirou o Oficio da /cadeira), e saía «ausente» em toda cadeira: a tela pintava o que a abertura
nao produz. Prova: o pacote de hoje (conduta, persona, alias-cadeiras, mesa, cadernos, rotinas)
rende a linha da cadeira sem «ausente» e sem coluna Manifesto; a ausencia real (cadeira sem
persona) segue «ausente»; a linha indisponivel continua alinhada com o cabecalho.
Nao prova: o que `expediente montar` serve (testes/test_expediente.py) nem a rota HTTP
(test_web_fumaca).
"""
from __future__ import annotations

from harness_controle.render import bloco_cadeiras


def _peca(nome, frescor="fresco"):
    return {"peca": nome, "ref": f"verbo:{nome}", "sha": "x", "frescor": frescor,
            "tokens": 1, "conteudo": "c"}


PACOTE_DE_HOJE = [_peca(n) for n in
                  ("conduta", "persona", "alias-cadeiras", "mesa", "cadernos", "rotinas")]


def _item(cadeira, pecas):
    return {"cadeira": cadeira, "lido_em": 1000.0, "estado": "ok", "motivo": None,
            "dados": {"pecas": pecas}}


def _bloco(*itens):
    return {"lido_em": 1000.0, "estado": "ok", "motivo": None, "itens": list(itens)}


def test_pacote_de_hoje_nao_mostra_ausente_nem_coluna_manifesto():
    html = bloco_cadeiras(_bloco(_item("ti", PACOTE_DE_HOJE), _item("dados", PACOTE_DE_HOJE)))
    assert "ausente" not in html
    assert "Manifesto" not in html
    assert html.count('<span class="chip calmo">presente</span>') == 2
    assert html.count('<span class="chip calmo">lida</span>') == 2


def test_cadeira_sem_persona_segue_ausente():
    """A ausencia real nao some junto com a coluna morta."""
    sem_persona = [p for p in PACOTE_DE_HOJE if p["peca"] != "persona"]
    html = bloco_cadeiras(_bloco(_item("ti", sem_persona)))
    assert html.count('<span class="chip alert">ausente</span>') == 1
    assert "Manifesto" not in html


def test_peca_velha_no_pacote_nao_volta_a_coluna():
    """Pacote de monta-sessao deprecado ainda traz `oficio`: a tela nao o mede."""
    html = bloco_cadeiras(_bloco(_item("ti", [*PACOTE_DE_HOJE, _peca("oficio")])))
    assert "Manifesto" not in html
    assert "ausente" not in html


def test_linha_indisponivel_cobre_as_colunas_que_sobraram():
    indisponivel = {"cadeira": "ti", "lido_em": 1000.0, "estado": "indisponivel",
                    "motivo": "timeout apos 15s", "dados": None}
    html = bloco_cadeiras(_bloco(indisponivel))
    cabecalho = html.split("<thead>")[1].split("</thead>")[0]
    assert cabecalho.count("<th") == 4            # Cadeira, Persona, Mesa, acao
    assert "<td colspan='2'>" in html             # Persona + Mesa
    assert "timeout apos 15s" in html
