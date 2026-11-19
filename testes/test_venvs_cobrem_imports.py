# componente: componente:porta
# verifica: configuracao:registro-venvs
"""O registro de venvs da família platafirma-harness não declara mais ops nem politica-acesso
(a porta e o acesso moram em platafirma-core desde a F4073, #4340 e #4348)."""
from __future__ import annotations

import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def test_registro_venvs_harness_sem_ops_nem_politica_acesso():
    registro = json.loads((RAIZ / "registro" / "venvs.json").read_text(encoding="utf-8"))
    chaves_harness = {
        k for k, v in registro.items()
        if isinstance(v, dict) and v.get("familia") == "platafirma-harness"
    }
    assert "ops" not in chaves_harness
    assert "politica-acesso" not in chaves_harness
    assert "espelho-ops" not in registro
    assert "porta" in registro and registro["porta"]["familia"] == "platafirma-core"
