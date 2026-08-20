"""Contrato do envelope. `python3 -m pytest recuperacao/ -q` da raiz do repo.

Cada teste corresponde a uma linha do §3 da `spec_recuperador.md`. Invariante que não
tem teste aqui não está conferida — e o §3 diz, com todas as letras, que elas são
conferidas em teste de contrato e **não por leitura**.

O teto de 40 tokens (inv. 3) FALHA O BUILD. É o único número da spec que é meta dura:
é ele que impede o envelope de virar imposto por giro.
"""

from __future__ import annotations

import json
import os

import pytest

from recuperacao.envelope import (
    CAMPOS_PROIBIDOS,
    Casamento,
    Causa,
    Cobertura,
    ContratoViolado,
    Envelope,
    Expansao,
    Item,
    LinhaFonte,
    Procedencia,
    Sinal,
    Versao,
    VersaoTipo,
    linha_disjuntor_aberto,
)
from recuperacao.fontes import CLASSE, PREFIXO_CHAVE, TIMEOUT_MS, Classe, Fonte, timeout_ms

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
TOKENIZADOR = os.path.join(RAIZ, "opt", "tokenizers", "qwen2.5.json")
TETO_ENVELOPE_VAZIO = 40


# ---------------------------------------------------------------------- construtores


def versao(tipo=VersaoTipo.SEQ, valor="1") -> Versao:
    return Versao(tipo=tipo, valor=valor)


def proc(fonte=Fonte.BOARD, chave=None, **kw) -> Procedencia:
    chave = chave or PREFIXO_CHAVE[fonte][0] + "1"
    return Procedencia(fonte=fonte, chave=chave, versao=kw.pop("versao", versao()), **kw)


def item(fonte=Fonte.BOARD, **kw) -> Item:
    kw.setdefault("ref", "x")
    return Item(procedencia=proc(fonte), **kw)


def sinal_ok(valor=0.9, piso=0.79) -> Sinal:
    return Sinal(medida="rerank", valor=valor, piso=piso)


# ============================================================ 1. vocabulário fechado


def test_os_seis_valores_de_cobertura():
    assert {c.value for c in Cobertura} == {
        "coberta", "fraca", "ausente", "nao-calibrada", "fonte-nao-indexada", "vazia",
    }


def test_os_quatro_valores_de_casamento():
    assert {c.value for c in Casamento} == {
        "exato", "flexionado", "alternativo-de-chapeu", "aproximado",
    }


def test_os_seis_valores_de_causa():
    assert {c.value for c in Causa} == {
        "sem-rota", "fora-do-ar", "sem-indice", "timeout", "disjuntor-aberto", "sem-concessao",
    }


def test_os_cinco_tipos_de_versao():
    assert {v.value for v in VersaoTipo} == {"sha", "revid", "seq", "stream-id", "digest"}


def test_as_seis_fontes_e_a_classe_de_cada_uma():
    assert {f.value for f in Fonte} == {"board", "fila", "mesa", "registro", "wiki", "acervo"}
    assert CLASSE[Fonte.ACERVO] is Classe.SEMANTICA
    assert all(CLASSE[f] is Classe.EXATA for f in Fonte if f is not Fonte.ACERVO)


def test_timeout_por_classe_bate_com_a_spec():
    # §8 — exata 250 ms, semântica 2 s. Timeout único de 2 s deixa fonte exata
    # quebrada travar o giro sem ganho.
    assert TIMEOUT_MS[Classe.EXATA] == 250
    assert TIMEOUT_MS[Classe.SEMANTICA] == 2000
    assert timeout_ms(Fonte.BOARD) == 250
    assert timeout_ms(Fonte.ACERVO) == 2000


@pytest.mark.parametrize("valor", ["boa", "COBERTA", "indefinida", ""])
def test_cobertura_fora_do_enum_levanta(valor):
    with pytest.raises(ContratoViolado):
        LinhaFonte(fonte=Fonte.BOARD, cobertura=valor)


# ================================ 2. invariante 1 — procedência completa ou nada entra


