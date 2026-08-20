"""Registro das fontes — derivado da tabela `Fontes da plataforma` do catálogo.

`spec_recuperador.md` §5 (tabela das seis fontes) e §8 (timeout por classe).
`docs/catalogo-de-verbos.md` é a fonte da verdade única (arq:0064 §10.5, arq:0067 §5).
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path

from .gerador import ErroTabelaFontes, FonteInfo, le_tabela_fontes


class Classe(StrEnum):
    """Classe de consulta (§5). Decide o timeout (§8) e a exigência de `sinal` (§3, inv. 2)."""

    EXATA = "exata"
    SEMANTICA = "semantica"


def _constroi_fontes(caminho: Path | str | None = None, texto: str | None = None) -> tuple[type[StrEnum], dict[StrEnum, Classe]]:
    infos = le_tabela_fontes(caminho=caminho, texto=texto)
    if not infos:
        infos = [
            FonteInfo("board", "trabalho", "claudinho-TI", "HTTP", "exata", "", "", 0),
            FonteInfo("fila", "mensagem", "claudinho-TI", "stream", "exata", "", "", 0),
            FonteInfo("mesa", "memoria", "claudinho-IA", "postgres", "exata", "", "", 0),
            FonteInfo("registro", "decisao", "claudinha-gestao-estrategica", "git", "exata", "", "", 0),
            FonteInfo("wiki", "conhecimento", "claudinho-dados", "HTTP", "exata", "", "", 0),
            FonteInfo("acervo", "conhecimento", "claudinho-dados", "HTTP", "semantica", "", "", 0),
        ]

    membros = {info.slug.upper().replace("-", "_"): info.slug for info in infos}
    _FonteEnum = StrEnum("Fonte", membros)
    _classes = {_FonteEnum(info.slug): Classe(info.classe) for info in infos}
    return _FonteEnum, _classes


Fonte, CLASSE = _constroi_fontes()

# §5 — carimbo, domínio, tipo e prefixo de `sobre`, por fonte.
_DOMINIO_MAP = {
    "board": "plataforma",
    "fila": "mensageria",
    "mesa": "plataforma",
    "registro": "plataforma",
    "wiki": "plataforma-wiki",
    "acervo": "plataforma-acervo",
}

_TIPO_MAP = {
    "board": "documento",
    "fila": "mensagem",
    "mesa": "documento",
    "registro": "documento",
    "wiki": "wiki",
    "acervo": "acervo",
}

_PREFIXO_SOBRE_MAP = {
    "board": "item:",
    "fila": "caixa:",
    "mesa": "mem:",
    "registro": "adr:",
    "wiki": "wiki:",
    "acervo": "acervo:",
}

_PREFIXO_CHAVE_MAP = {
    "board": ("item:",),
    "fila": ("caixa:",),
    "mesa": ("mem:",),
    "registro": ("adr:", "seg:", "ont:"),
    "wiki": ("wiki:",),
    "acervo": ("acervo:",),
}

DOMINIO: dict[Fonte, str] = {f: _DOMINIO_MAP.get(f.value, "plataforma") for f in Fonte}
TIPO: dict[Fonte, str] = {f: _TIPO_MAP.get(f.value, "documento") for f in Fonte}
PREFIXO_SOBRE: dict[Fonte, str] = {f: _PREFIXO_SOBRE_MAP.get(f.value, f"{f.value}:") for f in Fonte}
PREFIXO_CHAVE: dict[Fonte, tuple[str, ...]] = {f: _PREFIXO_CHAVE_MAP.get(f.value, (f"{f.value}:",)) for f in Fonte}

# §8 — timeout por CLASSE, não por fonte. Medido: rag sem rerank 334 ms, com rerank
# ~660 ms; timeout único de 2 s deixa fonte exata quebrada travar o giro sem ganho.
TIMEOUT_MS: dict[Classe, int] = {
    Classe.EXATA: 250,
    Classe.SEMANTICA: 2000,
}


def classe(fonte: Fonte) -> Classe:
    return CLASSE[Fonte(fonte)]


def timeout_ms(fonte: Fonte) -> int:
    return TIMEOUT_MS[classe(fonte)]
