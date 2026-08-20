"""Registro das fontes — slug, classe de consulta e timeout.

`spec_recuperador.md` §5 (tabela das seis fontes) e §8 (timeout por classe).

**Fonte da verdade, hoje e depois.** O §3 diz que `fonte` é "slug da tabela de fonte
do catálogo (§7)". Essa tabela — segunda de `docs/catalogo-de-verbos.md` — está vazia
de propósito até o F1, e validar contra tabela vazia reprovaria todo envelope. Até lá
a verdade é este enum, que reproduz a tabela do §5 da própria spec. No F1, quando o
gerador de descrição existir, este enum passa a ser DERIVADO da tabela do catálogo e
esta docstring cai. Nenhuma linha de roteamento (pergunta → fonte) é escrita aqui: o
§7 proíbe, e o que há aqui é identidade de fonte, não roteamento.
"""

from __future__ import annotations

from enum import StrEnum


class Classe(StrEnum):
    """Classe de consulta (§5). Decide o timeout (§8) e a exigência de `sinal` (§3, inv. 2)."""

    EXATA = "exata"
    SEMANTICA = "semantica"


class Fonte(StrEnum):
    """As seis fontes do §5. Valor = slug, que é o que viaja em `procedencia.fonte`."""

    BOARD = "board"
    FILA = "fila"
    MESA = "mesa"
    REGISTRO = "registro"
    WIKI = "wiki"
    ACERVO = "acervo"


# §5 — classe, carimbo, domínio, tipo e prefixo de `sobre`, por fonte.
# `dominio`/`tipo`/`sobre` é o par que o PEP consome no F1 (§6): carimbo de domínio é
# declaração do adaptador, não propriedade do processo.
CLASSE: dict[Fonte, Classe] = {
    Fonte.BOARD: Classe.EXATA,
    Fonte.FILA: Classe.EXATA,
    Fonte.MESA: Classe.EXATA,
    Fonte.REGISTRO: Classe.EXATA,
    Fonte.WIKI: Classe.EXATA,
    Fonte.ACERVO: Classe.SEMANTICA,
}

DOMINIO: dict[Fonte, str] = {
    Fonte.BOARD: "plataforma",
    Fonte.FILA: "mensageria",
    Fonte.MESA: "plataforma",
    Fonte.REGISTRO: "plataforma",
    Fonte.WIKI: "plataforma-wiki",
    Fonte.ACERVO: "plataforma-acervo",
}

TIPO: dict[Fonte, str] = {
    Fonte.BOARD: "documento",
    Fonte.FILA: "mensagem",
    Fonte.MESA: "documento",
    Fonte.REGISTRO: "documento",
    Fonte.WIKI: "wiki",
    Fonte.ACERVO: "acervo",
}

PREFIXO_SOBRE: dict[Fonte, str] = {
    Fonte.BOARD: "item:",
    Fonte.FILA: "caixa:",
    Fonte.MESA: "mem:",
    Fonte.REGISTRO: "adr:",
    Fonte.WIKI: "wiki:",
    Fonte.ACERVO: "acervo:",
}

# §4 — prefixo aceito na `chave` de procedência, por fonte. Chave é ESTRUTURAL: o
# prefixo identifica a fonte, e chave com prefixo de outra fonte é procedência errada
# com cara de certa. `registro` aceita três porque as três séries moram na mesma fonte.
PREFIXO_CHAVE: dict[Fonte, tuple[str, ...]] = {
    Fonte.BOARD: ("item:",),
    Fonte.FILA: ("caixa:",),
    Fonte.MESA: ("mem:",),
    Fonte.REGISTRO: ("adr:", "seg:", "ont:"),
    Fonte.WIKI: ("wiki:",),
    Fonte.ACERVO: ("acervo:",),
}

# §8 — timeout por CLASSE, não por fonte. Medido: rag sem rerank 334 ms, com rerank
# ~660 ms; timeout único de 2 s deixa fonte exata quebrada travar o giro sem ganho.
# ⚪ hipótese — os dois números são palpite calibrado, não medição de distribuição.
# O que confirma: latência por fonte com a instrumentação do §9 no ar, depois do F2.
TIMEOUT_MS: dict[Classe, int] = {
    Classe.EXATA: 250,
    Classe.SEMANTICA: 2000,
}


def classe(fonte: Fonte) -> Classe:
    return CLASSE[Fonte(fonte)]


def timeout_ms(fonte: Fonte) -> int:
    return TIMEOUT_MS[classe(fonte)]
