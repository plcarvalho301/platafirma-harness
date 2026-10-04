"""Isolamento da suíte: teste não lê nem escreve estado real (lib/teste_isolado.py)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
import teste_isolado  # noqa: E402

_RAIZ = None


def pytest_configure(config):
    global _RAIZ
    _RAIZ = teste_isolado.isolar()


def pytest_runtest_logstart(nodeid, location):  # TRACE TEMPORARIO #3274: nao vai para a main
    sys.__stderr__.write("TRACE " + nodeid + "\n")
    sys.__stderr__.flush()


def pytest_unconfigure(config):
    teste_isolado.desfazer(_RAIZ)
