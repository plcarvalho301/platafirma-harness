"""Contrato do roteador de chapeu (recursao do P2). Testa o modulo ISOLADO — a desconfianca
do dono e sobre o fluxo, entao o fluxo tem prova propria, sem montar sessao nem tocar disco
(exceto os testes que leem os chapeus reais da cadeira ia no disco, em abertura/)."""

from __future__ import annotations

import os

from recuperacao import roteador_chapeu as rot

RAIZ_CHAPEUS = os.path.join(os.environ.get("PF_RAIZ", os.path.expanduser("~/AI")),
                            "platafirma-harness", "abertura")

R = [
    rot.Rota(slug="harness", rotulos=("Janela de contexto", "Degradacao em contexto longo")),
    rot.Rota(slug="contexto", rotulos=("Pipeline RAG", "Reranking")),
    rot.Rota(slug="agente", rotulos=("Loop agentico", "Multiagente")),
]


def test_casa_e_puro_e_conta_por_slug():
    a = rot.casa("orcamento e janela de contexto aqui", R)
    assert a == {"harness": 1}, a


def test_plural_nao_zera_o_casamento():
    # "reranking" declarado; pergunta no plural nao deveria matar (regua do motor)
    a = rot.casa("pipeline rag e rerankings", R)
    assert "contexto" in a


def test_decide_por_margem_estrita():
    d = rot.decide("janela de contexto e degradacao em contexto longo", R)
    assert d.slug == "harness" and d.via == "deterministico", d


def test_empate_cai_no_fallback():
    # um rotulo de harness e um de contexto: empate 1x1 -> None
    d = rot.decide("janela de contexto e pipeline rag", R)
    assert d.slug is None and d.via == "fallback", d


def test_sem_casamento_e_fallback():
    d = rot.decide("bom dia, tudo certo?", R)
    assert d.slug is None and d.via == "fallback"


def test_escolhe_sem_pergunta_e_fallback():
    d = rot.escolhe("", "ia", RAIZ_CHAPEUS)
    assert d.slug is None and d.via == "fallback"


def test_escolhe_forcado_vence_tudo():
    d = rot.escolhe("qualquer coisa", "ia", RAIZ_CHAPEUS, forcado="contexto")
    assert d.slug == "contexto" and d.via == "comando"


def test_forcado_inexistente_nao_inventa_chapeu():
    d = rot.escolhe("x", "ia", RAIZ_CHAPEUS, forcado="nao-existe")
    assert d.slug is None and d.via == "fallback"


def test_rotas_do_disco_traz_um_slug_por_subdir_de_chapeu():
    # so subdir vira rota; persona.md (arquivo) nao.
    rotas = rot.rotas_do_disco("ia", RAIZ_CHAPEUS)
    slugs = {r.slug for r in rotas}
    assert "persona" not in slugs
    assert {"agente", "contexto", "engenharia-de-harness"} <= slugs


def test_rotas_do_disco_popula_rotulos_do_artefato_gerado():
    # #250/#314: rotas_do_disco le os gatilhos de abertura/rotas-chapeu.json (gerado do
    # golden record). O chapeu com (b) preenchida vem com rotulos != () — o (a) acorda.
    # Regua: relacao declarada, entao o gatilho tem de existir na tabela do chapeu.
    rotas = {r.slug: r for r in rot.rotas_do_disco("ia", RAIZ_CHAPEUS)}
    harness = rotas["engenharia-de-harness"]
    assert harness.rotulos, "artefato rotas-chapeu.json nao populou o chapeu harness"
    normalizados = {rot._normaliza(x) for x in harness.rotulos}
    assert rot._normaliza("Complexidade assintotica") in normalizados


def test_escolhe_roteia_pelo_disco_real_via_deterministico():
    # ponta a ponta com o disco real: pergunta de harness -> chapeu certo, via (a).
    d = rot.escolhe("como reduzir a complexidade assintotica do rerank", "ia", RAIZ_CHAPEUS)
    assert d.slug == "engenharia-de-harness" and d.via == "deterministico", d


def test_semantico_declara_inatividade_nao_finge():
    d = rot.roteia_semantico("qualquer", R)
    assert d.slug is None and "embed" in d.motivo


if __name__ == "__main__":
    import sys
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    fail = 0
    for f in funcs:
        try:
            f()
            print(f"ok   {f.__name__}")
        except AssertionError as e:
            fail += 1
            print(f"FAIL {f.__name__}: {e}")
    print(f"\n{len(funcs) - fail}/{len(funcs)} passaram")
    sys.exit(1 if fail else 0)
