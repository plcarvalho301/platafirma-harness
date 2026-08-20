"""Adaptadores — um por fonte, ao contrato, nunca ao binário (§5).

F1: o núcleo e cinco das seis fontes. #2298 trouxe registro, fila e mesa (as baratas);
#2301 a wiki (Cargo + API do MediaWiki) e #2302 o acervo (API do rag, a única semântica).
Falta board (#2300), que espera a projeção #2299 de claudinho-TI.
"""

from .acervo import AdaptadorAcervo
from .base import Adaptador, FonteIndisponivel, Resultado, monta_envelope
from .fila import AdaptadorFila
from .mesa import AdaptadorMesa
from .registro import AdaptadorRegistro
from .wiki import AdaptadorWiki

__all__ = [
    "Adaptador",
    "AdaptadorAcervo",
    "AdaptadorFila",
    "AdaptadorMesa",
    "AdaptadorRegistro",
    "AdaptadorWiki",
    "FonteIndisponivel",
    "Resultado",
    "monta_envelope",
]
