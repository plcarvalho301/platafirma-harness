"""Núcleo do adaptador — o contrato que as seis fontes cumprem.

`spec_recuperador.md` §5. Três regras que valem para todo adaptador, e que este módulo
é quem faz valer:

- **Ao contrato da fonte, nunca ao binário.** O adaptador chama o que o CLI chama por
  baixo. Subprocess sobre saída de CLI acopla à superfície humana, que é volátil por
  desenho, e transforma mudança de forma em quebra de recuperação (`arq:0064` §1).
- **Nenhum adaptador reimplementa a fonte.** Ele projeta o que a fonte já sabe
  responder, no envelope.
- **Fonte sem gold serve `nao-calibrada`, nunca "boa"** (§13). É por isso que
  `tem_gold` é campo do adaptador e não comentário: hoje é `False` nas seis, e o
  rótulo servido diz isso em vez de fingir régua.

Quem levanta e quem declara: o adaptador **levanta** `FonteIndisponivel` quando a fonte
não responde, porque quem precisa saber disso é o disjuntor. Quem transforma em linha de
envelope é `busca_declarada()`, aqui. O consumidor nunca vê exceção — vê `aviso.causa`.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..envelope import Causa, Cobertura, Envelope, Item, LinhaFonte, Sinal
from ..fontes import Fonte, timeout_ms


class FonteIndisponivel(Exception):
    """A fonte não respondeu. Carrega a causa, que é o que vai ao envelope."""

    def __init__(self, causa: Causa, detalhe: str = "") -> None:
        self.causa = Causa(causa)
        super().__init__(f"{self.causa}: {detalhe}" if detalhe else str(self.causa))


@dataclass(slots=True)
class Resultado:
    """O que um adaptador devolve: a linha da fonte e os itens dela.

    Uma linha SEMPRE, mesmo sem item e mesmo com a fonte caída — é a invariante 4.
    """

    linha: LinhaFonte
    itens: list[Item] = field(default_factory=list)


class Adaptador(ABC):
    """Um por fonte. Subclasse implementa `_carimbo` e `_busca`; o resto é comum."""

    fonte: Fonte
    tem_gold: bool = False  # §13 — vira True quando o gold da fonte existir (#2309)

    # ---- o que a subclasse implementa ----------------------------------------------

    @abstractmethod
    def _carimbo(self) -> str:
        """Versão corrente da fonte inteira: `evento.id`, `last-generated-id`, sha.

        Não `max(atualizado_em)`: timestamp falha em dois atos no mesmo instante e em
        apagar-e-criar (§5).
        """

    @abstractmethod
    def _busca(self, alvo: str, filtros: dict | None, k: int, texto: str) -> list[Item]:
        """Os itens, já com procedência completa. Levanta `FonteIndisponivel`."""

    # ---- o que é comum às seis ------------------------------------------------------

    def cobertura_com_item(self) -> Cobertura:
        """Sem gold, o instrumento está desligado — e o valor honesto do instrumento
        desligado é `nao-calibrada`, jamais `coberta` (§13, `arq:0064` §2)."""
        return Cobertura.COBERTA if self.tem_gold else Cobertura.NAO_CALIBRADA

    def sinal(self, itens: list[Item]) -> Sinal | None:
        """Classe exata não gradua: retorno é determinístico e não há piso a comparar."""
        return None

    def busca(self, alvo: str = "", filtros: dict | None = None, k: int = 8,
              texto: str = "secao") -> Resultado:
        """Caminho feliz. Levanta `FonteIndisponivel` — use `busca_declarada`."""
        itens = self._busca(alvo, filtros, k, texto)[:k]
        carimbo = self._carimbo()
        cobertura = self.cobertura_com_item() if itens else Cobertura.VAZIA
        return Resultado(
            linha=LinhaFonte(
                fonte=self.fonte,
                cobertura=cobertura,
                sinal=self.sinal(itens) if itens else None,
                carimbo=carimbo,
            ),
            itens=itens,
        )

    def busca_declarada(self, alvo: str = "", filtros: dict | None = None, k: int = 8,
                        texto: str = "secao") -> Resultado:
        """A falha vira linha, nunca exceção. É o contrato que o consumidor enxerga."""
        try:
            return self.busca(alvo, filtros, k, texto)
        except FonteIndisponivel as e:
            return self.recusa(e.causa)
        except Exception:  # noqa: BLE001 — fonte que estoura de um jeito não previsto
            return self.recusa(Causa.FORA_DO_AR)

    def recusa(self, causa: Causa) -> Resultado:
        return Resultado(
            linha=LinhaFonte(
                fonte=self.fonte,
                cobertura=Cobertura.FONTE_NAO_INDEXADA,
                causa=Causa(causa),
            )
        )

    @property
    def timeout_ms(self) -> int:
        return timeout_ms(self.fonte)

    # ---- instrumentação -------------------------------------------------------------

    def busca_medida(self, alvo: str = "", filtros: dict | None = None, k: int = 8,
                     texto: str = "secao") -> tuple[Resultado, float]:
        """O par (resultado, ms). A latência por fonte é o que fecha a hipótese dos
        timeouts do §8, e ela não existe se ninguém a medir desde o primeiro release."""
        t0 = time.perf_counter()
        r = self.busca_declarada(alvo, filtros, k, texto)
        return r, (time.perf_counter() - t0) * 1000


def monta_envelope(resultados, codigo_exato: bool = False, falta: str | None = None,
                   proximo: str | None = None) -> Envelope:
    """N resultados → um envelope de N linhas. A ordem das linhas é a da consulta."""
    resultados = list(resultados)
    itens: list[Item] = []
    for r in resultados:
        itens.extend(r.itens)
    return Envelope(
        linhas=[r.linha for r in resultados],
        itens=itens,
        codigo_exato=codigo_exato,
        falta=falta,
        proximo=proximo,
    )
