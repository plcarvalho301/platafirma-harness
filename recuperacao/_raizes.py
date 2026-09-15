"""Ponte para `lib/raizes.py` da propria arvore do harness (card #3010).

O pacote `recuperacao` mora dentro da arvore do harness; `lib/` e irma dele, e e achada
por realpath deste arquivo — nunca por raiz montada a mao. Daqui saem as duas raizes de
producao (release e instancia); a bancada nunca e lida por este pacote.

`TOKENIZADOR` e o artefato de terceiro pinado da casa (qwen2.5): mora dentro da arvore da
familia, em `terceiros/tokenizers/`, e chega pela release. `PLATAFIRMA_TOKENIZADOR` existe para
teste e CI apontarem um arquivo baixado fora da arvore.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ARVORE = Path(__file__).resolve().parents[1]
_LIB = ARVORE / "lib"
if (_LIB / "raizes.py").is_file() and str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from raizes import instancia, release, release_raiz  # noqa: E402

TOKENIZADOR = os.environ.get(
    "PLATAFIRMA_TOKENIZADOR", str(ARVORE / "terceiros" / "tokenizers" / "qwen2.5.json"))

__all__ = ["ARVORE", "TOKENIZADOR", "instancia", "release", "release_raiz"]
