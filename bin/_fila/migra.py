#!/usr/bin/env python3
# _fila-migra — transporta as caixas em arquivo para os streams da malha msg.
# capacidade: msg
# dono: claudinho-IA
#
# Ato unico da passagem (arq:0018, arq:0036). Nao e verbo do PATH: roda uma vez,
# na troca de transporte, e depois vira historia. Sem --apply so mede e imprime.
#
# O id tecnico do stream vem do TIMESTAMP DA MENSAGEM, nao do relogio da migracao:
# XADD com id automatico faria carta de tres dias nascer com idade zero, e o trim
# por MINID conta idade pelo id. Colisao de ms resolve por sequencia.
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import redis
except ImportError:
    sys.exit("erro: modulo 'redis' nao instalado neste venv (uv pip install redis)")

RAIZ = os.environ.get("FILA_RAIZ", os.path.expanduser("~/AI/fila"))
HOST = os.environ.get("FILA_REDIS_HOST", "127.0.0.1")
PORT = int(os.environ.get("FILA_REDIS_PORT", "6379"))
CABECALHOS = ("tipo", "assunto", "ref", "responde")


def parse(caminho):
    """Devolve [{id, de, tipo, assunto, ref, responde, corpo}] do arquivo de caixa."""
    with open(caminho) as f:
        linhas = f.read().split("\n")
    msgs, atual = [], None
    for ln in linhas:
        if ln.startswith("===MSG ") and ln.rstrip().endswith("==="):
            if atual:
                msgs.append(atual)
            msgid = ln[len("===MSG "):].rstrip()[:-3]
            de = msgid.split("-", 1)[1] if "-" in msgid else ""
            atual = {"id": msgid, "de": de, "tipo": "", "assunto": "",
                     "ref": "", "responde": "", "corpo": ""}
            continue
        if atual is None:
            continue
        chave = ln.split(":", 1)[0] if ":" in ln else None
        if chave in CABECALHOS and not atual["corpo"]:
            atual[chave] = ln.split(":", 1)[1].strip()
        else:
            atual["corpo"] += ln + "\n"
    if atual:
        msgs.append(atual)
    for m in msgs:
        m["corpo"] = m["corpo"].strip("\n") + "\n"
    return msgs


def id_tecnico(msgid, usados):
    """<ms do timestamp da mensagem>-<seq>, unico dentro do stream."""
    carimbo = msgid.split("-", 1)[0]
    ms = int(datetime.strptime(carimbo, "%Y%m%dT%H%M%S").timestamp() * 1000)
    seq = 0
    while (ms, seq) in usados:
        seq += 1
    usados.add((ms, seq))
    return f"{ms}-{seq}"


def main():
    aplicar = "--apply" in sys.argv
    rc = redis.Redis(host=HOST, port=PORT, decode_responses=True)
    total = 0
    for arq in sorted(os.listdir(RAIZ)):
        if not arq.endswith(".md"):
            continue
        persona = arq[:-3]
        stream = f"caixa:{persona}"
        msgs = parse(os.path.join(RAIZ, arq))
        vivas = {c.get("id") for _, c in rc.xrange(stream, "-", "+")}
        novas = [m for m in msgs if m["id"] not in vivas]
        usados = set()
        for m in novas:
            tecnico = id_tecnico(m["id"], usados)
            if aplicar:
                rc.xadd(stream, m, id=tecnico)
        total += len(novas)
        print(f"{stream:40} arquivo={len(msgs):<4} ja_no_stream={len(vivas):<4} migradas={len(novas)}")
    print(f"\ntotal: {total}" + ("" if aplicar else "  (sem --apply: nada foi escrito)"))


if __name__ == "__main__":
    main()
