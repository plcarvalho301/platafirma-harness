"""Contrato de reinício da porta e atalhos em bin/release (card #4340).

Prova, com um `infra` de fixture que grava cada chamada de restart:
- promover `platafirma-harness`: 0 chamadas de `infra restart ops-mcp`;
- promover `platafirma-core`: 1 chamada de `infra restart ops-mcp`;
- promover outra família: 0 chamadas de `infra restart ops-mcp`;
- `assentar_atalhos platafirma-harness`: não cria o atalho `politica-acesso`.
"""
from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

BIN_RELEASE = Path(__file__).resolve().parents[1] / "bin" / "release"


def _extrair_funcoes(texto: str, nomes: tuple[str, ...]) -> str:
    """Extrai definições de funções bash de topo de bin/release."""
    linhas = texto.splitlines()
    blocos: list[str] = []
    i = 0
    while i < len(linhas):
        linha = linhas[i]
        if any(linha.startswith(f"{nome}()") for nome in nomes):
            inicio = i
            i += 1
            while i < len(linhas) and linhas[i] != "}":
                i += 1
            blocos.append("\n".join(linhas[inicio : i + 1]))
        i += 1
    return "\n\n".join(blocos)


def _cria_infra_fixture(pasta: Path, log: Path) -> Path:
    infra = pasta / "infra"
    infra.write_text(
        f"#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> {str(log)!r}\necho 'restart agendado (fixture)'\n",
        encoding="utf-8",
    )
    infra.chmod(infra.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return infra


def test_sintaxe_bash_de_bin_release():
    cp = subprocess.run(["bash", "-n", str(BIN_RELEASE)], capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr


def test_promover_harness_nao_reinicia_porta_e_core_reinicia(tmp_path: Path):
    texto = BIN_RELEASE.read_text(encoding="utf-8")
    funcoes = _extrair_funcoes(texto, ("reiniciar_porta",))
    assert "reiniciar_porta()" in funcoes

    restarts = tmp_path / "restarts.log"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    infra = _cria_infra_fixture(fake_bin, restarts)

    def _rodar(familia: str) -> subprocess.CompletedProcess[str]:
        script = f"""set -euo pipefail
FAMILIA_BIN="platafirma-harness"
PLATAFIRMA_RELEASE="{tmp_path / 'current'}"
resumo_imprime() {{ :; }}
achar_verbo() {{ [ "$1" = "infra" ] && printf '%s' "{infra}"; }}
{funcoes}
reiniciar_porta "{familia}"
"""
        env = {
            **os.environ,
            "PATH": f"{fake_bin}:/usr/bin:/bin",
            "PF_RELEASE_PORTA": "1",
            "XDG_RUNTIME_DIR": str(tmp_path),
        }
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)

    # Promoção do harness: 0 restarts de ops-mcp
    cp_h = _rodar("platafirma-harness")
    assert cp_h.returncode == 0, cp_h.stderr
    assert not restarts.exists() or restarts.read_text(encoding="utf-8").strip() == ""

    # Promoção de outra família (ex.: motor): 0 restarts de ops-mcp
    cp_m = _rodar("platafirma-motor")
    assert cp_m.returncode == 0, cp_m.stderr
    assert not restarts.exists() or restarts.read_text(encoding="utf-8").strip() == ""

    # Promoção do core: exatamente 1 restart de ops-mcp
    cp_c = _rodar("platafirma-core")
    assert cp_c.returncode == 0, cp_c.stderr
    linhas = [l for l in restarts.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert linhas == ["restart ops-mcp"]


def test_assentar_atalhos_harness_nao_cria_politica_acesso(tmp_path: Path):
    texto = BIN_RELEASE.read_text(encoding="utf-8")
    funcoes = _extrair_funcoes(texto, ("trocar_link", "assentar_atalhos"))
    assert "assentar_atalhos()" in funcoes

    atalhos = tmp_path / "current"
    script = f"""set -euo pipefail
FAMILIA_BIN="platafirma-harness"
PROD_RAIZ="{tmp_path}"
ATALHOS="{atalhos}"
VENVS_PRONTOS=()
{funcoes}
assentar_atalhos "platafirma-harness"
"""
    cp = subprocess.run(["bash", "-c", script], capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    assert (atalhos / "harness").is_symlink()
    assert not (atalhos / "politica-acesso").exists()
    assert not (atalhos / "politica-acesso").is_symlink()
