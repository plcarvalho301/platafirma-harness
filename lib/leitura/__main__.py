"""Ponto de entrada por processo de `ler_arquivo` (`python -m leitura`)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .leitura import envelope_erro, ler


def main() -> int:
    bruto = sys.stdin.read()
    try:
        req = json.loads(bruto) if bruto.strip() else {}
    except ValueError as exc:
        sys.stdout.write(json.dumps(envelope_erro(2, f"JSON inválido: {exc}"), ensure_ascii=False))
        return 2

    instancia = Path(req["instancia"]) if req.get("instancia") else None
    caminhos = req.get("caminhos")
    if isinstance(caminhos, list) and caminhos:
        itens = [
            ler(
                c,
                linhas=req.get("linhas"),
                paginas=req.get("paginas"),
                termo=req.get("termo"),
                modo=str(req.get("modo") or "texto"),
                encoding=req.get("encoding"),
                dpi=int(req.get("dpi") or 150),
                max_bytes=req.get("max_bytes"),
                versao=req.get("versao"),
                instancia=instancia,
            )
            for c in caminhos
        ]
        res = {"lote": itens, "lote_n": len(itens), "lote_next": None}
        sys.stdout.write(json.dumps(res, ensure_ascii=False))
        return 0

    caminho = req.get("caminho")
    if not caminho:
        res = envelope_erro(2, "informe 'caminho' ou 'caminhos'")
        sys.stdout.write(json.dumps(res, ensure_ascii=False))
        return 2

    res = ler(
        caminho,
        linhas=req.get("linhas"),
        paginas=req.get("paginas"),
        termo=req.get("termo"),
        modo=str(req.get("modo") or "texto"),
        encoding=req.get("encoding"),
        dpi=int(req.get("dpi") or 150),
        max_bytes=req.get("max_bytes"),
        versao=req.get("versao"),
        instancia=instancia,
    )
    sys.stdout.write(json.dumps(res, ensure_ascii=False))
    return int(res.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
