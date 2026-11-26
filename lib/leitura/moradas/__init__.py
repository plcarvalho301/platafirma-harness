"""Registro e despacho dos sete adaptadores de morada do componente leitura."""
from __future__ import annotations

import hashlib
import unicodedata
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


def normalizar_termo(texto: str) -> str:
    """Normaliza texto em NFC com casefold para filtros determinísticos."""
    return unicodedata.normalize("NFC", texto).casefold()


def montar_pagina_bruta(
    classe: str,
    itens: list[dict[str, str]],
    *,
    limite: int,
    cursor: CursorDecodificado | None,
    universo_fechado: bool,
) -> PaginaBruta:
    """Ordena, calcula versão determinística, detecta mudança de retrato e fatia por cursor."""
    ordenados = sorted(itens, key=lambda it: it["chave"])
    versao = hashlib.sha256(
        "\n".join(it["chave"] for it in ordenados).encode("utf-8")
    ).hexdigest()[:16]

    mudou: dict[str, str] | None = None
    avisos: list[str] = []
    filtrados = ordenados
    if cursor is not None:
        if cursor.versao_retrato != versao:
            mudou = {"de": cursor.versao_retrato, "para": versao}
            avisos.append("versao_alterada_entre_paginas")
        filtrados = [it for it in ordenados if it["chave"] > cursor.ultima_chave]

    tem_mais = len(filtrados) > limite
    pagina = filtrados[:limite]
    prox = (0, pagina[-1]["chave"]) if (tem_mais and pagina) else None
    return PaginaBruta(
        classe=classe,
        versao=versao,
        digest=None,
        universo_fechado=universo_fechado,
        total=len(ordenados),
        itens=tuple(pagina),
        proxima_tupla=prox,
        mudou=mudou,
        avisos=tuple(avisos),
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
        adaptador = self.obter(alvo.morada)
        prazo_efetivo = max(50, int(prazo_ms))
        return adaptador.ler_objeto(alvo, seletor, prazo_efetivo)

    def listar_chaves(  # noqa: PLR0913 -- assinatura fixa do protocolo AdaptadorMorada
        self, morada: str, classe: str, filtros: Sequence[FiltroCatalogo],
        termo: str | None, limite: int, cursor: CursorDecodificado | None, prazo_ms: int,
    ) -> PaginaBruta:
        return self.obter(morada).listar_chaves(
            classe=classe,
            filtros=filtros,
            termo=termo,
            limite=limite,
            cursor=cursor,
            prazo_ms=prazo_ms,
        )
