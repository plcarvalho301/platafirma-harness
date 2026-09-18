"""Testes de contrato para injeção entre itens do lote em run_command (#3053).

Cobre:
- Lote run_command executando sessao abrir seguido de expediente montar:
  sessao abrir cunha sessao_id e grava na chave;
  antes do item n+1, ident é resolvido via _sessao_resolve;
  o item seguinte recebe PF_SESSAO, PF_ORDEM_ID e PF_CADEIRA no subprocesso.
- Ramo legado (_run_command_legado com PF_RUN_SO_VERBO=0) executando sessao abrir seguido de comando posterior.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
PDP_CODE_DIR = HARNESS_DIR / "politica-acesso"
for d in (OPS_SERVER_DIR, PDP_CODE_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

os.environ["PF_HARNESS"] = str(HARNESS_DIR)
import server as s


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_run_command_injecao_entre_itens_lote():
    sid_novo = "33333333-4444-5555-6666-777777777777"
    oid_novo = "o20260914T150000-newoid"
    cad_nova = "ia"

    mock_rc = MagicMock()
    def fake_get(k):
        if k == f"sessao:{sid_novo}":
            return json.dumps({"cadeira": cad_nova, "ordem_id": oid_novo})
        return None
    mock_rc.get.side_effect = fake_get
    mock_rc.hget.return_value = None

    chamadas = []
    def fake_run_verbo_blocking(argv, stdin, timeout, ident):
        chamadas.append({"argv": list(argv), "ident": dict(ident)})
        slug = argv[0].rsplit("/", 1)[-1]
        ato = argv[1] if len(argv) > 1 else ""
        if slug == "sessao" and ato == "abrir":
            out = json.dumps({"sessao_id": sid_novo, "cadeira": cad_nova, "ordem_id": oid_novo})
            return {"exit_code": 0, "stdout": {"texto": out, "bytes_total": len(out), "truncado": False}}
        elif slug == "expediente" and ato == "montar":
            out = json.dumps({"cadeira": cad_nova, "ok": True})
            return {"exit_code": 0, "stdout": {"texto": out, "bytes_total": len(out), "truncado": False}}
        return {"exit_code": 1, "stdout": {"texto": "", "bytes_total": 0, "truncado": False}}

    novos_slugs = set(s.SLUGS_SERVIDOS) | {"sessao", "expediente"}
    novos_bins = dict(s.BINARIOS)
    novos_bins["sessao"] = "/opt/bin/sessao"
    novos_bins["expediente"] = "/opt/bin/expediente"

    with patch("server.SLUGS_SERVIDOS", novos_slugs),          patch("server.BINARIOS", novos_bins),          patch("server._autoriza", return_value=None),          patch("server._rc", return_value=mock_rc),          patch("server._audit"),          patch("server._run_verbo_blocking", side_effect=fake_run_verbo_blocking):

        res = await s.run_command(commands=[
            "sessao abrir ia",
            "expediente montar"
        ])

    assert len(chamadas) == 2
    # Primeiro item rodou sem sessão prévia
    assert chamadas[0]["ident"]["sessao_id"] == "-"
    # Segundo item recebeu PF_* resolvidos da chave do sessao abrir
    assert chamadas[1]["ident"]["sessao_id"] == sid_novo
    assert chamadas[1]["ident"]["ordem_id"] == oid_novo
    assert chamadas[1]["ident"]["cadeira"] == cad_nova


@pytest.mark.anyio
async def test_run_command_legado_injecao_entre_itens_lote():
    sid_novo = "44444444-5555-6666-7777-888888888888"
    oid_novo = "o20260914T160000-legadooid"
    cad_nova = "ia"

    mock_rc = MagicMock()
    def fake_get(k):
        if k == f"sessao:{sid_novo}":
            return json.dumps({"cadeira": cad_nova, "ordem_id": oid_novo})
        return None
    mock_rc.get.side_effect = fake_get
    mock_rc.hget.return_value = None

    chamadas = []
    def fake_run_blocking(cmd, d, timeout, sessao_id, ordem_id, cadeira):
        chamadas.append({"cmd": cmd, "sessao_id": sessao_id, "ordem_id": ordem_id, "cadeira": cadeira})
        if "sessao abrir" in cmd:
            out = json.dumps({"sessao_id": sid_novo, "cadeira": cad_nova, "ordem_id": oid_novo})
            return {"exit_code": 0, "stdout": {"texto": out, "bytes_total": len(out), "truncado": False}}
        return {"exit_code": 0, "stdout": {"texto": "ok", "bytes_total": 2, "truncado": False}}

    with patch("server.PF_RUN_SO_VERBO", False),          patch("server.PF_TOOLS_LOTE", True),          patch("server._autoriza", return_value=None),          patch("server._rc", return_value=mock_rc),          patch("server._audit"),          patch("server._run_blocking", side_effect=fake_run_blocking):

        res = await s.run_command(commands=[
            "sessao abrir ia --json",
            "git status"
        ])

    assert len(chamadas) == 2
    assert chamadas[0]["sessao_id"] == "-"
    assert chamadas[1]["sessao_id"] == sid_novo
    assert chamadas[1]["ordem_id"] == oid_novo
    assert chamadas[1]["cadeira"] == cad_nova


def test_operadores_como_token_recusam_e_regex_passa():
    """Card #3045 Passo 2 / Aceite (d):
    partir o item com shlex e recusar só operador como TOKEN; regex e aspas passam.
    """
    with patch("server.SLUGS_SERVIDOS", {"repo", "fila"}), \
         patch("server.BINARIOS", {"repo": "/opt/bin/repo", "fila": "/opt/bin/fila"}):
        # Aceite (d): grep com regex contendo |
        cmd_d = "repo git platafirma-harness grep -n 'def _audit\\|comando' -- ops-server/server.py"
        argv, stdin, recusa = s._item_de_lote(cmd_d)
        assert recusa is None
        assert argv[0] == "/opt/bin/repo"
        assert "-n" in argv
        assert "def _audit\\|comando" in argv

        # Aspas com espaço
        cmd_espaco = 'fila enviar ti --assunto "x y"'
        argv, stdin, recusa = s._item_de_lote(cmd_espaco)
        assert recusa is None
        assert "x y" in argv

        # Operadores como TOKEN recusam
        for op in ("|", ";", "&&", "||", ">", "<", ">>", "&"):
            _, _, rec = s._item_de_lote(f"repo git {op} algo")
            assert rec is not None
            assert rec["recusado"] is True
            assert "metacaractere de shell" in rec["motivo"]