def test_item_sem_procedencia_nao_entra():
    with pytest.raises(ContratoViolado):
        Item(procedencia=None, ref="x")
    with pytest.raises(ContratoViolado):
        Item(procedencia={"fonte": "board", "chave": "item:1"}, ref="x")


def test_chave_vazia_levanta():
    with pytest.raises(ContratoViolado):
        Procedencia(fonte=Fonte.BOARD, chave="  ", versao=versao())


def test_chave_com_prefixo_de_outra_fonte_levanta():
    # §4 — a chave é estrutural. Prefixo errado é procedência errada com cara de certa.
    with pytest.raises(ContratoViolado):
        Procedencia(fonte=Fonte.WIKI, chave="acervo:df70f05c#x", versao=versao())


def test_registro_aceita_as_tres_series():
    for chave in ("adr:0064", "seg:0013", "ont:0001"):
        p = Procedencia(fonte=Fonte.REGISTRO, chave=chave, versao=versao(VersaoTipo.SHA, "18350e7"))
        assert p.chave == chave


def test_versao_sem_valor_levanta():
    with pytest.raises(ContratoViolado):
        Versao(tipo=VersaoTipo.SHA, valor="")


def test_fonte_fora_do_catalogo_levanta():
    with pytest.raises(ContratoViolado):
        Procedencia(fonte="repo", chave="repo:x", versao=versao())


def test_conteudo_ou_ref_nunca_os_dois():
    with pytest.raises(ContratoViolado):
        Item(procedencia=proc(), conteudo="a", ref="b")
    with pytest.raises(ContratoViolado):
        Item(procedencia=proc())
    assert Item(procedencia=proc(), conteudo="a").conteudo == "a"
    assert Item(procedencia=proc(), ref="b").ref == "b"


def test_digest_e_opcional_e_sai_quando_existe():
    p = proc(Fonte.ACERVO, chave="acervo:df70f05c#in-memory-caching", digest="a" * 64)
    assert p.para_json()["digest"] == "a" * 64
    assert "digest" not in proc().para_json()


# ========================= 3. invariante 2 — sinal só com medida; sem medida, calibração


def test_sinal_sem_medida_levanta():
    with pytest.raises(ContratoViolado):
        Sinal(medida="", valor=0.9, piso=0.79)


def test_fonte_semantica_sem_medida_nao_pode_dizer_coberta_nem_fraca():
    for c in (Cobertura.COBERTA, Cobertura.FRACA):
        with pytest.raises(ContratoViolado):
            LinhaFonte(fonte=Fonte.ACERVO, cobertura=c)
    # o valor honesto do instrumento desligado:
    assert LinhaFonte(fonte=Fonte.ACERVO, cobertura=Cobertura.NAO_CALIBRADA).sinal is None


def test_fonte_exata_nao_precisa_de_sinal():
    linha = LinhaFonte(fonte=Fonte.BOARD, cobertura=Cobertura.COBERTA)
    assert linha.sinal is None
    assert "sinal" not in linha.para_json()


def test_sinal_omitido_quando_null():
    env = Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.VAZIA)])
    assert "sinal" not in env.para_json()


def test_a_regua_viaja_no_envelope():
    # duas chamadas na mesma sessão podem sair com réguas distintas (arq:0064 §1)
    linha = LinhaFonte(Fonte.ACERVO, Cobertura.COBERTA, sinal=sinal_ok())
    assert linha.para_json()["sinal"] == {"medida": "rerank", "valor": 0.9, "piso": 0.79}


# ================================== 4. invariante 3 — envelope sem itens ≤ 40 tokens


def conta_tokens(texto: str) -> int:
    """Tokenizador do modelo servido. `tiktoken` tokeniza qwen errado e por isso não
    serve — e estimativa por bytes/4 erra ~40%."""
    from tokenizers import Tokenizer

    assert os.path.isfile(TOKENIZADOR), f"tokenizador ausente: {TOKENIZADOR}"
    return len(Tokenizer.from_file(TOKENIZADOR).encode(texto).ids)


