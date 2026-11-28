# componente: componente:suite
"""test_borda_despachar — contrato da borda comum do ato `despachar` e `ler execucao` (card #4455, t11)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

TESTS_DIR = Path(__file__).resolve().parent
HARNESS_ROOT = TESTS_DIR.parents[1]
SUJEITO_DONO = "11111111-1111-1111-1111-111111111111"


def _carregar_modulos() -> tuple[Any, Any, Any]:
    for pasta in (HARNESS_ROOT / "lib", HARNESS_ROOT / "bin"):
        txt = str(pasta)
        if txt not in sys.path:
            sys.path.insert(0, txt)
    import despacho
    import leitura.recusa as mod_recusa
    import oplog

    return despacho, mod_recusa, oplog


def _escrever_porta_yaml(pasta: Path) -> Path:
    arq = pasta / "porta.yaml"
    arq.write_text(
        yaml.safe_dump(
            {
                "verbos": {
                    "release": {
                        "descricao": "opera a release · atos: estado (leitura, operacao), despachar (escrita, operacao)",
                    },
                    "mesa": {
                        "descricao": "guarda na lousa · atos: ver, item, corpo, fez",
                    },
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    return arq


def test_borda_despachar_chega_ao_core_com_classe_chave_fan_out_e_parametros(tmp_path: Path) -> None:
    despacho, _, _ = _carregar_modulos()
    porta_yaml = _escrever_porta_yaml(tmp_path)
    capturado: dict[str, Any] = {}

    def _fake_runner(cmd: list[str], *, input: str, **_kw: Any) -> subprocess.CompletedProcess[str]:
        capturado["cmd"] = cmd
        capturado["payload"] = json.loads(input)
        out = json.dumps({"execucao_id": "exec-borda-1", "estado": "concluida", "exit_code": 0}) + "\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    resp = despacho.despachar_pela_borda(
        "release",
        ["pipeline", "conferir-ar", "--fan-out", "2", "--pedido", "ped-1", "--param", "familia=platafirma-core"],
        porta_yaml=porta_yaml,
        config_cliente=despacho.ConfigClienteDespacho(runner=_fake_runner),
        ident={"sujeito": SUJEITO_DONO, "cadeira": "ti"},
    )

    assert resp.exit_code == 0
    assert resp.execucao_id == "exec-borda-1"
    assert capturado["payload"]["verbo_entrada"] == "release"
    assert capturado["payload"]["alvo_classe"] == "pipeline"
    assert capturado["payload"]["alvo_chave"] == "conferir-ar"
    assert capturado["payload"]["fan_out"] == 2
    assert capturado["payload"]["pedido_id"] == "ped-1"
    assert capturado["payload"]["parametros"] == {"familia": "platafirma-core"}


def test_borda_despachar_recusa_com_2_verbo_que_nao_declara_sem_chamar_core(tmp_path: Path) -> None:
    despacho, mod_recusa, _ = _carregar_modulos()
    porta_yaml = _escrever_porta_yaml(tmp_path)
    chamou_core = False

    def _fake_runner(cmd: list[str], **_kw: Any) -> subprocess.CompletedProcess[str]:
        nonlocal chamou_core
        chamou_core = True
        return subprocess.CompletedProcess(cmd, 0, stdout="{}\n", stderr="")

    with pytest.raises(mod_recusa.Recusa) as exc:
        despacho.despachar_pela_borda(
            "mesa",
            ["conferir-ar"],
            porta_yaml=porta_yaml,
            config_cliente=despacho.ConfigClienteDespacho(runner=_fake_runner),
        )
    assert exc.value.saida == 2
    assert exc.value.codigo == "ato-nao-declarado"
    assert chamou_core is False


def test_borda_ler_execucao_le_evento_da_trilha(tmp_path: Path) -> None:
    despacho, _, oplog = _carregar_modulos()
    porta_yaml = _escrever_porta_yaml(tmp_path)
    oplog_dir = tmp_path / "ops"
    oplog_dir.mkdir()
    oplog.emitir(
        {
            "evento": "execucao",
            "execucao_id": "exec-borda-ler",
            "alvo_classe": "pipeline",
            "alvo_chave": "conferir-ar",
            "verbo_entrada": "release",
            "estado": "concluida",
            "exit_code": 0,
            "sujeito": SUJEITO_DONO,
            "fases": [{"id": "estado-ar", "indice": 0, "verbo": "release", "ato": "estado", "estado": "concluido", "exit_code": 0, "linha": "ok", "harness_sha": "506d5e5", "dur_ms": 12}],
        },
        diretorio_=oplog_dir,
    )

    lido = despacho.ler_execucao_pela_borda(
        "release",
        "exec-borda-ler",
        sujeito=SUJEITO_DONO,
        porta_yaml=porta_yaml,
        diretorio_oplog=oplog_dir,
    )
    assert lido["execucao_id"] == "exec-borda-ler"
    assert lido["estado"] == "concluida"
    assert len(lido["fases"]) == 1
