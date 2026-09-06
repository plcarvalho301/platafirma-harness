"""Contrato da lógica a/b/c do `sessao_id` na porta `monta_sessao` (ordem do dono, 06/09/2026).

Prova que quem cunha o `sessao_id` é a PORTA, não o schema da tool (o gate do cliente
"No approval received" na abertura era regressão de expor o campo como input a preencher):

  (a) fita SEM sessao + primeiro giro (há prompt do dono) -> a porta CUNHA um uuid e o passa a `_montar`
  (b) fita PORTA um sessao_id válido -> a porta passa ESSE id a `_montar`, sem recunhar
  (c) valor presente porém inválido, ou reabertura sem portar id -> NEGA (não adivinha)

Testa o ramo isolando `_montar` (capturamos o `sessao_id` que a porta lhe entrega) e
`_autoriza` (deixa passar). Não depende de valkey: o ramo é decidido ANTES do to_thread.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops-server"))
import server as s  # noqa: E402

RFC4122 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@pytest.fixture
def anyio_backend():
    return "asyncio"


def _captura_montar():
    """side_effect que grava o sessao_id recebido e devolve um pacote mínimo válido."""
    capturado = {}

    def _fake(cadeira, atualizar, chapeu, pergunta, sessao_id):
        capturado["sessao_id"] = sessao_id
        return {"cadeira": cadeira or "ia", "nome_canonico": "claudinho-IA",
                "sessao_id": sessao_id, "sessao": {"cunhada_agora": True}}

    return _fake, capturado


def _primeiro_giro_puro():
    assert s._primeiro_giro("bom dia, abre a fita") is True
    assert s._primeiro_giro("   ") is False
    assert s._primeiro_giro("") is False


def test_primeiro_giro_predicado_puro():
    _primeiro_giro_puro()


@pytest.mark.anyio
async def test_a_abertura_a_porta_cunha_uuid():
    fake, cap = _captura_montar()
    with patch("server._autoriza", return_value=None), \
         patch("server._montar", side_effect=fake), \
         patch("server._sessao_atual", return_value="sid-x"), \
         patch("server._audit"), patch("redis.Redis", return_value=MagicMock()):
        await s.monta_sessao(cadeira="ia", pergunta="abre a fita")
    assert RFC4122.match(cap["sessao_id"]), f"nao cunhou uuid RFC-4122: {cap['sessao_id']!r}"


@pytest.mark.anyio
async def test_b_fita_porta_id_valido_nao_recunha():
    sid = "4bb375b6-fb77-4cbd-97c2-e7a3e808ef83"
    fake, cap = _captura_montar()
    with patch("server._autoriza", return_value=None), \
         patch("server._montar", side_effect=fake), \
         patch("server._sessao_atual", return_value="sid-x"), \
         patch("server._audit"), patch("redis.Redis", return_value=MagicMock()):
        await s.monta_sessao(cadeira="ia", pergunta="segundo giro", sessao_id=sid)
    assert cap["sessao_id"] == sid, "recunhou em vez de portar o id da fita"


@pytest.mark.anyio
async def test_c_valor_invalido_nega_e_nao_monta():
    fake, cap = _captura_montar()
    with patch("server._autoriza", return_value=None), \
         patch("server._montar", side_effect=fake), \
         patch("server._audit"), patch("redis.Redis", return_value=MagicMock()):
        r = await s.monta_sessao(cadeira="ia", pergunta="", sessao_id="nao-e-uuid")
    assert r.get("regra") == "sessao", f"deveria negar por regra=sessao: {r}"
    assert "sessao_id" not in cap, "montou apesar de sessao_id invalido"


@pytest.mark.anyio
async def test_a_primeira_abertura_nao_exige_sessao_id_do_cliente():
    """A regressão que travava a fábrica: abrir sem enviar sessao_id tem de FUNCIONAR."""
    fake, cap = _captura_montar()
    with patch("server._autoriza", return_value=None), \
         patch("server._montar", side_effect=fake), \
         patch("server._sessao_atual", return_value="sid-x"), \
         patch("server._audit"), patch("redis.Redis", return_value=MagicMock()):
        r = await s.monta_sessao(cadeira="ia", pergunta="oi")
    assert not r.get("erro"), f"abertura sem sessao_id nao pode falhar: {r.get('erro')}"
    assert "sessao_id" in cap
