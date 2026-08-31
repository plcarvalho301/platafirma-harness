"""Testes de contrato e conformidade de `descobrir` (#2952, arq:0085 §5, §3).

Invariantes conferidas:
1. Procedência completa em todo item (invariante 1 do §3).
2. Envelope vazio ≤ 40 tokens medido com qwen2.5.json (invariante 3 do §3).
3. Uma linha por fonte consultada (invariante 4).
4. Sujeito não entra no envelope (invariante 5).
5. Varredura multi-eixo devolve união (OR), não interseção.
6. Dedupe por digest: obra que entra por 2 eixos aparece 1 vez, com os 2 eixos marcados.
7. Fonte indisponível responde `fonte-nao-indexada` declarada, nunca zero (§4).
8. PEP nega por concessão quando sujeito sem acesso.
9. CLI `bin/descobrir` obedece contrato de chamada e saída.
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
    ConceitoInfo,
    ImpressaoInfo,
    ObraInfo,
    SubdominioInfo,
)
from recuperacao.adaptadores.base import FonteIndisponivel
from recuperacao.descobrir import EIXOS_PADRAO, descobrir
from recuperacao.disjuntor import Disjuntor, EstadoDisjuntor, Painel
from recuperacao.envelope import (
    CAMPOS_PROIBIDOS,
    Casamento,
    Causa,
    Cobertura,
    ContratoViolado,
    Expansao,
    Fonte,
    VersaoTipo,
)
from recuperacao.pep import PEP

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
TOKENIZADOR = os.path.join(RAIZ, "opt", "tokenizers", "qwen2.5.json")
BIN_DESCOBRIR = Path(__file__).resolve().parents[1] / "bin" / "descobrir"


def catalogo_mock() -> CatalogoAcervo:
    """Catálogo determinístico para testes de contrato."""
    cat = CatalogoAcervo()

    # Obras
    # Obra 1: casa por titulo ("Padrao de Arquitetura") e por conceito ("design-patterns")
    cat.obras["o1"] = ObraInfo(
        id="o1",
        titulo="Padrao de Arquitetura de Software",
        objeto="acervo/1111111111111111111111111111111111111111111111111111111111111111",
        arquivo="padrao_arq.pdf",
        dominio="engenharia-software",
        subdominio="artesania-e-design-de-codigo",
    )
    # Obra 2: casa só por conceito ("design-patterns")
    cat.obras["o2"] = ObraInfo(
        id="o2",
        titulo="Clean Code",
        objeto="acervo/2222222222222222222222222222222222222222222222222222222222222222",
        arquivo="clean_code.pdf",
        dominio="engenharia-software",
        subdominio="artesania-e-design-de-codigo",
    )
    # Obra 3: casa só por subdominio ("seguranca-aplicacao")
    cat.obras["o3"] = ObraInfo(
        id="o3",
        titulo="Guia OWASP",
        objeto="acervo/3333333333333333333333333333333333333333333333333333333333333333",
        arquivo="owasp.pdf",
        dominio="seguranca-privacidade",
        subdominio="seguranca-aplicacao",
    )

    for o in cat.obras.values():
        cat.obras_por_titulo.setdefault(o.titulo.lower(), []).append(o)
        if o.subdominio:
            cat.subdominio_obras.setdefault(o.subdominio, set()).add(o.id)

    # Conceitos
    cat.conceitos["design-patterns"] = ConceitoInfo(
        slug="design-patterns",
        rotulo="Padrões de Projeto",
        outros_rotulos=("padroes de arquitetura", "design patterns"),
        definicao="Soluções reutilizáveis para problemas comuns de design de software.",
    )
    cat.conceitos["seguranca-web"] = ConceitoInfo(
        slug="seguranca-web",
        rotulo="Segurança Web",
        outros_rotulos=("appsec",),
        definicao="Práticas de proteção de aplicações web.",
    )

    # Subdominios
    cat.subdominios["artesania-e-design-de-codigo"] = SubdominioInfo(
        slug="artesania-e-design-de-codigo",
        rotulo="Artesania e Design de Código",
        dominio="engenharia-software",
        recorte="padrão, refatoração, teste, qualidade",
    )
    cat.subdominios["seguranca-aplicacao"] = SubdominioInfo(
        slug="seguranca-aplicacao",
        rotulo="Segurança de Aplicação",
        dominio="seguranca-privacidade",
        recorte="owasp, vulnerabilidade, appsec",
    )

    # Vínculos
    cat.obra_trata_de["o1"] = {"design-patterns"}
    cat.obra_trata_de["o2"] = {"design-patterns"}
    cat.conceito_obras["design-patterns"] = {"o1", "o2"}
    cat.obra_trata_de["o3"] = {"seguranca-web"}
    cat.conceito_obras["seguranca-web"] = {"o3"}

    cat.carimbo = "acervo:mock123"
    return cat


# =============================================================================
# 1. Testes de Contrato de Descoberta Multi-Eixo
# =============================================================================


def test_descobrir_uniao_tres_eixos_e_dedupe():
    """Prova que descobrir varre os três eixos, devolve a união e deduplica com marcação."""
    cat = catalogo_mock()
    env = descobrir(assunto="padrao", catalogo=cat, eixos=["titulo", "conceito", "subdominio"])

    assert len(env.linhas) == 1
    assert env.linhas[0].fonte == Fonte.ACERVO
    assert env.linhas[0].cobertura == Cobertura.NAO_CALIBRADA

    # o1 casa por titulo E conceito
    # o2 casa por conceito (rotulo "Padroes de Projeto") E subdominio (recorte contem "padrao")
    # Conjunto união: {o1, o2}
    ids_encontrados = {i.procedencia.chave for i in env.itens}
    assert "acervo:1111111111111111111111111111111111111111111111111111111111111111" in ids_encontrados
    assert "acervo:2222222222222222222222222222222222222222222222222222222222222222" in ids_encontrados

    # Cada obra entra uma única vez (dedupe)
    assert len(env.itens) == 2

    # Marcação de expansão em cada item
    item_o1 = next(i for i in env.itens if "1111" in i.procedencia.chave)
    assert item_o1.expansao is not None
    assert item_o1.expansao.conceito_origem == "padrao"
    assert "titulo" in item_o1.expansao.aresta
    assert "conceito" in item_o1.expansao.aresta
    assert item_o1.expansao.familia == "descoberta"


def test_descobrir_eixo_isolado():
    """Prova que restringir os eixos só pesquisa nos eixos selecionados."""
    cat = catalogo_mock()
    # Só por título: apenas o1 tem "Padrao" no título
    env_titulo = descobrir(assunto="padrao", catalogo=cat, eixos=["titulo"])
    assert len(env_titulo.itens) == 1
    assert "1111" in env_titulo.itens[0].procedencia.chave
    assert env_titulo.itens[0].expansao.aresta == "titulo"

    # Só por subdomínio: o3 casa "owasp"
    env_sub = descobrir(assunto="owasp", catalogo=cat, eixos=["subdominio"])
    assert len(env_sub.itens) == 1
    assert "3333" in env_sub.itens[0].procedencia.chave
    assert env_sub.itens[0].expansao.aresta == "subdominio"


def test_descobrir_eixo_invalido_levanta():
    """Eixo fora de titulo/conceito/subdominio rejeita como ContratoViolado."""
    cat = catalogo_mock()
    with pytest.raises(ContratoViolado):
        descobrir(assunto="padrao", catalogo=cat, eixos=["eixo_fantasma"])


def test_descobrir_procedencia_completa_e_invariantes():
    """Invariante 1: todo item tem procedência completa (fonte, chave acervo:*, versao digest)."""
    cat = catalogo_mock()
    env = descobrir(assunto="clean", catalogo=cat)
    assert len(env.itens) >= 1
    for item in env.itens:
        p = item.procedencia
        assert p.fonte == Fonte.ACERVO
        assert p.chave.startswith("acervo:")
        assert p.versao.tipo == VersaoTipo.DIGEST
        assert p.versao.valor is not None
        assert item.ref is not None


def test_descobrir_sujeito_nao_entra_no_envelope():
    """Invariante 5: o sujeito nunca aparece no envelope."""
    cat = catalogo_mock()
    env = descobrir(assunto="padrao", sujeito="claudinho-TI", catalogo=cat)
    d = env.para_json()
    assert "sujeito" not in d
    assert "sujeito" not in json.dumps(d)


def test_descobrir_vazio_cabe_no_teto_40_tokens():
    """Invariante 3: envelope vazio ≤ 40 tokens no tokenizador do modelo."""
    cat = catalogo_mock()
    env = descobrir(assunto="assunto_inexistente_xyz_12345", catalogo=cat)
    assert env.cobertura == Cobertura.VAZIA
    assert env.itens == []
    texto = env.para_texto()

    if os.path.isfile(TOKENIZADOR):
        from tokenizers import Tokenizer

        tok = Tokenizer.from_file(TOKENIZADOR)
        n = len(tok.encode(texto).ids)
        assert n <= 40, f"envelope vazio a {n} tokens (teto 40): {texto}"
    else:
        # Fallback se tokenizador não estiver no host: comprimento de bytes é compacto
        assert len(texto.encode("utf-8")) <= 120


def test_descobrir_fonte_indisponivel_responde_nao_indexada_nunca_zero():
    """Regra dura arq:0085 §4: fonte que não alcança o vivo responde indeterminavel, nunca zero."""
    # Injetando falha proposital
    env = descobrir(assunto="qualquer", raiz="/caminho/completamente/inexistente")
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA
    assert len(env.linhas) == 1
    assert env.linhas[0].causa in (Causa.SEM_ROTA, Causa.FORA_DO_AR)
    assert env.itens == []
    assert env.aviso != []


def test_descobrir_pep_negativo():
    """PEP recusa acesso quando o sujeito não tem concessão."""
    class PEPMudo(PEP):
        def autoriza(self, *args, **kwargs):
            from recuperacao.pep import Negativa
            return [Negativa(fonte=Fonte.ACERVO, alvo="acervo:*", regra="padrao", motivo="negado nos testes")]

    env = descobrir(assunto="padrao", catalogo=catalogo_mock(), pep=PEPMudo())
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA
    assert env.linhas[0].causa == Causa.SEM_CONCESSAO
    assert env.falta is not None
    assert env.proximo is not None


def test_descobrir_disjuntor_aberto():
    """Disjuntor aberto responde em 0 ms com disjuntor-aberto."""
    painel = Painel()
    painel[Fonte.ACERVO]._estado = EstadoDisjuntor.ABERTO
    painel[Fonte.ACERVO]._aberto_em = 10000000000.0

    env = descobrir(assunto="padrao", catalogo=catalogo_mock(), painel=painel)
    assert env.linhas[0].causa == Causa.DISJUNTOR_ABERTO
    assert env.cobertura == Cobertura.FONTE_NAO_INDEXADA


# =============================================================================
# 2. Testes de Execução CLI de bin/descobrir
# =============================================================================


def test_bin_descobrir_sem_argumento_sai_2():
    """Chamada sem argumentos imprime o uso e sai com código 2."""
    p = subprocess.run([sys.executable, str(BIN_DESCOBRIR)], capture_output=True, text=True)
    assert p.returncode == 2
    assert "uso:" in p.stderr


def test_bin_descobrir_ajuda_sai_2():
    """-h/--help sai com código 2."""
    p = subprocess.run([sys.executable, str(BIN_DESCOBRIR), "-h"], capture_output=True, text=True)
    assert p.returncode == 2
    assert "uso:" in p.stderr


def test_bin_descobrir_executa_e_emite_envelope():
    """Execução com termo retorna envelope formatado."""
    p = subprocess.run(
        [sys.executable, str(BIN_DESCOBRIR), "seguranca", "--json"],
        capture_output=True,
        text=True,
    )
    assert p.returncode == 0
    d = json.loads(p.stdout)
    assert "cobertura" in d


# =============================================================================
# Regressão: ramo `cache is not None` chama a API real do Cache (le/grava).
# Bug corrigido: descobrir chamava cache.obtem (inexistente -> AttributeError)
# e cache.grava com 4 args (assinatura é 3 -> TypeError); ambos escapavam do
# except SemCache. Nenhum teste exercia o ramo, por isso passou. arq:0085.
# =============================================================================


class _CacheFalso:
    """Cache mínimo que honra a API real (`le`/`grava`) — fake, não mock."""

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


def test_descobrir_miss_usa_api_real_do_cache():
    """Miss: consulta `cache.le` e grava `(fonte, ch, Resultado)` — 3 args, sem estourar."""
    from recuperacao.adaptadores.base import Resultado

    cache = _CacheFalso(retorno=None)
    env = descobrir(assunto="padrao", catalogo=catalogo_mock(), cache=cache)
    assert env is not None
    assert cache.leu, "descobrir deve consultar cache.le no miss"
    assert cache.gravou, "descobrir deve gravar o resultado no miss"
    for _fonte, _ch, r in cache.gravou:
        assert isinstance(r, Resultado)


def test_descobrir_hit_de_cache_retorna_sem_reler_acervo():
    """Hit: `cache.le` devolve Resultado e descobrir devolve-o sem regravar."""
    from recuperacao.adaptadores.base import Resultado

    semente = descobrir(assunto="padrao", catalogo=catalogo_mock())
    cache = _CacheFalso(retorno=Resultado(linha=semente.linhas[0], itens=semente.itens))
    env = descobrir(assunto="padrao", catalogo=catalogo_mock(), cache=cache)
    assert env.linhas[0].fonte == Fonte.ACERVO
    assert not cache.gravou, "hit não deve regravar"
