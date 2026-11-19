"""Recusa de chamada de tool sem sessão aberta (regra 36 da F4269, t3 da S4334).

Quando a cadeira chama outra tool sem sessão aberta, a porta recusa e devolve a chamada que abre:
`monta_sessao(cadeira=<slug>, pergunta=<turno>)`. A própria abertura e as leituras da tela passam.
"""

from __future__ import annotations

from dataclasses import dataclass

CHAMADA_QUE_ABRE = "monta_sessao(cadeira=<slug>, pergunta=<turno>)"
TOOLS_DE_ABERTURA = frozenset({"monta_sessao", "abertura"})
LIVRES_PADRAO = frozenset({"monta_sessao", "abertura", "tela"})


@dataclass(frozen=True)
class Recusa:
    codigo: str = "sem-sessao"
    tool: str = ""
    chamada: str = CHAMADA_QUE_ABRE
    mensagem: str = ""

    def __post_init__(self) -> None:
        if not self.mensagem:
            object.__setattr__(
                self,
                "mensagem",
                f"sem sessão aberta para chamar '{self.tool}': abra antes com {self.chamada}",
            )

    def como_dict(self) -> dict:
        return {
            "erro": self.mensagem,
            "codigo": self.codigo,
            "tool": self.tool,
            "chamada": self.chamada,
            "exit_code": 2,
        }


def exigir_sessao(
    tool: str,
    sessao_id: str | None,
    livres: frozenset[str] = LIVRES_PADRAO,
) -> Recusa | None:
    """Deixa passar a abertura e as leituras da tela (`livres`); sem `sessao_id`, devolve a recusa com a chamada que abre."""
    nome = (tool or "").strip()
    if nome in TOOLS_DE_ABERTURA or nome in livres or nome.startswith(("tela:", "tela/")):
        return None
    sid = (sessao_id or "").strip()
    if sid and sid != "-":
        return None
    return Recusa(tool=nome)
