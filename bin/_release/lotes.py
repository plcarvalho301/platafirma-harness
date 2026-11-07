"""Antes de recriar conhecimento, declarar os lotes em voo (#2856 linha 140)."""
from __future__ import annotations

import json
import subprocess
import sys

SQL = """SELECT coalesce(json_agg(id::text ORDER BY criado_em), '[]'::json)
           FROM acervo.lote_reextracao WHERE estado = 'aplicando'"""


def conferir(*, confirmar: bool = False) -> int:
    try:
        proc = subprocess.run(["acervo", "psql", "-t", "-A", "-c", SQL],
                              capture_output=True, text=True, timeout=20, check=False)
        if proc.returncode:
            print("release: não consegui conferir lotes de transcrição: " + proc.stderr[-300:],
                  file=sys.stderr)
            return 3
        # acervo psql pode devolver a tabela do psql, mesmo com -t -A.
        linhas = [linha.strip() for linha in proc.stdout.splitlines() if linha.strip().startswith("[")]
        lotes = json.loads(linhas[0] if len(linhas) == 1 else proc.stdout.strip())
        if not isinstance(lotes, list):
            raise TypeError("lista de lotes inválida")
    except (OSError, subprocess.SubprocessError, ValueError, TypeError) as exc:
        print(f"release: não consegui conferir lotes de transcrição: {exc}", file=sys.stderr)
        return 3
    if not lotes:
        return 0
    print("release: lote(s) de transcrição em voo: " + ", ".join(lotes) +
          ". A recriação interrompe o processo; a fila durável retoma na subida.", file=sys.stderr)
    if not confirmar:
        print("release: current preservado; repita com --confirmar-lotes para autorizar a interrupção.",
              file=sys.stderr)
        return 4
    return 0


if __name__ == "__main__":
    sys.exit(conferir(confirmar="--confirmar" in sys.argv[1:]))
