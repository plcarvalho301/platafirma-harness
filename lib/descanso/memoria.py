"""A chave da sessão na memória de trabalho (Valkey msg-mem): `sessao:<id>`, que vive 48 h.

A chave vencida é o único sinal de que a sessão parou. Duas implementações com a mesma forma:

  Valkey       fala com o Valkey pelo protocolo da lousa (lib/postura/lousa.py), sem biblioteca de cliente
  Fixtura      lê e grava um JSON `{"chaves": [...]}` ou `{"fora": true}`; liga com PF_VALKEY_FIXTURE (teste)

`Fora` sobe quando a memória não responde: quem conta diz «não consegui olhar», e não zero.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1]
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from postura.lousa import Fora, Lousa  # noqa: E402

__all__ = ["Fora", "Valkey", "Fixtura", "memoria_do_ambiente", "chave_da_sessao"]


def chave_da_sessao(sessao_id: str) -> str:
    return f"sessao:{sessao_id}"


class Valkey:
    def __init__(self, lousa: Lousa | None = None):
        self._lousa = lousa or Lousa()

    def existe(self, sessao_id: str) -> bool:
        return bool(self._lousa._manda([("EXISTS", chave_da_sessao(sessao_id))])[0])

    def apagar(self, sessao_id: str) -> None:
        self._lousa._manda([("DEL", chave_da_sessao(sessao_id))])


class Fixtura:
    def __init__(self, caminho: str | Path):
        self.caminho = Path(caminho)

    def _ler(self) -> dict:
        try:
            dado = json.loads(self.caminho.read_text(encoding="utf-8"))
        except (OSError, ValueError) as erro:
            raise Fora(f"fixtura da memória ilegível: {erro}") from None
        if dado.get("fora"):
            raise Fora("memória de trabalho fora (fixtura)")
        return dado

    def existe(self, sessao_id: str) -> bool:
        return chave_da_sessao(sessao_id) in set(self._ler().get("chaves") or [])

    def apagar(self, sessao_id: str) -> None:
        dado = self._ler()
        dado["chaves"] = [c for c in dado.get("chaves") or [] if c != chave_da_sessao(sessao_id)]
        self.caminho.write_text(json.dumps(dado, ensure_ascii=False), encoding="utf-8")


def memoria_do_ambiente():
    fixtura = (os.environ.get("PF_VALKEY_FIXTURE") or "").strip()
    return Fixtura(fixtura) if fixtura else Valkey()
