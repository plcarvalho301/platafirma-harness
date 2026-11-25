"""Testes do aviso de sucessor em `bin/ler_arquivo` na fase de expansão (story #4442, t10)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
BIN_LER_ARQUIVO = RAIZ / "bin" / "ler_arquivo"


def test_ler_arquivo_emite_aviso_de_sucessor_em_stderr_sem_corromper_stdout(tmp_path: Path) -> None:
    arq = tmp_path / "nota.txt"
    arq.write_text("ola mundo\nsegunda linha\n", encoding="utf-8")

    payload = json.dumps({"caminho": str(arq), "bancada": str(tmp_path)})
    proc = subprocess.run(
        [sys.executable, str(BIN_LER_ARQUIVO)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ler_arquivo será retirado" in proc.stderr
    assert "busca ler" in proc.stderr

    # stdout continua sendo JSON válido e íntegro (aviso não vaza para stdout).
    dados = json.loads(proc.stdout)
    assert "ola mundo" in dados.get("conteudo", "")
    assert "ler_arquivo será retirado" not in proc.stdout


def test_ler_arquivo_mantem_recusa_de_entrada_invalida_com_aviso() -> None:
    payload = json.dumps({})
    proc = subprocess.run(
        [sys.executable, str(BIN_LER_ARQUIVO)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert proc.returncode == 2
    assert "ler_arquivo será retirado" in proc.stderr
    dados = json.loads(proc.stdout)
    assert dados.get("exit_code") == 2
