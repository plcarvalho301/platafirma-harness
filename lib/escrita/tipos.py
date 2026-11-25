"""Estruturas imutáveis de fronteira e catálogo fechado de recusas do ato escrever."""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, TextIO

from leitura.recusa import CAMPOS as CAMPOS_ERRO
from leitura.recusa import cortar as cortar_recebido

FORMAS_ESCRITA = frozenset(
    {"gravar", "criar", "trocar", "retirar", "restaurar", "ensaiar"}
)
FORMAS_ENSAIAR = frozenset({"criar", "trocar", "recompor"})
FORMATOS_CONTEUDO = frozenset({"inteiro", "trecho", "patch"})
DOCUMENTOS_ALVO = frozenset({"golden", "referencia"})
REGIMES_ESCRITA = frozenset({"comum", "guardada"})
MORADAS_ESCRITA = frozenset(
    {"git", "banco", "wiki", "rastreador", "fila", "balde", "cofre"}
)

CODIGOS_POR_SAIDA: dict[int, frozenset[str]] = {
    1: frozenset(
        {
            "classe-fora-do-verbo",
            "alvo-inexistente",
        }
    ),
    2: frozenset(
        {
            "ato-nao-aceito",
            "variante-nao-executa",
            "forma-fora-do-regime",
            "forma-sem-morada",
            "flag-desconhecida",
            "conflito-de-opcoes",
            "chave-invalida",
            "caminho-solto-recusado",
            "documento-ambiguo",
            "sem-bancada",
            "clone-base-recusado",
            "bancada-ambigua",
            "ja-existe",
            "versao-ausente",
            "versao-invalida",
            "versao-divergente",
            "conteudo-vazio",
            "conteudo-parcial",
            "encoding-invalido",
            "arquivo-binario",
            "tamanho-excedido",
            "sem-shebang",
            "trecho-invalido",
            "trecho-nao-encontrado",
            "trecho-ambiguo",
            "patch-invalido",
            "patch-multi-alvo",
            "remocao-nao-suportada",
            "hunk-nao-casa",
            "patch-sem-efeito",
            "pedido-invalido",
            "pedido-com-conteudo-diferente",
            "em-curso",
        }
    ),
    3: frozenset(
        {
            "escritor-indisponivel",
            "morada-sem-resposta",
            "politica-indisponivel",
            "bancada-ocupada",
            "sem-espaco",
        }
    ),
    4: frozenset(
        {
            "identidade-sem-assinatura",
            "token-invalido",
            "acesso-negado",
            "segredo-recusado",
            "superficie-vedada",
            "caminho-com-atalho",
            "fora-de-morada",
        }
    ),
    5: frozenset(
        {
            "tempo-esgotado",
            "morto-por-sinal",
            "falta-de-memoria",
            "falha-disco",
            "resposta-perdida",
        }
    ),
}

SAIDA_POR_CODIGO: dict[str, int] = {
    codigo: saida
    for saida, codigos in CODIGOS_POR_SAIDA.items()
    for codigo in codigos
}


@dataclass(frozen=True, kw_only=True)
class ErroEscrita:
    """Recusa estruturada em seis campos fixos ligada ao catálogo fechado 1..5."""

    codigo: str
    saida: int
    onde: str = ""
    recebido: str = ""
    regra: str = ""
    cura: str = ""
    proximo: str = ""

    def __post_init__(self) -> None:
        permitidos = CODIGOS_POR_SAIDA.get(self.saida)
        if permitidos is None:
            raise ValueError(f"saída {self.saida!r} fora do catálogo 1..5")
        if self.codigo not in permitidos:
            raise ValueError(
                f"código {self.codigo!r} fora do catálogo fechado para saída {self.saida}"
            )
        object.__setattr__(self, "recebido", cortar_recebido(self.recebido))

    def como_dict(self) -> dict[str, str]:
        """Devolve os seis campos na ordem fixa do contrato."""
        return {campo: str(getattr(self, campo) or "") for campo in CAMPOS_ERRO}


class RecusaEscrita(Exception):
    """Exceção tipada com uma ou mais recusas do mesmo pedido."""

    def __init__(self, erros: ErroEscrita | Sequence[ErroEscrita]) -> None:
        lista = (erros,) if isinstance(erros, ErroEscrita) else tuple(erros)
        if not lista:
            raise ValueError("lista de recusas vazia")
        self.erros: tuple[ErroEscrita, ...] = lista
        self.primeiro: ErroEscrita = lista[0]
        self.saida: int = self.primeiro.saida
        super().__init__(self.primeiro.codigo)

    def como_payload(self) -> dict[str, Any]:
        """Devolve `{"erro": ..., "erros": [...]}` com os seis campos fixos."""
        itens = [err.como_dict() for err in self.erros]
        return {"erro": itens[0], "erros": itens}

    def como_linha_json(self) -> str:
        """Serializa o payload de recusa em uma única linha JSON."""
        return json.dumps(self.como_payload(), ensure_ascii=False)


def emitir_recusa(recusa: RecusaEscrita, *, fluxo: TextIO | None = None) -> int:
    """Escreve o JSON único da recusa na última linha de stderr e devolve a saída."""
    destino = sys.stderr if fluxo is None else fluxo
    destino.write(recusa.como_linha_json() + "\n")
    destino.flush()
    return recusa.saida


@dataclass(frozen=True)
class ContextoEscrita:
    """Contexto imutável da chamada, com o campo `token` reservado para #3943."""

    verbo: str
    cadeira: str = ""
    sujeito: str = ""
    sessao_id: str = ""
    ordem_id: str = ""
    card: str = ""
    prazo_ns: int = 0
    token: str = ""
    classe_unica: str | None = None
    exige_objeto_casa: bool = False


