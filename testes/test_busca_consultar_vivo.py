# componente: componente:verbo-busca
"""Suíte viva de `busca consultar` contra o banco `casa` e a release servida (story 4427, t11).

Executa no degrau `rodada` as duas chamadas canônicas de «Como se confere» em
`platafirma-casa@referencias/instancias/verbo/busca.md`; o prazo de 5 segundos por chamada
é garantido pelo próprio `Retrato` do leitor.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BIN = RAIZ / "bin" / "busca"


def _executar_consultar(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BIN), "consultar", *args],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


def test_consultar_classes_cuja_capacidade_e_busca() -> None:
    proc = _executar_consultar("--classe", "classe", "--prop", "capacidade=busca")
    assert proc.returncode == 0, proc.stderr
    linhas = proc.stdout.splitlines()
    assert linhas, "stdout vazio"
    assert linhas[0].startswith("classe · fornada ")
    assert " · fichas 1 a 1 de 1 · digest v1:" in linhas[0]
    assert any(ln == "exploracao" or ln.startswith("exploracao · ") for ln in linhas[1:])


def test_consultar_gabaritos_de_modelos_formais_vira_condicao() -> None:
    proc = _executar_consultar("gabaritos de modelos formais")
    assert proc.returncode == 0, proc.stderr
    linhas = proc.stdout.splitlines()
    assert linhas, "stdout vazio"
    assert linhas[0].startswith("nome «gabaritos de modelos formais» virou condição")
    assert " · digest v1:" in linhas[0]
    assert any(
        ln == "gabarito:framework-da-ontologia" or ln.startswith("gabarito:framework-da-ontologia · ")
        for ln in linhas[1:]
    )
