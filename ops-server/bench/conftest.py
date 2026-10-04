"""Costura do bench de leitura (spec ler-arquivo §16): põe `ops-server/` e `ops-server/bench/`
no `sys.path` e leva o derrame da poda para tmp, para o bench não escrever na instância."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_BENCH = Path(__file__).resolve().parent
for _d in (_BENCH.parent, _BENCH):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))


@pytest.fixture(autouse=True)
def _derrame_em_tmp(tmp_path, monkeypatch):
    import poda
    monkeypatch.setattr(poda, "DERRAME", tmp_path / "derrame")
