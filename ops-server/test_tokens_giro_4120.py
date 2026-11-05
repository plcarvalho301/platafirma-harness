"""Testes de contagem e registro de tokens no giro da porta (#4120).

U11 da story 4120:
- _campos_poda calcula tokens e metodo_tokens do texto servido
- oplog.validar aceita tokens e metodo_tokens no giro
- o giro gravado no ops log contém tokens e metodo_tokens
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

OPS_SERVER_DIR = Path(__file__).resolve().parent
HARNESS_DIR = OPS_SERVER_DIR.parent
for _d in (OPS_SERVER_DIR, HARNESS_DIR / "politica-acesso", HARNESS_DIR / "lib"):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

_TMP = Path(tempfile.mkdtemp(prefix="ops-tokens-"))
os.environ["PF_HARNESS"] = str(HARNESS_DIR)
for _var, _sub in (("PF_RELEASE_RAIZ", "release"), ("PLATAFIRMA_INSTANCIA", "instancia")):
    if not os.environ.get(_var, "").startswith(tempfile.gettempdir()):
        os.environ[_var] = str(_TMP / _sub)

import oplog
import server as s
import tokenizador

SID = "11111111-1111-4111-8111-111111111111"
IDENT_TOKEN = {"sujeito": "b6986be0", "sub": "b6986be0", "username": "megafone",
               "azp": "claudinho-mcp", "sid": "sid-login", "jti": "jti-1"}


@pytest.fixture(autouse=True)
def porta_isolada():
    s._ORIGENS.clear()
    s._CARIMBOS.clear()
    s._DECLARA_EXIT.clear()
    with patch.object(s, "_rc", return_value=MagicMock(get=MagicMock(return_value=None))), \
            patch.object(s, "_quem", return_value=IDENT_TOKEN):
        yield
    s._ORIGENS.clear()
    s._CARIMBOS.clear()


def test_campos_poda_retorna_tokens_e_metodo():
    retorno = {"stdout": {"texto": "Olá mundo, teste de contagem de tokens na porta."}}
    poda = s._campos_poda(retorno)
    assert "tokens" in poda
    assert "metodo_tokens" in poda
    assert isinstance(poda["tokens"], int)
    assert poda["tokens"] > 0
    assert "tokenizador" in poda["metodo_tokens"] or "ESTIMATIVA" in poda["metodo_tokens"]


def test_oplog_validar_aceita_tokens_no_giro():
    reg = {
        "ts": "2026-11-05T12:00:00.000+00:00",
        "evento_id": "0192f000-0000-7000-8000-000000000001",
        "schema_v": 1,
        "origem": "cadeira",
        "mapa_v": None,
        "tool": "teste",
        "sessao_id": SID,
        "cadeira": "engenharia",
        "ordem_id": "o1",
        "exit_code": 0,
        "classe": "ok",
        "classe_fonte": "verbo",
        "bytes_produzidos": 100,
        "bytes_servidos": 100,
        "lavado": [],
        "capacidade": "verificacao",
        "ferramenta": "teste",
        "escopo": "#4120",
        "turno_id": "t1",
        "turno_fonte": "declarado",
        "tokens": 42,
        "metodo_tokens": "tokenizador qwen2.5",
        "sujeito": "b6986be0",
        "sub": "b6986be0",
        "username": "megafone",
        "azp": "claudinho-mcp",
        "sid": "sid-login",
        "jti": "jti-1",
    }
    erros = oplog.validar(reg)
    assert not erros, f"erros de validacao: {erros}"


def test_audit_grava_tokens_no_giro(tmp_path):
    log_dir = tmp_path / "var" / "log" / "ops"
    log_dir.mkdir(parents=True)
    with patch.object(s, "LOG_DIR", log_dir), \
            patch.object(s, "_sessao_atual", return_value=SID):
        s._audit(tool="teste", evento="verbo",
                 sessao_id=SID, ordem_id="o1", cadeira="engenharia", exit_code=0,
                 **s._campos_poda({"stdout": {"texto": "saída do comando de teste"}}))

    arquivos = list(log_dir.glob("ops-*.jsonl"))
    assert len(arquivos) == 1
    linhas = [json.loads(l) for l in arquivos[0].read_text(encoding="utf-8").splitlines()]
    assert len(linhas) == 1
    giro = linhas[0]
    assert "tokens" in giro
    assert giro["tokens"] > 0
    assert "metodo_tokens" in giro
