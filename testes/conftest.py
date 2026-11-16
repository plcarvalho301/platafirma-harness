"""Isolamento da suíte: teste não lê nem escreve estado real (lib/teste_isolado.py)."""
from __future__ import annotations

import socketserver
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "lib"))
import teste_isolado  # noqa: E402

_RAIZ = None
_ORIG_SERVE_FOREVER = socketserver.BaseServer.serve_forever


def _serve_forever_rapido(self, poll_interval=0.01):
    # O padrão da stdlib (0.5 s) faz cada server.shutdown() em teste esperar até 0.5 s.
    return _ORIG_SERVE_FOREVER(self, poll_interval=poll_interval)


def pytest_configure(config):
    global _RAIZ
    socketserver.BaseServer.serve_forever = _serve_forever_rapido
    _RAIZ = teste_isolado.isolar(config)


def pytest_unconfigure(config):
    teste_isolado.desfazer(_RAIZ)
