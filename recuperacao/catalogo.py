"""Catálogo de existência — a peça de abertura (#2315, F4).

`spec_recuperador.md` §12 e `arq:0064` item 3. Peça `catalogo-existencia`, regime
`indice`, gatilho `abertura`, teto ⚪ 250 tokens.

## O que a peça responde, e o que ela não responde

Ela responde **existe?** — quantas unidades cada fonte tem e em que carimbo. Não responde
*o quê*: conteúdo sai por `recuperar`, sob demanda. É a diferença entre saber que há 2.816
impressões e carregar as 2.816 na janela.

Por que na abertura: sem ela, a cadeira decide se vale consultar uma fonte pela lembrança
do que ela tinha na última fita — e lembrança de volume envelhece calada. Com ela, a
decisão de consultar é informada por 250 tokens.

## Contadores O(1), mantidos na escrita — nunca `COUNT` na abertura

O §12 é explícito, e a regra é executável aqui: um leitor declara seu `custo`, e leitor de
custo `varredura` é **recusado no construtor**. Contar na abertura transformaria a peça
mais barata do pacote na mais cara, e o defeito só apareceria sob corpus grande — ou seja,
tarde. `CustoProibido` falha o build, não a produção.

## Fonte sem contador entra DECLARADA, nunca omitida

Fonte que não sabe se contar sai com `origem: indisponivel` e o motivo. Peça menor em
silêncio é indistinguível de peça certa, e é o segundo item da lista de armadilhas do
chapéu `harness`: presença lida como prova, ausência lida como zero.

**Zero medido e contador ausente não são a mesma coisa**, e a peça os distingue no texto:
`0` contra `—`.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from enum import StrEnum

from .fontes import Fonte

TETO_TOKENS = 250
RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
TOKENIZADOR = os.path.join(RAIZ, "opt", "tokenizers", "qwen2.5.json")


class Custo(StrEnum):
    """Como o leitor obtém o número. `VARREDURA` não entra na abertura."""

    CONTADOR = "contador"      # O(1): HGET, ledger, `GET /api/carimbo`
    VARREDURA = "varredura"    # O(n): `COUNT`, listagem, walk — proibido aqui


class Origem(StrEnum):
    CONTADOR = "contador"
    INDISPONIVEL = "indisponivel"


class CustoProibido(Exception):
    """Leitor de custo `varredura` na abertura. §12: nunca `COUNT` na abertura."""


@dataclass(frozen=True, slots=True)
class Leitor:
    """Um por fonte. `ler()` devolve `(itens, carimbo)`; levantar é permitido e vira
    linha `indisponivel` — o catálogo não deixa uma fonte quebrada derrubar a abertura."""

    fonte: Fonte
    ler: object
    custo: Custo = Custo.CONTADOR

    def __post_init__(self) -> None:
        if Custo(self.custo) is Custo.VARREDURA:
            raise CustoProibido(
                f"`{self.fonte}` declarou custo `varredura`: §12 manda contador O(1) "
                "mantido na escrita, nunca COUNT na abertura"
            )
        if not callable(self.ler):
            raise TypeError("Leitor.ler tem de ser chamável")


@dataclass(frozen=True, slots=True)
class LinhaCatalogo:
    fonte: str
    itens: int | None = None
    carimbo: str = ""
    origem: Origem = Origem.CONTADOR
    motivo: str = ""

    def para_json(self) -> dict:
        d: dict = {"fonte": self.fonte, "itens": self.itens, "origem": str(self.origem)}
        if self.carimbo:
            d["carimbo"] = self.carimbo
        if self.motivo:
            d["motivo"] = self.motivo
        return d


@dataclass(frozen=True, slots=True)
class Catalogo:
    linhas: tuple[LinhaCatalogo, ...]

    @property
    def indisponiveis(self) -> tuple[LinhaCatalogo, ...]:
        return tuple(l for l in self.linhas if l.origem is Origem.INDISPONIVEL)

    def para_json(self) -> dict:
        return {"pecas": [l.para_json() for l in self.linhas]}

    def para_texto(self) -> str:
        """A forma servida. Curta por contrato: cada caractere aqui sai de outra peça.

        `—` é contador ausente; `0` é zero medido. Distingui-los é o ponto."""
        largura = max((len(l.fonte) for l in self.linhas), default=0)
        linhas = []
        for l in self.linhas:
            n = "—" if l.itens is None else f"{l.itens:,}".replace(",", ".")
            cauda = l.carimbo or l.motivo
            linhas.append(f"{l.fonte:<{largura}} {n:>9}  {cauda}".rstrip())
        return "\n".join(linhas)


def monta(leitores) -> Catalogo:
    """Chama cada leitor uma vez. Leitor que levanta vira linha declarada, não exceção."""
    linhas = []
    for leitor in leitores:
        if not isinstance(leitor, Leitor):
            raise TypeError("catálogo se monta de Leitor, para o custo poder ser recusado")
        try:
            itens, carimbo = leitor.ler()
            linhas.append(LinhaCatalogo(
                fonte=str(leitor.fonte), itens=int(itens), carimbo=str(carimbo or ""),
                origem=Origem.CONTADOR,
            ))
        except Exception as e:  # noqa: BLE001 — a falha vira declaração, não silêncio
            linhas.append(LinhaCatalogo(
                fonte=str(leitor.fonte), itens=None, origem=Origem.INDISPONIVEL,
                motivo=f"sem contador: {type(e).__name__}",
            ))
    return Catalogo(linhas=tuple(linhas))


def conta_tokens(texto: str) -> int:
    """Tokenizador do modelo servido. `tiktoken` tokeniza qwen errado, e estimativa por
    bytes/4 erra ~40% — teto medido com a régua errada é teto declarado."""
    from tokenizers import Tokenizer

    if not os.path.isfile(TOKENIZADOR):
        raise FileNotFoundError(f"tokenizador ausente: {TOKENIZADOR}")
    return len(Tokenizer.from_file(TOKENIZADOR).encode(texto).ids)


def fontes_sem_leitor(leitores) -> tuple[str, ...]:
    """As seis do catálogo menos as cobertas. Insumo do aviso da montagem."""
    cobertas = {str(l.fonte) for l in leitores}
    return tuple(sorted({str(f) for f in Fonte} - cobertas))


if __name__ == "__main__":  # bancada: mede a peça contra o teto, não estima
    # Números de ORDEM DE GRANDEZA, para medir a forma — não são medição de fonte
    # nenhuma, e por isso não se atribuem a fonte nenhuma no relato. O que se mede
    # aqui é quantos tokens a PEÇA custa, não quanto cada fonte tem.
    exemplo = Catalogo(linhas=tuple(
        LinhaCatalogo(fonte=str(f), itens=n, carimbo="<carimbo>")
        for f, n in zip(Fonte, (999999, 999999, 999999, 999999, 999999, 999999))
    ))
    texto = exemplo.para_texto()
    print(texto)
    print(f"\n{conta_tokens(texto)} tokens (qwen2.5) · teto {TETO_TOKENS}")
    print(json.dumps(exemplo.para_json(), ensure_ascii=False))
