# componente: componente:agente-hooks
"""Testes do gancho porta-sessao.py para itens estruturados do malote (card #4369)."""
from __future__ import annotations

import importlib.util
from pathlib import Path

HOOK_PATH = Path(__file__).resolve().parent / "porta-sessao.py"


def _carrega_hook():
    spec = importlib.util.spec_from_file_location("porta_sessao_hook_4369", str(HOOK_PATH))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_liga_origem_em_itens_estruturados_do_malote():
    hook = _carrega_hook()
    entrada = {
        "itens": [
            {"verbo": "sessao", "ato": "abrir", "args": ["engenharia"]},
            {"verbo": "repo", "ato": "estado", "args": ["platafirma-casa-espelho"]},
        ]
    }
    saida = hook.liga_origem("mcp__claudinho-mcp__malote", entrada, "orig-123")
    assert saida["itens"][0]["args"] == ["engenharia", "--origem", "orig-123"]
    assert saida["itens"][1]["args"] == ["platafirma-casa-espelho"]


def test_liga_origem_em_commands_estruturados_sem_duplicar():
    hook = _carrega_hook()
    entrada = {
        "commands": [
            {"verbo": "sessao", "ato": "abrir", "args": ["engenharia"]},
            {"verbo": "sessao", "ato": "abrir", "args": ["engenharia", "--origem", "ja-tem"]},
        ]
    }
    saida = hook.liga_origem("malote", entrada, "orig-123")
    assert saida["commands"][0]["args"] == ["engenharia", "--origem", "orig-123"]
    assert saida["commands"][1]["args"] == ["engenharia", "--origem", "ja-tem"]


def test_liga_origem_em_texto_com_prefixo_malote():
    hook = _carrega_hook()
    entrada = {"commands": ["malote sessao abrir engenharia", "sessao abrir engenharia"]}
    saida = hook.liga_origem("malote", entrada, "orig-999")
    assert saida["commands"][0] == "malote sessao abrir engenharia --origem orig-999"
    assert saida["commands"][1] == "sessao abrir engenharia --origem orig-999"


def test_liga_origem_em_verbo_sessao_lote():
    hook = _carrega_hook()
    entrada = {"lote": [{"ato": "abrir", "args": ["ti"]}]}
    saida = hook.liga_origem("mcp__claudinho-mcp__sessao", entrada, "orig-abc")
    assert saida["lote"][0]["args"] == ["ti", "--origem", "orig-abc"]
