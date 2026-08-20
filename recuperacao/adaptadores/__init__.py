"""Adaptadores — um por fonte, ao contrato, nunca ao binário (§5).

F1 · card #2298: o núcleo e as três fontes baratas — as que não dependem de trabalho de
outra cadeira. Board (#2300, espera a projeção #2299 de claudinho-TI), wiki (#2301) e
acervo (#2302) entram nos cards seguintes.
"""

from .base import Adaptador, FonteIndisponivel, Resultado, monta_envelope
from .fila import AdaptadorFila
from .mesa import AdaptadorMesa
from .registro import AdaptadorRegistro

__all__ = [
    "Adaptador",
    "AdaptadorFila",
    "AdaptadorMesa",
    "AdaptadorRegistro",
    "FonteIndisponivel",
    "Resultado",
    "monta_envelope",
]
