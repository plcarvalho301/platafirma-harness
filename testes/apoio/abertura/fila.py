"""Stub do verbo fila para os testes da abertura."""

from __future__ import annotations

import os
import sys


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] != "ler":
        return 0
    saida = os.environ.get("PF_STUB_FILA")
    if saida is not None:
        print(saida)
        return 0
    print("msg-101 · gestao-estrategica · story 4334 pronta para execução")
    return 0


if __name__ == "__main__":
    sys.exit(main())
