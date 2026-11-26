"""Contratos imutáveis tipados do componente leitura."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

ModoLeitura = Literal["texto", "pagina", "sumario", "visivel"]
TipoMorada = Literal["banco", "git", "wiki", "balde", "fila", "rastreador", "cofre"]
TipoFiltro = Literal["prop", "sem_prop", "ligacao", "sem_ligacao", "estado", "filhas"]

CAMPOS_RECUSA = ("codigo", "onde", "recebido", "regra", "cura", "proximo")
TETO_RECEBIDO = 200


def cortar_recebido(valor: object, teto: int = TETO_RECEBIDO) -> str:
    """Sanitiza e corta o valor recebido no teto seguro de 200 caracteres."""
    texto = "" if valor is None else str(valor)
    return texto if len(texto) <= teto else texto[: teto - 1] + "…"


@dataclass(frozen=True, slots=True)
class ContextoChamada:
    """Contexto imutável da chamada atravessando os nove estágios."""

    sujeito_jwt: bytes | None = None
    sujeito: str = ""
    sessao_id: str | None = None
    ordem_id: str | None = None
    verbo: str = ""
    origem_autenticada: str = ""
    origem_declarada: str = ""
    prazo_ms: int = 30_000


@dataclass(frozen=True, slots=True)
class SeletorParte:
    """Recorte e modo de renderização validados na borda."""

    modo: ModoLeitura = "texto"
    linhas: tuple[int, int | None] | None = None
    cauda_linhas: int | None = None
    paginas: tuple[int, int | None] | None = None
    cauda_paginas: int | None = None
    offset: int | None = None
    max_bytes: int = 40_000
    inteiro: bool = False
    dpi: int = 150
    encoding: str | None = None
    versao_pedida: str | None = None
    membro: str | None = None
    com_decisoes_ancestrais: bool = False


@dataclass(frozen=True, slots=True)
class FiltroCatalogo:
    """Um filtro validado para a forma listar."""

    tipo: TipoFiltro
    nome: str
    valor: str | None = None


@dataclass(frozen=True, slots=True)
class CursorDecodificado:
    """Cursor opaco de continuação validado e decodificado."""

    versao_token: str
    sujeito: str
    verbo: str
    classe: str
    query_hash: str
    versao_retrato: str
    ultima_ordem: str | int
    ultima_chave: str


@dataclass(frozen=True, slots=True)
class PedidoLer:
    """Pedido validado da forma ler."""

    verbo: str
    classe: str | None
    chaves: tuple[str, ...]
    seletor: SeletorParte = field(default_factory=SeletorParte)
    como_json: bool = False
    avisos_borda: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PedidoListar:
    """Pedido validado da forma listar."""

    verbo: str
    classe: str | None
    filtros: tuple[FiltroCatalogo, ...] = ()
    termo: str | None = None
    limite: int = 100
    cursor: CursorDecodificado | None = None
    como_json: bool = False
    avisos_borda: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AlvoResolvido:
    """Resultado do estágio 3 (resolução pela vista de alcance)."""

    chave_pedida: str
    chave_canonica: str
    classe: str
    morada: TipoMorada
    endereco: str
    universo_fechado: bool
    digest_release: str | None
    eh_ficha_da_classe: bool = False


@dataclass(frozen=True, slots=True)
class ObjetoBruto:
    """Objeto entregue por um adaptador de morada ao núcleo puro."""

    alvo: AlvoResolvido
    versao: str
    dados: bytes | None = None
    fluxo: Any | None = None
    nome_arquivo: str = ""
    total_bytes: int | None = None
    mtime_ns: int | None = None
    avisos: tuple[str, ...] = ()
    mudou: dict[str, str] | None = None


@dataclass(frozen=True, slots=True)
class PaginaBruta:
    """Página crua de chaves entregue por um adaptador de morada."""

    classe: str
    versao: str
    digest: str | None
    universo_fechado: bool
    total: int
    itens: tuple[dict[str, str], ...]
    proxima_tupla: tuple[str | int, str] | None = None
    mudou: dict[str, str] | None = None
    avisos: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Recusa:
    """Registro imutável de recusa contratual em seis campos."""

    saida: int
    codigo: str
    onde: str = ""
    recebido: str = ""
    regra: str = ""
    cura: str = ""
    proximo: str = ""

    def campos(self) -> dict[str, str]:
        return {
            "codigo": str(self.codigo),
            "onde": str(self.onde),
            "recebido": cortar_recebido(self.recebido),
            "regra": str(self.regra),
            "cura": str(self.cura),
            "proximo": str(self.proximo),
        }


@dataclass(frozen=True, slots=True)
class ResultadoLeitura:
    """Resultado estruturado da forma ler."""

    cabecalho: str
    chave: str
    chave_canonica: str
    classe: str
    morada: str
    versao: str
    parte: str
    parcial: bool
    com_perda: bool = False
    avisos: tuple[str, ...] = ()
    conteudo: str | None = None
    imagens: tuple[dict[str, Any], ...] | None = None
    sumario: Any | None = None
    bytes: tuple[int, int] | None = None
    total_bytes: int | None = None
    linhas: tuple[int, int] | None = None
    linhas_total: int | None = None
    paginas: tuple[int, int] | None = None
    paginas_total: int | None = None
    sem_texto: tuple[int, ...] | None = None
    mudou: dict[str, str] | None = None
    proximo: str | None = None
    proximo_args: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class ResultadoListagem:
    """Resultado estruturado da forma listar."""

    cabecalho: str
    classe: str
    versao: str
    digest: str | None
    universo_fechado: bool
    total: int
    itens: tuple[dict[str, str], ...]
    parcial: bool
    avisos: tuple[str, ...] = ()
    mudou: dict[str, str] | None = None
    proximo: str | None = None
    cursor: str | None = None


class AdaptadorMorada(Protocol):
    """Protocolo estreito implementado pelos sete adaptadores de morada."""

    def ler_objeto(
        self, alvo: AlvoResolvido, seletor: SeletorParte, prazo_ms: int
    ) -> ObjetoBruto: ...

    def listar_chaves(
        self,
        classe: str,
        filtros: Sequence[FiltroCatalogo],
        termo: str | None,
        limite: int,
        cursor: CursorDecodificado | None,
        prazo_ms: int,
    ) -> PaginaBruta: ...
