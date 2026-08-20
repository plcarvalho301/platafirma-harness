"""Disjuntor por fonte — biblioteca, dentro do recuperador.

`spec_recuperador.md` §8. Três coisas que a spec fixa e que este módulo implementa
literalmente:

- **Aberto, a fonte responde em 0 ms** com `fonte-nao-indexada` +
  `aviso.causa = disjuntor-aberto`. Não há chamada à fonte, não há espera.
- **Meia-abertura por SONDAGEM, nunca por retentativa imediata.** Passada a espera, o
  disjuntor libera uma tentativa por vez; enquanto ela não volta, todo o resto segue
  recusado. Retentativa imediata devolve a fonte quebrada a carga cheia, que é como
  disjuntor vira amplificador de incidente.
- **Estado observável**, publicado junto de `hit`/`miss` (§9): disjuntor abrindo é sinal
  de problema sério e tem de ser visível à operação, não só ao chamador.

Relógio injetável porque teste de disjuntor com `sleep` mede a paciência de quem roda a
suíte, não o comportamento da peça.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import StrEnum

from .envelope import LinhaFonte, linha_disjuntor_aberto
from .fontes import Fonte


class EstadoDisjuntor(StrEnum):
    FECHADO = "fechado"
    ABERTO = "aberto"
    MEIO_ABERTO = "meio-aberto"


# Padrões. Não são medição: são ponto de partida conservador, e o que os fecha é a
# distribuição de latência e de falha por fonte, depois do F2 (§8, ⚪ hipótese).
LIMIAR_FALHAS = 5
ESPERA_S = 30.0
SONDAGENS = 1


@dataclass(slots=True)
class Disjuntor:
    """Um por fonte. Contagem de falha CONSECUTIVA: sucesso zera.

    Falha esparsa em fonte que funciona não é sintoma de fonte caída, e disjuntor que
    abre com ela troca um incidente da fonte por um incidente do recuperador.
    """

    fonte: Fonte
    limiar_falhas: int = LIMIAR_FALHAS
    espera_s: float = ESPERA_S
    sondagens: int = SONDAGENS
    relogio: object = time.monotonic

    _estado: EstadoDisjuntor = field(default=EstadoDisjuntor.FECHADO, init=False)
    _falhas: int = field(default=0, init=False)
    _aberto_em: float | None = field(default=None, init=False)
    _sondando: int = field(default=0, init=False)
    _abriu_n: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        self.fonte = Fonte(self.fonte)

    # ---- decisão -------------------------------------------------------------------

    def permite(self) -> bool:
        """`True` = pode chamar a fonte. `False` = recusa em 0 ms.

        Consome a vaga de sondagem quando devolve `True` em meia-abertura, por isso não
        é consulta pura: chamar duas vezes e usar uma é bug do chamador. Use `janela()`.
        """
        with self._lock:
            return self._permite_travado()

    def _permite_travado(self) -> bool:
        if self._estado is EstadoDisjuntor.FECHADO:
            return True
        agora = self.relogio()
        if self._estado is EstadoDisjuntor.ABERTO:
            if self._aberto_em is None or (agora - self._aberto_em) < self.espera_s:
                return False
            self._estado = EstadoDisjuntor.MEIO_ABERTO
            self._sondando = 0
        if self._sondando >= self.sondagens:
            return False
        self._sondando += 1
        return True

    def registra_sucesso(self) -> None:
        with self._lock:
            self._falhas = 0
            self._sondando = 0
            self._aberto_em = None
            self._estado = EstadoDisjuntor.FECHADO

    def registra_falha(self) -> None:
        """Falha em meia-abertura reabre na hora e reinicia a espera: a sondagem existe
        para descobrir se a fonte voltou, e ela respondeu que não."""
        with self._lock:
            if self._estado is EstadoDisjuntor.MEIO_ABERTO:
                self._abre()
                return
            self._falhas += 1
            if self._falhas >= self.limiar_falhas:
                self._abre()

    def abre(self) -> None:
        """Abertura forçada — operação, ou fonte que se declarou fora do ar."""
        with self._lock:
            self._abre()

    def _abre(self) -> None:
        if self._estado is not EstadoDisjuntor.ABERTO:
            self._abriu_n += 1
        self._estado = EstadoDisjuntor.ABERTO
        self._aberto_em = self.relogio()
        self._sondando = 0
        self._falhas = 0

    def fecha(self) -> None:
        self.registra_sucesso()

    # ---- estado --------------------------------------------------------------------

    @property
    def estado(self) -> EstadoDisjuntor:
        """Leitura sem efeito. Aberto com a espera vencida já lê `meio-aberto`, porque é
        o que a operação precisa ver: o disjuntor está pronto a sondar."""
        with self._lock:
            if self._estado is EstadoDisjuntor.ABERTO and self._aberto_em is not None:
                if (self.relogio() - self._aberto_em) >= self.espera_s:
                    return EstadoDisjuntor.MEIO_ABERTO
            return self._estado

    def observavel(self) -> dict:
        """§8 — o que vai publicado junto de `hit`/`miss` por fonte (§9)."""
        with self._lock:
            estado = self._estado
            aberto_em = self._aberto_em
            falhas = self._falhas
            abriu_n = self._abriu_n
            sondando = self._sondando
        return {
            "fonte": str(self.fonte),
            "disjuntor": str(estado),
            "falhas_consecutivas": falhas,
            "aberturas": abriu_n,
            "sondagens_em_voo": sondando,
            "aberto_ha_s": None if aberto_em is None else round(self.relogio() - aberto_em, 3),
        }

    # ---- uso ------------------------------------------------------------------------

    def janela(self):
        """Contexto que registra sucesso/falha sozinho.

        Uso:

            with disjuntores[Fonte.WIKI].janela() as passa:
                if not passa:
                    linhas.append(linha_disjuntor_aberto(Fonte.WIKI))
                else:
                    ...  # chama a fonte
        """
        return _Janela(self)

    def linha_recusa(self) -> LinhaFonte:
        """A linha que o envelope recebe quando a chamada não sai — em 0 ms."""
        return linha_disjuntor_aberto(self.fonte)


class _Janela:
    __slots__ = ("_d", "_passa", "_falhou")

    def __init__(self, d: Disjuntor) -> None:
        self._d = d
        self._passa = False
        self._falhou = False

    def __enter__(self) -> bool:
        self._passa = self._d.permite()
        return self._passa

    def __exit__(self, exc_tipo, exc, tb) -> bool:
        if not self._passa:
            return False
        if exc_tipo is not None:
            self._d.registra_falha()
        else:
            self._d.registra_sucesso()
        return False


@dataclass(slots=True)
class Painel:
    """Um disjuntor por fonte, e a vista que a operação lê.

    Painel, não singleton global: o `ops-mcp` é um processo, mas teste e sondagem
    precisam de instância própria, e estado de resiliência escondido em módulo é o que
    faz suíte passar sozinha e falhar em lote.
    """

    limiar_falhas: int = LIMIAR_FALHAS
    espera_s: float = ESPERA_S
    sondagens: int = SONDAGENS
    relogio: object = time.monotonic
    _por_fonte: dict[Fonte, Disjuntor] = field(default_factory=dict, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __getitem__(self, fonte: Fonte) -> Disjuntor:
        f = Fonte(fonte)
        with self._lock:
            d = self._por_fonte.get(f)
            if d is None:
                d = Disjuntor(
                    fonte=f,
                    limiar_falhas=self.limiar_falhas,
                    espera_s=self.espera_s,
                    sondagens=self.sondagens,
                    relogio=self.relogio,
                )
                self._por_fonte[f] = d
            return d

    def observavel(self) -> list[dict]:
        with self._lock:
            ds = list(self._por_fonte.values())
        return [d.observavel() for d in ds]

    @property
    def abertos(self) -> list[Fonte]:
        with self._lock:
            ds = list(self._por_fonte.values())
        return [d.fonte for d in ds if d.estado is not EstadoDisjuntor.FECHADO]
