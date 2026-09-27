"""organizacao — lista de verificacao de antipadroes de organizacao documental."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from .lista import resolver_lista
from .resultado import Apontamento

CHAVE_LISTA = "checklist-antipadroes-organizacao-documental"


def verificar_organizacao(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> Tuple[list[Apontamento], str, Optional[int]]:
    """Verifica organizacao documental contra checklist-antipadroes-organizacao-documental.
    
    Lanca ValueError(5, msg) se a lista ainda nao existir no acervo.
    """
    lista = resolver_lista(CHAVE_LISTA)
    if not lista:
        raise ValueError(5, f"indeterminavel — lista de verificacao '{CHAVE_LISTA}' nao encontrada no acervo")

    rev = lista.get("rev", 1)
    apontamentos: list[Apontamento] = []
    # Quando o modelo local ou detector existir, aplica sobre os arquivos
    return apontamentos, CHAVE_LISTA, rev
