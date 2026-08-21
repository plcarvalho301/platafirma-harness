"""Contrato do veredito instrumentado (#2312). Spec §11 e §13.

A invariante central deste arquivo: **série parcial nunca se publica como completa.**
"""

from __future__ import annotations

import json

import pytest

from .envelope import Cobertura, Item, LinhaFonte, Procedencia, Sinal, Versao, VersaoTipo
from .adaptadores.base import Resultado, monta_envelope
from .fontes import Fonte
from .gate import Gate
from .resolvedor import Resolvedor, Secao
from .veredito import LinhaVeredito, instrumenta, linha_de, serie

SHA = "df70f05c9a1b4e2d8c3f6a7b0e1d2c3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d"
CHAVE = f"acervo:{SHA}#in-memory-caching"


def _secao(**kw) -> Secao:
    base = dict(
        obra="Nygard, Release It! (2007)", ancora="in-memory-caching", impressao="4b6f610a",
        titulo="In-Memory Caching", hierarquia=("Stability Patterns",), pagina=208,
    )
    base.update(kw)
    return Secao(**base)


def _envelope(chave: str, cheio: bool = True):
    if not cheio:
        return monta_envelope([Resultado(linha=LinhaFonte(fonte=Fonte("acervo"), cobertura=Cobertura.VAZIA))])
    proc = Procedencia(fonte=Fonte("acervo"), chave=chave,
                       versao=Versao(tipo=VersaoTipo.DIGEST, valor="4b6f610a"))
    linha = LinhaFonte(fonte=Fonte("acervo"), cobertura=Cobertura.COBERTA,
                       sinal=Sinal(medida="sim", valor=0.72, piso=0.55))
    return monta_envelope([Resultado(linha=linha, itens=[Item(procedencia=proc, conteudo="…")])])


def _gate(achou: bool = True) -> Gate:
    return Gate(lambda c, servindo=True: _envelope(c, achou), Resolvedor(lambda _: _secao()))


def _parecer(achou: bool = True, texto: str = f"Ver {CHAVE}."):
    return _gate(achou).julga(texto)


# ------------------------------------------------- as duas identidades (§11)

def test_linha_carrega_sujeito_e_sessao():
    v = _parecer().vereditos[0]
    linha = linha_de(v, tool="ops-mcp", sujeito="claudinho-IA", sessao="fita-77")
    assert linha.sujeito == "claudinho-IA"
    assert linha.sessao == "fita-77"
    assert linha.fonte == "acervo"


@pytest.mark.parametrize(("sujeito", "sessao"), [("", "fita-77"), ("claudinho-IA", ""), ("", "")])
def test_linha_sem_as_duas_identidades_nao_grava(tmp_path, sujeito, sessao):
    with pytest.raises(ValueError):
        instrumenta(_parecer(), tool="ops-mcp", sujeito=sujeito, sessao=sessao,
                    trilha=str(tmp_path / "t.jsonl"))


def test_uma_linha_por_chave_julgada_nao_por_chamada():
    texto = f"Ver {CHAVE} e também acervo:{SHA}#circuit-breaker."
    linhas = _gate().julga(texto).vereditos
    assert len(linhas) == 2


# ------------------------------------------------------ estado não medido

def test_estado_sai_nulo_e_declarado_quando_o_predicado_esta_desligado():
    """`veredito_por_conceito` desligado: campo nulo COM a marca, nunca campo ausente."""
    linha = linha_de(_parecer().vereditos[0], tool="ops-mcp", sujeito="s", sessao="f")
    d = linha.para_json()
    assert "estado" in d
    assert d["estado"] is None
    assert d["estado_medido"] is False


def test_estado_entra_quando_medido():
    linha = linha_de(_parecer().vereditos[0], tool="ops-mcp", sujeito="s", sessao="f",
                     estado_medido=True)
    assert linha.para_json()["estado"] == "ancorado"


# --------------------------------------------------------------- a trilha

def test_grava_jsonl_uma_linha_por_veredito(tmp_path):
    t = tmp_path / "t.jsonl"
    instrumenta(_parecer(), tool="ops-mcp", sujeito="claudinho-IA", sessao="f", trilha=str(t))
    linhas = t.read_text(encoding="utf-8").strip().splitlines()
    assert len(linhas) == 1
    assert json.loads(linhas[0])["chave"] == CHAVE