def test_envelope_vazio_cabe_no_teto():
    env = Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.VAZIA)])
    texto = env.para_texto()
    n = conta_tokens(texto)
    assert n <= TETO_ENVELOPE_VAZIO, f"envelope vazio a {n} tokens (teto {TETO_ENVELOPE_VAZIO}): {texto}"


def test_recusa_de_disjuntor_cabe_no_teto():
    env = Envelope(linhas=[linha_disjuntor_aberto(Fonte.WIKI)])
    n = conta_tokens(env.para_texto())
    assert n <= TETO_ENVELOPE_VAZIO, f"recusa a {n} tokens: {env.para_texto()}"


# ============================ 5. invariante 4 — N fontes, N linhas; nenhuma some


def test_envelope_sem_linha_levanta():
    with pytest.raises(ContratoViolado):
        Envelope(linhas=[])


def test_fonte_que_nao_respondeu_continua_na_lista():
    env = Envelope(
        linhas=[
            LinhaFonte(Fonte.BOARD, Cobertura.COBERTA, carimbo="4412"),
            linha_disjuntor_aberto(Fonte.WIKI),
            LinhaFonte(Fonte.FILA, Cobertura.FONTE_NAO_INDEXADA, causa=Causa.TIMEOUT),
        ],
        itens=[item(Fonte.BOARD)],
    )
    d = env.para_json()
    assert d["aviso"] == [
        {"fonte": "wiki", "causa": "disjuntor-aberto"},
        {"fonte": "fila", "causa": "timeout"},
    ]
    # a união é o que a invariante 4 garante: nenhuma das três some do envelope
    vistas = {l["fonte"] for l in d.get("linhas", [])} | {a["fonte"] for a in d["aviso"]}
    assert vistas == {"board", "wiki", "fila"}
    assert {l.fonte for l in env.linhas} == set(Fonte(f) for f in vistas)


def test_nenhuma_das_seis_fontes_some_quando_todas_caem():
    env = Envelope(linhas=[linha_disjuntor_aberto(f) for f in Fonte])
    d = env.para_json()
    vistas = {l["fonte"] for l in d.get("linhas", [])} | {a["fonte"] for a in d["aviso"]}
    assert vistas == {f.value for f in Fonte}
    # Teto de REGRESSÃO, não meta da spec: o único número duro é o de 40 (inv. 3).
    # Medido em 20/08/2026, qwen2.5: 113 tokens — e 209 antes de a linha caída parar de
    # repetir o que `aviso[]` já diz. Este assert existe para que uma volta a 209 apareça
    # como falha e não como "envelope um pouco maior".
    n = conta_tokens(env.para_texto())
    assert n <= 120, f"recusa das seis fontes a {n} tokens: {env.para_texto()}"


def test_fonte_nao_indexada_sem_causa_levanta():
    with pytest.raises(ContratoViolado):
        LinhaFonte(Fonte.WIKI, Cobertura.FONTE_NAO_INDEXADA)


def test_fonte_repetida_levanta():
    with pytest.raises(ContratoViolado):
        Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.VAZIA),
                         LinhaFonte(Fonte.BOARD, Cobertura.COBERTA)])


def test_item_de_fonte_sem_linha_levanta():
    with pytest.raises(ContratoViolado):
        Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.COBERTA)], itens=[item(Fonte.WIKI)])


def test_fonte_que_declarou_nao_entrega_nao_pode_trazer_item():
    with pytest.raises(ContratoViolado):
        Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.VAZIA)], itens=[item(Fonte.BOARD)])


def test_aviso_omitido_quando_vazio():
    assert "aviso" not in Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.VAZIA)]).para_json()


# ================================= 6. invariante 5 — `sujeito` não entra no envelope


