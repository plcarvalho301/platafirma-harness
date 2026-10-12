"""claude_cli — onde mora o Claude Code que a casa chama (debito #2856 linha 248).

O CLI e dependencia como as outras: vem de uma trava no git (venvs/claude-code/package-lock.json),
construida pela release em <release>/venv/claude-code e trocada so por promocao. Antes disto
cada verbo pegava o `claude` do PATH ou de ~/.local/bin, instalado a mao, fora de trava e fora
do relatorio de dependencias; ficou velho sem ninguem ver (o alias haiku seguia no Haiku 4.5).

A trava prende o pacote do binario nativo (@anthropic-ai/claude-code-linux-x64), porque o
pacote de cima so monta o binario no postinstall e a casa nao roda script de pacote.

Ordem: PF_CLAUDE_BIN (teste com stub) e depois o ambiente da release. Sem fallback para o PATH:
um `claude` solto voltaria a ser a versao que ninguem prendeu. Ambiente ausente e falha alta.
"""
from __future__ import annotations

import os
import stat
from pathlib import Path

import raizes

PACOTE = ("@anthropic-ai", "claude-code-linux-x64")
NOMES = ("claude", "bin/claude", "claude.exe")


class ClaudeAusente(RuntimeError):
    """O ambiente claude-code da release nao tem o binario; quem chama sai 3."""


def ambiente() -> Path:
    return raizes.release() / "venv" / "claude-code"


def _executavel(p: Path) -> bool:
    try:
        m = p.stat().st_mode
    except OSError:
        return False
    return stat.S_ISREG(m) and bool(m & stat.S_IXUSR)


def resolver() -> str:
    """Caminho absoluto do binario. Levanta ClaudeAusente com o porque."""
    sob = os.environ.get("PF_CLAUDE_BIN", "").strip()
    if sob:
        return sob
    base = ambiente() / "node_modules" / PACOTE[0] / PACOTE[1]
    for nome in NOMES:
        if _executavel(base / nome):
            return str(base / nome)
    if base.is_dir():
        soltos = sorted(p for p in base.iterdir()
                        if p.suffix not in (".json", ".md") and _executavel(p))
        if soltos:
            return str(soltos[0])
    raise ClaudeAusente(
        f"claude ausente: nenhum binario executavel em {base} — o ambiente claude-code da "
        f"release nao foi construido (registro/venvs.json, release promover platafirma-harness)")


def ambiente_de_execucao(base: dict | None = None) -> dict:
    """Ambiente para o processo do CLI: o binario mora em arvore so leitura, entao o
    atualizador automatico fica desligado; versao nova so entra pela trava."""
    env = dict(os.environ if base is None else base)
    env["DISABLE_AUTOUPDATER"] = "1"
    return env
