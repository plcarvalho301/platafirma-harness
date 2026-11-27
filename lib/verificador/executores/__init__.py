"""executores — adaptadores determinísticos por família de régua (card #4454)."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..tipos import Apontamento


def traduzir_apontamentos(itens: Iterable[Any]) -> tuple[Apontamento, ...]:
    """Converte apontamentos de serviço para o registro imutável da fronteira do verificador."""
    return tuple(
        Apontamento(
            item=a.item,
            alvo=a.alvo,
            lugar=a.lugar,
            exigencia=a.exigencia,
            severidade=a.severidade,
            cura=a.cura,
        )
        for a in itens
    )


from .gabarito import executar_gabarito  # noqa: E402
from .teste import executar_teste  # noqa: E402

__all__ = ["executar_gabarito", "executar_teste", "traduzir_apontamentos"]
