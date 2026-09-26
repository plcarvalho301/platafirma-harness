"""pre_commit — executor do hook pre-commit: avalia APENAS predicados bloqueantes."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Garante path para import de _lint
AQUI = Path(__file__).resolve().parent
HARNESS_DIR = AQUI.parent.parent
if str(AQUI.parent) not in sys.path:
    sys.path.insert(0, str(AQUI.parent))
if str(HARNESS_DIR) not in sys.path:
    sys.path.insert(0, str(HARNESS_DIR))

try:
    from _lint.arranque import verificar_arranque
    from _lint.repo import verificar_repo
    from _lint.superficie import verificar_superficie
except ImportError:
    from arranque import verificar_arranque
    from repo import verificar_repo
    from superficie import verificar_superficie


def main() -> int:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
        raiz = Path(p.stdout.strip())
    except Exception:
        raiz = Path.cwd()

    bloqueantes = []

    # 1. repo (staged)
    for apt in verificar_repo(raiz, staged=True):
        if apt.severidade == "bloqueante":
            bloqueantes.append(("repo", apt))

    # 2. superficie (staged)
    for apt in verificar_superficie(raiz, staged=True):
        if apt.severidade == "bloqueante":
            bloqueantes.append(("superficie", apt))

    # 3. arranque (staged)
    for apt in verificar_arranque(raiz, staged=True):
        if apt.severidade == "bloqueante":
            bloqueantes.append(("arranque", apt))

    if bloqueantes:
        print("pre-commit: commit bloqueado por violacao de regra bloqueante:\n", file=sys.stderr)
        for modulo, apt in bloqueantes:
            print(f"    [{modulo}] {apt.arquivo}:{apt.linha}: {apt.o_que_fere}", file=sys.stderr)
            print(f"            cura: {apt.cura}", file=sys.stderr)
        print("\nPassar por cima: git commit --no-verify (fica so no teu terminal).\n", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
