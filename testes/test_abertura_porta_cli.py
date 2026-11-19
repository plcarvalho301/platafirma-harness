"""Testes do CLI JSON `python -m abertura` e da remontagem sem cultura (story #4343, T2)."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

_RAIZ_ESPELHO = Path(__file__).resolve().parents[3]
_LIB_DIR = Path(__file__).resolve().parents[1] / "lib"
if not (_RAIZ_ESPELHO / "instancias").is_dir():
    pytest.skip("instancias da casa-espelho ausentes fora da arvore do espelho", allow_module_level=True)


def _rodar_cli(ato: str, payload: dict, *, env_extra: dict[str, str] | None = None) -> tuple[int, dict]:
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{_LIB_DIR}:{env.get('PYTHONPATH', '')}".rstrip(":")
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, "-m", "abertura", ato],
        input=json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        env=env,
        timeout=15,
        check=False,
    )
    assert proc.stdout.strip(), f"rc={proc.returncode} stderr={proc.stderr}"
    return proc.returncode, json.loads(proc.stdout)


def test_cli_abrir_le_da_casa_nova_sem_abertura_publicada():
    rc, saida = _rodar_cli(
        "abrir",
        {
            "cadeira": "engenharia",
            "chapeu": "back-end",
            "pergunta": "(engenharia, back-end) testar abertura",
            "casa_raiz": str(_RAIZ_ESPELHO),
        },
        env_extra={"PF_ABERTURA_DIR": "/tmp/nao-existe-abertura-publicada-4343"},
    )
    assert rc == 0
    assert saida["ok"] is True
    assert saida["cadeira"] == "engenharia"
    assert saida["chapeu"] == "back-end"
    assert "persona" in saida["pecas"]
    assert "chapeu" in saida["pecas"]
    assert "cultura" in saida["pecas"]
    assert "conduta" not in saida["pecas"]
    assert any(c["cadeira"] == "engenharia" for c in saida["cadeiras"])


def test_cli_remontar_omite_cultura_e_respeita_teto():
    rc, saida = _rodar_cli(
        "remontar",
        {
            "cadeira": "engenharia",
            "chapeu": "back-end",
            "sessao_id": "11111111-1111-4111-8111-111111111111",
            "casa_raiz": str(_RAIZ_ESPELHO),
            "incluir_cultura": False,
            "teto_caracteres": 9500,
            "sem_valkey": True,
        },
    )
    assert rc == 0
    assert saida["ok"] is True
    assert saida["cultura"] == ""
    assert saida["persona"]
    assert saida["caracteres"] < 10_000
    assert len(saida["texto"]) <= 9500


def test_cli_exigir_sessao_recusa_sem_sessao_e_libera_abertura_e_tela():
    rc_rec, saida_rec = _rodar_cli("exigir-sessao", {"tool": "tarefas", "sessao_id": None})
    assert rc_rec == 2
    assert saida_rec["permitido"] is False
    assert "monta_sessao" in saida_rec["recusa"]["chamada"]

    rc_ok, saida_ok = _rodar_cli("exigir-sessao", {"tool": "monta_sessao", "sessao_id": None})
    assert rc_ok == 0
    assert saida_ok["permitido"] is True

    rc_tela, saida_tela = _rodar_cli("exigir-sessao", {"tool": "tela:resumo", "sessao_id": None})
    assert rc_tela == 0
    assert saida_tela["permitido"] is True
