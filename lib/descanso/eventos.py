"""Os dois eventos de negócio da sessão: aberta e encerrada (regra 29 da F4269).

Saem pelo `oplog.emitir`, o único caminho que a casa nova tem hoje para o evento de negócio da porta. A sessão
vai como `sobre`, e o sujeito do dono, em `correlacao`. A encerrada leva o desfecho: `descanso`, quando a cadeira
chamou o descanso, ou `abandonada`, quando a abertura seguinte do mesmo sujeito achou a sessão parada.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_LIB = Path(__file__).resolve().parents[1]
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

import oplog  # noqa: E402

SESSAO_ABERTA = "sessao_aberta"
SESSAO_ENCERRADA = "sessao_encerrada"
DESFECHOS = ("descanso", "abandonada")
TOOL = "descanso"


def sujeito_do_ambiente(cadeira: str | None = None) -> str:
    """O sujeito que a porta injeta; sem ele, a cadeira faz as vezes (sessão de teste ou de mão)."""
    return (os.environ.get("PF_SUJEITO") or "").strip() or (cadeira or "").strip() or "-"


def emitir_aberta(sessao_id: str, *, sujeito: str, cadeira: str, diretorio_=None) -> bool:
    return oplog.emitir({
        "tool": "abertura", "evento": SESSAO_ABERTA, "sessao_id": sessao_id, "cadeira": cadeira,
        "sobre": sessao_id, "correlacao": sujeito,
    }, diretorio_=diretorio_)


def emitir_encerrada(sessao_id: str, *, sujeito: str, cadeira: str | None, desfecho: str,
                     diretorio_=None) -> bool:
    if desfecho not in DESFECHOS:
        raise ValueError(f"desfecho fora de {DESFECHOS}: {desfecho!r}")
    return oplog.emitir({
        "tool": TOOL, "evento": SESSAO_ENCERRADA, "sessao_id": sessao_id, "cadeira": cadeira,
        "sobre": sessao_id, "correlacao": sujeito, "desfecho": desfecho,
    }, diretorio_=diretorio_)
