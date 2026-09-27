"""commit_msg — executor do hook commit-msg: avalia predicados bloqueantes de citacao."""
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
    from _lint.commit import declaracao_de_commit, verificar_commit
except ImportError:
    from commit import declaracao_de_commit, verificar_commit


def main() -> int:
    if len(sys.argv) < 2:
        return 0

    arquivo_msg = sys.argv[1]
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

    # OPT-IN POR REPO (limite 1 da classe commit): sem `.conferir-commit` na raiz, o hook
    # nao pergunta nada. O hook vale para todo clone que aponta o hooksPath; gatear quem
    # nao pediu ligaria o gate em todos de uma vez, sem aviso e sem rollout.
    if declaracao_de_commit(raiz) is None:
        return 0

    apts = verificar_commit(raiz, alvo=arquivo_msg)
    bloqueantes = [a for a in apts if a.severidade == "bloqueante"]

    if bloqueantes:
        print("commit-msg: mensagem recusada pelo rastreador:\n", file=sys.stderr)
        for apt in bloqueantes:
            print(f"    {apt.o_que_fere}", file=sys.stderr)
            print(f"    cura: {apt.cura}", file=sys.stderr)
        print("\nPassar por cima: git commit --no-verify (fica so no teu terminal).\n", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
