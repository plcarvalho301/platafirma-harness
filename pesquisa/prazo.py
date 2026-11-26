"""Prazo total de uma chamada de rede do verbo (card #4457 t3).

A porta corta a conexão perto de 45 s. O timeout do httpx vale por operação e por endereço
que o DNS devolve, e no `resolver doi` somou 80 s: a porta caiu antes do JSON de falha. Aqui a
chamada roda numa thread daemon e o ato espera até o prazo. Vencido o prazo, sai a falha
`prazo-total-esgotado` em JSON, e o processo não espera a thread presa no socket.

Só a ida à rede passa por aqui. A gravação no disco fica na thread do ato, depois que a
chamada volta, para que nada se grave depois de o ato ter respondido.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

from .envelope import FalhaFonte

PRAZO_TOTAL_S = 40.0  # abaixo dos ~45 s em que a porta corta a conexão
CONEXAO_S = 10.0  # por tentativa de conexão; o resto do tempo é do prazo total

T = TypeVar("T")


class Relogio:
    """O que sobra do prazo total de um ato, para repartir entre as chamadas dele."""

    def __init__(self, prazo_s: float | None = None) -> None:
        self.prazo_s = PRAZO_TOTAL_S if prazo_s is None else float(prazo_s)
        self._fim = time.monotonic() + self.prazo_s

    def resta(self) -> float:
        return max(0.0, self._fim - time.monotonic())


def com_prazo(fn: Callable[[], T], prazo_s: float | None = None, *, onde: str = "rede") -> T:
    """Roda `fn` e devolve o retorno dela, ou levanta a exceção dela, dentro do prazo.

    Prazo vencido levanta `FalhaFonte("prazo-total-esgotado")`, com o prazo e o trecho no extra.
    """
    prazo = PRAZO_TOTAL_S if prazo_s is None else max(0.0, float(prazo_s))
    caixa: dict[str, Any] = {}

    def _roda() -> None:
        try:
            caixa["valor"] = fn()
        except BaseException as exc:  # noqa: BLE001 — a exceção volta inteira a quem chamou
            caixa["erro"] = exc

    fio = threading.Thread(target=_roda, name=f"pesquisa-{onde}", daemon=True)
    fio.start()
    fio.join(prazo)
    if fio.is_alive():
        raise FalhaFonte("prazo-total-esgotado", prazo_s=round(prazo, 1), onde=onde)
    if "erro" in caixa:
        raise caixa["erro"]
    return caixa["valor"]
