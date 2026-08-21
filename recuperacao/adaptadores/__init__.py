"""Adaptadores — um por fonte, ao contrato, nunca ao binário (§5).

F1 fechado: as seis fontes. #2298 trouxe registro, fila e mesa (as baratas); #2301 a
wiki (Cargo + API do MediaWiki); #2302 o acervo (API do rag, a única semântica); #2300 o
board, sobre a projeção `?campos=` que #2299 entregou.
"""

from .acervo import AdaptadorAcervo
from .base import Adaptador, FonteIndisponivel, Resultado, monta_envelope
from .board import AdaptadorBoard
from .fila import AdaptadorFila
from .mesa import AdaptadorMesa
from .registro import AdaptadorRegistro
from .wiki import AdaptadorWiki

__all__ = [
    "Adaptador",
    "AdaptadorAcervo",
    "AdaptadorBoard",
    "AdaptadorFila",
    "AdaptadorMesa",
    "AdaptadorRegistro",
    "AdaptadorWiki",
    "FonteIndisponivel",
    "Resultado",
    "monta_envelope",
]