def _chaves(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from _chaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from _chaves(v)


def test_sujeito_nao_aparece_em_lugar_nenhum():
    env = Envelope(
        linhas=[LinhaFonte(Fonte.ACERVO, Cobertura.COBERTA, sinal=sinal_ok(), carimbo="imp-4b6f")],
        itens=[
            Item(
                procedencia=proc(Fonte.ACERVO, chave="acervo:df70f05c#in-memory-caching"),
                conteudo="…",
                casamento=Casamento.APROXIMADO,
                expansao=Expansao("cache-semantico", "mais_amplo_id", "ia"),
            )
        ],
        codigo_exato=True,
    )
    chaves = set(_chaves(env.para_json()))
    for proibido in CAMPOS_PROIBIDOS:
        assert proibido not in chaves
    assert not hasattr(env, "sujeito")
    with pytest.raises(AttributeError):  # slots: não dá para enfiar o campo depois
        env.sujeito = "claudinho-IA"


# ========================================================= 7. cobertura agregada


def test_uma_fonte_a_cobertura_e_a_dela():
    env = Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.COBERTA)], itens=[item()])
    assert env.cobertura is Cobertura.COBERTA


def test_fonte_caida_nao_rebaixa_quem_respondeu():
    # arq:0064 §2, `fonte-nao-indexada`: as demais fontes respondem normalmente;
    # esta linha declara o vão.
    env = Envelope(
        linhas=[LinhaFonte(Fonte.BOARD, Cobertura.COBERTA), linha_disjuntor_aberto(Fonte.WIKI)],
        itens=[item(Fonte.BOARD)],
    )
    assert env.cobertura is Cobertura.COBERTA


def test_envelope_com_item_nunca_se_rotula_vazia_nem_ausente():
    env = Envelope(
        linhas=[LinhaFonte(Fonte.BOARD, Cobertura.COBERTA), LinhaFonte(Fonte.MESA, Cobertura.AUSENTE)],
        itens=[item(Fonte.BOARD)],
    )
    assert env.cobertura is Cobertura.COBERTA


def test_sem_item_manda_a_mais_informativa():
    env = Envelope(
        linhas=[LinhaFonte(Fonte.MESA, Cobertura.AUSENTE), LinhaFonte(Fonte.BOARD, Cobertura.VAZIA)]
    )
    assert env.cobertura is Cobertura.AUSENTE
    env2 = Envelope(
        linhas=[LinhaFonte(Fonte.BOARD, Cobertura.VAZIA), linha_disjuntor_aberto(Fonte.WIKI)]
    )
    assert env2.cobertura is Cobertura.VAZIA


def test_tudo_caido_vira_fonte_nao_indexada():
    env = Envelope(linhas=[linha_disjuntor_aberto(Fonte.WIKI), linha_disjuntor_aberto(Fonte.FILA)])
    assert env.cobertura is Cobertura.FONTE_NAO_INDEXADA


def test_sinal_no_topo_so_com_uma_regua():
    um = Envelope(linhas=[LinhaFonte(Fonte.ACERVO, Cobertura.COBERTA, sinal=sinal_ok())],
                  itens=[item(Fonte.ACERVO, ref="acervo:x")])
    assert um.sinal is not None
    dois = Envelope(
        linhas=[
            LinhaFonte(Fonte.ACERVO, Cobertura.COBERTA, sinal=sinal_ok()),
            LinhaFonte(Fonte.WIKI, Cobertura.COBERTA, sinal=Sinal("sim", 0.5, 0.4)),
        ]
    )
    assert dois.sinal is None, "duas réguas no mesmo envelope: o escalar mentiria"


# ============================================================== 8. o par que instrui


def test_falta_e_proximo_so_saem_quando_existem():
    env = Envelope(
        linhas=[LinhaFonte(Fonte.BOARD, Cobertura.VAZIA)],
        falta="item:9999 não resolve em nenhuma impressão",
        proximo="tarefas listar --cadeira claudinho-IA",
    )
    d = env.para_json()
    assert d["falta"] and d["proximo"]
    assert "falta" not in Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.VAZIA)]).para_json()


def test_serializa_para_json_valido():
    env = Envelope(linhas=[LinhaFonte(Fonte.BOARD, Cobertura.COBERTA)], itens=[item()])
    assert json.loads(env.para_texto())["cobertura"] == "coberta"


def test_casamento_omitido_em_consulta_exata():
    assert "casamento" not in item().para_json()
    assert item(casamento=Casamento.EXATO).para_json()["casamento"] == "exato"
