"""Regressão do incidente #4251: forma única de erro/recusa da porta, isError no MCP e borda."""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

RAIZ = Path(__file__).resolve().parents[1]
os.environ.setdefault("PF_HARNESS", str(RAIZ))
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(RAIZ / "borda"))

import borda as _borda  # noqa: E402
import leitura as L  # noqa: E402
import lote as _lote  # noqa: E402
import server as s  # noqa: E402


# --------------------------------------------------------------------------- 1. Forma única + lote
def test_envelope_erro_forma_unica_e_lote_le_exit_code_antes():
    r = L.envelope_erro(4, "negado pela política", None, recusado=True, motivo="x")
    assert r["exit_code"] == 4
    assert r["falta"] == "negado pela política"
    assert "proximo" not in r
    assert r["recusado"] is True and r["motivo"] == "x"

    # Lote encadeado lê exit_code antes de deduzir 2 por recusado=True
    assert _lote.exit_do_item(r) == 4
    assert _lote.exit_do_item({"recusado": True}) == 2


# --------------------------------------------------------------------------- 2. Tool de verbo com args string
def test_tool_verbo_args_em_texto_recusa_como_malote(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "SLUGS_SERVIDOS", {"fake"})
    verbo = tmp_path / "fake"
    verbo.write_text("#!/bin/sh\necho ok\n", encoding="utf-8")
    verbo.chmod(0o755)
    tool = s._faz_tool_verbo("fake", str(verbo), "desc")

    r = asyncio.run(tool(ato="ler", args="4148"))
    assert r["recusado"] is True
    assert r["exit_code"] == 2
    assert r["motivo"] == "args deve ser lista de tokens, recebido string; use args: [ ... ]"
    assert "sugestao" not in r
    assert r["proximo"].startswith("fake(")


# --------------------------------------------------------------------------- 3. write_file absoluto fora de morada
def test_write_file_absoluto_fora_de_morada_nao_fala_em_relativo(tmp_path, monkeypatch):
    monkeypatch.setattr(s, "_autoriza", lambda *a, **kw: None)
    monkeypatch.setattr(s, "_sessao_resolve", lambda sid: {
        "sessao_id": "-", "ordem_id": "-", "cadeira": "engenharia", "sujeito": "s"
    })
    monkeypatch.setattr(s, "_bancada", lambda: tmp_path)

    r_abs = s.write_file(path="/tmp/revisao-erro-4251.txt", content="x")
    assert r_abs["recusado"] is True
    assert r_abs["exit_code"] == 4
    assert "fora de morada" in r_abs["motivo"]
    assert "caminho relativo parte da bancada declarada" not in r_abs["motivo"]

    r_rel = s.write_file(path="fora/arquivo.txt", content="x")
    assert r_rel["recusado"] is True
    assert "caminho relativo parte da bancada declarada" in r_rel["motivo"]


# --------------------------------------------------------------------------- 4. ler_arquivo sob a fila
def test_ler_arquivo_sob_fila_devolve_recusado_com_verbo_fila(tmp_path, monkeypatch):
    fila_dir = tmp_path / "fila"
    fila_dir.mkdir()
    alvo = fila_dir / "caixa.jsonl"
    alvo.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(s, "FILA_RAIZ", fila_dir.resolve())
    monkeypatch.setattr(s, "_autoriza", lambda *a, **kw: None)
    monkeypatch.setattr(s, "_sessao_resolve", lambda sid: {
        "sessao_id": "-", "ordem_id": "-", "cadeira": "engenharia", "sujeito": "s"
    })

    r = s.ler_arquivo(caminho=str(alvo))
    assert r["recusado"] is True
    assert r["exit_code"] == 4
    assert "fila" in r["motivo"]
    assert r["caminho"] == str(alvo)
    assert "fila(" in r["proximo"]


# --------------------------------------------------------------------------- 5. Cura sem reticências
def test_ler_arquivo_linhas_invalida_traz_caminho_na_cura_e_proximo(tmp_path):
    arq = tmp_path / "amostra.txt"
    arq.write_text("a\nb\n", encoding="utf-8")
    r = L.le(arq, linhas="abc")
    assert r["exit_code"] == 2
    assert "…" not in r["cura"]
    assert str(arq) in r["cura"]
    assert r["proximo"] == r["cura"]


# --------------------------------------------------------------------------- 6. termo em arquivo
def test_ler_arquivo_termo_em_arquivo_devolve_erro_e_doc_cita_termo(tmp_path):
    arq = tmp_path / "amostra.txt"
    arq.write_text("linha 1\nlinha 2\n", encoding="utf-8")
    r = L.le(arq, termo="linha")
    assert r["exit_code"] == 2
    assert "diretório" in r["erro"]
    assert "termo" in (s.ler_arquivo.__doc__ or "")


