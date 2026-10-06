"""#3202: `acervo exportar` p\u00f5e no PYTHONPATH o rag/ e o conversor/ da bancada.

Desde a #3205 o motor_acervo importa o pacote `conversor`, que mora ao lado de rag/; com s\u00f3 rag/
no caminho, o export morria no import (medido em 01/10). Sem banco e sem subprocesso: `roda`, o
ambiente e o `git status` s\u00e3o trocados por dubl\u00eas.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import subprocess
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
EXPORTAR = RAIZ / "bin" / "_acervo" / "exportar"


def _modulo():
    loader = importlib.machinery.SourceFileLoader("acervo_exportar_3202", str(EXPORTAR))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


def test_pythonpath_leva_rag_e_conversor_da_bancada(monkeypatch, tmp_path):
    mod = _modulo()
    wt = tmp_path / "bancada"
    (wt / "rag").mkdir(parents=True)
    (wt / "conversor").mkdir()
    rodadas = []
    monkeypatch.setattr(mod, "bancada_do_repo", lambda chave="": wt)  # --bancada <chave>, #3163
    monkeypatch.setattr(mod, "python_do_rag", lambda: "/bin/true")
    monkeypatch.setattr(mod, "ambiente_da_ingestao", lambda: {"EMBED_MODEL": "x"})
    monkeypatch.setattr(mod, "roda", lambda titulo, cmd, cwd, env: rodadas.append(env))
    monkeypatch.setattr(mod.subprocess, "run",
                        lambda *a, **k: subprocess.CompletedProcess(a, 0, stdout="", stderr=""))
    assert mod.main([]) == 0
    assert rodadas, "o export n\u00e3o rodou"
    caminho = rodadas[0]["PYTHONPATH"].split(os.pathsep)
    assert caminho == [str(wt / "rag"), str(wt / "conversor")]
