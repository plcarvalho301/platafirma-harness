"""Contrato de lib/claude_cli.py (debito #2856 linha 248): o Claude Code que a casa chama
vem do ambiente claude-code da release, nunca do PATH; ambiente ausente e falha alta;
PF_CLAUDE_BIN so para teste; o processo do CLI roda com o atualizador desligado.
Tambem confere que a trava existe e esta declarada no registro de venvs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "lib"))

import claude_cli  # noqa: E402

PKG = ("node_modules", "@anthropic-ai", "claude-code-linux-x64")


def _release(tmp_path: Path, monkeypatch) -> Path:
    rel = tmp_path / "current"
    monkeypatch.setenv("PLATAFIRMA_RELEASE", str(rel))
    monkeypatch.delenv("PF_CLAUDE_BIN", raising=False)
    return rel


def _binario(base: Path, nome: str, modo: int = 0o755) -> Path:
    base.mkdir(parents=True, exist_ok=True)
    p = base / nome
    p.write_bytes(b"\x7fELF fixture")
    p.chmod(modo)
    return p


def test_acha_o_binario_da_release(tmp_path, monkeypatch):
    rel = _release(tmp_path, monkeypatch)
    p = _binario(rel.joinpath("venv", "claude-code", *PKG), "claude")
    assert claude_cli.resolver() == str(p)


def test_nome_desconhecido_cai_no_unico_executavel(tmp_path, monkeypatch):
    rel = _release(tmp_path, monkeypatch)
    base = rel.joinpath("venv", "claude-code", *PKG)
    _binario(base, "package.json", 0o644)
    p = _binario(base, "cc-nativo")
    assert claude_cli.resolver() == str(p)


def test_sem_ambiente_falha_alto_e_nao_usa_o_path(tmp_path, monkeypatch):
    _release(tmp_path, monkeypatch)
    falso = _binario(tmp_path / "bin-solto", "claude")
    monkeypatch.setenv("PATH", str(falso.parent))
    with pytest.raises(claude_cli.ClaudeAusente) as e:
        claude_cli.resolver()
    assert "venv/claude-code" in str(e.value)


def test_binario_sem_bit_de_execucao_nao_serve(tmp_path, monkeypatch):
    rel = _release(tmp_path, monkeypatch)
    _binario(rel.joinpath("venv", "claude-code", *PKG), "claude", 0o644)
    with pytest.raises(claude_cli.ClaudeAusente):
        claude_cli.resolver()


def test_override_de_teste_vence(tmp_path, monkeypatch):
    _release(tmp_path, monkeypatch)
    monkeypatch.setenv("PF_CLAUDE_BIN", "/stub/claude")
    assert claude_cli.resolver() == "/stub/claude"


def test_atualizador_desligado():
    assert claude_cli.ambiente_de_execucao({"X": "1"}) == {"X": "1", "DISABLE_AUTOUPDATER": "1"}


def test_trava_declarada_e_presa():
    reg = json.loads((REPO_ROOT / "registro" / "venvs.json").read_text(encoding="utf-8"))
    assert reg["claude-code"] == {"familia": "platafirma-harness",
                                  "lock": "venvs/claude-code/package-lock.json"}
    pkg = json.loads((REPO_ROOT / "venvs" / "claude-code" / "package.json").read_text(encoding="utf-8"))
    versao = pkg["dependencies"]["@anthropic-ai/claude-code-linux-x64"]
    assert versao[0].isdigit(), "versao exata, sem faixa: a trava prende"
    lock = json.loads((REPO_ROOT / "venvs" / "claude-code" / "package-lock.json").read_text(encoding="utf-8"))
    assert lock["packages"]["node_modules/@anthropic-ai/claude-code-linux-x64"]["version"] == versao
