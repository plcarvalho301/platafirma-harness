"""transcript — o uso de tokens lido do transcript que o Claude Code grava em ~/.claude/projects/.

Uma régua só para fita e agente (dono, 16/10/2026: «a decisão está tomada: é o transcript»).
O transcript guarda o `usage` que a API devolveu em cada chamada ao modelo; cada `requestId`
conta uma vez, pelo último `usage` que trouxe (o Code repete a linha da resposta a cada bloco).
Nada se estima: sem transcript, quem chama diz a falta.

Quem usa: `descansar` (fecho da fita, pela pasta de fitas da cadeira) e `agente rodar` (pelo
id da sessão que o `claude -p` devolve).
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

CAMPOS = (("entrada", "input_tokens"), ("saida", "output_tokens"),
          ("cache_criacao", "cache_creation_input_tokens"),
          ("cache_leitura", "cache_read_input_tokens"))


def base() -> Path:
    return Path(os.path.expanduser("~/.claude/projects"))


def por_pedido(caminho) -> dict | None:
    """{requestId: usage} do transcript, o último usage de cada pedido. None se não lê."""
    pedidos: dict = {}
    try:
        with open(caminho, encoding="utf-8", errors="replace") as fh:
            for linha in fh:
                try:
                    d = json.loads(linha)
                except ValueError:
                    continue
                uso = (d.get("message") or {}).get("usage") if isinstance(d, dict) else None
                if isinstance(uso, dict) and d.get("requestId"):
                    pedidos[d["requestId"]] = uso
    except OSError:
        return None
    return pedidos


def soma(caminho) -> dict | None:
    """{entrada, saida, cache_criacao, cache_leitura} somados por pedido, ou None (sem arquivo
    ou sem pedido com usage). `entrada` aqui é a entrada nova (input_tokens), como no fecho."""
    pedidos = por_pedido(caminho)
    if not pedidos:
        return None
    total = {chave: 0 for chave, _ in CAMPOS}
    for uso in pedidos.values():
        for chave, campo in CAMPOS:
            valor = uso.get(campo)
            if isinstance(valor, int):
                total[chave] += valor
    return total


def da_sessao(sessao_code: str, raiz: Path | None = None) -> Path | None:
    """O transcript da sessão do Code pelo id, em qualquer pasta de projeto. None se não achou."""
    if not sessao_code or "/" in sessao_code or sessao_code.startswith("."):
        return None
    achados = glob.glob(str((raiz or base()) / "*" / f"{sessao_code}.jsonl"))
    return Path(max(achados, key=os.path.getmtime)) if achados else None


def da_cadeira(cadeira: str, raiz: Path | None = None) -> Path | None:
    """O transcript mais recente da pasta de fitas da cadeira (*fitas-<cadeira>). None se não há."""
    alvo = (cadeira or "").lower()
    if not alvo:
        return None
    dirs = [d for d in glob.glob(str((raiz or base()) / "*fitas-*")) if d.lower().endswith("fitas-" + alvo)]
    arqs = [a for d in dirs for a in glob.glob(os.path.join(d, "*.jsonl"))]
    return Path(max(arqs, key=os.path.getmtime)) if arqs else None
