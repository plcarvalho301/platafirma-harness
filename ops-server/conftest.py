"""Isolamento da suíte: teste não lê nem escreve estado real (lib/teste_isolado.py, arq:0116 §1).

Sem ele, a suíte da porta herdava o ambiente de quem a rodava — PLATAFIRMA_INSTANCIA,
PF_SESSAO, PF_SUJEITO — e mudava de cor conforme a sessão (medido em 28/09: 6 vermelhos
rodando pela porta, todos por variável herdada).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import teste_isolado  # noqa: E402

_RAIZ = None


def pytest_configure(config):
    global _RAIZ
    _RAIZ = teste_isolado.isolar()


def pytest_unconfigure(config):
    teste_isolado.desfazer(_RAIZ)
