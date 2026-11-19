"""Testes da poda no harness por processo e resolvedor único de ato (story #4342, t3)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HARNESS_LIB = Path(__file__).resolve().parents[1] / "lib"
if str(HARNESS_LIB) not in sys.path:
    sys.path.insert(0, str(HARNESS_LIB))

from poda import (
    atos_que_escrevem,
    podar_envelope,
    resolver_ato,
)

FACES_MOTOR = {"motor": {"instancia": "rag", "sem_instancia": ["listar"]}}


def _criar_bin_motor(pasta: Path) -> Path:
    arq = pasta / "motor"
    arq.write_text(
        "#!/usr/bin/env bash\n"
        "# poda: cosmetica@buscar\n"
        "# atos: listar (leitura, texto), buscar (leitura, busca), trocar (escrita, geracao)\n"
        "exit 0\n",
        encoding="utf-8",
    )
    arq.chmod(0o755)
    return arq


def test_resolvedor_unico_de_ato_para_verbo_com_instancia(tmp_path: Path):
    bin_motor = _criar_bin_motor(tmp_path)
    assert resolver_ato([str(bin_motor), "rag", "trocar", "g1"], binario=bin_motor, faces=FACES_MOTOR) == "trocar"
    assert resolver_ato([str(bin_motor), "rag", "buscar", "casa", "x"], binario=bin_motor, faces=FACES_MOTOR) == "buscar"
    assert resolver_ato([str(bin_motor), "listar"], binario=bin_motor, faces=FACES_MOTOR) == "listar"
    assert resolver_ato([str(bin_motor), "rag", "listar"], binario=bin_motor, faces=FACES_MOTOR) == "listar"
    assert resolver_ato(["/bin/repo", "--flag", "abrir", "x"]) == "abrir"


def test_motor_rag_trocar_nao_deduplica_e_listar_nao_escapa_do_teto(tmp_path: Path):
    bin_motor = _criar_bin_motor(tmp_path)
    derrame = tmp_path / "derrame"
    ledger = tmp_path / "ledger"

    env_trocar = {"exit_code": 0, "stdout": {"texto": "geracao g2 ativada\n", "truncado": False, "bytes_total": 19}}
    r1 = podar_envelope(
        env_trocar,
        verbo="motor",
        argv=[str(bin_motor), "rag", "trocar", "g2"],
        binario=bin_motor,
        sessao_id="s-motor",
        alca="motor rag trocar g2",
        derrame_dir=derrame,
        ledger_dir=ledger,
        faces=FACES_MOTOR,
    )
    r2 = podar_envelope(
        env_trocar,
        verbo="motor",
        argv=[str(bin_motor), "rag", "trocar", "g2"],
        binario=bin_motor,
        sessao_id="s-motor",
        alca="motor rag trocar g2",
        derrame_dir=derrame,
        ledger_dir=ledger,
        faces=FACES_MOTOR,
    )
    assert r1["stdout"]["texto"] == "geracao g2 ativada\n"
    assert r2["stdout"]["texto"] == "geracao g2 ativada\n"
    assert "[igual ao giro" not in r2["stdout"]["texto"]
    assert r2["poda"]["ato_efetivo"] == "trocar"
    assert r2["poda"]["ledger"] == "escrita"

    # Listagem grande (motor listar / motor rag listar) NÃO escapa do teto
    lista_grande = "\n".join(f"item-{i:04d} valor-{i}" for i in range(4000))
    env_listar = {
        "exit_code": 0,
        "stdout": {"texto": lista_grande, "truncado": False, "bytes_total": len(lista_grande)},
    }
    rl = podar_envelope(
        env_listar,
        verbo="motor",
        argv=[str(bin_motor), "rag", "listar"],
        binario=bin_motor,
        sessao_id="s-motor",
        alca="motor rag listar",
        derrame_dir=derrame,
        ledger_dir=ledger,
        cap=4096,
        faces=FACES_MOTOR,
    )
    assert rl["stdout"]["truncado"] is True
    assert len(rl["stdout"]["texto"].encode("utf-8")) <= 4096 + 200
    assert Path(rl["stdout"]["cru"]).exists()
    assert rl["poda"]["modo"] == "corte"


def test_poda_por_processo_deduplica_leitura_e_respeita_inteiro(tmp_path: Path):
    bin_motor = _criar_bin_motor(tmp_path)
    env_sub = {**os.environ, "PYTHONPATH": str(HARNESS_LIB)}
    payload = {
        "envelope": {"exit_code": 0, "stdout": {"texto": "lista pequena", "truncado": False, "bytes_total": 13}},
        "verbo": "motor",
        "argv": [str(bin_motor), "listar"],
        "binario": str(bin_motor),
        "sessao_id": "s-proc",
        "alca": "motor listar",
        "derrame_dir": str(tmp_path / "derrame"),
        "ledger_dir": str(tmp_path / "ledger"),
        "faces": FACES_MOTOR,
    }
    p1 = subprocess.run(
        [sys.executable, "-m", "poda"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env_sub,
        check=True,
    )
    out1 = json.loads(p1.stdout)
    assert out1["stdout"]["texto"] == "lista pequena"

    p2 = subprocess.run(
        [sys.executable, "-m", "poda"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env_sub,
        check=True,
    )
    out2 = json.loads(p2.stdout)
    assert "[igual ao giro 1" in out2["stdout"]["texto"]

    payload["inteiro"] = True
    p3 = subprocess.run(
        [sys.executable, "-m", "poda"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env_sub,
        check=True,
    )
    out3 = json.loads(p3.stdout)
    assert out3["stdout"]["texto"] == "lista pequena"


def test_atos_que_escrevem_nao_polui_cache_com_caminho_inexistente(tmp_path: Path):
    ficticio = tmp_path / "nao-existe"
    assert atos_que_escrevem("x", ficticio) == frozenset()
    ficticio.write_text("#!/bin/sh\n# atos: gravar (escrita, x)\n", encoding="utf-8")
    assert "gravar" in atos_que_escrevem("x", ficticio)
