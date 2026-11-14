"""DT 527 / incidente #4188: lint arranque barra primitiva de provider em texto comum."""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
if str(RAIZ / "bin") not in sys.path:
    sys.path.insert(0, str(RAIZ / "bin"))

from _lint.arranque import verificar_arranque  # noqa: E402


def test_reprova_primitiva_em_abertura_dono_e_cultura(tmp_path):
    (tmp_path / "abertura").mkdir()
    (tmp_path / "2-comportamento" / "cultura").mkdir(parents=True)
    (tmp_path / "abertura" / "dono.md").write_text(
        "Use ToolSearch com select:foo.\n", encoding="utf-8"
    )
    (tmp_path / "2-comportamento" / "cultura" / "cultura.md").write_text(
        "Chame call_mcp_tool ou tool_search.\n", encoding="utf-8"
    )

    apts = verificar_arranque(tmp_path)
    arqs_e_msgs = [(a.arquivo, a.o_que_fere) for a in apts]
    assert any(arq == "abertura/dono.md" and "ToolSearch" in msg for arq, msg in arqs_e_msgs)
    assert any(
        arq == "2-comportamento/cultura/cultura.md" and "call_mcp_tool" in msg
        for arq, msg in arqs_e_msgs
    )
    assert any(
        arq == "2-comportamento/cultura/cultura.md" and "tool_search" in msg
        for arq, msg in arqs_e_msgs
    )


def test_permite_primitiva_na_tabela_de_providers_do_agents_e_claude(tmp_path):
    (tmp_path / "agente").mkdir()
    (tmp_path / "AGENTS.md").write_text(
        "| Claude Code | `ToolSearch` | `providers/claude-code.md` |\n",
        encoding="utf-8",
    )
    (tmp_path / "agente" / "CLAUDE.md").write_text(
        "| agy | `call_mcp_tool` | `providers/agy.md` |\n"
        "Consulte `abertura/arranque.md`.\n",
        encoding="utf-8",
    )

    apts = verificar_arranque(tmp_path)
    assert apts == []


def test_repo_atual_passa_sem_primitiva_em_dono_md():
    apts = verificar_arranque(RAIZ, alvo="abertura/dono.md")
    assert apts == []  # DT 527
