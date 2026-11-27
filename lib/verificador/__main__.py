"""Entrada CLI `python -m verificador <verbo> verificar …` (card #4454)."""
from __future__ import annotations

import sys
from collections.abc import Sequence

from . import executar

_MIN_ARGS = 2


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < _MIN_ARGS or args[1] != "verificar":
        sys.stderr.write(
            "uso: python -m verificador <verbo> verificar [<substrato>] [<alvo>…] [--regua <chave>…] [--json]\n"
        )
        return 2
    return executar(args[0], args[2:])


if __name__ == "__main__":
    raise SystemExit(main())
