"""Stub do verbo mesa para os testes da abertura."""

from __future__ import annotations

import os
import sys


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] != "ver":
        return 0
    saida = os.environ.get("PF_STUB_MESA")
    if saida is not None:
        print(saida)
        return 0
    print("#1 [front-end] ajustar espaçamento da grade → card 4100   (plantado ha 3 h)")
    print("#2 [back-end] ligar abertura na porta → card 4334   (plantado ha 1 h)")
    print("  (executou? `mesa fez <n>` — leitura nao esvazia)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
