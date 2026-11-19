"""Regressivo #4378: despacho unificado de `bin/conferir`.

Prova que `conferir ontologia` aciona `bin/_conferir` (Olaria) e que os demais atos
(`verbo`, `servico`, `existe`, `pdp`, `alcance`) seguem acionando
`bin/_release/conferir/conferir.py` (ou `release conferir`), sem colisão de contrato.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
CONFERIR_SRC = RAIZ / "bin" / "conferir"


def _montar_arvore_falsa(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Cria um bin/conferir isolado com stubs em `_conferir` e `_release/conferir/conferir.py`."""
    bin_dir = tmp_path / "bin"
    (bin_dir / "_conferir").mkdir(parents=True)
    (bin_dir / "_release" / "conferir").mkdir(parents=True)

    conferir = bin_dir / "conferir"
    conferir.write_text(CONFERIR_SRC.read_text(encoding="utf-8"), encoding="utf-8")
    conferir.chmod(0o755)

    (bin_dir / "_conferir" / "__init__.py").write_text("", encoding="utf-8")
    (bin_dir / "_conferir" / "__main__.py").write_text(
        "import sys\nprint('ROTA=_conferir ARGS=' + ' '.join(sys.argv[1:]))\nsys.exit(0)\n",
        encoding="utf-8",
    )

    impl = bin_dir / "_release" / "conferir" / "conferir.py"
    impl.write_text(
        "#!/usr/bin/env python3\nimport sys\nprint('ROTA=_release_conferir ARGS=' + ' '.join(sys.argv[1:]))\nsys.exit(0)\n",
        encoding="utf-8",
    )
    impl.chmod(0o755)

    # Stub `release` que repassa `release conferir ...` para o impl local, como no ar.
    release_stub = bin_dir / "release"
    release_stub.write_text(
        f"#!/usr/bin/env bash\nshift\nexec python3 \"{impl}\" \"$@\"\n",
        encoding="utf-8",
    )
    release_stub.chmod(0o755)

    return conferir, bin_dir, impl


def _rodar(conferir: Path, bin_dir: Path, args: list[str]) -> subprocess.CompletedProcess:
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "PF_BIN_DIR": str(bin_dir),
        "PF_SESSAO": "teste-conferir-unificado",
        "PLATAFIRMA_RELEASE": str(bin_dir.parent / "release-ausente"),
    }
    return subprocess.run([str(conferir), *args], capture_output=True, text=True, env=env)


def test_conferir_tem_bit_executavel():
    modo = CONFERIR_SRC.stat().st_mode
    assert modo & stat.S_IXUSR, "bin/conferir precisa ter bit executável"


def test_conferir_ontologia_despacha_para_modulo_conferir(tmp_path):
    conferir, bin_dir, _ = _montar_arvore_falsa(tmp_path)
    p = _rodar(conferir, bin_dir, ["ontologia", "capacidade:harness"])
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "ROTA=_conferir ARGS=ontologia capacidade:harness"


@pytest.mark.parametrize("ato,alvo", [
    ("verbo", "repo"),
    ("servico", "ops-mcp"),
    ("existe", "verbo"),
    ("pdp", "ops-mcp"),
    ("alcance", "ti"),
])
def test_conferir_demais_atos_despacham_para_release_conferir(tmp_path, ato, alvo):
    conferir, bin_dir, _ = _montar_arvore_falsa(tmp_path)
    p = _rodar(conferir, bin_dir, [ato, alvo])
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == f"ROTA=_release_conferir ARGS={ato} {alvo}"


def test_conferir_ajuda_responde_pelo_despachante(tmp_path):
    conferir, bin_dir, _ = _montar_arvore_falsa(tmp_path)
    p = _rodar(conferir, bin_dir, ["--help"])
    assert p.returncode == 0, p.stderr
    assert p.stdout.strip() == "ROTA=_release_conferir ARGS=--ajuda"
