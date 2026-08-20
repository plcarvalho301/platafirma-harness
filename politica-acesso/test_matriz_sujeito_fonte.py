"""Matriz sujeito × fonte — o aceite de fase do F1 (spec §6, card #2303).

    python3 -m pytest politica-acesso/test_matriz_sujeito_fonte.py -q

**Isto falha o build.** É o que a spec pede em vez de desejo: um teste que quebra quando
`pesquisador-externo` alcançar `wiki:PlataFirma/*` ou `acervo:pessoal/*` por dentro do
`recuperar`. Sem ele, "o externo não alcança a casa por dentro" é intenção de projeto,
e intenção não é controle.

Mora aqui, e não em `recuperacao/`, porque o que ela julga é a POLÍTICA: quebra por
merge no PAP, não por mudança de biblioteca. O contrato do mecanismo (fail-closed,
negativa total, alvo que nunca vira `*`) é o outro arquivo,
`recuperacao/test_contrato_pep.py`.

A matriz é literal de propósito. Gerar a expectativa da mesma política que ela confere
seria escrever o gabarito com a prova aberta: o teste passaria a repetir o PAP em vez de
julgá-lo, e uma regra a mais viraria uma linha a mais nos dois lados, sem alarme nenhum.
Aqui, concessão nova só fica verde quando alguém escreve à mão que a quer.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
for p in (str(RAIZ), str(AQUI)):
    if p not in sys.path:
        sys.path.insert(0, p)

from recuperacao.fontes import Fonte  # noqa: E402
from recuperacao.pep import PEP  # noqa: E402

PERMITE, NEGA = True, False

# Sujeitos reais de `sujeitos.yaml`, mais um que não existe. O que não está na projeção
# não tem atributo, e atributo ausente nega — é a régua, não a exceção.
DONO = "megafone"                  # operador, credencial própria no realm
EMERGENCIA = "claudinho"           # operador, rota de token estático
EXTERNO = "jaiminho"               # pesquisador-externo (seg:0009, card 344)
FABRICA = "jaiminho-fabrica"       # fornecedor (org:0020)
ESTRANHO = "cadeira-que-nao-existe"

# (sujeito, fonte, alvo, esperado, por quê)
MATRIZ: list[tuple[str, str, str, bool, str]] = [
    # --- o dono: alcance amplo por `operador-plataforma`, e é assim que tem de ser ---
    (DONO, "board", "item:*", PERMITE, "operador-plataforma, sobre *"),
    (DONO, "fila", "caixa:*", PERMITE, "operador-plataforma"),
    (DONO, "mesa", "mem:*", PERMITE, "operador-plataforma"),
    (DONO, "registro", "adr:*", PERMITE, "operador-plataforma"),
    (DONO, "wiki", "wiki:PlataFirma/*", PERMITE, "a casa por dentro é dele"),
    (DONO, "acervo", "acervo:pessoal/*", PERMITE, "coleção pessoal é do titular"),
    (EMERGENCIA, "wiki", "wiki:PlataFirma/*", PERMITE, "mesma mão, quando o realm cai"),
    (EMERGENCIA, "acervo", "acervo:firma/*", PERMITE, "idem"),

    # --- o externo: lê o que foi nomeado, e nada mais -------------------------------
    (EXTERNO, "acervo", "acervo:firma/*", PERMITE, "jaiminho-le-acervo-inteiro"),
    (EXTERNO, "acervo", "acervo:firma/ia/*", PERMITE, "recorte dentro da concessão"),
    # DESATUALIZADO ATE 20/08/2026: as duas linhas abaixo esperavam NEGA. Ordem do dono
    # nesta data concedeu o acervo INTEIRO ao externo (`jaiminho-le-acervo-inteiro`) e
    # removeu `externo-nunca-alcanca-acervo-pessoal`. Fundamento dele: externo que coda
    # contra a plataforma sem base sólida quebra o ambiente, e a coleção pessoal é do
    # titular. Corrigidas à mão, como o gabarito literal exige.
    (EXTERNO, "acervo", "acervo:pessoal/*", PERMITE, "jaiminho-le-acervo-inteiro, 20/08/2026"),
    (EXTERNO, "acervo", "acervo:*", PERMITE, "a concessão é o corpus inteiro, por ordem do dono"),
    (EXTERNO, "wiki", "wiki:principal/*", PERMITE, "jaiminho-le-wiki-conceito"),
    (EXTERNO, "wiki", "wiki:PlataFirma/*", NEGA, "externo-nao-le-wiki-interna"),
    (EXTERNO, "wiki", "wiki:Operar/*", NEGA, "runbook é a casa por dentro"),
    (EXTERNO, "wiki", "wiki:Frente/*", NEGA, "trabalho em curso idem"),
    (EXTERNO, "wiki", "wiki:*", NEGA, "genérico não casa a concessão nominal"),
    (EXTERNO, "fila", "caixa:jaiminho", PERMITE, "jaiminho-canal-exclusivo-com-IA"),
    (EXTERNO, "fila", "caixa:claudinho-IA", PERMITE, "a outra ponta do mesmo canal"),
    (EXTERNO, "fila", "caixa:claudinho-TI", NEGA, "canal é exclusivo, não é malha"),
    (EXTERNO, "fila", "caixa:*", NEGA, "as outras seis caixas não são alcançáveis"),
    (EXTERNO, "board", "item:*", NEGA, "sem regra: o default nega"),
    (EXTERNO, "board", "item:2303", NEGA, "idem, e nominal não muda nada"),
    (EXTERNO, "mesa", "mem:*", NEGA, "memória de cadeira não é de externo"),
    (EXTERNO, "mesa", "mem:ia:harness", NEGA, "idem"),
    (EXTERNO, "registro", "adr:*", NEGA, "decisão da casa não é de externo"),
    (EXTERNO, "registro", "seg:0009", NEGA, "idem — inclusive a que o concede"),

    # --- a fábrica: executa card sobre repositório, e o recuperador não a amplia ----
    (FABRICA, "board", "item:2303", NEGA, "`recuperar` não é verbo do fornecedor"),
    (FABRICA, "mesa", "mem:*", NEGA, "idem"),
    (FABRICA, "registro", "adr:*", NEGA, "idem"),
    (FABRICA, "wiki", "wiki:principal/*", NEGA, "não há regra de wiki para fornecedor"),
    (FABRICA, "wiki", "wiki:PlataFirma/*", NEGA, "idem, e esta é a casa por dentro"),
    # DESATUALIZADO ATE 20/08/2026: a linha esperava NEGA, e a suite quebrou quando
    # `fabrica-le-acervo-firma` entrou por ordem do dono na mesma data. Corrigida aqui,
    # e a falha era do teste, não da política — o gabarito literal fez o trabalho dele.
    (FABRICA, "acervo", "acervo:firma/*", PERMITE, "fabrica-le-acervo-firma, 20/08/2026"),
    (FABRICA, "acervo", "acervo:pessoal/*", NEGA, "fornecedor-nunca-alcanca-acervo-pessoal"),
    (FABRICA, "fila", "caixa:jaiminho-fabrica", NEGA, "a fábrica fala por card, não por caixa"),

    # --- quem não está na projeção ---------------------------------------------------
    (ESTRANHO, "acervo", "acervo:firma/*", NEGA, "atributo ausente nega"),
    (ESTRANHO, "mesa", "mem:*", NEGA, "idem"),
]


@pytest.fixture(scope="module")
def pep() -> PEP:
    return PEP(AQUI)


@pytest.mark.parametrize("sujeito,fonte,alvo,esperado,porque", MATRIZ,
                         ids=[f"{s}-{f}-{a}" for s, f, a, _, _ in MATRIZ])
def test_matriz(pep, sujeito, fonte, alvo, esperado, porque):
    n = pep.autoriza_fonte(sujeito, Fonte(fonte), [alvo])
    obtido = n is None
    assert obtido is esperado, (
        f"{sujeito} × {fonte} × {alvo}: esperado "
        f"{'PERMITE' if esperado else 'NEGA'} ({porque}), "
        f"obtido {'PERMITE' if obtido else f'NEGA[{n.regra}: {n.motivo}]'}"
    )


# --- o aceite duro do §6, escrito uma vez mais e sozinho -----------------------------
# Repetido de propósito: as duas linhas que a spec nomeia não podem depender de alguém
# ler a matriz inteira para achá-las. Falha aqui é vazamento, não regressão de forma.

# `acervo:pessoal/*` SAIU desta lista em 20/08/2026: deixou de ser vedado por ordem do
# dono. O que resta vedado ao externo é a casa por dentro — decisão, runbook e trabalho
# em curso —, que é outra matéria e não foi tocada.
VEDADO_AO_EXTERNO = [("wiki", "wiki:PlataFirma/*"), ("wiki", "wiki:Operar/*")]


@pytest.mark.parametrize("fonte,alvo", VEDADO_AO_EXTERNO)
def test_externo_nao_alcanca_a_casa_por_dentro_pelo_recuperar(pep, fonte, alvo):
    assert pep.autoriza_fonte(EXTERNO, Fonte(fonte), [alvo]) is not None, (
        f"VAZAMENTO: pesquisador-externo alcançou {alvo} por dentro do recuperar (§6)"
    )


def test_vedado_nao_passa_nem_misturado_com_alvo_concedido(pep):
    """Negativa total: o alvo vedado no meio de um pedido legítimo derruba a fonte."""
    n = pep.autoriza_fonte(EXTERNO, Fonte("wiki"),
                           ["wiki:principal/*", "wiki:PlataFirma/*"])
    assert n is not None and n.alvo == "wiki:PlataFirma/*"


# --- completude: fonte nova entra na matriz, ou o build para -------------------------

def test_toda_fonte_tem_caso_para_o_externo():
    """Fonte que nasce sem linha aqui nasce sem prova de que não vaza."""
    cobertas = {f for s, f, *_ in MATRIZ if s == EXTERNO}
    faltam = {str(f) for f in Fonte} - cobertas
    assert not faltam, f"fonte sem caso de externo na matriz: {sorted(faltam)}"


def test_toda_fonte_tem_caso_para_o_dono():
    cobertas = {f for s, f, *_ in MATRIZ if s in (DONO, EMERGENCIA)}
    faltam = {str(f) for f in Fonte} - cobertas
    assert not faltam, f"fonte sem caso de operador na matriz: {sorted(faltam)}"
