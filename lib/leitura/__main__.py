"""Ponto de entrada por processo de `ler_arquivo` (`python -m leitura`, DT 919)."""
from __future__ import annotations

import base64
import json
import os
import sys
from pathlib import Path
from typing import Any

from . import formatos as _formatos
from .leitura import ORCAMENTO_MAX, envelope_erro, ler, lote

_SELETORES = (
    "linhas",
    "paginas",
    "termo",
    "modo",
    "encoding",
    "dpi",
    "max_bytes",
    "versao",
    "offset",
    "membro",
)


def _serializar_imagens(res: dict[str, Any]) -> dict[str, Any]:
    """Converte `png: bytes` em `base64: str` na fronteira JSON com a porta."""
    if isinstance(res.get("lote"), list):
        return {
            **res,
            "lote": [
                _serializar_imagens(it) if isinstance(it, dict) else it for it in res["lote"]
            ],
        }
    if not isinstance(res.get("imagens"), list):
        return res
    novas = []
    for item in res["imagens"]:
        if isinstance(item, dict) and isinstance(item.get("png"), (bytes, bytearray)):
            it = dict(item)
            raw = bytes(it.pop("png"))
            it["base64"] = base64.b64encode(raw).decode("ascii")
            novas.append(it)
        else:
            novas.append(item)
    return {**res, "imagens": novas}


def _extrair_ctx(req: dict[str, Any]) -> dict[str, Any]:
    return {
        "instancia": Path(req["instancia"]) if req.get("instancia") else None,
        "bancada": Path(req["bancada"]) if req.get("bancada") else None,
        "release": Path(req["release"]) if req.get("release") else None,
        "pdp": Path(req["pdp_dir"]) if req.get("pdp_dir") else None,
        "cadeira": str(req.get("cadeira") or os.environ.get("PF_CADEIRA") or ""),
    }


def _ler_item(item: Any, req: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any]:
    """Lê um item do lote: texto é o caminho; objeto traz caminho e seletores próprios (DT 897)."""
    if isinstance(item, dict):
        caminho = item.get("caminho")
        sel = {k: item.get(k, req.get(k)) for k in _SELETORES}
    else:
        caminho = item
        sel = {k: req.get(k) for k in _SELETORES}
    if not caminho or not isinstance(caminho, str):
        return envelope_erro(2, "item do lote sem 'caminho'")
    dpi = _formatos.DPI_PADRAO if sel["dpi"] is None else sel["dpi"]
    return ler(
        caminho,
        linhas=sel["linhas"],
        paginas=sel["paginas"],
        termo=sel["termo"],
        modo=str(sel["modo"] or "texto"),
        encoding=sel["encoding"],
        dpi=dpi,
        max_bytes=sel["max_bytes"],
        versao=sel["versao"],
        offset=sel["offset"],
        membro=sel["membro"],
        **ctx,
    )


def main() -> int:
    bruto = sys.stdin.read()
    try:
        req = json.loads(bruto) if bruto.strip() else {}
    except ValueError as exc:
        sys.stdout.write(json.dumps(envelope_erro(2, f"JSON inválido: {exc}"), ensure_ascii=False))
        return 2

    ctx = _extrair_ctx(req)
    caminhos = req.get("caminhos")
    if isinstance(caminhos, str):
        res = envelope_erro(2, "parâmetro `caminhos` exige lista, não texto escalar")
        sys.stdout.write(json.dumps(res, ensure_ascii=False))
        return 2
    if isinstance(caminhos, list) and caminhos:
        teto = int(req.get("teto") or req.get("cap") or ORCAMENTO_MAX)
        res = lote(caminhos, lambda _i, c: _ler_item(c, req, ctx), teto=teto)
        sys.stdout.write(json.dumps(_serializar_imagens(res), ensure_ascii=False))
        return 0

    caminho = req.get("caminho")
    if not caminho:
        res = envelope_erro(2, "informe 'caminho' ou 'caminhos'")
        sys.stdout.write(json.dumps(res, ensure_ascii=False))
        return 2

    dpi = _formatos.DPI_PADRAO if req.get("dpi") is None else req.get("dpi")
    res = ler(
        caminho,
        linhas=req.get("linhas"),
        paginas=req.get("paginas"),
        termo=req.get("termo"),
        modo=str(req.get("modo") or "texto"),
        encoding=req.get("encoding"),
        dpi=dpi,
        max_bytes=req.get("max_bytes"),
        versao=req.get("versao"),
        offset=req.get("offset"),
        membro=req.get("membro"),
        **ctx,
    )
    sys.stdout.write(json.dumps(_serializar_imagens(res), ensure_ascii=False))
    return int(res.get("exit_code") or 0)


if __name__ == "__main__":
    raise SystemExit(main())
