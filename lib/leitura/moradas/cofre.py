"""Adaptador da morada `cofre` — recusa no leitor geral e delegação à ponta isolada (story #4442, t6)."""
from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from ..morada import eh_segredo
from ..tipos import (
    AlvoResolvido,
    CursorDecodificado,
    FiltroCatalogo,
    ObjetoBruto,
    PaginaBruta,
    Recusa,
    SeletorParte,
)
from . import ErroMorada


class PontaLeituraSegredo(Protocol):
    """Interface da ponta isolada `ponta-leitura-segredo` (conta pf-segredo-leitor)."""

    def ler_segredo(
        self, alvo: AlvoResolvido, seletor: SeletorParte, prazo_ms: int
    ) -> ObjetoBruto: ...

    def listar_segredos(
        self,
        filtros: Sequence[FiltroCatalogo],
        termo: str | None,
        limite: int,
        cursor: CursorDecodificado | None,
        prazo_ms: int,
    ) -> PaginaBruta: ...


def _recusa_segredo_fora(chave_ou_classe: str, *, proximo: str = "") -> ErroMorada:
    return ErroMorada(
        Recusa(
            saida=4,
            codigo="segredo-fora-do-leitor",
            onde="morada:cofre",
            recebido=chave_ou_classe,
            regra="segredo-vedado-no-leitor-geral",
            cura="segredos e superfícies vedadas não podem ser lidos pelo leitor geral",
            proximo=proximo,
        )
    )


class AdaptadorCofre:
    """Recusa segredos e superfícies vedadas no leitor geral; delega `segredo` só à ponta isolada."""

    def __init__(self, *, ponta_isolada: PontaLeituraSegredo | None = None) -> None:
        self._ponta = ponta_isolada

    def ler_objeto(
        self, alvo: AlvoResolvido, seletor: SeletorParte, prazo_ms: int
    ) -> ObjetoBruto:
        if eh_segredo(Path(alvo.endereco)) or eh_segredo(Path(alvo.chave_pedida)):
            raise _recusa_segredo_fora(alvo.chave_pedida)

        if alvo.classe == "segredo" and self._ponta is not None:
            return self._ponta.ler_segredo(alvo, seletor, prazo_ms)

        slug = alvo.chave_canonica.split(":", 1)[1] if ":" in alvo.chave_canonica else alvo.chave_pedida
        prox = f"seg ler segredo {slug}" if alvo.classe == "segredo" else ""
        raise _recusa_segredo_fora(alvo.chave_pedida, proximo=prox)

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, classe: str, filtros: Sequence[FiltroCatalogo], termo: str | None,
        limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        if classe == "segredo" and self._ponta is not None:
            return self._ponta.listar_segredos(filtros, termo, limite, cursor, prazo_ms)
        prox = "seg listar segredo" if classe == "segredo" else ""
        raise _recusa_segredo_fora(classe, proximo=prox)
