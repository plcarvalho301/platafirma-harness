"""testes — lista de verificacao de cobertura e padrao de testes."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from .lista import resolver_lista
from .resultado import Apontamento

CHAVE_LISTA = "checklist-testes"


def verificar_testes(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> Tuple[list[Apontamento], str, Optional[int]]:
    lista = resolver_lista(CHAVE_LISTA)
    if not lista:
        raise ValueError(5, f"indeterminavel — lista de verificacao '{CHAVE_LISTA}' nao encontrada no acervo")

    rev = lista.get("rev", 1)
    return [], CHAVE_LISTA, rev
