"""Isolamento da suíte: teste não lê nem escreve estado real (lib/teste_isolado.py).

E guarda de SIGPIPE (#3274): `bin/_acervo/registrar` e irmãos faziam
`signal(SIGPIPE, SIG_DFL)` ao serem importados (agora só na execução direta, test_guarda_sigpipe.py), e o fixture `acervo` de test_bot.py restaura
esse valor ao terminar. Com SIG_DFL, uma thread de servidor falso que ainda escreve num
socket fechado pelo cliente mata o pytest inteiro (exit 141) em vez de dar BrokenPipeError;
sob carga, no pre-push, isso virou "suite nao medida" e o push passou. A suíte roda com
SIGPIPE ignorado, antes e depois de cada teste; quem precisa de SIG_DFL o põe dentro do
próprio teste e o devolve.
"""
from __future__ import annotations

import signal
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "lib"))
import teste_isolado  # noqa: E402

_RAIZ = None


def pytest_configure(config):
    global _RAIZ
    _RAIZ = teste_isolado.isolar()


def pytest_unconfigure(config):
    teste_isolado.desfazer(_RAIZ)


@pytest.fixture(autouse=True)
def _sigpipe_ignorado():
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    yield
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
