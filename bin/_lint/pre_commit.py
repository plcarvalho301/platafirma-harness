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


def _nome_do_repo(raiz: Path) -> str:
    p = subprocess.run(["git", "config", "--get", "remote.origin.url"],
                       cwd=raiz, capture_output=True, text=True)
    url = p.stdout.strip() if p.returncode == 0 else ""
    nome = url.rstrip("/").rsplit("/", 1)[-1] if url else raiz.name
    return nome[:-4] if nome.endswith(".git") else nome


def _organizacao_habilitada(raiz: Path) -> bool:
    """Repo declarado em registro/organizacao-bloqueia.json (da release que roda o hook)."""
    import json
    reg = os.environ.get("PF_ORGANIZACAO_BLOQUEIA") or str(HARNESS_DIR / "registro" / "organizacao-bloqueia.json")
    try:
        with open(reg, encoding="utf-8") as f:
            habilitados = json.load(f).get("repositorios", [])
    except (OSError, ValueError):
        return False
    return _nome_do_repo(raiz) in habilitados


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

    # 4. organizacao (staged), so em repositorio declarado (card #3118)
    if _organizacao_habilitada(raiz):
        try:
            from _lint.organizacao import bloqueantes_no_stage
        except ImportError:
            from organizacao import bloqueantes_no_stage
        achados, aviso = bloqueantes_no_stage(raiz)
        if aviso:
            print(f"pre-commit: aviso: {aviso}", file=sys.stderr)
        for apt in achados:
            bloqueantes.append(("organizacao", apt))

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
