#!/usr/bin/env python3
# porta-sessao — a fita do Claude Code PORTA o sessao_id em toda chamada (arq:0101 §1, spec do dono).
# capacidade: porte-de-sessao-no-cliente
# dono: claudinho-TI
#
# O problema medido (card 3007, 06/09): a cadeira em Code recebe o `sessao_id` no
# retorno do `monta_sessao` e NAO o repassa nas chamadas seguintes (0/190). A porta
# nao infere mais (85ece31), entao sem porte a fita roda sem sessao. Este hook faz o
# porte ser MECANICO, no cliente, independe do agente lembrar — que e a spec:
# `monta_sessao` cunha -> Valkey -> a fita porta o id.
#
# Dois eventos, um script:
#  - PostToolUse em monta_sessao: extrai o sessao_id do RETORNO e grava por fita do Code.
#  - PreToolUse nas tools do claudinho-mcp: se a chamada nao traz sessao_id, injeta o
#    gravado via `updatedInput` (nunca sobrescreve um id que o agente ja pos).
import json, sys, re, os
from pathlib import Path

DIR = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "pf-sessao-code"
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

def arquivo(sid_code: str) -> Path:
    seguro = re.sub(r"[^0-9a-zA-Z_-]", "_", sid_code or "sem")
    return DIR / f"{seguro}.sid"

def le(sid_code):
    try:
        return arquivo(sid_code).read_text().strip() or None
    except Exception:
        return None

def grava(sid_code, sessao_id):
    try:
        DIR.mkdir(parents=True, exist_ok=True)
        arquivo(sid_code).write_text(sessao_id)
    except Exception as e:
        print(f"[porta-sessao] grava falhou: {e!r}", file=sys.stderr)

def main():
    try:
        ev = json.load(sys.stdin)
    except Exception:
        sys.exit(0)                        # entrada ma: nao atrapalha a fita
    evento = ev.get("hook_event_name") or ev.get("hookEventName") or ""
    tool = ev.get("tool_name") or ev.get("toolName") or ""
    sid_code = ev.get("session_id") or ev.get("sessionId") or "sem"
    if not (tool.endswith("run_command") or tool.endswith("read_file") or
            tool.endswith("write_file") or tool.endswith("mesa") or tool.endswith("fila") or
            tool.endswith("tarefas") or tool.endswith("motor") or tool.endswith("descansar") or
            tool.endswith("monta_sessao") or ("claudinho-mcp" in tool)):
        sys.exit(0)

    if evento == "PostToolUse" and tool.endswith("monta_sessao"):
        resp = ev.get("tool_response") or ev.get("toolResponse") or ""
        texto = resp if isinstance(resp, str) else json.dumps(resp, ensure_ascii=False)
        m = re.search(r'"sessao_id"\s*:\s*"(' + UUID.pattern + r')"', texto) or UUID.search(texto)
        if m:
            grava(sid_code, m.group(1) if m.lastindex else m.group(0))
        sys.exit(0)

    if evento == "PreToolUse":
        ti = ev.get("tool_input") or ev.get("toolInput") or {}
        if not isinstance(ti, dict):
            sys.exit(0)
        if ti.get("sessao_id"):
            sys.exit(0)                    # o agente ja portou — respeita
        if tool.endswith("monta_sessao"):
            sys.exit(0)                    # abertura: quem cunha e o verbo
        sid = le(sid_code)
        if not sid:
            sys.exit(0)                    # nada gravado ainda — roda sem sessao (contado)
        novo = dict(ti); novo["sessao_id"] = sid
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse", "updatedInput": novo}}))
        sys.exit(0)
    sys.exit(0)

if __name__ == "__main__":
    main()
