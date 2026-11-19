"""Ponto de entrada por processo de `ler_arquivo` (`python -m leitura`)."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from .leitura import envelope_erro, ler


_SELETORES = ("linhas", "paginas", "termo", "modo", "encoding", "dpi", "max_bytes", "versao")


def _ler_item(
    item: Any,
    req: dict,
    *,
    instancia: Path | None,
    bancada: Path | None,
    release: Path | None,
    pdp: Path | None,
    cadeira: str,
) -> dict:
    """Lê um item do lote: texto é o caminho; objeto traz caminho e seletores próprios (DT 897)."""
    if isinstance(item, dict):
        caminho = item.get("caminho")
        sel = {k: item.get(k, req.get(k)) for k in _SELETORES}
    else:
        caminho = item
        sel = {k: req.get(k) for k in _SELETORES}
    if not caminho or not isinstance(caminho, str):
        return envelope_erro(2, "item do lote sem 'caminho'")
    return ler(
        caminho,
        linhas=sel["linhas"],
        paginas=sel["paginas"],
        termo=sel["termo"],
        modo=str(sel["modo"] or "texto"),
        encoding=sel["encoding"],
        dpi=int(sel["dpi"] or 150),
        max_bytes=sel["max_bytes"],
        versao=sel["versao"],
        instancia=instancia,
        bancada=bancada,
        release=release,
        pdp=pdp,
        cadeira=cadeira,
    )


def main() -> int:
    bruto = sys.stdin.read()
    try:
        req = json.loads(bruto) if bruto.strip() else {}
    except ValueError as exc:
        sys.stdout.write(json.dumps(envelope_erro(2, f"JSON inválido: {exc}"), ensure_ascii=False))
        return 2

    instancia = Path(req["instancia"]) if req.get("instancia") else None
    bancada = Path(req["bancada"]) if req.get("bancada") else None
    release = Path(req["release"]) if req.get("release") else None
    pdp = Path(req["pdp_dir"]) if req.get("pdp_dir") else None
    cadeira = str(req.get("cadeira") or os.environ.get("PF_CADEIRA") or "")

    caminhos = req.get("caminhos")
    if isinstance(caminhos, str):
        res = envelope_erro(2, "parâmetro `caminhos` exige lista, não texto escalar")
        sys.stdout.write(json.dumps(res, ensure_ascii=False))
        return 2
    if isinstance(caminhos, list) and caminhos:
        itens = [
            _ler_item(
                c,
                req,
                instancia=instancia,
                bancada=bancada,
                release=release,
                pdp=pdp,
                cadeira=cadeira,
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
        bancada=bancada,
        release=release,
        pdp=pdp,
        cadeira=cadeira,
    )
    sys.stdout.write(json.dumps(res, ensure_ascii=False))
    return int(res.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
