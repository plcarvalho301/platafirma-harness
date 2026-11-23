"""recusa.py — a recusa em seis campos dos verbos de leitura (stories 4426 e 4427).

Contratos:
- platafirma-casa@referencias/instancias/interface-de-verbo/busca.md, seção «Erros»
- platafirma-casa@referencias/instancias/verbo/busca.md, seção «Os códigos de saída»

Módulo isolado, sem dependência do resto da leitura, para os verbos reusarem.
"""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TextIO

CAMPOS = ("codigo", "onde", "recebido", "regra", "cura", "proximo")
SAIDAS = {
    0: "fez",
    1: "negativo",
    2: "uso",
    3: "dependencia",
    4: "recusa",
    5: "indeterminavel",
}
TETO_RECEBIDO = 200


def cortar(valor: object, teto: int = TETO_RECEBIDO) -> str:
    """O valor recebido, cortado no teto seguro."""
    s = "" if valor is None else str(valor)
    return s if len(s) <= teto else s[: teto - 1] + "…"


@dataclass(eq=False)
class Recusa(Exception):
    """Uma recusa: o código de saída e os seis campos."""

    saida: int
    codigo: str
    onde: str = ""
    recebido: str = ""
    regra: str = ""
    cura: str = ""
    proximo: str = ""

    def __post_init__(self) -> None:
        if self.saida not in SAIDAS:
            raise ValueError(f"saída {self.saida!r} fora de 0 a 5")
        Exception.__init__(self, self.codigo)
        self.recebido = cortar(self.recebido)

    def campos(self) -> dict[str, str]:
        return {c: str(getattr(self, c) or "") for c in CAMPOS}

    def linha(self) -> str:
        return " · ".join(f"{c}: {v}" for c, v in self.campos().items())


class Recusas(Exception):
    """Lista não vazia de recusas do mesmo pedido, escrita como erro e erros em JSON."""

    def __init__(self, erros: Sequence[Recusa]) -> None:
        if not erros:
            raise ValueError("lista de recusas vazia")
        self.erros = list(erros)
        self.primeiro = self.erros[0]
        self.saida = self.primeiro.saida
        super().__init__(self.primeiro.codigo)


def formato_lista(recusas: Sequence[Recusa]) -> dict[str, object]:
    """O par `erro` (primeiro) e `erros` (todos), cada um com os seis campos."""
    if not recusas:
        raise ValueError("lista de recusas vazia")
    itens = [r.campos() for r in recusas]
    return {"erro": itens[0], "erros": itens}


def escrever(recusa: Recusa, *, como_json: bool = False, fluxo: TextIO | None = None) -> int:
    """Escreve uma recusa (contrato do ato ler) na saída de erro e devolve o código de saída."""
    destino = sys.stderr if fluxo is None else fluxo
    texto = json.dumps(recusa.campos(), ensure_ascii=False) if como_json else recusa.linha()
    destino.write(texto + "\n")
    destino.flush()
    return recusa.saida


def escrever_lista(recusas: Sequence[Recusa], *, fluxo: TextIO | None = None) -> int:
    """Escreve `erro` e `erros` numa linha JSON na saída de erro e devolve o código de saída."""
    destino = sys.stderr if fluxo is None else fluxo
    corpo = formato_lista(recusas)
    destino.write(json.dumps(corpo, ensure_ascii=False) + "\n")
    destino.flush()
    return recusas[0].saida
