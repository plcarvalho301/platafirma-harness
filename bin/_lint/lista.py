"""lista — resolucao de lista de verificacao via acervo da casa."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


class ListaNaoEncontrada(Exception):
    def __init__(self, chave: str, msg: str = ""):
        super().__init__(msg or f"lista de verificacao '{chave}' nao encontrada no acervo")
        self.chave = chave


def resolver_lista(chave: str) -> Optional[Dict[str, Any]]:
    """Tenta obter a lista de verificacao no acervo.
    
    Devolve dict com chaves 'id', 'rev', 'itens' etc., ou None se ausente/indeterminavel.
    """
    if not chave:
        return None

    # Verifica se existe acervo executavel
    aqui = Path(__file__).resolve().parent
    harness_raiz = aqui.parent.parent
    acervo_bin = harness_raiz / "bin" / "acervo"

    if not acervo_bin.exists():
        # Fallback para PATH
        acervo_bin_str = "acervo"
    else:
        acervo_bin_str = str(acervo_bin)

    try:
        proc = subprocess.run(
            [acervo_bin_str, "ler", "casa", "lista-de-verificacao", chave],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                dado = json.loads(proc.stdout)
                return dado
            except json.JSONDecodeError:
                pass
    except (subprocess.SubprocessError, OSError):
        pass

    return None
