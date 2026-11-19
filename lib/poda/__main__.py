"""Ponto de entrada por processo da poda no harness (`python -m poda`)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .poda import CAP_PADRAO, podar_envelope


def main() -> int:
    bruto = sys.stdin.read()
    try:
        req = json.loads(bruto)
    except ValueError as exc:
        sys.stderr.write(f"poda: JSON invalido em stdin: {exc}\n")
        return 2

    envelope = req.get("envelope")
    if not isinstance(envelope, dict):
        sys.stderr.write("poda: campo 'envelope' obrigatorio\n")
        return 2

    res = podar_envelope(
        envelope,
        verbo=str(req.get("verbo") or ""),
        argv=list(req.get("argv") or []),
        binario=req.get("binario"),
        sessao_id=str(req.get("sessao_id") or "-"),
        alca=str(req.get("alca") or ""),
        derrame_dir=Path(req.get("derrame_dir") or "/tmp/porta-poda-derrames"),
        ledger_dir=Path(req["ledger_dir"]) if req.get("ledger_dir") else None,
        cap=int(req.get("cap") or CAP_PADRAO),
        inteiro=bool(req.get("inteiro", False)),
        faces=req.get("faces"),
    )
    sys.stdout.write(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
