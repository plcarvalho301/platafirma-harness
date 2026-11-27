"""tipos — estruturas imutáveis de fronteira e protocolos do componente verificador (card #4454)."""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

VERSAO_CONTRATO = 1
SERVICO_LINT = "servico:harness:lint"
SERVICO_EXECUTOR_TESTES = "servico:harness:executor-de-testes"
MOTOR_SUITE_TESTES = "motor:harness:suite-de-testes"

FORMAS_VERIFICACAO = frozenset({"gabarito", "teste", "bateria"})
PLANOS_VERIFICACAO = frozenset({"construcao", "producao"})


@dataclass(frozen=True, slots=True)
class PedidoVerificacao:
    """Pedido imutável convertido na borda a partir de `<verbo> verificar …`."""

    verbo: str
    substrato: str | None
    alvos: tuple[str, ...]
    reguas: tuple[str, ...]
    como_json: bool = False
    prazo_s: float = 60.0


@dataclass(frozen=True, slots=True)
class AlvoVerificado:
    """Alvo resolvido no plano `construcao` pronto para o serviço que julga."""

    chave: str
    classe: str
    slug: str
    versao: str = "head"
    raiz: Path | None = None
    caminho: str | None = None
    texto: str | None = None


@dataclass(frozen=True, slots=True)
class ReguaFicha:
    """Metadados normativos de uma ficha de verificação (`gabarito`, `teste` ou `bateria`)."""

    chave: str
    forma: str
    sobre: tuple[str, ...] = ()
    contra_o_que: str = "construcao"
    garantido_por: str | None = None
    versao: str = "1"
    itens: tuple[str, ...] = ()
    verifica: str | None = None


@dataclass(frozen=True, slots=True)
class ReguaCasada:
    """Conjunto compatível de réguas casadas com a classe de alvo e o serviço que julga."""

    forma: str
    servico: str
    reguas: tuple[ReguaFicha, ...]
    contra_o_que: str = "construcao"

    @property
    def chaves(self) -> tuple[str, ...]:
        return tuple(r.chave for r in self.reguas)


@dataclass(frozen=True, slots=True)
class Apontamento:
    """Achado estruturado emitido por um serviço que julga."""

    item: str
    alvo: str
    lugar: str
    exigencia: str
    severidade: str
    cura: str

    def como_dict(self) -> dict[str, str]:
        return {
            "item": self.item,
            "alvo": self.alvo,
            "lugar": self.lugar,
            "exigencia": self.exigencia,
            "severidade": self.severidade,
            "cura": self.cura,
        }


@dataclass(frozen=True, slots=True)
class VereditoItem:
    """Veredito individual de um alvo ou ficha inspecionada."""

    alvo: str
    resultado: str
    constatacao: str
    apontamentos: tuple[Apontamento, ...] = ()
    modo: str = "enquadrou"
    quesito: str = ""
    chave: str = ""
    motor: str = ""
    versao_servico: str = ""
    versao_regua: str = ""
    nao_julgados: tuple[str, ...] = ()

    def como_dict(self) -> dict[str, Any]:
        return {
            "alvo": self.alvo,
            "resultado": self.resultado,
            "constatacao": self.constatacao,
            "apontamentos": [a.como_dict() for a in self.apontamentos],
        }


@dataclass(frozen=True, slots=True)
class VereditoEmitido:
    """Objeto contratual devolvido na saída 0 pelo verificador."""

    versao_contrato: int
    resultado: str
    constatacao: str
    modo: str
    quesito: str | tuple[str, ...]
    chave: str
    motor: str
    itens: tuple[VereditoItem, ...]
    apontamentos: tuple[Apontamento, ...]
    nao_julgados: tuple[str, ...] = ()

    def como_dict(self) -> dict[str, Any]:
        quesito_val: Any = (
            self.quesito[0]
            if isinstance(self.quesito, tuple) and len(self.quesito) == 1
            else (list(self.quesito) if isinstance(self.quesito, tuple) else self.quesito)
        )
        dados: dict[str, Any] = {
            "versao_contrato": self.versao_contrato,
            "veredito": {
                "resultado": self.resultado,
                "constatacao": self.constatacao,
                "modo": self.modo,
                "quesito": quesito_val,
                "chave": self.chave,
                "motor": self.motor,
            },
            "itens": [item.como_dict() for item in self.itens],
            "apontamentos": [a.como_dict() for a in self.apontamentos],
        }
        if self.nao_julgados:
            dados["nao_julgados"] = list(self.nao_julgados)
        return dados


@dataclass(frozen=True, slots=True)
class VistaVerificar:
    """Espelho local das ligações `aceita` e `alcanca` do bloco `verificar` da vista de alcance."""

    verbos_aceitam: frozenset[str]
    alcance_por_verbo: Mapping[str, frozenset[str]]


class LeitorFichario(Protocol):
    """Interface de leitura do fichário usada por casamento e conteúdos sob retrato único."""

    def ler_regua(self, chave: str) -> ReguaFicha | None: ...

    def regua_padrao(self, classe: str) -> str | None: ...

    def ler_alvo(self, chave: str) -> AlvoVerificado | None: ...

    def linhagem_compativel(self, classe_alvo: str, sobre: Sequence[str]) -> bool: ...


class DelegadorSuite(Protocol):
    """Interface de delegação à suíte de testes que a story #4455 liga ao ato despachar."""

    def despachar_suite(
        self,
        chaves_fichas: Sequence[str],
        arvore: Path,
        *,
        alvo: str,
        prazo_s: float,
    ) -> VereditoEmitido: ...


class ErroVerificacaoParcial(Exception):
    """Recusa na saída 5 que preserva os vereditos individuais das partes já olhadas."""

    def __init__(self, recusa: Any, itens: Sequence[VereditoItem]) -> None:
        super().__init__(getattr(recusa, "cura", "verificação interrompida com parciais"))
        self.recusa = recusa
        self.itens = tuple(itens)


@dataclass(frozen=True, slots=True)
class AmbienteVerificacao:
    """Dependências injetáveis do verificador (sem estado global)."""

    vista: VistaVerificar | None = None
    caminho_vista: Path | None = None
    fichario: LeitorFichario | None = None
    executor_lint: Callable[..., Any] | None = None
    executor_isolado: Callable[[Path, list[str]], Mapping[str, Any]] | None = None
    delegador_suite: DelegadorSuite | None = None
    leitor_arvore: Callable[[str, str | None], AlvoVerificado | None] | None = None
    prazo_s: float = 60.0
    host: str = "casa"
    stack: str = "harness"
