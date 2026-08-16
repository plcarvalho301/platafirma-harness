#!/usr/bin/env python3
"""Frase da nota efemera de progresso — metadado do stream virando uma linha.

Mora em `comum/` porque e a unica peca do progresso que os DOIS lados tocam: o
worker produz o instantaneo, o receptor o pinta. Stdlib pura, pelo mesmo motivo
do journal — python 3.13 do container e 3.12 do systemd, um esquema so.

O que entra aqui e so metadado: relogio, contagem de passo e NOME de tool.
Texto do modelo, argumento de tool e retorno de tool nao atravessam esta porta.
"""

from __future__ import annotations

import json
import time


def frase(job) -> str:
    """`⏳ 4m12s · 23 passos · rag_search, edit_page`.

    O relogio responde 'travou ou esta trabalhando?'; a tool responde 'fazendo
    o que?'. Campo ausente nao vira zero — some da frase, porque numero
    inventado e pior que ausencia declarada.
    """
    corrido = max(0.0, time.time() - (job["iniciado_em"] or time.time()))
    minutos, segundos = divmod(int(corrido), 60)
    relogio = f"{minutos}m{segundos:02d}s" if minutos else f"{segundos}s"
    try:
        dados = json.loads(job["progresso"] or "{}")
    except (json.JSONDecodeError, TypeError):
        dados = {}
    pedacos = [f"⏳ {relogio}"]
    if dados.get("passos"):
        pedacos.append(f"{dados['passos']} passos")
    tools = [t for t in (dados.get("tools") or []) if isinstance(t, str)]
    if tools:
        # dict.fromkeys: repetida nao vira lista de repeticoes, e a ordem em que
        # aconteceu se preserva.
        pedacos.append(", ".join(dict.fromkeys(tools)))
    return " · ".join(pedacos)
