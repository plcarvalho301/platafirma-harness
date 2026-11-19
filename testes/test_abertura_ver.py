"""`agente/abertura-ver.py` (DT 369, spec expediente rev 1.3): sem chapéu não roteia e serve 6 peças."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "agente" / "abertura-ver.py"


def _roda(*args: str) -> dict:
    p = subprocess.run(
        [sys.executable, str(SCRIPT), "--clone", str(REPO_ROOT), *args, "--json"],
        capture_output=True, text=True, timeout=30, check=True,
    )
    return json.loads(p.stdout)


def test_sem_chapeu_nao_roteia_e_serve_quatro_pecas():
    pac = _roda("ia", "--pergunta", "janela de contexto")
    assert pac["chapeu"] is None
    assert pac["roteador"]["via"] == "nenhum"
    assert [p["peca"] for p in pac["pecas"]] == [
        "persona", "conduta", "alias-cadeiras", "mesa",
    ]


def test_com_chapeu_serve_chapeu_e_acervo_consultado():
    pac = _roda("ia", "orquestracao", "--pergunta", "janela de contexto")
    assert pac["chapeu"] == "orquestracao"
    assert pac["roteador"]["via"] == "comando"
    assert [p["peca"] for p in pac["pecas"]] == [
        "persona", "chapeu", "conduta", "alias-cadeiras", "mesa",
        "acervo-consultado",
    ]
