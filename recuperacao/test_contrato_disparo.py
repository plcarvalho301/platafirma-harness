"""Contrato do eixo 2 — taxa de disparo por release (#2317). Spec §11 e §13.

A invariante central: **taxa sem denominador medido não sai como número.**
"""

from __future__ import annotations

import json

import pytest

from .disparo import Disparo, SemDenominador, delta, serie_disparo
from .fontes import Fonte


def _trilha(tmp_path, linhas, nome="leitura.jsonl") -> str:
    p = tmp_path / nome
    p.write_text("\n".join(json.dumps(l, ensure_ascii=False) for l in linhas) + "\n", encoding="utf-8")
    return str(p)


def _linha(**kw) -> dict:
    base = dict(ts="2026-08-21T10:00:00+00:00", tool="ops-mcp", sujeito="claudinho-IA",
                sessao="fita-1", fonte="acervo", cobertura="coberta", carimbo="bda62dd",
                hit=True, disjuntor="fechado", release="F4")
    base.update(kw)
    return base


# ------------------------------------------------- o denominador não se inventa

def test_sem_denominador_a_taxa_e_none_e_a_contagem_continua(tmp_path):
    s = serie_disparo(_trilha(tmp_path, [_linha()]), release="F4")
    assert s.sessoes == 1
    assert s.taxa is None
    assert s.denominador == "não medido"


def test_com_denominador_a_taxa_sai(tmp_path):
    t = _trilha(tmp_path, [_linha(sessao="a"), _linha(sessao="b")])
    s = serie_disparo(t, release="F4", sessoes_abertas=8)
    assert s.sessoes == 2
    assert s.taxa == 0.25


def test_taxa_nunca_aparece_como_zero_por_falta_de_denominador(tmp_path):
    s = serie_disparo(_trilha(tmp_path, [_linha()]))
    assert s.taxa is not None or "—" in s.para_texto()
    assert s.para_json()["taxa"] is None


def test_delta_recusa_sem_denominador_nas_duas_pontas(tmp_path):
    a = serie_disparo(_trilha(tmp_path, [_linha(release="F3")], "a.jsonl"), release="F3",
                      sessoes_abertas=10)
    b = serie_disparo(_trilha(tmp_path, [_linha()], "b.jsonl"), release="F4")
    with pytest.raises(SemDenominador):
        delta(a, b)


def test_delta_com_as_duas_medidas(tmp_path):
    a = serie_disparo(_trilha(tmp_path, [_linha(release="F3")], "a.jsonl"), release="F3",
                      sessoes_abertas=10)
    b = serie_disparo(_trilha(tmp_path, [_linha(sessao="x"), _linha(sessao="y")], "b.jsonl"),
                      release="F4", sessoes_abertas=10)
    d = delta(a, b)
    assert d["delta"] == 0.1
    assert d["parcial"] is True


# ------------------------------------------------- a unidade é a sessão, por sujeito

def test_a_unidade_e_a_sessao_nao_a_linha(tmp_path):
    """§11: uma linha por fonte alcançada — a mesma sessão alcança seis e dispara uma vez."""
    linhas = [_linha(fonte=str(f)) for f in Fonte]
    s = serie_disparo(_trilha(tmp_path, linhas), release="F4")
    assert s.sessoes == 1
    assert s.linhas == 6


def test_sujeitos_saem_nomeados(tmp_path):
    t = _trilha(tmp_path, [_linha(sujeito="claudinho-IA"), _linha(sujeito="claudinho-TI", sessao="f2")])
    s = serie_disparo(t, release="F4")
    assert s.sujeitos == ("claudinho-IA", "claudinho-TI")


def test_linha_sem_sessao_nao_conta(tmp_path):
    """Sem as duas identidades a linha não serve ao §11 — e não vira disparo fantasma."""
    s = serie_disparo(_trilha(tmp_path, [_linha(sessao="")]), release="F4")
    assert s.sessoes == 0
    assert s.linhas == 0


# ----------------------------------------------------------------- por fonte

def test_hit_e_miss_por_fonte(tmp_path):
    t = _trilha(tmp_path, [_linha(hit=True), _linha(hit=False, sessao="f2")])
    (acervo,) = serie_disparo(t, release="F4").por_fonte
    assert acervo.hit == 1
    assert acervo.miss == 1
    assert acervo.taxa_hit == 0.5


def test_taxa_hit_sem_caso_e_none(tmp_path):
    t = _trilha(tmp_path, [_linha(hit=None)])
    (acervo,) = serie_disparo(t, release="F4").por_fonte
    assert acervo.taxa_hit is None


def test_disjuntor_aberto_e_contado(tmp_path):
    t = _trilha(tmp_path, [_linha(disjuntor="aberto")])
    assert serie_disparo(t, release="F4").por_fonte[0].disjuntor_aberto == 1


def test_fonte_sem_linha_sai_nomeada(tmp_path):
    s = serie_disparo(_trilha(tmp_path, [_linha(fonte="board")]), release="F4")
    assert "acervo" in s.fontes_ausentes


# ------------------------------------------------------------ release e ruído

def test_filtra_por_release(tmp_path):
    t = _trilha(tmp_path, [_linha(release="F3"), _linha(release="F4", sessao="f2")])
    assert serie_disparo(t, release="F3").sessoes == 1
    assert serie_disparo(t).sessoes == 2


def test_linha_malformada_nao_derruba(tmp_path):
    p = tmp_path / "t.jsonl"
    p.write_text(json.dumps(_linha()) + "\n{quebrada\n", encoding="utf-8")
    assert serie_disparo(str(p), release="F4").linhas == 1


def test_trilha_inexistente_devolve_serie_vazia_e_parcial(tmp_path):
    s = serie_disparo(str(tmp_path / "nao-existe.jsonl"))
    assert s.sessoes == 0
    assert s.parcial


# ------------------------------------------------------ parcialidade declarada

def test_serie_e_sempre_parcial_ate_a_paridade_do_wiki_mcp(tmp_path):
    s = serie_disparo(_trilha(tmp_path, [_linha()]), release="F4")
    assert s.parcial
    assert "wiki-mcp" in s.motivo
    assert "PARCIAL" in s.para_texto()


def test_produtor_sem_paridade_e_nomeado(tmp_path):
    s = serie_disparo(_trilha(tmp_path, [_linha(tool="wiki-mcp")]), release="F4")
    assert "wiki-mcp" in s.motivo


def test_texto_declara_o_denominador_ausente():
    assert "não medido" in Disparo(release="F4", sessoes=3).para_texto()
