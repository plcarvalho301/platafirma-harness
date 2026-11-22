"""recusa.py — a recusa em seis campos dos verbos de leitura (story 4426).

Contrato: platafirma-casa@referencias/instancias/interface-de-verbo/busca.md, seção «Erros».
Toda recusa sai na saída de erro, numa linha formatada ou num objeto JSON sob --json, com os seis
campos sempre na mesma ordem, e o código de saída vai de 0 a 5. Módulo isolado, sem dependência
do resto da leitura, para os outros verbos reusarem.
"""
from __future__ import annotations

import json
import sys
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


def escrever(recusa: Recusa, *, como_json: bool = False, fluxo: TextIO | None = None) -> int:
    """Escreve a recusa na saída de erro e devolve o código de saída."""
    destino = sys.stderr if fluxo is None else fluxo
    texto = json.dumps(recusa.campos(), ensure_ascii=False) if como_json else recusa.linha()
    destino.write(texto + "\n")
    destino.flush()
    return recusa.saida
