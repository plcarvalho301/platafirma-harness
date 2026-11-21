"""Testes do portão de configuração da porta (armário e conector, story #4412).

O armário de chaves e o conector do túnel são versionados no core
(deploy/armario-de-chaves.yaml e deploy/porta/conector-do-tunel.yaml); o portão
confere os dois na árvore do core com o validador dela mesma.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

HARNESS_DIR = Path(__file__).resolve().parents[2]
CONFERIR_PY = HARNESS_DIR / "bin" / "_release" / "conferir" / "conferir.py"
BIN_RELEASE = HARNESS_DIR / "bin" / "release"


def _carregar_conferir():
    spec = importlib.util.spec_from_file_location("conferir_mod", CONFERIR_PY)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(CONFERIR_PY.parent))
    sys.path.insert(0, str(HARNESS_DIR / "bin"))
    spec.loader.exec_module(mod)
    return mod


def _criar_core(core_dir: Path, *, armario: str | None, conector: str | None) -> None:
    """Árvore do core falsa: validador simples e os dois arquivos em deploy/."""
    porta = core_dir / "porta"
    porta.mkdir(parents=True, exist_ok=True)
    (porta / "__init__.py").write_text("", encoding="utf-8")
    (porta / "configuracao.py").write_text(
        "import sys\n"
        "from pathlib import Path\n"
        "_, _, tipo, arq = sys.argv\n"
        "p = Path(arq)\n"
        "if not p.is_file():\n"
        "    sys.stderr.write(f'porta: subida recusada alvo={p}: arquivo ausente\\n')\n"
        "    raise SystemExit(1)\n"
        "txt = p.read_text(encoding='utf-8')\n"
        "if 'INVALIDO' in txt:\n"
        "    sys.stderr.write(f'porta: subida recusada alvo={p}: fora do schema\\n')\n"
        "    raise SystemExit(1)\n"
        "sys.stdout.write(f'ok {tipo} {p}\\n')\n",
        encoding="utf-8",
    )
    (core_dir / "deploy" / "porta").mkdir(parents=True, exist_ok=True)
    if armario is not None:
        (core_dir / "deploy" / "armario-de-chaves.yaml").write_text(armario, encoding="utf-8")
    if conector is not None:
        (core_dir / "deploy" / "porta" / "conector-do-tunel.yaml").write_text(
            conector, encoding="utf-8"
        )


def test_conferir_configuracao_porta_valido_e_divergente(tmp_path: Path) -> None:
    mod = _carregar_conferir()

    core_ok = tmp_path / "ok" / "core"
    _criar_core(
        core_ok,
        armario="versao: 1\nsegredos: []\n",
        conector="versao: 1\ncabecalho: cf-connecting-ip\n",
    )
    itens_ok = dict(
        mod.conferir_configuracao_porta(core_dir=core_ok, python_porta=sys.executable)
    )
    assert itens_ok["armario-de-chaves.yaml (4406.r21)"].estado == "conforme"
    assert itens_ok["conector-do-tunel.yaml (4406.r4)"].estado == "conforme"

    core_ruim = tmp_path / "ruim" / "core"
    _criar_core(core_ruim, armario="INVALIDO\n", conector=None)
    itens_ruim = dict(
        mod.conferir_configuracao_porta(core_dir=core_ruim, python_porta=sys.executable)
    )
    assert itens_ruim["armario-de-chaves.yaml (4406.r21)"].estado == "divergente"
    assert itens_ruim["conector-do-tunel.yaml (4406.r4)"].estado == "divergente"


@pytest.mark.parametrize(
    "armario,conector,esperado_rc",
    [
        ("versao: 1\n", "versao: 1\n", 0),
        ("INVALIDO\n", "versao: 1\n", 4),
        ("versao: 1\n", None, 4),
        (None, "versao: 1\n", 4),
    ],
)
def test_gate_release_recusa_antes_de_trocar_current(
    tmp_path: Path, armario: str | None, conector: str | None, esperado_rc: int
) -> None:
    prod = tmp_path / "prod"
    sha_atual = "1111111111111111111111111111111111111111"
    sha_cand = "2222222222222222222222222222222222222222"
    (prod / "platafirma-core" / sha_atual).mkdir(parents=True)
    _criar_core(prod / "platafirma-core" / sha_cand, armario=armario, conector=conector)
    (prod / "current").mkdir(parents=True)
    current_link = prod / "current" / "core"
    current_link.symlink_to(prod / "platafirma-core" / sha_atual)

    # Um armário válido deixado na instância não salva a rev candidata sem o dela.
    inst = tmp_path / "inst"
    (inst / "deploy" / "porta").mkdir(parents=True)
    (inst / "deploy" / "armario-de-chaves.yaml").write_text("versao: 1\n", encoding="utf-8")
    (inst / "deploy" / "porta" / "conector-do-tunel.yaml").write_text(
        "versao: 1\n", encoding="utf-8"
    )

    script = (
        f"PROD_RAIZ={prod}\n"
        f"PLATAFIRMA_INSTANCIA={inst}\n"
        f"PF_PORTA_PYTHON={sys.executable}\n"
        "curto_ou() { [ -n \"$1\" ] && printf '%s' \"${1:0:7}\" || printf '%s' \"$2\"; }\n"
        f"eval \"$(awk '/^gate_conferir_configuracao_porta\\(\\) /,/^\\}}/' {BIN_RELEASE})\"\n"
        f"gate_conferir_configuracao_porta platafirma-core {sha_cand} {sha_atual}\n"
    )
    proc = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        env=dict(os.environ),
        check=False,
    )
    assert proc.returncode == esperado_rc, proc.stderr + proc.stdout
    assert current_link.resolve() == (prod / "platafirma-core" / sha_atual).resolve()