@dataclass(frozen=True)
class TrocaTrecho:
    """Pedido validado de substituição de trecho em arquivo de componente."""

    antes: str
    depois: str
    todos: bool = False

    def __post_init__(self) -> None:
        if not self.antes:
            raise ValueError("trecho.antes não pode ser vazio")


@dataclass(frozen=True)
class HunkPatch:
    """Um hunk validado de unified diff estrito."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    linhas: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.old_start < 0 or self.new_start < 0:
            raise ValueError("posição inicial de hunk negativa")
        if self.old_count < 0 or self.new_count < 0:
            raise ValueError("contagem de linhas de hunk negativa")
        if not self.linhas:
            raise ValueError("hunk sem linhas")


@dataclass(frozen=True)
class PatchEstrito:
    """Unified diff estrito de um único arquivo."""

    old_path: str
    new_path: str
    hunks: tuple[HunkPatch, ...]

    def __post_init__(self) -> None:
        if not self.hunks:
            raise ValueError("patch sem hunks")


@dataclass(frozen=True)
class PedidoEscrita:
    """Registro imutável entregue pela conversão de borda aos estágios seguintes."""

    verbo: str
    forma: str
    classe: str | None
    chave: str
    versao: str | None
    pedido: str
    formato: str = "inteiro"
    documento: str | None = None
    permitir_vazio: bool = False
    como_json: bool = False
    forma_ensaiada: str | None = None
    conteudo: str | None = None
    trecho: TrocaTrecho | None = None
    patch: PatchEstrito | None = None
    contexto: ContextoEscrita = ContextoEscrita(verbo="")

    def __post_init__(self) -> None:
        if self.forma not in FORMAS_ESCRITA:
            raise ValueError(f"forma inválida: {self.forma!r}")
        if self.formato not in FORMATOS_CONTEUDO:
            raise ValueError(f"formato inválido: {self.formato!r}")
        if self.documento is not None and self.documento not in DOCUMENTOS_ALVO:
            raise ValueError(f"documento inválido: {self.documento!r}")
        if self.forma == "ensaiar" and self.forma_ensaiada not in FORMAS_ENSAIAR:
            raise ValueError(f"forma ensaiada inválida: {self.forma_ensaiada!r}")


@dataclass(frozen=True)
class AlvoEscrita:
    """Alvo resolvido depois do portão de acesso."""

    classe: str
    chave: str
    regime: str
    morada: str
    endereco: str
    documento: str | None = None
    repo: str | None = None
    caminho_relativo: str | None = None

    def __post_init__(self) -> None:
        if self.regime not in REGIMES_ESCRITA:
            raise ValueError(f"regime inválido: {self.regime!r}")
        if self.morada not in MORADAS_ESCRITA:
            raise ValueError(f"morada inválida: {self.morada!r}")


@dataclass(frozen=True)
class ResultadoEscrita:
    """Retorno canônico das seis formas do ato escrever."""

    chave: str
    classe: str
    forma: str
    morada: str
    release: str
    pedido: str
    alterou: bool
    ja_gravado: bool
    substituiu: bool
    bytes: int
    versao: str | None = None
    versao_completa: str | None = None
    versao_anterior: str | None = None
    ocorrencias: int | None = None
    hunks_aplicados: int | None = None
    desfazer: str | None = None
    ensaiado: bool = False
    mudaria: bool | None = None
    fornada: str | None = None

    def como_dict(self) -> dict[str, Any]:
        """Serializa no formato do esquema retorno-escrever.schema.json."""
        payload: dict[str, Any] = {
            "ok": True,
            "chave": self.chave,
            "classe": self.classe,
            "forma": self.forma,
            "morada": self.morada,
            "release": self.release,
            "versao": self.versao,
            "versao_completa": self.versao_completa,
            "versao_anterior": self.versao_anterior,
            "pedido": self.pedido,
            "alterou": self.alterou,
            "ja_gravado": self.ja_gravado,
            "substituiu": self.substituiu,
            "bytes": self.bytes,
            "ocorrencias": self.ocorrencias,
            "hunks_aplicados": self.hunks_aplicados,
            "desfazer": self.desfazer,
        }
        if self.ensaiado:
            payload["ensaiado"] = True
            payload["mudaria"] = self.mudaria
        if self.fornada is not None:
            payload["fornada"] = self.fornada
        return payload

    def primeira_linha(self) -> str:
        """Renderiza a primeira linha textual fixa da saída padrão."""
        if self.ensaiado:
            resumo = "ensaiado (mudaria)" if self.mudaria else "ensaiado (sem mudança)"
            return f"{self.chave} · versão - · {resumo}"
        resumo = "já gravada" if self.ja_gravado else self.forma
        versao_txt = self.versao or "-"
        return f"{self.chave} · versão {versao_txt} · {resumo}"


__all__ = [
    "CAMPOS_ERRO",
    "CODIGOS_POR_SAIDA",
    "DOCUMENTOS_ALVO",
    "FORMAS_ENSAIAR",
    "FORMAS_ESCRITA",
    "FORMATOS_CONTEUDO",
    "MORADAS_ESCRITA",
    "REGIMES_ESCRITA",
    "SAIDA_POR_CODIGO",
    "AlvoEscrita",
    "ContextoEscrita",
    "ErroEscrita",
    "HunkPatch",
    "PatchEstrito",
    "PedidoEscrita",
    "RecusaEscrita",
    "ResultadoEscrita",
    "TrocaTrecho",
    "cortar_recebido",
    "emitir_recusa",
]
