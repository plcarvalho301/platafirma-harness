"""Testes de contrato da tool monta_sessao como projeção do lote (spec_sessao §6, #3053).

Aceite coberto:
- abrir ok → expediente recebe os três PF_* em slug puro (assert no env do execve);
- abrir exit 3 → expediente não roda;
- sessao_id portado → ordem_id novo, id igual;
- pergunta chega por stdin.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import subprocess

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
async def test_abrir_ok_expediente_recebe_tres_pf_em_slug_puro():
    sid = "11111111-2222-3333-4444-555555555555"
    oid = "o20260914T120000-abcdef"
    sub = "user-sub-123"

    abrir_out = {
        "sessao_id": sid,
        "cunhada_agora": True,
        "sujeito": sub,
        "cadeira": "ia",
        "canonizada": True,
        "autorizada_por": "regra@plano",
        "ordem_id": oid,
        "registrada": True,
        "duravel": True,
        "porte": "devolva este sessao_id",
    }

    exp_out = {
        "cadeira": "ia",
        "sessao_id": sid,
        "ordem_id": oid,
        "chapeu": None,
        "roteador": {"via": "fallback", "slug": None},
        "pacote": {"pecas": 7, "tokens": 1200},
        "pecas": [{"peca": "conduta", "tokens": 100}],
        "avisos": [],
    }

    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": oid, "sub": sub})

    chamadas_run = []

    def fake_subprocess_run(argv, *args, **kwargs):
        chamadas_run.append({"argv": list(argv), "kwargs": dict(kwargs)})
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(abrir_out), stderr=""
            )
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(exp_out), stderr=""
            )
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="comando desconhecido")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub, "sujeito": "claudinho"}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="claudinho-IA", pergunta="iniciar fita")

    # Assert: sessao abrir foi chamado com PF_SUJEITO = sub
    assert len(chamadas_run) == 2
    abrir_call = chamadas_run[0]
    assert "abrir" in abrir_call["argv"]
    # a porta passa a cadeira COMO RECEBEU; canonizar e etapa 3 de `sessao abrir` (spec_sessao §2)
    assert "claudinho-IA" in abrir_call["argv"]
    assert "ia" not in abrir_call["argv"]
    assert abrir_call["kwargs"]["env"]["PF_SUJEITO"] == sub

    # Assert: expediente montar recebeu os três PF_* em slug puro
    exp_call = chamadas_run[1]
    env_exp = exp_call["kwargs"]["env"]
    assert env_exp["PF_CADEIRA"] == "ia", f"esperava slug puro 'ia', recebido: {env_exp['PF_CADEIRA']}"
    assert env_exp["PF_SESSAO"] == sid
    assert env_exp["PF_ORDEM_ID"] == oid

    # Assert: resposta traz bloco sessao no topo
    chaves = list(res.keys())
    assert chaves[0] == "sessao"
    assert res["sessao"]["sessao_id"] == sid
    assert res["pacote"]["pecas"] == 7


@pytest.mark.anyio
async def test_abrir_exit_3_expediente_nao_roda():
    mock_rc = MagicMock()
    chamadas_run = []

    def fake_subprocess_run(argv, *args, **kwargs):
        chamadas_run.append({"argv": list(argv), "kwargs": dict(kwargs)})
        return subprocess.CompletedProcess(
            argv, returncode=3,
            stdout=json.dumps({"erro": "sem sujeito: a porta não autenticou"}),
            stderr=""
        )

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": None}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="ia", pergunta="qualquer")

    # Apenas o abrir roda; expediente NÃO roda
    assert len(chamadas_run) == 1
    assert "abrir" in chamadas_run[0]["argv"]
    assert res.get("erro") == "sem sujeito: a porta não autenticou"


@pytest.mark.anyio
async def test_sessao_id_portado_ordem_id_novo_id_igual():
    sid_portado = "22222222-3333-4444-5555-666666666666"
    oid_novo = "o20260914T130000-newoid"
    sub = "user-sub-123"

    abrir_out = {
        "sessao_id": sid_portado,
        "cunhada_agora": False,
        "sujeito": sub,
        "cadeira": "ia",
        "canonizada": True,
        "autorizada_por": "regra@plano",
        "ordem_id": oid_novo,
        "registrada": True,
        "duravel": True,
        "porte": "devolva este sessao_id",
    }

    exp_out = {
        "cadeira": "ia",
        "sessao_id": sid_portado,
        "ordem_id": oid_novo,
        "chapeu": None,
        "roteador": {"via": "fallback", "slug": None},
        "pacote": {"pecas": 7, "tokens": 1200},
        "pecas": [],
        "avisos": [],
    }

    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": oid_novo, "sub": sub})

    chamadas_run = []

    def fake_subprocess_run(argv, *args, **kwargs):
        chamadas_run.append({"argv": list(argv), "kwargs": dict(kwargs)})
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(abrir_out), stderr=""
            )
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(exp_out), stderr=""
            )
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="ia", sessao_id=sid_portado)

    abrir_call = chamadas_run[0]
    assert "--sessao-id" in abrir_call["argv"]
    idx = abrir_call["argv"].index("--sessao-id")
    assert abrir_call["argv"][idx + 1] == sid_portado

    exp_call = chamadas_run[1]
    assert exp_call["kwargs"]["env"]["PF_SESSAO"] == sid_portado
    assert exp_call["kwargs"]["env"]["PF_ORDEM_ID"] == oid_novo

    assert res["sessao_id"] == sid_portado
    assert res["ordem_id"] == oid_novo


@pytest.mark.anyio
async def test_pergunta_chega_por_stdin():
    sid = "33333333-4444-5555-6666-777777777777"
    oid = "o20260914T140000-zzzzzz"
    sub = "user-sub-123"
    pergunta_literal = "Qual é o status da migração de dados?"

    abrir_out = {
        "sessao_id": sid,
        "cunhada_agora": True,
        "sujeito": sub,
        "cadeira": "ia",
        "ordem_id": oid,
    }

    exp_out = {
        "cadeira": "ia",
        "sessao_id": sid,
        "ordem_id": oid,
        "chapeu": "contexto",
        "pacote": {"pecas": 7, "tokens": 1000},
        "pecas": [],
        "avisos": [],
    }

    mock_rc = MagicMock()
    mock_rc.get.return_value = json.dumps({"cadeira": "ia", "ordem_id": oid, "sub": sub})

    chamadas_run = []

    def fake_subprocess_run(argv, *args, **kwargs):
        chamadas_run.append({"argv": list(argv), "kwargs": dict(kwargs)})
        is_py = "python" in Path(argv[0]).name
        cmd = argv[1] if is_py else argv[0]
        args_rest = argv[2:] if is_py else argv[1:]
        if "sessao" in cmd and len(args_rest) > 0 and args_rest[0] == "abrir":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(abrir_out), stderr=""
            )
        elif "expediente" in cmd and len(args_rest) > 0 and args_rest[0] == "montar":
            return subprocess.CompletedProcess(
                argv, returncode=0, stdout=json.dumps(exp_out), stderr=""
            )
        return subprocess.CompletedProcess(argv, returncode=1, stdout="", stderr="")

    with patch("server._autoriza", return_value=None), \
         patch("server._quem", return_value={"sub": sub}), \
         patch("server._rc", return_value=mock_rc), \
         patch("server._audit"), \
         patch("subprocess.run", side_effect=fake_subprocess_run):

        res = await s.monta_sessao(cadeira="ia", pergunta=pergunta_literal, chapeu="contexto")

    exp_call = chamadas_run[1]
    assert exp_call["kwargs"]["input"] == pergunta_literal
    assert "--pergunta" not in exp_call["argv"]
    assert "--chapeu" in exp_call["argv"]
    assert res["chapeu"] == "contexto"
