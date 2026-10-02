"""prosa — lista de verificacao de estilo e prosa documental."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple

from .lista import resolver_lista
from .resultado import Apontamento

CHAVE_LISTA = "styleguide-da-wiki"
# A regua mora no acervo como `padrao`, nao como lista-de-verificacao (#2856 linha 84); a lista
# segue aceita primeiro, para o dia em que ela existir.
ESPECIES_REGUA = ("lista-de-verificacao", "padrao")


def verificar_prosa(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> Tuple[list[Apontamento], str, Optional[int]]:
    lista = resolver_lista(CHAVE_LISTA, especies=ESPECIES_REGUA)
    if not lista:
        raise ValueError(5, f"indeterminavel — regua '{CHAVE_LISTA}' nao encontrada no acervo "
                            f"(especies tentadas: {', '.join(ESPECIES_REGUA)})")

    rev = lista.get("rev", 1)
    return [], CHAVE_LISTA, rev
