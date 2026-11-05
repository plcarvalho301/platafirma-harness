"""Expurgo da área de chegada pela regra 20 (#4120).

Itens na área de chegada (var/chegada/<sha256>) com mais de 7 dias são expurgados;
itens recentes (com menos de 7 dias) são mantidos.
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
import time
from pathlib import Path


def expurgar_chegada(
    pasta_chegada: str | Path,
    dias: int = 7,
    agora: float | None = None,
    dry_run: bool = False,
) -> list[str]:
    """Expurga diretórios ou arquivos em pasta_chegada com mtime mais antigo que `dias` dias."""
    p = Path(pasta_chegada)
    if not p.is_dir():
        return []

    agora_ts = time.time() if agora is None else agora
    limite = agora_ts - (dias * 86400)
    removidos: list[str] = []

    for item in sorted(p.iterdir()):
        try:
            st = item.stat()
            # Avalia mtime contra o limite
            if st.st_mtime < limite:
                nome = item.name
                if not dry_run:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                removidos.append(nome)
        except OSError:
            continue

    return removidos


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Expurgo da área de chegada (regra 20)")
    parser.add_argument("--pasta", default=os.environ.get("PF_CHEGADA_RAIZ") or "var/chegada")
    parser.add_argument("--dias", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    removidos = expurgar_chegada(args.pasta, dias=args.dias, dry_run=args.dry_run)
    for r in removidos:
        sys.stdout.write(f"expurgado: {r}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
