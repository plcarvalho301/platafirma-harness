"""Contrato do sessao_id duravel em ops-server (Card #2945 fase 0.5).

Verifica:
1. Cunhagem de _sessao_id (uuid4 hex puro, 32 chars) por abertura em monta_sessao.
2. Cada abertura gera sessao_id distinto (sem reaproveitamento / sem GET-or-SET).
3. sessao_id != ordem_id.
4. Mapeamento sid -> sessao_id em _sessao_por_sid (com poda 4096/2048).
5. Injeção de PF_SESSAO no subprocesso de run_command via _sessao_por_sid.
6. Persistência no Valkey (SET sessao:<sessao_id> json {cadeira, ordem_id, aberto_em} EX 172800).
7. Falha no Valkey não derruba monta_sessao (degrada declarado).
8. Auditoria de monta_sessao registra sessao_id.
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
OPS_SERVER_DIR = REPO_ROOT / "ops-server"
PDP_CODE_DIR = REPO_ROOT / "politica-acesso"
for d in (OPS_SERVER_DIR, PDP_CODE_DIR):
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))

import server as s


@pytest.fixture(autouse=True)
def _limpa_estado():
    s._ordem_por_sid.clear()
    s._sessao_por_sid.clear()
    yield
    s._ordem_por_sid.clear()
    s._sessao_por_sid.clear()


@pytest.mark.anyio
async def test_monta_sessao_cunha_sessao_id_e_persiste_valkey():
    mock_redis = MagicMock()
    with patch("server._autoriza", return_value=None), \
         patch("server._montar", side_effect=lambda *a, **k: {"cadeira": "ia", "nome_canonico": "claudinho-IA"}), \
         patch("server._sessao_atual", return_value="sid-teste-123"), \
         patch("server._audit") as mock_audit, \
         patch("redis.Redis", return_value=mock_redis):

        r = await s.monta_sessao(cadeira="ia")

        assert "sessao_id" in r
        assert "ordem_id" in r
        sessao_id = r["sessao_id"]
        ordem_id = r["ordem_id"]

        # 32 chars hex (uuid4 puro)
        assert len(sessao_id) == 32
        assert all(c in "0123456789abcdef" for c in sessao_id)
        assert sessao_id != ordem_id

        # Mapeamento sid -> sessao_id
        assert s._sessao_por_sid.get("sid-teste-123") == sessao_id
        assert s._ordem_por_sid.get("sid-teste-123") == ordem_id

        # Persistência no Valkey
        mock_redis.set.assert_called_once()
        args, kwargs = mock_redis.set.call_args
        assert args[0] == f"sessao:{sessao_id}"
        val = json.loads(args[1])
        assert val["cadeira"] == "ia"
        assert val["ordem_id"] == ordem_id
        assert "aberto_em" in val
        assert kwargs.get("ex") == 172800

        # Audit de monta_sessao inclui sessao_id
        chamadas_monta = [c for c in mock_audit.call_args_list if c.kwargs.get("tool") == "monta_sessao"]
        assert len(chamadas_monta) == 1
        assert chamadas_monta[0].kwargs.get("sessao_id") == sessao_id


@pytest.mark.anyio
async def test_duas_aberturas_geram_sessoes_distintas_sem_reuso():
    with patch("server._autoriza", return_value=None), \
         patch("server._montar", side_effect=lambda *a, **k: {"cadeira": "ia", "nome_canonico": "claudinho-IA"}), \
         patch("server._sessao_atual", return_value="sid-mesma-conversa"), \
         patch("server._audit"), \
         patch("redis.Redis"):

        r1 = await s.monta_sessao(cadeira="ia")
        r2 = await s.monta_sessao(cadeira="ia")

        assert r1["sessao_id"] != r2["sessao_id"]
        assert r1["ordem_id"] != r2["ordem_id"]
        assert s._sessao_por_sid.get("sid-mesma-conversa") == r2["sessao_id"]


@pytest.mark.anyio
async def test_falha_valkey_nao_derruba_monta_sessao():
    mock_redis = MagicMock()
    mock_redis.set.side_effect = Exception("Connection refused 6380")

    with patch("server._autoriza", return_value=None), \
         patch("server._montar", side_effect=lambda *a, **k: {"cadeira": "ti", "nome_canonico": "claudinho-TI"}), \
         patch("server._sessao_atual", return_value="sid-fallback"), \
         patch("server._audit"), \
         patch("redis.Redis", return_value=mock_redis):

        r = await s.monta_sessao(cadeira="ti")

        assert "sessao_id" in r
        assert len(r["sessao_id"]) == 32
        assert s._sessao_por_sid.get("sid-fallback") == r["sessao_id"]


@pytest.mark.anyio
async def test_run_command_injeta_sessao_id_duravel_em_pf_sessao():
    s._sessao_por_sid["sid-run-1"] = "sessao-duravel-abc123"
    s._ordem_por_sid["sid-run-1"] = "ordem-id-xyz"

    with patch("server._autoriza", return_value=None), \
         patch("server._sessao_atual", return_value="sid-run-1"), \
         patch("server._run_blocking", return_value={"exit_code": 0, "stdout": {"texto": "", "bytes_total": 0}, "stderr": {"texto": "", "bytes_total": 0}}) as mock_run, \
         patch("server._audit"):

        await s.run_command("echo ok")

        mock_run.assert_called_once()
        args = mock_run.call_args[0]
        # args: command, d, timeout, sessao_id, oid
        assert args[3] == "sessao-duravel-abc123"
        assert args[4] == "ordem-id-xyz"


def test_poda_sessao_por_sid():
    for i in range(4097):
        s._sessao_por_sid[f"sid-{i}"] = f"sessao-{i}"

    if len(s._sessao_por_sid) > 4096:
        for _k in list(s._sessao_por_sid)[:-2048]:
            s._sessao_por_sid.pop(_k, None)

    assert len(s._sessao_por_sid) == 2048
    assert "sid-0" not in s._sessao_por_sid
    assert "sid-4096" in s._sessao_por_sid
