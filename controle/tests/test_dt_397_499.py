"""Regressões dos débitos #2856 linhas 397 e 499."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]

@pytest.mark.parametrize("container", [False, True])
def test_logs_preserva_janela_com_espacos(tmp_path, container):
    for name, body in {
        "docker": 'if [ "$1" = ps ]; then ' + ('echo alvo' if container else 'true') + '; else printf "%s\\n" "$@"; fi',
        "journalctl": 'printf "%s\\n" "$@"',
    }.items():
        p = tmp_path / name
        p.write_text("#!/bin/bash\n" + body + "\n")
        p.chmod(0o755)
    env = dict(os.environ, PATH=str(tmp_path) + ":" + os.environ["PATH"])
    r = subprocess.run(["bash", str(ROOT / "bin/infra"), "logs", "alvo",
                        "--since", "2026-11-05 12:00", "--until", "2026-11-06 12:00"],
                       env=env, text=True, capture_output=True)
    assert r.returncode == 0, r.stderr
    args = r.stdout.splitlines()
    assert args[args.index("--since") + 1] == "2026-11-05 12:00"
    assert args[args.index("--until") + 1] == "2026-11-06 12:00"
    assert "-n" not in args
    if "--tail" in args:
        assert args[args.index("--tail") + 1] == "all"

def test_situacao_nao_busca_nem_serve_corpo(monkeypatch, capsys):
    path = ROOT / "bin/_acervo/casa"
    monkeypatch.syspath_prepend(str(path.parent))
    loader = importlib.machinery.SourceFileLoader("casa_dt397", str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    monkeypatch.setattr(mod, "_especie", lambda _: {})
    monkeypatch.setattr(mod, "resolver", lambda *a: {"id": "x"})
    monkeypatch.setattr(mod, "_fonte", lambda: {})
    monkeypatch.setattr(mod, "_estado_espelho", lambda: ())
    monkeypatch.setattr(mod, "marca_linha", lambda *a: "documento")
    monkeypatch.setattr(mod, "ident", lambda *a: "x")
    monkeypatch.setattr(mod, "_item", lambda *a: {"id": "x"})
    sit = dict(fonte="f", ingerido="i", servido="s", status="vigente", vetorizado="v")
    monkeypatch.setattr(mod, "_situacao", lambda *a: sit)
    def proibido(*a, **kw):
        raise AssertionError("situação não deve carregar corpo")
    monkeypatch.setattr(mod, "_q", proibido)
    assert mod.ler("guia", "x", False, situacao=True) == 0
    saida = capsys.readouterr().out
    assert "fonte: f" in saida and "status: vigente" in saida
    assert mod.ler("guia", "x", True, situacao=True) == 0
    dado = json.loads(capsys.readouterr().out)
    assert dado["situacao"] == sit and "corpo" not in dado
