"""DT 337 (promover do acervo em indexar) e DT 441 (401 do motor com causa e cura)."""
import importlib.machinery
import importlib.util
import subprocess
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def test_usage_do_acervo_menciona_rag_api_token_e_bin_pf():
    r = subprocess.run(["bash", str(ROOT / "bin/acervo"), "--ajuda"],
                       text=True, capture_output=True, timeout=60, check=False)
    assert "RAG_API_TOKEN" in r.stdout or "RAG_API_TOKEN" in r.stderr
    assert "bin/pf" in r.stdout or "bin/pf" in r.stderr
    assert "leitura e anonima" not in r.stdout and "leitura e anonima" not in r.stderr


def test_curar_401_do_motor_sai_com_exit_3_e_causa_e_cura(capsys):
    try:
        import requests  # noqa: F401
    except ImportError:
        class _SemRede(types.ModuleType):
            def __getattr__(self, nome):
                return type(nome, (Exception,), {})
        sys.modules.setdefault("requests", _SemRede("requests"))

    loader = importlib.machinery.SourceFileLoader("curar_441", str(ROOT / "bin/curar"))
    spec = importlib.util.spec_from_loader("curar_441", loader)
    curar = importlib.util.module_from_spec(spec)
    loader.exec_module(curar)

    class FakeResp:
        status_code = 401

    with pytest.raises(SystemExit) as exc:
        curar.falha_problem(FakeResp())
    assert exc.value.code == 3
    err = capsys.readouterr().err
    assert "401 não autorizado pelo motor" in err
    assert "RAG_API_TOKEN" in err
    assert "bin/pf" in err
