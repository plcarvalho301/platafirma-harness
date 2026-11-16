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
    _RAIZ = teste_isolado.isolar(config)


def pytest_unconfigure(config):
    teste_isolado.desfazer(_RAIZ)


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _cliente_msg_mem_novo():
    """O cliente do msg-mem fica guardado no processo (server._rc, DT 730). Teste que troca o módulo redis por
    um falso deixava o cliente falso para o seguinte no mesmo trabalhador, e a ordem decidia a cor (medido no
    pre-push de 16/11: 7 vermelhos em test_poda_porta com MagicMock no hget). Cada teste começa sem cliente."""
    s = sys.modules.get("server")
    if s is not None and hasattr(s, "_rc_instancia"):
        s._rc_instancia, s._rc_alvo = None, None
    yield
    s = sys.modules.get("server")
    if s is not None and hasattr(s, "_rc_instancia"):
        s._rc_instancia, s._rc_alvo = None, None