def test_trilha_e_append_nao_sobrescreve(tmp_path):
    t = tmp_path / "t.jsonl"
    for _ in range(3):
        instrumenta(_parecer(), tool="ops-mcp", sujeito="s", sessao="f", trilha=str(t))
    assert len(t.read_text(encoding="utf-8").strip().splitlines()) == 3


# ----------------------------------------------------------------- a série

def test_serie_conta_por_fonte_e_por_julgamento(tmp_path):
    t = str(tmp_path / "t.jsonl")
    instrumenta(_parecer(True), tool="ops-mcp", sujeito="s", sessao="f", trilha=t)
    instrumenta(_parecer(False), tool="ops-mcp", sujeito="s", sessao="f", trilha=t)
    s = serie(t)
    (acervo,) = [x for x in s.por_fonte if x.fonte == "acervo"]
    assert acervo.citavel == 1
    assert acervo.fabricada == 1
    assert acervo.taxa_recusa == 0.5


def test_serie_e_sempre_declarada_parcial_ate_a_paridade_do_wiki_mcp(tmp_path):
    t = str(tmp_path / "t.jsonl")
    instrumenta(_parecer(), tool="ops-mcp", sujeito="s", sessao="f", trilha=t)
    s = serie(t)
    assert s.parcial
    assert "wiki-mcp" in s.motivo
    assert "PARCIAL" in s.para_texto()


def test_produtor_sem_paridade_e_nomeado_no_motivo(tmp_path):
    t = str(tmp_path / "t.jsonl")
    instrumenta(_parecer(), tool="wiki-mcp", sujeito="s", sessao="f", trilha=t)
    assert "wiki-mcp" in serie(t).motivo


def test_taxa_de_recusa_sem_caso_e_none_nao_zero(tmp_path):
    """0,0 com denominador zero é número inventado."""
    s = serie(str(tmp_path / "vazia.jsonl"))
    assert s.linhas == 0
    assert s.por_fonte == ()


def test_fontes_sem_linha_saem_nomeadas(tmp_path):
    t = str(tmp_path / "t.jsonl")
    instrumenta(_parecer(), tool="ops-mcp", sujeito="s", sessao="f", trilha=t)
    assert "board" in serie(t).fontes_ausentes
    assert "acervo" not in serie(t).fontes_ausentes


def test_linha_malformada_nao_derruba_a_serie(tmp_path):
    t = tmp_path / "t.jsonl"
    instrumenta(_parecer(), tool="ops-mcp", sujeito="s", sessao="f", trilha=str(t))
    with t.open("a", encoding="utf-8") as f:
        f.write("{isto não é json\n")
    assert serie(str(t)).linhas == 1


def test_serie_filtra_por_release(tmp_path):
    t = str(tmp_path / "t.jsonl")
    instrumenta(_parecer(), tool="ops-mcp", sujeito="s", sessao="f", trilha=t, release="F3")
    instrumenta(_parecer(), tool="ops-mcp", sujeito="s", sessao="f", trilha=t, release="F4")
    assert serie(t, release="F3").linhas == 1
    assert serie(t).linhas == 2


def test_a_serie_com_o_predicado_desligado_e_o_baseline(tmp_path):
    """§13: instrumentar primeiro, não segurar por baseline."""
    t = str(tmp_path / "t.jsonl")
    instrumenta(_parecer(), tool="ops-mcp", sujeito="s", sessao="f", trilha=t)
    s = serie(t)
    assert s.linhas == 1
    assert s.estado_medido is False
    assert "desligado" in s.motivo


def test_json_da_serie_traz_parcial_e_motivo(tmp_path):
    t = str(tmp_path / "t.jsonl")
    instrumenta(_parecer(), tool="ops-mcp", sujeito="s", sessao="f", trilha=t)
    d = serie(t).para_json()
    assert d["parcial"] is True
    assert d["motivo"]
    assert d["por_fonte"][0]["fonte"] == "acervo"
