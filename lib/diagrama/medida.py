"""Largura do texto na Inter, sem abrir arquivo de fonte.

A grade precisa da largura de cada rótulo para dar tamanho à caixa e à calha, e mede sem depender da
fonte instalada onde a peça roda. A tabela `inter-metricas.json`, ao lado, guarda o avanço de cada caractere em cada peso
que a figura usa; a largura é a soma dos avanços, na escala do tamanho da letra.
"""
from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
import re

TABELA = Path(__file__).with_name("inter-metricas.json")


@lru_cache(maxsize=1)
def tabela() -> dict:
    return json.loads(TABELA.read_text(encoding="utf-8"))


def _peso(peso: int | str) -> dict:
    """Os avanços do peso pedido, ou do mais próximo que a tabela tem."""
    pesos = tabela()["pesos"]
    alvo = int(str(peso).strip())
    mais_perto = min(pesos, key=lambda k: (abs(int(k) - alvo), int(k)))
    return pesos[mais_perto]


def largura(texto: str, tamanho: float, peso: int | str = 400) -> float:
    """Largura de `texto`, em px, na Inter de `tamanho` px e `peso`."""
    p = _peso(peso)
    avanco, padrao = p["avanco"], p["padrao"]
    return sum(avanco.get(c, padrao) for c in texto) * tamanho / tabela()["upm"]


def subida(tamanho: float) -> float:
    """Da linha de base ao topo da letra mais alta, em px."""
    return tabela()["subida"] * tamanho / tabela()["upm"]


def descida(tamanho: float) -> float:
    """Da linha de base ao pé da letra mais baixa, em px, positivo."""
    return -tabela()["descida"] * tamanho / tabela()["upm"]


def quebrar(texto: str, tamanho: float, peso: int | str, maximo: float) -> list[str]:
    """Quebra `texto` em linhas de até `maximo` px, entre palavras.

    A palavra composta que sozinha passa do máximo quebra depois do hífen, que fica no fim da linha. A
    palavra sem hífen que sozinha passa do máximo fica numa linha só; quem chama decide o que fazer com ela.
    """
    fichas: list[tuple[str, str]] = []  # (pedaço, o que vai antes dele na mesma linha)
    for palavra in texto.split():
        pedacos = [palavra]
        if largura(palavra, tamanho, peso) > maximo and "-" in palavra.strip("-"):
            pedacos = [p for p in re.split(r"(?<=-)(?=.)", palavra) if p]
        fichas += [(p, " " if i == 0 else "") for i, p in enumerate(pedacos)]
    if not fichas:
        return [""]
    linhas: list[str] = []
    atual = fichas[0][0]
    for pedaco, cola in fichas[1:]:
        tentativa = f"{atual}{cola}{pedaco}"
        if largura(tentativa, tamanho, peso) <= maximo:
            atual = tentativa
        else:
            linhas.append(atual)
            atual = pedaco
    linhas.append(atual)
    return linhas
