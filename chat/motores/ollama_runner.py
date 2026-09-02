#!/usr/bin/env python3
"""ollama_runner — o lado que RODA o modelo local e controla a sessao.

Invocado por MotorOllama.comando() como subprocess, dentro do um_giro de bin/chat.
Le o corpo do dono em stdin, fala com o ollama em /api/chat (stream), e emite no
stdout o mesmo stream-json que o Claude Code emite — para o um_giro nao distinguir
um motor do outro. Um passo por linha vai no proprio stream (o um_giro chama
motor.passo() sobre cada evento).

CONTRATO DE SAIDA (stdout, uma linha JSON por evento):
    {"type":"system","subtype":"init","session_id":"<id>"}   # abre, carrega id
    {"type":"assistant","message":{"content":[{"type":"text","text":"..."}]}}
    {"type":"result","subtype":"success","result":"<texto final>","session_id":"<id>",
     "usage":{"prompt_eval_count":N,"eval_count":M}}
stderr: diagnostico de invocacao (modelo inexistente, ollama fora do ar).

SESSAO: o ollama nao guarda historico. Este runner guarda em
~/AI/fitas/ollama/<session_id>.json (lista de mensagens role/content) e o remonta
a cada giro. Fita nova cunha id e grava so o system (persona) + a 1a msg. Fita
existente (--resume) recarrega o historico e anexa. E o "controla a sessao" (c).

PERSONA (d): --sistema recebe o pacote de monta-sessao e vira a mensagem system
da conversa. Mesma persona das cadeiras; muda so o cerebro (qwen) e o alcance.
"""
import argparse
import json
import os
import sys
import urllib.request
import uuid
from datetime import datetime, timezone

RAIZ = os.environ.get("PF_RAIZ", os.path.expanduser("~/AI"))
HIST_DIR = os.path.join(RAIZ, "fitas", "ollama")
# Teto de historico remontado: alem disso, corta as mais antigas (mantendo o
# system) e declara compactou=True no result. Modelo local tem janela menor.
MAX_MSGS = int(os.environ.get("PF_OLLAMA_MAX_MSGS", "40"))


def emite(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def hist_path(sid):
    return os.path.join(HIST_DIR, f"{sid}.json")


def carrega_hist(sid):
    try:
        with open(hist_path(sid), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def grava_hist(sid, msgs):
    os.makedirs(HIST_DIR, exist_ok=True)
    tmp = hist_path(sid) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(msgs, f, ensure_ascii=False)
    os.replace(tmp, hist_path(sid))


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True)
    ap.add_argument("--base-url", default="http://localhost:11434")
    ap.add_argument("--cwd", default=".")
    ap.add_argument("--resume", default="")
    ap.add_argument("--session-id", default="")
    ap.add_argument("--sistema", default="")   # pacote de persona (fita nova)
    args = ap.parse_args(argv)

    sid = args.resume or args.session_id or str(uuid.uuid4())
    corpo = sys.stdin.read()

    # (c) monta a sessao: carrega historico da fita ou abre nova com a persona.
    msgs = carrega_hist(sid) if args.resume else []
    if not msgs and args.sistema:
        msgs.append({"role": "system", "content": args.sistema})
    msgs.append({"role": "user", "content": corpo})

    # corte de janela (compactacao propria do modelo local)
    compactou = False
    if len(msgs) > MAX_MSGS:
        cabeca = [m for m in msgs[:1] if m["role"] == "system"]
        msgs = cabeca + msgs[-(MAX_MSGS - len(cabeca)):]
        compactou = True

    emite({"type": "system", "subtype": "init", "session_id": sid})

    # (b) RODA o modelo local: /api/chat com stream de tokens.
    payload = {"model": args.modelo, "messages": msgs, "stream": True}
    req = urllib.request.Request(
        f"{args.base_url}/api/chat",
        data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})

    texto = ""
    prompt_n = eval_n = 0
    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            for linha in resp:
                linha = linha.strip()
                if not linha:
                    continue
                ev = json.loads(linha)
                pedaco = (ev.get("message") or {}).get("content") or ""
                if pedaco:
                    texto += pedaco
                    # passo de progresso: conteudo NAO vai (contrato); so o fato
                    # de que houve texto assistente. O um_giro chama passo() disto.
                    emite({"type": "assistant",
                           "message": {"content": [{"type": "text", "text": pedaco}]}})
                if ev.get("done"):
                    prompt_n = ev.get("prompt_eval_count") or 0
                    eval_n = ev.get("eval_count") or 0
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"ollama runner falhou: {e!r}\n")
        emite({"type": "result", "subtype": "error", "is_error": True,
               "result": "", "session_id": sid})
        return 0  # contrato: exit 0 sempre que houver JSON valido em stdout

    # (c) fecha a sessao: grava historico com a resposta, para o proximo giro.
    msgs.append({"role": "assistant", "content": texto})
    grava_hist(sid, msgs)

    emite({"type": "result", "subtype": "success", "is_error": False,
           "result": texto, "session_id": sid, "compactou": compactou,
           "usage": {"prompt_eval_count": prompt_n, "eval_count": eval_n}})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
