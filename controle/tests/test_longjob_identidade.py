"""`sessao longjob run` repassa a identidade da porta a unit (mesa ti #21).

O systemd --user nao herda o ambiente de quem chama: sem repasse explicito, verbo que
exige PF_SUJEITO (infra up, migrar aplicar) recusava dentro do job. O teste troca o
`systemd-run` por um stub que grava os argumentos e confere o que chegaria a unit.
"""
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LONGJOB = REPO_ROOT / "bin" / "_sessao" / "longjob"

IDENT = ("PF_SUJEITO", "PF_CADEIRA", "PF_SESSAO", "PF_ORDEM_ID", "PF_SUPERFICIE")


def _roda(tmp_path, extra):
    stubdir = tmp_path / "stub"
    stubdir.mkdir()
    capt = tmp_path / "args.txt"
    stub = stubdir / "systemd-run"
    stub.write_text(f'#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done > "{capt}"\n')
    stub.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in IDENT}
    env.update({
        "PATH": f"{stubdir}:{env.get('PATH', '/usr/bin:/bin')}",
        "PLATAFIRMA_INSTANCIA": str(tmp_path / "inst"),
        "LONGJOB_LOGDIR": str(tmp_path / "log"),
    })
    env.update(extra)
    r = subprocess.run(["bash", str(LONGJOB), "run", "prova", "true"],
                       env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    log = next((tmp_path / "log").glob("platafirma-job-prova-*.log")).read_text()
    return capt.read_text().splitlines(), log


def test_repassa_identidade_presente(tmp_path):
    args, log = _roda(tmp_path, {"PF_SUJEITO": "jose-123", "PF_CADEIRA": "ti",
                                  "PF_SESSAO": "s-1"})
    assert "--setenv=PF_SUJEITO=jose-123" in args
    assert "--setenv=PF_CADEIRA=ti" in args
    assert "--setenv=PF_SESSAO=s-1" in args
    assert "# sujeito=jose-123" in log
    # o comando continua depois do separador
    assert args[args.index("--") + 1:] == ["true"]


def test_ausente_segue_ausente(tmp_path):
    args, log = _roda(tmp_path, {})
    assert not [a for a in args if a.startswith("--setenv=PF_")]
    assert "# sujeito=(ausente)" in log
