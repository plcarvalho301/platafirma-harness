"""Contrato do PEP por fonte (§6, card #2303). `python3 -m pytest recuperacao/ -q`

O que este arquivo julga é o MECANISMO: fail-closed, uma decisão por fonte, negativa
total, alvo que nunca vira `*`, e o envelope de recusa que mantém a invariante 4.

O que ele NÃO julga é QUEM alcança O QUÊ — isso é a matriz sujeito × fonte, e mora em
`politica-acesso/test_matriz_sujeito_fonte.py`, junto do PAP que ela confere. Separar é
de propósito: mecanismo quebra por código, matriz quebra por merge no PAP, e misturar
os dois faria uma concessão nova parecer regressão de biblioteca.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from recuperacao.envelope import Causa, Cobertura, ContratoViolado
from recuperacao.fontes import DOMINIO, PREFIXO_SOBRE, TIPO, Fonte
from recuperacao.pep import ACAO, PEP, Negativa, recusa_por_concessao

RAIZ = Path(__file__).resolve().parents[1]
POLITICA = RAIZ / "politica-acesso"

OPERADOR = "megafone"          # papel `operador`, dominio `plataforma`
EXTERNO = "jaiminho"           # papel `pesquisador-externo`


@pytest.fixture
def pep() -> PEP:
    return PEP(POLITICA)


# 1. Fail-closed — falha de MECANISMO nega, e diz que foi mecanismo -------------------

def test_politica_ilegivel_nega_todas_as_fontes(tmp_path):
    p = PEP(tmp_path)  # diretório sem politica.yaml
    for f in Fonte:
        n = p.autoriza_fonte(OPERADOR, f)
        assert n is not None, f"{f} passou sem politica — fail-open"
        assert n.regra == "politica"


def test_politica_malformada_nega_em_vez_de_estourar(tmp_path):
    (tmp_path / "politica.yaml").write_text("versao: 1\nregras: [{: :}]\n")
    (tmp_path / "sujeitos.yaml").write_text("sujeitos: {}\n")
    n = PEP(tmp_path).autoriza_fonte(OPERADOR, Fonte("mesa"))
    assert n is not None and n.regra == "politica"


def test_sujeito_fora_da_projecao_nega_por_atributo_ausente(pep):
    n = pep.autoriza_fonte("ninguem-nunca-concedido", Fonte("mesa"))
    assert n is not None
    assert n.regra == "projecao"
    assert n.por_atributo_ausente, "defeito de projecao tem de sair distinguivel de regra"


def test_sem_identidade_nega(pep):
    n = pep.autoriza_fonte("", Fonte("mesa"))
    assert n is not None and n.regra == "identidade"


# 2. Uma decisão por fonte, com o par (dominio, sobre) do §5 --------------------------

def test_cada_fonte_leva_o_proprio_dominio_e_tipo(pep):
    """§6 — o carimbo é declaração do adaptador, não propriedade do processo. Fundir as
    seis num PEP só faria a concessão de uma matéria valer pela outra (`seg:0009`)."""
    vistos = []
    p = PEP(POLITICA, auditor=vistos.append)
    p.autoriza(OPERADOR, list(Fonte))
    permitidos = [e for e in vistos if e["evento"] == "pep_permitiu"]
    assert len(permitidos) == len(list(Fonte)), "uma chamada por fonte alcançada"
    assert {DOMINIO[f] for f in Fonte} > {"plataforma"}, "as seis não têm domínio único"


def test_acao_por_fonte_e_o_verbo_humano_da_materia(pep):
    assert pep.acao(Fonte("acervo")) == "rag_buscar"
    assert pep.acao(Fonte("wiki")) == "wiki_ler"
    assert pep.acao(Fonte("fila")) == "msg_ler"
    for f in (Fonte("board"), Fonte("mesa"), Fonte("registro")):
        assert pep.acao(f) == "recuperar", "fonte sem verbo no PAP cai em `recuperar`"
    assert set(ACAO) == {str(f) for f in Fonte}, "ação declarada para as seis"


# 3. Alvo — nunca `*` ------------------------------------------------------------------

def test_alvo_ausente_vira_prefixo_da_materia_nunca_asterisco(pep):
    for f in Fonte:
        alvo = pep.alvo_padrao(f)
        assert alvo == f"{PREFIXO_SOBRE[f]}*"
        assert alvo != "*", "`sobre` vazio vira `*` no PDP e entrega a matéria inteira"


def test_alvo_padrao_tem_de_bater_na_concessao_nominal(pep):
    """O alvo padrão não atravessa: ele CASA, ou nega. Que ele passe hoje no acervo é
    consequência de `jaiminho-le-acervo-inteiro` (`sobre: ["acervo:*"]`, `458178c`, ordem
    do dono de 20/08) — e a wiki, que não teve concessão alargada, continua provando a
    régra: alvo padrão sem regra que o cubra é negativa."""
    assert pep.autoriza_fonte(EXTERNO, Fonte("acervo")) is None
    assert pep.autoriza_fonte(EXTERNO, Fonte("acervo"), ["acervo:firma/ia/*"]) is None
    assert pep.autoriza_fonte(EXTERNO, Fonte("mesa")) is not None, (
        "`mem:*` não é concedido ao externo: o alvo padrão não vira salvo-conduto"
    )


# 4. Negativa total — nem entre alvos, nem entre fontes -------------------------------

def test_alvo_negado_nega_a_fonte_inteira(pep):
    """Pedido de dois recortes com concessão de um não vira busca em um (§6).

    O par usado aqui era `acervo:firma/*` + `acervo:pessoal/*`, que deixou de servir: o
    `458178c` concedeu o acervo INTEIRO ao externo por ordem do dono, e a regra
    `externo-nunca-alcanca-acervo-pessoal` saiu do PAP. A régra do §6 não mudou — mudou
    qual par a exercita. A wiki é o par vivo: `principal` concedido, camada interna não.
    """
    n = pep.autoriza_fonte(EXTERNO, Fonte("wiki"),
                           ["wiki:principal/*", "wiki:PlataFirma/*"])
    assert n is not None
    assert n.alvo == "wiki:PlataFirma/*"
    assert n.regra == "externo-nao-le-wiki-interna"


def test_autoriza_devolve_todas_as_negativas_nao_a_primeira(pep):
    negs = pep.autoriza(EXTERNO, {Fonte("registro"): ["adr:*"],
                                  Fonte("wiki"): ["wiki:PlataFirma/*"],
                                  Fonte("mesa"): []})
    assert {n.fonte for n in negs} == {Fonte("registro"), Fonte("wiki"), Fonte("mesa")}
    assert pep.autoriza_fonte(EXTERNO, Fonte("acervo"), ["acervo:pessoal/*"]) is None, (
        "o acervo saiu deste conjunto por ato do dono (458178c), não por defeito do PEP"
    )


def test_uma_negativa_no_meio_do_pedido_nega_o_pedido_inteiro(pep):
    pedido = {Fonte("acervo"): ["acervo:firma/ia/*"],   # concedido
              Fonte("wiki"): ["wiki:PlataFirma/*"]}     # negado
    negs = pep.autoriza(EXTERNO, pedido)
    env = recusa_por_concessao(pedido, negs)
    assert env.itens == []
    assert {l.fonte for l in env.linhas} == set(pedido), "invariante 4: N linhas"
    assert all(l.causa is Causa.SEM_CONCESSAO for l in env.linhas), (
        "a unidade autorizada é o pedido: nenhuma fonte foi alcançada"
    )


# 5. A recusa instrui ------------------------------------------------------------------

def test_recusa_nomeia_o_alvo_a_regra_e_o_proximo_pedido(pep):
    pedido = {Fonte("acervo"): ["acervo:firma/ia/*"], Fonte("wiki"): ["wiki:PlataFirma/*"]}
    env = recusa_por_concessao(pedido, pep.autoriza(EXTERNO, pedido))
    assert "wiki:PlataFirma/*" in env.falta
    assert "externo-nao-le-wiki-interna" in env.falta
    assert "repetir sem wiki" in env.proximo
    assert "acervo segue alcancavel" in env.proximo


def test_recusa_sai_no_json_como_aviso_por_fonte(pep):
    pedido = {Fonte("acervo"): ["acervo:pessoal/*"], Fonte("wiki"): ["wiki:PlataFirma/*"]}
    j = recusa_por_concessao(pedido, pep.autoriza(EXTERNO, pedido)).para_json()
    assert {a["fonte"] for a in j["aviso"]} == {"acervo", "wiki"}
    assert {a["causa"] for a in j["aviso"]} == {"sem-concessao"}
    assert j["cobertura"] == "fonte-nao-indexada"
    assert "sujeito" not in j and EXTERNO not in str(j), (
        "§3 inv. 5 — `sujeito` não entra no envelope, entra na trilha"
    )


def test_recusa_sem_fonte_nenhuma_levanta_em_vez_de_mentir():
    with pytest.raises(ContratoViolado):
        recusa_por_concessao([], [])


# 6. Trilha — o §11 é do host, e o PEP entrega o material ------------------------------

def test_negativa_e_permissao_saem_auditadas_por_fonte():
    ev = []
    p = PEP(POLITICA, auditor=ev.append)
    p.autoriza_fonte(EXTERNO, Fonte("wiki"), ["wiki:principal/*"])
    p.autoriza_fonte(EXTERNO, Fonte("wiki"), ["wiki:PlataFirma/*"])
    assert [e["evento"] for e in ev] == ["pep_permitiu", "pep_negou"]
    assert all(e["fonte"] == "wiki" and e["sujeito"] == EXTERNO for e in ev)
    assert ev[1]["regra"] == "externo-nao-le-wiki-interna"


def test_sem_auditor_o_pep_decide_igual(pep):
    assert pep.autoriza_fonte(EXTERNO, Fonte("wiki"), ["wiki:PlataFirma/*"]) is not None


# 7. Releitura do PAP sem restart ------------------------------------------------------

def test_merge_no_pap_vale_sem_restart(tmp_path):
    pol, suj = tmp_path / "politica.yaml", tmp_path / "sujeitos.yaml"
    suj.write_text("sujeitos:\n  s1:\n    natureza: pessoa\n    papeis: [operador]\n"
                   "    dominios: [plataforma]\n")
    pol.write_text("versao: 1\neixos:\n  dominio:\n    plataforma: {rotulo: p}\n"
                   "  papel:\n    operador: {rotulo: o}\n  tema: {}\nregras: []\n")
    p = PEP(tmp_path)
    assert p.autoriza_fonte("s1", Fonte("mesa")) is not None, "sem regra, o default nega"
    pol.write_text(pol.read_text().replace(
        "regras: []",
        "regras:\n  - id: r1\n    efeito: permite\n    motivo: m\n"
        "    quando: {papel: operador, dominio: plataforma}\n"
        "    acoes: ['*']\n    sobre: ['mem:*']\n"))
    import os
    os.utime(pol, (0, 0))  # mtime diferente do lido; o carimbo é (ns, ns), não hora
    assert p.autoriza_fonte("s1", Fonte("mesa")) is None
