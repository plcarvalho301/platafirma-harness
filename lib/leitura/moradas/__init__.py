"""Registro e despacho dos adaptadores de morada do componente leitura (story #4442, t5)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence

from ..tipos import (
    AdaptadorMorada,
    AlvoResolvido,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    Recusa,
    SeletorParte,
    TipoMorada,
)

MORADAS_VALIDAS: frozenset[str] = frozenset(
    {"banco", "git", "wiki", "balde", "fila", "rastreador", "cofre"}
)


class ErroMorada(Exception):
    """Recusa estruturada levantada por um adaptador de morada."""

    def __init__(self, recusa: Recusa) -> None:
        self.recusa = recusa
        self.saida = recusa.saida
        super().__init__(recusa.codigo)


class RegistroMoradas:
    """Despacha `ler_objeto` e `listar_chaves` para o adaptador da morada do alvo."""

    def __init__(self, adaptadores: Mapping[str, AdaptadorMorada] | None = None) -> None:
        self._adaptadores: dict[str, AdaptadorMorada] = dict(adaptadores or {})

    def registrar(self, morada: TipoMorada, adaptador: AdaptadorMorada) -> None:
        if morada not in MORADAS_VALIDAS:
            raise ValueError(f"morada desconhecida: {morada!r}")
        self._adaptadores[morada] = adaptador

    def obter(self, morada: str) -> AdaptadorMorada:
        adaptador = self._adaptadores.get(morada)
        if adaptador is None:
            raise ErroMorada(
                Recusa(
                    saida=3,
                    codigo="morada-sem-resposta",
                    onde=f"morada:{morada}",
                    recebido=morada,
                    regra="adaptador-morada-registrado",
                    cura=f"adaptador da morada {morada!r} não está ativo nesta instância",
                    proximo="",
                )
            )
        return adaptador

    def ler_objeto(
        self,
        alvo: AlvoResolvido,
        seletor: SeletorParte,
        prazo_ms: int,
    ) -> ObjetoBruto:
        return self.obter(alvo.morada).ler_objeto(alvo, seletor, prazo_ms)

    def listar_chaves(
        self,
        morada: str,
        classe: str,
        filtros: Sequence[FiltroCatalogo],
        termo: str | None,
        limite: int,
        cursor: CursorDecodificado | None,
        prazo_ms: int,
    ) -> PaginaBruta:
        return self.obter(morada).listar_chaves(
            classe=classe,
            filtros=filtros,
            termo=termo,
            limite=limite,
            cursor=cursor,
            prazo_ms=prazo_ms,
        )
