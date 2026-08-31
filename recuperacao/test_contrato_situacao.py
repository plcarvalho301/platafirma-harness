"""Testes de contrato e conformidade de `situacao` (#2953, arq:0085 §4, §2).

Invariantes conferidas:
1. Lê a cadeia viva (impressão -> estado de serviço) e reporta payload {servivel, desde, impressao_id, degrau}.
2. Degrau mapeia nos estados canônicos (ancorado, declarado-não-servindo, sem-obra-não-julgado, órfão).
3. Procedência completa no item (invariante 1 do §3).
4. Envelope vazio ≤ 40 tokens medido com qwen2.5.json (invariante 3 do §3).
5. Uma linha por fonte consultada (invariante 4).
6. Sujeito não entra no envelope (invariante 5).
7. Fonte indisponível responde `fonte-nao-indexada` declarada, nunca zero (§4).
8. PEP nega por concessão quando sujeito sem acesso.
9. CLI `bin/situacao` obedece contrato de chamada e saída.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from recuperacao.acervo_leitor import (
    CatalogoAcervo,
    ImpressaoInfo,
    ObraInfo,
)
from recuperacao.adaptadores.base import FonteIndisponivel
from recuperacao.disjuntor import Disjuntor, EstadoDisjuntor, Painel
from recuperacao.envelope import (
    Casamento,
    Causa,
    Cobertura,
    ContratoViolado,
    Fonte,
    VersaoTipo,
)
from recuperacao.pep import PEP
from recuperacao.resolvedor import EstadoConceito
from recuperacao.situacao import situacao

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
TOKENIZADOR = os.path.join(RAIZ, "opt", "tokenizers", "qwen2.5.json")
BIN_SITUACAO = Path(__file__).resolve().parents[1] / "bin" / "situacao"


def catalogo_situacao_mock() -> CatalogoAcervo:
    """Catálogo determinístico para testes de situação."""
    cat = CatalogoAcervo()

    # Obra 1: Ancorada (classificada com impressão servindo)
    cat.obras["o1"] = ObraInfo(
        id="o1",
        titulo="Clean Architecture",
        objeto="acervo/1111111111111111111111111111111111111111111111111111111111111111",
        dominio="engenharia-software",
        subdominio="artesania-e-design-de-codigo",
    )
    cat.impressoes_por_obra["o1"] = [
        ImpressaoInfo(
            id="imp-001",
            obra_id="o1",
            estado="servindo",
            criada_em="2026-08-15T10:00:00Z",
        )
    ]

    # Obra 2: Declarada não servindo (classificada, mas sem impressão ativa/servindo)
    cat.obras["o2"] = ObraInfo(
        id="o2",
        titulo="Legacy Code",
        objeto="acervo/2222222222222222222222222222222222222222222222222222222222222222",
        dominio="engenharia-software",
        subdominio="artesania-e-design-de-codigo",
    )
    cat.impressoes_por_obra["o2"] = [
        ImpressaoInfo(
            id="imp-002",
            obra_id="o2",
            estado="em_construcao",
            criada_em="2026-08-20T10:00:00Z",
        )
    ]

    # Obra 3: Órfã (sem classificação)
    cat.obras["o3"] = ObraInfo(
        id="o3",
        titulo="Documento Avulso Sem Metadados",
        objeto="acervo/3333333333333333333333333333333333333333333333333333333333333333",
        dominio=None,
        subdominio=None,
    )
    cat.impressoes_por_obra["o3"] = [
        ImpressaoInfo(
            id="imp-003",
            obra_id="o3",
            estado="servindo",
            criada_em="2026-08-01T10:00:00Z",
        )
    ]

    for o in cat.obras.values():
        cat.obras_por_titulo.setdefault(o.titulo.lower(), []).append(o)

    cat.carimbo = "acervo:mock-sit"
    return cat


# =============================================================================
# 1. Testes de Contrato de Situação
# =============================================================================


def test_situacao_ancorado():
    """Obra classificada e com impressão servindo reporta degrau ancorado e servivel True."""
    cat = catalogo_situacao_mock()
    env = situacao("Clean Architecture", catalogo=cat)

    assert len(env.linhas) == 1
    assert env.linhas[0].fonte == Fonte.ACERVO
    assert len(env.itens) == 1

    item = env.itens[0]
    assert item.procedencia.chave == "acervo:1111111111111111111111111111111111111111111111111111111111111111"
    assert item.conteudo is not None

    payload = json.loads(item.conteudo)
    assert payload["servivel"] is True
    assert payload["desde"] == "2026-08-15T10:00:00Z"
    assert payload["impressao_id"] == "imp-001"
    assert payload["degrau"] == str(EstadoConceito.ANCORADO)


def test_situacao_declarado_nao_servindo():
    """Obra sem impressão em estado 'servindo' reporta declarado-nao-servindo e servivel False."""
    cat = catalogo_situacao_mock()
    env = situacao("Legacy Code", catalogo=cat)

    assert len(env.itens) == 1
    payload = json.loads(env.itens[0].conteudo)
    assert payload["servivel"] is False
    assert payload["desde"] is None
    assert payload["degrau"] == str(EstadoConceito.DECLARADO_NAO_SERVINDO)


def test_situacao_orfao():
    """Obra sem classificação (sem domínio/subdomínio/conceito) reporta degrau orfao."""
    cat = catalogo_situacao_mock()
    env = situacao("Documento Avulso Sem Metadados", catalogo=cat)

    assert len(env.itens) == 1
    payload = json.loads(env.itens[0].conteudo)
    assert payload["degrau"] == str(EstadoConceito.ORFAO)


def test_situacao_obra_inexistente_retorna_vazio():
    """Obra que não existe no acervo vivo retorna envelope vazio."""
    cat = catalogo_situacao_mock()
    env = situacao("Obra Inexistente Fantasma XYZ", catalogo=cat)
    assert env.cobertura == Cobertura.VAZIA
    assert env.itens == []


def test_situacao_sujeito_nao_entra_no_envelope():
    """Invariante 5: o sujeito nunca aparece no envelope."""
    cat = catalogo_situacao_mock()
    env = situacao("Clean Architecture", sujeito="claudinho-dados", catalogo=cat)
    d = env.para_json()
    assert "sujeito" not in d
    assert "sujeito" not in json.dumps(d)


def test_situacao_vazio_cabe_no_teto_40_tokens():
    """Invariante 3: envelope vazio ≤ 40 tokens no tokenizador."""
    cat = catalogo_situacao_mock()
    env = situacao("Inexistente", catalogo=cat)
    texto = env.para_texto()

    if os.path.isfile(TOKENIZADOR):
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(TOKENIZADOR)
        n = len(tok.encode(texto).ids)
        assert n <= 40, f"envelope vazio a {n} tokens (teto 40): {texto}"
    else:
        assert len(texto.encode("utf-8")) <= 120


def test_situacao_fonte_indisponivel_responde_nao_indexada_nunca_zero():
    """Regra dura arq:0085 §4: fonte que não alcança o vivo responde indeterminavel, nunca zero."""
    env = situacao("Clean Architecture", raiz="/caminho/inexistente")
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA
    assert env.linhas[0].causa in (Causa.SEM_ROTA, Causa.FORA_DO_AR)
    assert env.itens == []


def test_situacao_pep_negativo():
    """PEP recusa acesso quando o sujeito não tem concessão."""
    class PEPMudo(PEP):
        def autoriza(self, *args, **kwargs):
            from recuperacao.pep import Negativa
            return [Negativa(fonte=Fonte.ACERVO, alvo="acervo:*", regra="padrao", motivo="negado")]

    env = situacao("Clean Architecture", catalogo=catalogo_situacao_mock(), pep=PEPMudo())
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA
    assert env.linhas[0].causa == Causa.SEM_CONCESSAO


def test_situacao_disjuntor_aberto():
    """Disjuntor aberto responde em 0 ms com disjuntor-aberto."""
    painel = Painel()
    painel[Fonte.ACERVO]._estado = EstadoDisjuntor.ABERTO
    painel[Fonte.ACERVO]._aberto_em = 10000000000.0

    env = situacao("Clean Architecture", catalogo=catalogo_situacao_mock(), painel=painel)
    assert env.linhas[0].causa == Causa.DISJUNTOR_ABERTO
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA


# =============================================================================
# 2. Testes de Execução CLI de bin/situacao
# =============================================================================


def test_bin_situacao_sem_argumento_sai_2():
    """Chamada sem argumentos imprime o uso e sai com código 2."""
    p = subprocess.run([sys.executable, str(BIN_SITUACAO)], capture_output=True, text=True)
    assert p.returncode == 2
    assert "uso:" in p.stderr


def test_bin_situacao_ajuda_sai_2():
    """-h/--help sai com código 2."""
    p = subprocess.run([sys.executable, str(BIN_SITUACAO), "-h"], capture_output=True, text=True)
    assert p.returncode == 2
    assert "uso:" in p.stderr


def test_bin_situacao_executa_e_emite_payload():
    """Execução com obra retorna envelope com payload formatado."""
    p = subprocess.run(
        [sys.executable, str(BIN_SITUACAO), "2020-devops-transformation-google-cloud-dora", "--json"],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    d = json.loads(p.stdout)
    assert "cobertura" in d
    assert len(d.get("itens", [])) >= 1
    conteudo = json.loads(d["itens"][0]["conteudo"])
    assert "degrau" in conteudo
    assert "servivel" in conteudo


# =============================================================================
# Regressão: ramo `cache is not None` chama a API real do Cache (le/grava).
# Mesmo bug de `descobrir` — cache.obtem/grava-4-args escapavam do except
# SemCache. Trava o contrato de chamada. arq:0085.
# =============================================================================


class _CacheFalsoSit:
    """Cache mínimo que honra a API real (`le`/`grava`)."""

    def __init__(self, retorno=None):
        self.retorno = retorno
        self.leu: list = []
        self.gravou: list = []

    def le(self, fonte, ch):
        self.leu.append((fonte, ch))
        return self.retorno

    def grava(self, fonte, ch, r):
        self.gravou.append((fonte, ch, r))
        return True


def test_situacao_miss_usa_api_real_do_cache():
    """Miss: consulta `cache.le` e grava `(fonte, ch, Resultado)` — 3 args, sem estourar."""
    from recuperacao.adaptadores.base import Resultado

    cache = _CacheFalsoSit(retorno=None)
    env = situacao("Clean Architecture", catalogo=catalogo_situacao_mock(), cache=cache)
    assert env is not None
    assert cache.leu, "situacao deve consultar cache.le no miss"
    assert cache.gravou, "situacao deve gravar o resultado no miss"
    for _fonte, _ch, r in cache.gravou:
        assert isinstance(r, Resultado)


def test_situacao_hit_de_cache_retorna_sem_reler_acervo():
    """Hit: `cache.le` devolve Resultado e situacao devolve-o sem regravar."""
    from recuperacao.adaptadores.base import Resultado

    semente = situacao("Clean Architecture", catalogo=catalogo_situacao_mock())
    cache = _CacheFalsoSit(retorno=Resultado(linha=semente.linhas[0], itens=semente.itens))
    env = situacao("Clean Architecture", catalogo=catalogo_situacao_mock(), cache=cache)
    assert env.linhas[0].fonte == Fonte.ACERVO
    assert not cache.gravou, "hit não deve regravar"
