"""porta-sessao.py como o Code o chama: JSON no stdin, JSON no stdout, exit 0 sempre."""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "porta-sessao.py"
SID = "0a1b2c3d-1111-4222-8333-444455556666"


def _roda(ev: dict, tmp: Path) -> str:
    env = {**os.environ, "XDG_RUNTIME_DIR": str(tmp / "run"),
           "PF_ABERTURA_DIR": str(tmp / "morada")}
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), text=True,
                       capture_output=True, env=env, timeout=20)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _publica(tmp: Path, cadeira: str, texto: str) -> None:
    d = tmp / "morada" / "current" / "abertura" / cadeira
    d.mkdir(parents=True)
    (d / "persona.md").write_text(texto, encoding="utf-8")


def _abre(tmp: Path, resposta) -> None:
    _roda({"hook_event_name": "PostToolUse", "session_id": "fita-1",
           "tool_name": "mcp__claudinho-mcp__monta_sessao", "tool_response": resposta}, tmp)


def test_compact_devolve_persona_publicada_e_sessao(tmp_path):
    _publica(tmp_path, "ia", "Você é Elias Elefante.")
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    fora = json.loads(_roda({"hook_event_name": "SessionStart", "session_id": "fita-1",
                             "source": "compact"}, tmp_path))
    ctx = fora["hookSpecificOutput"]["additionalContext"]
    assert fora["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "Elias Elefante" in ctx and SID in ctx and "cadeira `ia`" in ctx


def test_retorno_como_string_escapada_tambem_grava_cadeira(tmp_path):
    _publica(tmp_path, "ti", "Você é Oswaldo Aranha.")
    _abre(tmp_path, json.dumps({"sessao": {"sessao_id": SID, "cadeira": "ti"}}))
    _abre(tmp_path, json.dumps(json.dumps({"sessao": {"sessao_id": SID, "cadeira": "ti"}})))
    ctx = json.loads(_roda({"hook_event_name": "SessionStart", "session_id": "fita-1",
                            "source": "resume"}, tmp_path))["hookSpecificOutput"]["additionalContext"]
    assert "Oswaldo Aranha" in ctx


def test_startup_e_fita_sem_abertura_ficam_calados(tmp_path):
    assert _roda({"hook_event_name": "SessionStart", "session_id": "fita-1",
                  "source": "startup"}, tmp_path) == ""
    assert _roda({"hook_event_name": "SessionStart", "session_id": "outra",
                  "source": "compact"}, tmp_path) == ""


def test_persona_grande_respeita_o_teto_do_code(tmp_path):
    _publica(tmp_path, "ia", "x" * 20_000)
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    ctx = json.loads(_roda({"hook_event_name": "SessionStart", "session_id": "fita-1",
                            "source": "compact"}, tmp_path))["hookSpecificOutput"]["additionalContext"]
    assert len(ctx) < 10_000 and "persona ler" in ctx


def test_porte_do_sessao_id_segue_como_antes(tmp_path):
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    fora = json.loads(_roda({"hook_event_name": "PreToolUse", "session_id": "fita-1",
                             "tool_name": "mcp__claudinho-mcp__mesa",
                             "tool_input": {"ato": "ver"}}, tmp_path))
    assert fora["hookSpecificOutput"]["updatedInput"] == {"ato": "ver", "sessao_id": SID}
