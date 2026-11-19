"""Stub do verbo sessao para os testes da abertura."""

from __future__ import annotations

import json
import os
import sys


def main() -> int:
    argv = sys.argv[1:]
    if not argv or argv[0] != "abrir":
        return 0
    cadeira = "engenharia"
    for arg in argv[1:]:
        if not arg.startswith("--"):
            cadeira = arg
            break
    sid = os.environ.get("PF_STUB_SESSAO_ID", "11111111-2222-4333-8444-555555555555")
    oid = os.environ.get("PF_STUB_ORDEM_ID", "o20261117T170000-ab12cd")
    print(json.dumps({
        "sessao_id": sid,
        "cadeira": cadeira,
        "ordem_id": oid,
        "cunhada_agora": True,
        "canonizada": True,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