# --------------------------------------------------------------------------- 7. sugestao só em sem verbo
def test_recusa_sugestao_so_em_sem_verbo():
    r_meta = s._recusa("tarefas", "metacaractere de shell — um verbo por item",
                       proximo='malote(commands=[{"verbo": "tarefas", "ato": "ler"}])')
    assert "sugestao" not in r_meta
    assert r_meta["exit_code"] == 2
    assert r_meta["proximo"].startswith("malote(")

    r_sv = s._recusa("cat", "sem verbo")
    assert r_sv["sugestao"] == "ler_arquivo"
    assert r_sv["exit_code"] == 2
    assert r_sv["proximo"] == 'ler_arquivo(caminho="...")'

    r_falta = s._recusa("verbo_inexistente_4251", "sem verbo")
    assert r_falta["sugestao"] is None
    assert "proximo" not in r_falta
    assert "verbos_servidos" in r_falta


# --------------------------------------------------------------------------- 8. Retornos sem chamada que resolve
def test_retornos_sem_chamada_que_resolve(tmp_path, monkeypatch):
    # Timeout em _run_verbo_blocking (< 600 -> tem proximo; >= 600 -> sem proximo)
    with patch("subprocess.Popen") as mp:
        proc = mp.return_value
        proc.pid = 999999
        proc.communicate.side_effect = subprocess.TimeoutExpired("cmd", 10)
        with patch("os.killpg"), patch("os.getpgid", return_value=999999):
            r_t10 = s._run_verbo_blocking(["/bin/tarefas", "ler", "1"], None, 10,
                                          {"sessao_id": "-", "ordem_id": "-", "cadeira": ""})
            r_t600 = s._run_verbo_blocking(["/bin/tarefas", "ler", "1"], None, 600,
                                           {"sessao_id": "-", "ordem_id": "-", "cadeira": ""})
    assert r_t10["exit_code"] == 5 and "timeout=20" in r_t10["proximo"]
    assert r_t600["exit_code"] == 5 and "proximo" not in r_t600

    # OSError ao executar verbo
    with patch("subprocess.Popen", side_effect=OSError("no such file")):
        r_os = s._run_verbo_blocking(["/bin/tarefas", "ler"], None, 10,
                                     {"sessao_id": "-", "ordem_id": "-", "cadeira": ""})
    assert r_os["exit_code"] == 5 and "proximo" not in r_os and "ti" in r_os["falta"]

    # Negativa de política
    monkeypatch.setattr(s, "_carrega_politica", lambda: {"erro": "sem arquivo"})
    r_pdp = s._autoriza("tarefas", "run_command", "comando", "tarefas ler", "runtime")
    assert r_pdp["exit_code"] == 3 and "proximo" not in r_pdp


# --------------------------------------------------------------------------- 9. isError no MCP + borda
def test_marca_is_error_mcp_e_borda_decide_pelo_corpo():
    from mcp import types as _tipos

    assert s._deve_marcar_erro({"exit_code": 0}) is False
    assert s._deve_marcar_erro({"exit_code": 1}) is False
    assert s._deve_marcar_erro({"em_andamento": True}) is False
    assert s._deve_marcar_erro({"exit_code": 2, "recusado": True}) is True
    assert s._deve_marcar_erro({"exit_code": 3}) is True
    assert s._deve_marcar_erro({"exit_code": 4}) is True
    assert s._deve_marcar_erro({"exit_code": 5}) is True

    # Handler CallToolRequest da porta marca isError=True em exit 2..5 e não em exit 1
    async def _roda_req(tool_name, arguments):
        req = _tipos.CallToolRequest(
            method="tools/call",
            params=_tipos.CallToolRequestParams(name=tool_name, arguments=arguments),
        )
        handler = s.mcp._mcp_server.request_handlers[_tipos.CallToolRequest]
        return (await handler(req)).root

    with patch.object(s, "_autoriza", return_value=None), \
            patch.object(s, "_sessao_resolve", return_value={
                "sessao_id": "-", "ordem_id": "-", "cadeira": "engenharia", "sujeito": "s"
            }):
        res_err = asyncio.run(_roda_req("ler_arquivo", {"caminho": ""}))
        assert res_err.isError is True

    # Borda com isError=True + envelope válido decide pelo corpo (não retorna 502 cego)
    rpc_rec = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "result": {
            "isError": True,
            "content": [{"type": "text", "text": json.dumps({"recusado": True, "exit_code": 4, "motivo": "negado"})}],
            "structuredContent": {"recusado": True, "exit_code": 4, "motivo": "negado"},
        },
    }).encode()
    st, env = _borda._envelope_do_rpc("application/json", rpc_rec)
    assert st == 200 and env["recusado"] is True
    assert _borda._resposta_do_tema("GET", env, None)[0] == 403
    assert _borda._resposta_da_leitura("telas", env)[0] == 403
    assert _borda._resposta_do_tema("PUT", {"exit_code": 2}, "claro")[0] == 400
    assert _borda._resposta_do_tema("GET", {"exit_code": 3}, None)[0] == 401
    assert _borda._resposta_do_tema("GET", {"exit_code": 5}, None)[0] == 502
