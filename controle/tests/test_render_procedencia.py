"""Bloco Procedencia da tela do plano de controle contra o veredito comum (#3267).

O painel dizia «0 · sem divergencia» com 10 servicos divergentes e 18 sem leitura: o
predicado lia `resultado`/`servicos`, chaves que o veredito comum (#3142) nao tem, e caia
sempre no ramo verde. O veredito e {ancora, classe, alvo, release, itens: [{nome, estado,
desde, motivo}]}, com estado em conforme | divergente | indeterminavel.

Prova: o numero de divergentes e de indeterminados sai de `itens[].estado`; so indeterminados
nao pinta verde; tudo conforme e zero; dado sem a lista `itens` e «sem leitura», nunca verde
(ausencia nao e saude); o bloco inteiro da recepcao mostra os dois numeros.
Nao prova: o verbo `release conferir` nem a rota HTTP (ficam em test_conferir_veredito e
test_web_fumaca).
"""
from __future__ import annotations

from harness_controle.agregador import bloco_de
from harness_controle.render import _predicado, bloco_procedencia
from harness_controle.verbos import ResultadoVerbo


def _bloco_conferir(itens):
    # `conferir` sai 1 quando ha divergencia, e o agregador ainda assim le o JSON (estado ok)
    return bloco_de(ResultadoVerbo(True, {
        "ancora": "a", "classe": "servico", "alvo": None, "release": "abc1234", "itens": itens,
    }, None, 1, 0.01), agora=1000.0)


def _item(estado):
    return {"nome": "x", "estado": estado, "desde": "2026-10-04T00:00:00Z", "motivo": None}


def test_conta_divergentes_e_indeterminados_do_veredito_comum():
    itens = [_item("conforme")] * 3 + [_item("divergente")] * 10 + [_item("indeterminavel")] * 18
    html = _predicado("conferir servico", _bloco_conferir(itens))
    assert '<span class="valor mal num">10</span>' in html
    assert '<span class="chip alert">divergem</span>' in html
    assert '<span class="chip caveat">18 sem leitura</span>' in html
    assert "sem divergência" not in html


def test_so_indeterminados_nao_pinta_verde():
    itens = [_item("conforme")] * 5 + [_item("indeterminavel")] * 2
    html = _predicado("conferir servico", _bloco_conferir(itens))
    assert '<span class="chip caveat">2 sem leitura</span>' in html
    assert "sem divergência" not in html and "chip calmo" not in html and "chip alert" not in html


def test_tudo_conforme_e_zero_sem_divergencia():
    html = _predicado("conferir servico", _bloco_conferir([_item("conforme")] * 4))
    assert '<span class="valor num">0</span>' in html
    assert '<span class="chip calmo">sem divergência</span>' in html


def test_formato_desconhecido_e_sem_leitura_nunca_verde():
    """Dados sem a lista `itens` (formato antigo ou verbo mudado): ausencia de leitura."""
    antigo = bloco_de(ResultadoVerbo(True, {"resultado": "divergente", "servicos": [{"divergencias": ["x"]}]},
                                     None, 1, 0.01), agora=1000.0)
    html = _predicado("conferir servico", antigo)
    assert '<span class="chip caveat">sem leitura</span>' in html
    assert "sem divergência" not in html


def test_bloco_sem_leitura_do_verbo_segue_sem_leitura():
    morto = {"estado": "indisponivel", "motivo": "timeout apos 60s", "dados": None, "lido_em": 1000.0}
    assert '<span class="chip caveat">sem leitura</span>' in _predicado("conferir servico", morto)


def test_bloco_procedencia_mostra_os_numeros_do_incidente():
    servico = _bloco_conferir([_item("divergente")] * 10 + [_item("indeterminavel")] * 18)
    limpo = _bloco_conferir([_item("conforme")])
    skills = {"estado": "ok", "lido_em": 1000.0, "itens": []}
    html = bloco_procedencia(servico, limpo, skills, limpo)
    trecho_servico = html.split("conferir servico")[1].split("conferir verbo")[0]
    assert ">10<" in trecho_servico and "divergem" in trecho_servico and "18 sem leitura" in trecho_servico
    trecho_verbo = html.split("conferir verbo")[1].split("conferir skill")[0]
    assert "sem divergência" in trecho_verbo
