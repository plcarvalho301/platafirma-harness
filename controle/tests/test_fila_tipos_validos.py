# componente: componente:verbo-fila
"""DT 202: fonte unica de TIPOS_VALIDOS entre bin/_fila/streams.py e controle/harness_controle/web.py."""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
for p in (str(RAIZ / "lib"), str(RAIZ / "bin" / "_fila"), str(RAIZ / "controle")):
    if p not in sys.path:
        sys.path.insert(0, p)

import fila_tipos  # noqa: E402
import streams as fila_streams  # noqa: E402
from harness_controle import web as controle_web  # noqa: E402


def test_tipos_validos_vem_da_mesma_fonte():
    assert fila_streams.TIPOS_VALIDOS is fila_tipos.TIPOS_VALIDOS
    assert controle_web.TIPOS_VALIDOS is fila_tipos.TIPOS_VALIDOS


def test_clientes_nao_redefinem_tipos_validos_localmente():
    streams_src = (RAIZ / "bin" / "_fila" / "streams.py").read_text(encoding="utf-8")
    web_src = (RAIZ / "controle" / "harness_controle" / "web.py").read_text(encoding="utf-8")
    assert "TIPOS_VALIDOS =" not in streams_src
    assert "TIPOS_VALIDOS =" not in web_src
