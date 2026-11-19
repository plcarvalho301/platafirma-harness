from __future__ import annotations

import os
import sys
import types
from pathlib import Path

_LIB = Path(__file__).resolve().parents[2] / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

try:
    import raizes  # noqa: F401
except ModuleNotFoundError:
    _mod = types.ModuleType("raizes")
    _mod.instancia = lambda: Path(os.environ.get("PLATAFIRMA_INSTANCIA", "/srv/platafirma/casa"))
    _mod.release = lambda: Path(os.environ.get("PLATAFIRMA_RELEASE", "/opt/platafirma/current"))
    sys.modules["raizes"] = _mod
