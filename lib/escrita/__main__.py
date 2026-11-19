"""Ponto de entrada por processo de `write_file` (`python -m escrita`)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from leitura.leitura import envelope_erro

from .escrita import escrever


def main() -> int:
    bruto = sys.stdin.read()
    try:
        req = json.loads(bruto) if bruto.strip() else {}
    except ValueError as exc:
        sys.stdout.write(json.dumps(envelope_erro(2, f"JSON inválido: {exc}"), ensure_ascii=False))
        return 2

    instancia = Path(req["instancia"]) if req.get("instancia") else None
    path = req.get("path")
    if not path:
        res = envelope_erro(2, "campo 'path' obrigatório")
        sys.stdout.write(json.dumps(res, ensure_ascii=False))
        return 2

    res = escrever(
        path,
        content=str(req.get("content") or ""),
        trecho=req.get("trecho"),
        patch=str(req.get("patch") or ""),
        instancia=instancia,
    )
    sys.stdout.write(json.dumps(res, ensure_ascii=False))
    return int(res.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
