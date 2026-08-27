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

    # --- jaiminho, agora papel `dev` (card #2899): le tudo que a cadeira le --------
    # O modelo DMZ do externo (read-only, canal exclusivo, casa-por-dentro vedada) foi
    # SUBSTITUIDO por conta segregada + PAP paridade-menos-publicar. Por isso varias
    # linhas viraram PERMITE — escritas a mao, como exige o gabarito literal.
    (EXTERNO, "acervo", "acervo:firma/*", PERMITE, "dev-faz-tudo-menos-publicar"),
    (EXTERNO, "acervo", "acervo:firma/ia/*", PERMITE, "recorte dentro do alcance"),
    (EXTERNO, "acervo", "acervo:pessoal/*", PERMITE, "dev le o acervo inteiro (o dono ja o abrira em 20/08)"),
    (EXTERNO, "acervo", "acervo:*", PERMITE, "idem"),
    (EXTERNO, "wiki", "wiki:principal/*", PERMITE, "dev le a wiki"),
    (EXTERNO, "wiki", "wiki:PlataFirma/*", PERMITE, "dev le a casa por dentro; contencao e a conta segregada, nao o PAP"),
    (EXTERNO, "wiki", "wiki:Operar/*", PERMITE, "idem: runbook"),
    (EXTERNO, "wiki", "wiki:Frente/*", PERMITE, "idem: trabalho em curso"),
    (EXTERNO, "fila", "caixa:claudinho-IA", PERMITE, "dev fala com qualquer cadeira (paridade)"),
    (EXTERNO, "fila", "caixa:claudinho-TI", PERMITE, "idem: o canal deixou de ser exclusivo"),
    (EXTERNO, "board", "item:*", PERMITE, "dev le o board"),
    (EXTERNO, "board", "item:2303", PERMITE, "idem, nominal nao muda"),
    (EXTERNO, "mesa", "mem:*", PERMITE, "dev le a mesa das cadeiras"),
    (EXTERNO, "mesa", "mem:ia:harness", PERMITE, "idem"),
    (EXTERNO, "registro", "adr:*", PERMITE, "dev le o registro"),
    (EXTERNO, "registro", "seg:0009", PERMITE, "idem — inclusive a que o concedia"),

    # --- a fábrica: executa card sobre repositório, e o recuperador não a amplia ----
    (FABRICA, "board", "item:2303", NEGA, "`recuperar` não é verbo do fornecedor"),
    (FABRICA, "mesa", "mem:*", NEGA, "idem"),
    (FABRICA, "registro", "adr:*", NEGA, "idem"),
    (FABRICA, "wiki", "wiki:principal/*", NEGA, "não há regra de wiki para fornecedor"),
    (FABRICA, "wiki", "wiki:PlataFirma/*", NEGA, "idem, e esta é a casa por dentro"),
    # DESATUALIZADO ATE 20/08/2026: a linha esperava NEGA, e a suite quebrou quando
    # `fabrica-le-acervo-firma` entrou por ordem do dono na mesma data. Corrigida aqui,
    # e a falha era do teste, não da política — o gabarito literal fez o trabalho dele.
    (FABRICA, "acervo", "acervo:firma/*", PERMITE, "fabrica-le-acervo-inteiro, 20/08/2026"),
    (FABRICA, "acervo", "acervo:*", PERMITE, "o alvo que o servidor submete hoje"),
    (FABRICA, "acervo", "acervo:pessoal/*", PERMITE, "fabrica-le-acervo-inteiro, 20/08/2026"),
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


# --- §6: aceite de contencao do externo REMOVIDO (card #2899, 27/08/2026) -----------
# A matriz §6 (VEDADO_AO_EXTERNO + os testes de vazamento) existia para provar que o
# `pesquisador-externo` nao alcancava a casa por dentro. jaiminho passou a `dev` e nao
# ha mais sujeito `pesquisador-externo`: o aceite ficou vacuo. A contencao do provider
# agora e a CONTA SEGREGADA, nao o PAP. SE um novo sujeito contido (DMZ read-only)
# nascer, este aceite tem de ser RESTAURADO para ELE — a prova nao pode morrer com o
# sujeito que a motivou.

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
