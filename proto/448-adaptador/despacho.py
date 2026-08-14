#!/usr/bin/env python3
"""Prototipo do adaptador Claude Code headless para a superficie de conversa.

NAO E O VERBO `chat`. E a prova de mecanismo do card 448, feita fora da stack
enquanto a fabrica constroi o card 447. Interface desenhada para o lado de
claudinho-IA plugar comportamento de fita sem tocar transporte.

Provado por execucao em 14/08/2026, Claude Code 2.1.220:
- `--session-id <uuid>` deixa o CHAMADOR escolher o id da sessao.
- `-r <uuid>` retoma; sessao inexistente sai com "No conversation found".
- `--output-format stream-json --verbose` da evento por linha, com `usage` e
  `rate_limit_event` no meio.
"""
from __future__ import annotations

import json
import subprocess
import uuid

NS_SALA = uuid.UUID("6f2b1c4e-0000-4000-8000-505461466972")
TETO_LINHA = 3800  # folga sob o teto util de evento Matrix (65536 bytes)


def id_da_fita(room_id: str) -> str:
    """A sala E a fita: o session-id deriva do room_id, sem estado a guardar.

    Rotacao de sala (card 449) troca o room_id, logo troca a fita — de graca.
    """
    return str(uuid.uuid5(NS_SALA, room_id))


def _comando(sid: str, texto: str, retomar: bool, cwd: str) -> list[str]:
    base = ["claude", "-p", "--output-format", "stream-json", "--verbose",
            "--permission-mode", "dontAsk"]
    base += ["-r", sid] if retomar else ["--session-id", sid]
    return base + [texto]


def despacha(room_id: str, texto: str, cwd: str, retomar: bool = True):
    """Roda um giro e devolve eventos normalizados.

    Devolve dicts de tres formas, e so estas chegam a sala:
      {"tipo": "texto",  "texto": str}   -> fatia publicavel
      {"tipo": "fim",    "custo_usd": float, "tokens": int, "erro": bool}
      {"tipo": "limite", "reseta_em": int} -> rate limit da assinatura

    Raciocinio, tool_use e tool_result sao DESCARTADOS aqui: e o criterio
    "sem raciocinio intermediario na sala", implementado no transporte.
    """
    sid = id_da_fita(room_id)
    proc = subprocess.run(_comando(sid, texto, retomar, cwd), cwd=cwd,
                          capture_output=True, text=True, timeout=600)

    if retomar and "No conversation found" in (proc.stdout + proc.stderr):
        # Fita morta (retencao do Code, /clear, host novo): abre uma e segue.
        yield from despacha(room_id, texto, cwd, retomar=False)
        return

    for linha in proc.stdout.splitlines():
        try:
            ev = json.loads(linha)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if t == "assistant":
            for bloco in ev.get("message", {}).get("content", []):
                if bloco.get("type") == "text":
                    for fatia in fatia_por_linha(bloco["text"]):
                        yield {"tipo": "texto", "texto": fatia}
        elif t == "rate_limit_event":
            info = ev.get("rate_limit_info", {})
            if info.get("status") != "allowed":
                yield {"tipo": "limite", "reseta_em": info.get("resetsAt")}
        elif t == "result":
            u = ev.get("usage", {})
            yield {"tipo": "fim", "erro": bool(ev.get("is_error")),
                   "custo_usd": ev.get("total_cost_usd"),
                   "tokens": u.get("output_tokens")}


def fatia_por_linha(texto: str) -> list[str]:
    """Fatia em mensagens, sem quebrar bloco de codigo (criterio de bloco atomico).

    Bloco ``` sai inteiro numa mensagem so, ainda que estoure o teto de linha —
    quebrar cerca de codigo destroi a renderizacao no cliente.
    """
    partes, buffer, dentro = [], [], False
    for linha in texto.splitlines():
        if linha.lstrip().startswith("```"):
            if dentro:
                buffer.append(linha)
                partes.append("\n".join(buffer))
                buffer, dentro = [], False
                continue
            if buffer:
                partes.append("\n".join(buffer))
            buffer, dentro = [linha], True
            continue
        buffer.append(linha)
        if not dentro and sum(len(x) + 1 for x in buffer) > TETO_LINHA:
            partes.append("\n".join(buffer))
            buffer = []
    if buffer:
        partes.append("\n".join(buffer))
    return [p for p in (x.strip() for x in partes) if p]
