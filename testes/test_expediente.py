"""Compatibilidade de descoberta pytest para testes/teste_expediente.py."""
import sys
from pathlib import Path

_AQUI = Path(__file__).resolve().parent
if str(_AQUI) not in sys.path:
    sys.path.insert(0, str(_AQUI))

from teste_expediente import *  # noqa: F401, F403
