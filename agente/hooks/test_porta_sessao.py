"""porta-sessao.py como o Code o chama: JSON no stdin, JSON no stdout, exit 0 sempre."""
import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parent / "porta-sessao.py"
SID = "0a1b2c3d-1111-4222-8333-444455556666"


def _roda(ev: dict, tmp: Path, projeto: Path | None = None) -> str:
    env = {k: v for k, v in os.environ.items() if k != "CLAUDE_PROJECT_DIR"}
    env.update(XDG_RUNTIME_DIR=str(tmp / "run"), PF_ABERTURA_DIR=str(tmp / "morada"))
    if projeto:
        env["CLAUDE_PROJECT_DIR"] = str(projeto)
    r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(ev), text=True,
                       capture_output=True, env=env, timeout=20)
    assert r.returncode == 0, r.stderr
    return r.stdout


def _publica(tmp: Path, cadeira: str, texto: str) -> None:
    raiz = tmp / "morada" / "current" / "abertura"
    (raiz / cadeira).mkdir(parents=True)
    (raiz / cadeira / "persona.md").write_text(texto, encoding="utf-8")
    (raiz / "dono.md").write_text("# conduta — o dono", encoding="utf-8")


def _posto(tmp: Path) -> Path:
    """O posto numa maquina que nao e o host: so a copia da conduta em `abertura/`."""
    raiz = tmp / "posto"
    (raiz / "abertura").mkdir(parents=True)
    (raiz / "abertura" / "dono.md").write_text("# conduta — o dono", encoding="utf-8")
    return raiz


def _abre(tmp: Path, resposta) -> None:
    _roda({"hook_event_name": "PostToolUse", "session_id": "fita-1",
           "tool_name": "mcp__claudinho-mcp__monta_sessao", "tool_response": resposta}, tmp)


def _retoma(tmp: Path, origem: str = "compact", fita: str = "fita-1",
            projeto: Path | None = None) -> str:
    return _roda({"hook_event_name": "SessionStart", "session_id": fita, "source": origem},
                 tmp, projeto)


def _ctx(saida: str) -> str:
    fora = json.loads(saida)
    assert fora["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    return fora["hookSpecificOutput"]["additionalContext"]


def test_no_host_compact_devolve_persona_publicada_e_sessao(tmp_path):
    _publica(tmp_path, "ia", "Você é Elias Elefante.")
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    ctx = _ctx(_retoma(tmp_path))
    assert "Elias Elefante" in ctx and SID in ctx and "cadeira `ia`" in ctx
    assert "CLAUDE.md (import)" in ctx and "ANTES de qualquer outra coisa" not in ctx


def test_no_posto_conduta_fica_e_persona_volta_por_monta_sessao(tmp_path):
    """Maquina que nao e o host, Code aberto da pasta do posto: a conduta esta no CLAUDE.md
    do projeto; a persona nao tem copia local e volta pelo mesmo sessao_id."""
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    ctx = _ctx(_retoma(tmp_path, projeto=_posto(tmp_path)))
    assert "CLAUDE.md (import)" in ctx
    assert f'monta_sessao(cadeira="ia", sessao_id="{SID}")' in ctx
    assert "sem persona." in ctx and "sem a conduta" not in ctx


def test_sem_host_e_sem_posto_manda_reabrir_por_tudo(tmp_path):
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    ctx = _ctx(_retoma(tmp_path))
    assert "ANTES de qualquer outra coisa" in ctx
    assert "sem persona e sem a conduta do dono" in ctx
    assert "(import)" not in ctx, "sem import resolvido, nao prometer conduta"


def test_retorno_como_string_escapada_tambem_grava_cadeira(tmp_path):
    _publica(tmp_path, "ti", "Você é Oswaldo Aranha.")
    _abre(tmp_path, json.dumps(json.dumps({"sessao": {"sessao_id": SID, "cadeira": "ti"}})))
    assert "Oswaldo Aranha" in _ctx(_retoma(tmp_path, "resume"))


def test_startup_e_fita_sem_abertura_ficam_calados(tmp_path):
    assert _retoma(tmp_path, "startup") == ""
    assert _retoma(tmp_path, "compact", fita="outra") == ""


def test_hook_declarado_na_conta_e_no_projeto_fala_uma_vez_so(tmp_path):
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    saidas = [_retoma(tmp_path), _retoma(tmp_path)]
    assert sum(1 for s in saidas if s) == 1


def test_persona_grande_respeita_o_teto_do_code(tmp_path):
    _publica(tmp_path, "ia", "x" * 20_000)
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    ctx = _ctx(_retoma(tmp_path))
    assert len(ctx) < 10_000 and "persona ler" in ctx


def test_porte_do_sessao_id_segue_como_antes(tmp_path):
    _abre(tmp_path, {"sessao": {"sessao_id": SID, "cadeira": "ia"}})
    fora = json.loads(_roda({"hook_event_name": "PreToolUse", "session_id": "fita-1",
                             "tool_name": "mcp__claudinho-mcp__mesa",
                             "tool_input": {"ato": "ver"}}, tmp_path))
    assert fora["hookSpecificOutput"]["updatedInput"] == {"ato": "ver", "sessao_id": SID}
