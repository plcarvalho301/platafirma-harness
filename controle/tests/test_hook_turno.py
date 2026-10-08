"""O hook do Code entrega o turno e a mensagem do dono a porta (card #3356).

`agente/hooks/porta-sessao.py` guarda, no UserPromptSubmit, o contador do turno (T0, T1, ...) e o
texto da mensagem, e marca o turno pendente; o PreToolUse seguinte poe `turno` na chamada da porta
e, so na primeira, `turno_texto`. Nada vai ao stdout do UserPromptSubmit (entraria no contexto do
modelo), sub-agente nao recebe o turno do orquestrador e o estado fica em arquivo 0600 numa pasta
0700. O nome do script tem hifen, entao entra por importlib.
"""
from __future__ import annotations

import importlib.util
import io
import json
import stat
from pathlib import Path

import pytest

HARNESS = Path(__file__).resolve().parents[2]
HOOK = HARNESS / "agente" / "hooks" / "porta-sessao.py"
SETTINGS = HARNESS / "agente" / "settings.json"

CODE = "code-sessao-1"
SID = "11111111-2222-4333-8444-555555555555"
MCP = "mcp__claudinho-mcp__tarefas"


@pytest.fixture
def hook(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("porta_sessao_hook", HOOK)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    monkeypatch.setattr(modulo, "DIR", tmp_path / "pf-sessao-code")
    return modulo


def rodar(hook, ev: dict, capsys) -> tuple[str, int]:
    """Roda o main() com `ev` no stdin; devolve (stdout, exit)."""
    import sys
    entrada = sys.stdin
    sys.stdin = io.StringIO(json.dumps(ev))
    try:
        try:
            hook.main()
            saida = 0
        except SystemExit as e:
            saida = e.code or 0
    finally:
        sys.stdin = entrada
    return capsys.readouterr().out, saida


def prompt(texto, **extra):
    return {"hook_event_name": "UserPromptSubmit", "session_id": CODE, "prompt": texto, **extra}


def pre(tool_input, tool=MCP, **extra):
    return {"hook_event_name": "PreToolUse", "session_id": CODE, "tool_name": tool,
            "tool_input": tool_input, **extra}


def atualizado(saida: str) -> dict:
    return json.loads(saida)["hookSpecificOutput"]["updatedInput"]


def test_prompt_guarda_contador_e_texto_marca_pendente_e_nao_imprime_nada(hook, capsys):
    saida, codigo = rodar(hook, prompt("cards 3356 e 3357"), capsys)
    assert (saida, codigo) == ("", 0)
    assert hook.le(CODE, "turno") == "T0" and hook.le(CODE, "texto") == "cards 3356 e 3357"
    assert hook.le(CODE, "pendente") == "1"


def test_cada_mensagem_sobe_o_contador_e_sobrescreve_o_texto(hook, capsys):
    rodar(hook, prompt("primeira"), capsys)
    rodar(hook, prompt("segunda"), capsys)
    assert hook.le(CODE, "turno") == "T1" and hook.le(CODE, "texto") == "segunda"


def test_a_primeira_chamada_leva_turno_e_texto_e_a_segunda_so_o_turno(hook, capsys):
    rodar(hook, prompt("cards 3356 e 3357"), capsys)
    primeira, _ = rodar(hook, pre({"ato": "ler", "args": ["3356"]}), capsys)
    assert atualizado(primeira)["turno"] == "T0"
    assert atualizado(primeira)["turno_texto"] == "cards 3356 e 3357"
    segunda, _ = rodar(hook, pre({"ato": "ler", "args": ["3357"]}), capsys)
    assert atualizado(segunda)["turno"] == "T0" and "turno_texto" not in atualizado(segunda)
    assert hook.le(CODE, "pendente") is None


def test_a_nova_mensagem_volta_a_levar_o_texto(hook, capsys):
    rodar(hook, prompt("um"), capsys)
    rodar(hook, pre({"ato": "ler"}), capsys)
    rodar(hook, prompt("dois"), capsys)
    saida, _ = rodar(hook, pre({"ato": "ler"}), capsys)
    assert (atualizado(saida)["turno"], atualizado(saida)["turno_texto"]) == ("T1", "dois")


def test_chamada_que_ja_traz_turno_segue_como_veio(hook, capsys):
    rodar(hook, prompt("oi"), capsys)
    saida, codigo = rodar(hook, pre({"ato": "ler", "turno": "T9"}), capsys)
    assert (saida, codigo) == ("", 0)                 # nada a alterar: o agente ja portou
    assert hook.le(CODE, "pendente") == "1"           # o texto ainda espera a chamada sem turno


def test_subagente_nao_recebe_o_turno_do_orquestrador(hook, capsys):
    rodar(hook, prompt("oi"), capsys)
    saida, codigo = rodar(hook, pre({"ato": "ler"}, agent_id="agente-1"), capsys)
    assert (saida, codigo) == ("", 0)
    assert hook.le(CODE, "pendente") == "1"           # o orquestrador ainda a recebe


def test_prompt_de_subagente_nao_grava_turno(hook, capsys):
    rodar(hook, prompt("do subagente", agent_id="agente-1"), capsys)
    assert hook.le(CODE, "turno") is None and hook.le(CODE, "texto") is None


def test_sem_mensagem_guardada_a_chamada_nao_ganha_turno(hook, capsys):
    saida, codigo = rodar(hook, pre({"ato": "ler"}), capsys)
    assert (saida, codigo) == ("", 0)


@pytest.mark.parametrize("ev", [prompt(""), prompt("   "), prompt(None),
                                {"hook_event_name": "UserPromptSubmit", "session_id": CODE}])
def test_prompt_vazio_ou_ausente_nao_guarda_nada_e_sai_zero(hook, capsys, ev):
    assert rodar(hook, ev, capsys) == ("", 0)
    assert hook.le(CODE, "turno") is None and hook.le(CODE, "pendente") is None


def test_o_texto_vai_aparado_a_16000_caracteres(hook, capsys):
    rodar(hook, prompt("a" * 20_000), capsys)
    saida, _ = rodar(hook, pre({"ato": "ler"}), capsys)
    assert len(atualizado(saida)["turno_texto"]) == 16_000


def test_estado_do_turno_e_0600_numa_pasta_0700(hook, capsys):
    rodar(hook, prompt("segredo do dono"), capsys)
    assert stat.S_IMODE(hook.DIR.stat().st_mode) == 0o700
    for sufixo in ("turno", "texto", "pendente"):
        assert stat.S_IMODE(hook.arquivo(CODE, sufixo).stat().st_mode) == 0o600, sufixo


def test_pasta_e_arquivo_que_ja_existiam_abertos_sao_fechados(hook, capsys):
    hook.DIR.mkdir(parents=True, mode=0o755)
    hook.DIR.chmod(0o755)
    velho = hook.arquivo(CODE, "texto")
    velho.write_text("antigo")
    velho.chmod(0o644)
    rodar(hook, prompt("novo"), capsys)
    assert stat.S_IMODE(hook.DIR.stat().st_mode) == 0o700
    assert stat.S_IMODE(velho.stat().st_mode) == 0o600 and velho.read_text() == "novo"


def test_a_mensagem_nao_vai_a_stdout_nem_a_stderr_do_hook(hook, capsys):
    rodar(hook, prompt("texto sigiloso do dono"), capsys)
    rodar(hook, pre({"ato": "ler"}), capsys)
    erro = capsys.readouterr().err
    assert "texto sigiloso do dono" not in erro


def test_o_porte_do_sessao_id_continua_junto_com_o_turno(hook, capsys):
    rodar(hook, {"hook_event_name": "PostToolUse", "session_id": CODE,
                 "tool_name": "mcp__claudinho-mcp__monta_sessao",
                 "tool_response": json.dumps({"sessao_id": SID, "cadeira": "ti"})}, capsys)
    rodar(hook, prompt("oi"), capsys)
    saida, _ = rodar(hook, pre({"ato": "ler"}), capsys)
    novo = atualizado(saida)
    assert (novo["sessao_id"], novo["turno"], novo["turno_texto"]) == (SID, "T0", "oi")


def test_o_settings_registra_o_evento_no_mesmo_script():
    hooks = json.loads(SETTINGS.read_text(encoding="utf-8"))["hooks"]
    comandos = [h["command"] for bloco in hooks["UserPromptSubmit"] for h in bloco["hooks"]]
    assert comandos and all("porta-sessao.py" in c for c in comandos)
    for evento in ("SessionStart", "PreToolUse", "PostToolUse"):     # os tres de hoje seguem
        assert hooks[evento]
