"""alcance — verificacao dos saltos de acesso sujeito->fonte (PEP/sujeitos/superficies)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Optional

from .resultado import Apontamento


def verificar_alcance(
    raiz: Path | str,
    alvo: Optional[str] = None,
) -> list[Apontamento]:
    """Verifica alcance sujeito->fonte conforme politica de acesso."""
    raiz = Path(raiz)
    # alvo esperado: "<sujeito> <fonte>" ou None
    if not alvo:
        return []

    tokens = alvo.split()
    if len(tokens) < 2:
        return [
            Apontamento(
                "politica-acesso",
                1,
                f"alvo de alcance deve ser '<sujeito> <fonte>', recebido: '{alvo}'",
                "informar sujeito e fonte validos (ex: claudinho-ti board)",
                severidade="aviso",
            )
        ]

    sujeito, fonte = tokens[0], tokens[1]
    politica_dir = raiz / "politica-acesso"
    if not politica_dir.is_dir():
        politica_dir = Path("/opt/platafirma/current/politica-acesso")

    sujeitos_yaml = politica_dir / "sujeitos.yaml"
    if not sujeitos_yaml.is_file():
        return []

    try:
        import yaml
        with open(sujeitos_yaml, encoding="utf-8") as f:
            doc = yaml.safe_load(f) or {}
        sujeitos = doc.get("sujeitos", {})
        if sujeito not in sujeitos:
            return [
                Apontamento(
                    "politica-acesso/sujeitos.yaml",
                    1,
                    f"sujeito '{sujeito}' nao projetado em sujeitos.yaml",
                    f"declarar sujeito '{sujeito}' em politica-acesso/sujeitos.yaml",
                    severidade="bloqueante",
                    id="ALCANCE",
                )
            ]
    except Exception:
        pass

    return []
