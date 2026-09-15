# _raizes — ponte para lib/raizes.py do harness (card #3010).
# capacidade: expediente
# dono: claudinho-TI
"""Duas moradas possiveis para este pacote, e as duas sem raiz montada a mao:

- no host (agregador, systemd --user) o pacote roda da propria arvore do harness na
  release; `lib/` e irma de `controle/` e sai do realpath deste arquivo.
- no container da tela o pacote mora em /app, fora da arvore; a release entra por bind
  somente-leitura e o compose aponta PYTHONPATH para <release>/harness/lib.

A marca da arvore e `lib/raizes.py`, nao `bin/`: em container parents[2] e "/", e /bin
existe em qualquer imagem — foi assim que nasceu o "/bin/conferir" que nao existe.
"""

from __future__ import annotations

import sys
from pathlib import Path

_CANDIDATA = Path(__file__).resolve().parents[2]
ARVORE: Path | None = _CANDIDATA if (_CANDIDATA / "lib" / "raizes.py").is_file() else None
if ARVORE is not None and str(ARVORE / "lib") not in sys.path:
    sys.path.insert(0, str(ARVORE / "lib"))

from raizes import instancia, release  # noqa: E402

__all__ = ["ARVORE", "instancia", "release"]
