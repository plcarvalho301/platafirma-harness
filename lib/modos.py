"""Modos de trabalho da casa, lidos do acervo (`acervo listar casa modo --json`)."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

MODOS_PADRAO = (
    "varrer", "revisar", "avaliar", "testar", "executar",
    "consultar", "pesquisar", "parecer",
)


def listar(bin_dir: Path, *, timeout: int = 30) -> tuple[str, ...]:
    """Devolve as chaves da espécie `modo` no acervo; cai no catálogo padrão se o acervo não responder."""
    raiz_bin = Path(os.environ.get("PF_BIN") or bin_dir)
    try:
        p = subprocess.run(
            [str(raiz_bin / "acervo"), "listar", "casa", "modo", "--json"],
            capture_output=True, text=True, timeout=timeout, check=False,
        )
        itens = json.loads(p.stdout) if p.returncode == 0 else None
    except (OSError, subprocess.SubprocessError, ValueError):
        return MODOS_PADRAO
    if not isinstance(itens, list):
        return MODOS_PADRAO
    chaves = tuple(
        str(item["chave"]).strip()
        for item in itens
        if isinstance(item, dict) and item.get("chave") and str(item["chave"]).strip()
    )
    return chaves or MODOS_PADRAO
