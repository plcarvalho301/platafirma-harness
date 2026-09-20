"""Registro das fontes — derivado da tabela `Fontes da plataforma` do catálogo.

`spec_recuperador.md` §5 (tabela das seis fontes) e §8 (timeout por classe).
A fonte da verdade é `acervo.ferramental_fonte` (arq:0076, arq:0067 §5 emendado), lida
via GET /acervo/fontes; o seed embutido é contingência de banco-fora-do-ar.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from enum import StrEnum
from pathlib import Path

from .gerador import ErroTabelaFontes, FonteInfo, le_tabela_fontes


class Classe(StrEnum):
    """Classe de consulta (§5). Decide o timeout (§8) e a exigência de `sinal` (§3, inv. 2)."""

    EXATA = "exata"
    SEMANTICA = "semantica"


def _le_fontes_do_acervo() -> list[FonteInfo] | None:
    """Lê a tabela de fontes do golden record via API do rag (arq:0076).

    Devolve None em qualquer indisponibilidade (banco fora, API fora, resposta vazia ou
    malformada) — o chamador cai no seed embutido. Mesma convenção de variáveis de
    ambiente de `adaptadores/acervo.py` (RAG_API_URL, RAG_API_TOKEN, RAG_TIMEOUT_S).
    """
    base = os.environ.get("RAG_API_URL", "http://127.0.0.1:8100").rstrip("/")
    token = os.environ.get("RAG_API_TOKEN", "")
    try:
        req = urllib.request.Request(
            f"{base}/acervo/fontes",
            headers={"authorization": f"Bearer {token}"} if token else {})
        with urllib.request.urlopen(req, timeout=float(os.environ.get("RAG_TIMEOUT_S", "10"))) as r:  # noqa: S310
            dados = json.loads(r.read())
    except Exception:
        return None
    linhas = dados.get("itens") or []
    if not linhas:
        return None
    try:
        return [FonteInfo(
            slug=l["slug"], capacidade=l["capacidade"], dono=l["dono"],
            transporte=l["transporte"], classe=l["classe"],
            contrato_de_leitura=l["contrato_de_leitura"], gold=l["gold"],
            linha_num=l.get("ordem", 0),
        ) for l in linhas]
    except (KeyError, TypeError):
        return None


def _constroi_fontes(caminho: Path | str | None = None, texto: str | None = None) -> tuple[type[StrEnum], dict[StrEnum, Classe]]:
    # 1) golden record via API (arq:0076); 2) tabela do catálogo (.md, se alguém passar
    # caminho/texto explícito, ou existir na release); 3) seed embutido — banco e API
    # fora, ou .md ausente/malformado. Nunca estoura no import (arq:0076).
    infos: list[FonteInfo] | None = None
    if caminho is None and texto is None:
        infos = _le_fontes_do_acervo()
    if not infos:
        try:
            infos = le_tabela_fontes(caminho=caminho, texto=texto)
        except (FileNotFoundError, ErroTabelaFontes):
            infos = []
    if not infos:
        infos = [
            FonteInfo("board", "trabalho", "ti", "HTTP", "exata", "", "", 0),
            FonteInfo("fila", "mensagem", "ti", "stream", "exata", "", "", 0),
            FonteInfo("mesa", "memoria", "ia", "postgres", "exata", "", "", 0),
            FonteInfo("registro", "decisao", "gestao-estrategica", "git", "exata", "", "", 0),
            FonteInfo("wiki", "conhecimento", "dados", "HTTP", "exata", "", "", 0),
            FonteInfo("acervo", "conhecimento", "dados", "HTTP", "semantica", "", "", 0),
        ]

    membros = {info.slug.upper().replace("-", "_"): info.slug for info in infos}
    _FonteEnum = StrEnum("Fonte", membros)
    _classes = {_FonteEnum(info.slug): Classe(info.classe) for info in infos}
    return _FonteEnum, _classes


Fonte, CLASSE = _constroi_fontes()

# §5 — carimbo, domínio, tipo e prefixo de `sobre`, por fonte.
# TODO arq:0076: estes mapas já vivem em acervo.ferramental_fonte (dominio, tipo,
# prefixo_sobre, prefixo_chave); consumir da API num próximo passo — fora do escopo desta
# entrega, que troca a leitura da FONTE (enum/classe), não estes mapas.
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
