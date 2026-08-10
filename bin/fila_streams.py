#!/home/claudinho/AI/.venv-harness/bin/python
# fila — caixa de mensagens entre personas da PlataFirma, sobre a malha msg (Valkey/Streams).
# capacidade: msg
# dono: claudinho-IA
#
# Substrato: componente msg do motor (arq:0018, arq:0036) — Valkey sobre Streams.
# Stream por caixa: "caixa:<persona>" (nomenclatura de arq:0036).
# Envelope inalterado: de/para/em/tipo/assunto/ref/responde + corpo auto-contido.
#
# POSSE (Frente:harness/posse-de-mensagem): o token nasce na LEITURA, não na sessão —
# identidade de sessão estável não existe (medido, ver ops-server/server.py:107,518).
# Chave posse:<caixa>:<msgid>, SET NX EX, TTL 60min (arq:0024). `consumir` e
# `enviar --responde` exigem o token; `ler` marca posse viva em vez de esconder.
#
# DESVIO DECLARADO do desenho original: não uso consumer group / XACK / XPENDING /
# XAUTOCLAIM. `ler` é XRANGE do stream inteiro (mailbox completa, sempre idempotente,
# igual ao comportamento do fila em arquivo); `consumir` é XDEL após validar o token de
# posse. A recuperação por sessão morta não precisa de XAUTOCLAIM: a mensagem nunca sai
# do stream até ser consumida, e a chave de posse expira sozinha pelo TTL — o efeito é o
# mesmo (mensagem redisponível), com menos peças. Concordo revisar para consumer group
# se claudinho-TI achar o motivo insuficiente.
import argparse
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

try:
    import redis
except ImportError:
    sys.exit("erro: modulo 'redis' nao instalado neste venv (uv pip install redis)")

RAIZ = os.environ.get("FILA_RAIZ", os.path.expanduser("~/AI/fila"))
PERSONAS_FILE = os.path.join(RAIZ, ".personas")
ESPIA = "claudinha-gestao-estrategica"
TTL_POSSE = 60 * 60  # 60 min — arq:0024
TIPOS_VALIDOS = {"decisao", "resposta", "pedido", "minuta", "demanda", "handoff"}

REDIS_HOST = os.environ.get("FILA_REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("FILA_REDIS_PORT", "6379"))


def r_conn():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def stream_key(persona: str) -> str:
    return f"caixa:{persona}"


def posse_key(persona: str, msgid: str) -> str:
    return f"posse:{persona}:{msgid}"


def personas_validas():
    if not os.path.isfile(PERSONAS_FILE):
        return None  # sem lista == nao valida (mesmo comportamento do bash original)
    with open(PERSONAS_FILE) as f:
        return {ln.strip() for ln in f if ln.strip()}


def valida_persona(p: str):
    validas = personas_validas()
    if validas is None:
        return
    if p in validas:
        return
    enc = os.path.join(RAIZ, ".encerradas", f"{p}.md")
    if os.path.isfile(enc):
        with open(enc) as f:
            corpo = f.read()
        sys.stderr.write(f'erro: caixa "{p}" esta encerrada.\n\n{corpo}')
        sys.exit(1)
    sys.stderr.write(
        f'erro: persona "{p}" nao esta em {PERSONAS_FILE} — caixa fantasma nao e lida por ninguem\n'
    )
    sys.exit(1)


def resolve_eu(args) -> str:
    c = args.eu or os.environ.get("PF_EU") or os.environ.get("PF_CADEIRA")
    if not c:
        sys.stderr.write(
            "erro: nao sei quem esta operando a fila.\n"
            "  exporte PF_CADEIRA=<cadeira> (ex.: PF_CADEIRA=IA) ou passe --eu <persona>.\n"
            "  sem isso a fila nao abre caixa nenhuma.\n"
        )
        sys.exit(1)
    validas = personas_validas()
    if validas is None:
        return c
    if c in validas:
        return c
    for cand in (f"claudinho-{c}", f"claudinha-{c}"):
        if cand in validas:
            return cand
    sys.stderr.write(f'erro: identidade "{c}" nao esta em {PERSONAS_FILE}\n')
    sys.exit(1)


def so_minha(eu: str, alvo: str):
    if alvo == eu or eu == ESPIA:
        return
    sys.stderr.write(
        f'erro: a caixa de "{alvo}" nao e tua (voce e {eu}) — nao le, nao consome.\n'
        f'para falar com ela: fila enviar {alvo} --tipo <t> --assunto <a>\n'
    )
    sys.exit(1)


def so_espia(eu: str):
    if eu == ESPIA:
        return
    sys.stderr.write(f'erro: --todas e so da {ESPIA} (voce e {eu}).\n')
    sys.exit(1)


def gerar_msgid(de: str, existentes) -> str:
    agora = datetime.now(timezone.utc).astimezone()
    seg = 0
    while True:
        candidato = (agora + timedelta(seconds=seg)).strftime("%Y%m%dT%H%M%S") + f"-{de}"
        if candidato not in existentes:
            return candidato
        seg += 1


def idade_fmt(segundos: float) -> str:
    segundos = int(segundos)
    if segundos < 60:
        return f"{segundos}s"
    m, s = divmod(segundos, 60)
    if m < 60:
        return f"{m}min{s}s" if s else f"{m}min"
    h, m = divmod(m, 60)
    return f"{h}h{m}min"


def ler_stream(rc, persona: str):
    """Devolve lista de dicts {msgid, tecnico, tipo, assunto, ref, responde, corpo}
    na ordem em que estao no stream (mais antiga primeiro)."""
    entradas = rc.xrange(stream_key(persona), min="-", max="+")
    out = []
    for tecnico, campos in entradas:
        out.append({
            "tecnico": tecnico,
            "msgid": campos.get("id", tecnico),
            "de": campos.get("de", ""),
            "tipo": campos.get("tipo", ""),
            "assunto": campos.get("assunto", ""),
            "ref": campos.get("ref", ""),
            "responde": campos.get("responde", ""),
            "corpo": campos.get("corpo", ""),
        })
    return out


# ---------- status ----------
def cmd_status(rc, eu: str, args):
    alvo = args.persona
    if alvo == "--todas":
        so_espia(eu)
        validas = personas_validas() or set()
        personas = sorted(validas)
    else:
        valida_persona(alvo)
        so_minha(eu, alvo)
        personas = [alvo]

    vazio = True
    for p in personas:
        msgs = ler_stream(rc, p)
        if not msgs:
            continue
        vazio = False
        por = {}
        for m in msgs:
            por[m["de"]] = por.get(m["de"], 0) + 1
        por_txt = ", ".join(f"{de} {n}" for de, n in por.items())
        mais_antiga = msgs[0]["msgid"]
        print(f"{p}: {len(msgs)} ({por_txt}) · mais antiga {mais_antiga}")
    if vazio:
        print("caixa vazia")


# ---------- ler ----------
def cmd_ler(rc, eu: str, args):
    alvo = args.persona
    remet = args.remetente
    if alvo == "--todas":
        so_espia(eu)
        validas = personas_validas() or set()
        personas = sorted(validas)
    else:
        valida_persona(alvo)
        so_minha(eu, alvo)
        personas = [alvo]

    vazio = True
    for p in personas:
        msgs = ler_stream(rc, p)
        if remet:
            msgs = [m for m in msgs if m["de"] == remet]
        if not msgs:
            continue
        vazio = False
        if alvo == "--todas":
            print(f"## caixa: {p}\n")
        # mais nova primeiro, igual ao comportamento antigo
        for m in reversed(msgs):
            pk = posse_key(p, m["msgid"])
            token = secrets.token_hex(8)
            obtida = rc.set(pk, token, nx=True, ex=TTL_POSSE)
            print(f"===MSG {m['msgid']}===")
            print(f"tipo: {m['tipo']}")
            print(f"assunto: {m['assunto']}")
            if m["ref"]:
                print(f"ref: {m['ref']}")
            if m["responde"]:
                print(f"responde: {m['responde']}")
            if obtida:
                print(f"posse: {token} (livre — TTL {TTL_POSSE // 60}min)")
            else:
                ttl_restante = rc.ttl(pk)
                idade = TTL_POSSE - ttl_restante if ttl_restante and ttl_restante > 0 else 0
                print(f"posse: VIVA ha {idade_fmt(idade)} — sem token novo, nao consome nem responde")
            print()
            print(m["corpo"])
            print()
    if vazio:
        print("nada a ler")


# ---------- consumir ----------
def cmd_consumir(rc, eu: str, args):
    p = args.persona
    valida_persona(p)
    so_minha(eu, p)
    msgs = ler_stream(rc, p)
    if not msgs:
        print("caixa vazia")
        return

    if args.todas:
        alvo_ids = {m["msgid"] for m in msgs}
    elif args.de:
        alvo_ids = {m["msgid"] for m in msgs if m["de"] == args.de}
    else:
        if not args.ids:
            sys.stderr.write("erro: informe id(s), --de <remetente> ou --todas\n")
            sys.exit(2)
        alvo_ids = set(args.ids)

    por_msgid = {m["msgid"]: m for m in msgs}

    removidos = 0
    recusados = []
    for msgid in alvo_ids:
        m = por_msgid.get(msgid)
        if not m:
            recusados.append((msgid, "nao encontrada"))
            continue
        pk = posse_key(p, msgid)
        token_atual = rc.get(pk)
        precisa_posse = not (args.todas or args.de)  # id explicito exige --posse
        if precisa_posse:
            if not args.posse or token_atual != args.posse:
                recusados.append((msgid, "posse ausente, errada ou expirada"))
                continue
        # consumo em lote (--todas/--de) sem token: permitido por decisao operacional
        # (mesmo comportamento do fila antigo); id explicito sempre exige token.
        rc.xdel(stream_key(p), m["tecnico"])
        if token_atual is not None:
            rc.delete(pk)
        removidos += 1

    restam = len(ler_stream(rc, p))
    print(f"consumidas {removidos}, restam {restam}")
    for msgid, motivo in recusados:
        sys.stderr.write(f"recusado {msgid}: {motivo}\n")
    if recusados:
        sys.exit(1)


# ---------- largar ----------
def cmd_largar(rc, eu: str, args):
    p = args.persona
    valida_persona(p)
    so_minha(eu, p)
    pk = posse_key(p, args.msgid)
    token_atual = rc.get(pk)
    if token_atual is None:
        print(f"{args.msgid}: sem posse viva (ja livre)")
        return
    if token_atual != args.posse:
        if not args.forca:
            sys.stderr.write(
                f"erro: token nao bate com a posse viva de {args.msgid}.\n"
                f"  perdeu o token da propria leitura: 'fila largar {p} {args.msgid} --forca'\n"
            )
            sys.exit(1)
        sys.stderr.write(f"aviso: posse de {args.msgid} liberada A FORCA — outra sessao pode estar com ela\n")
    rc.delete(pk)
    print(f"{args.msgid}: posse liberada")


# ---------- enviar ----------
def cmd_enviar(rc, eu: str, args):
    de = args.de or eu
    if de != eu:
        sys.stderr.write(
            f'erro: --de "{de}" nao bate com a identidade da sessao ({eu}) — remetente nao se forja.\n'
        )
        sys.exit(1)
    if not args.tipo or not args.assunto:
        sys.stderr.write("erro: --tipo e --assunto sao obrigatorios\n")
        sys.exit(2)
    if args.tipo not in TIPOS_VALIDOS:
        sys.stderr.write(f"erro: tipo invalido: {args.tipo}\n")
        sys.exit(1)
    valida_persona(args.destinatario)
    valida_persona(de)

    if args.responde:
        # --responde referencia mensagem na CAIXA de quem estamos respondendo a partir
        # da nossa leitura — a posse foi tirada quando 'eu' (de) leu a PROPRIA caixa.
        pk = posse_key(de, args.responde)
        token_atual = rc.get(pk)
        if not args.posse or token_atual != args.posse:
            sys.stderr.write(
                f"erro: responder a {args.responde} exige --posse valida "
                f"(tirada em 'fila ler {de}') — recusado.\n"
            )
            sys.exit(1)

    corpo = sys.stdin.read()
    if not corpo.strip():
        sys.stderr.write("erro: corpo vazio\n")
        sys.exit(1)

    stream = stream_key(args.destinatario)
    existentes = {m["msgid"] for m in ler_stream(rc, args.destinatario)}
    msgid = gerar_msgid(de, existentes)
    campos = {
        "id": msgid,
        "de": de,
        "tipo": args.tipo,
        "assunto": args.assunto,
        "ref": args.ref or "",
        "responde": args.responde or "",
        "corpo": corpo,
    }
    rc.xadd(stream, campos)
    print(msgid)


def build_parser():
    ap = argparse.ArgumentParser(prog="fila", add_help=False)
    ap.add_argument("--eu", default=None)
    sub = ap.add_subparsers(dest="verbo")

    p_status = sub.add_parser("status", add_help=False)
    p_status.add_argument("persona")

    p_ler = sub.add_parser("ler", add_help=False)
    p_ler.add_argument("persona")
    p_ler.add_argument("remetente", nargs="?", default=None)

    p_consumir = sub.add_parser("consumir", add_help=False)
    p_consumir.add_argument("persona")
    p_consumir.add_argument("ids", nargs="*")
    p_consumir.add_argument("--de", default=None)
    p_consumir.add_argument("--todas", action="store_true")
    p_consumir.add_argument("--posse", default=None)

    p_largar = sub.add_parser("largar", add_help=False)
    p_largar.add_argument("persona")
    p_largar.add_argument("msgid")
    p_largar.add_argument("--posse", default=None)
    p_largar.add_argument("--forca", action="store_true")

    p_enviar = sub.add_parser("enviar", add_help=False)
    p_enviar.add_argument("destinatario")
    p_enviar.add_argument("--de", default=None)
    p_enviar.add_argument("--tipo", default=None)
    p_enviar.add_argument("--assunto", default=None)
    p_enviar.add_argument("--ref", default=None)
    p_enviar.add_argument("--responde", default=None)
    p_enviar.add_argument("--posse", default=None)

    return ap


def uso():
    sys.stderr.write(
        "uso:\n"
        "  fila status <persona> | --todas\n"
        "  fila ler <persona> [remetente] | --todas [remetente]\n"
        "  fila consumir <persona> <id> --posse <token>\n"
        "  fila consumir <persona> --de <remetente> | --todas\n"
        "  fila largar <persona> <id> --posse <token>\n"
        "  fila enviar <destinatario> --tipo <t> --assunto <a> [--ref <r>]\n"
        "              [--responde <id> --posse <token>]   (corpo em stdin)\n"
    )
    sys.exit(2)


def main():
    ap = build_parser()
    args, resto = ap.parse_known_args()
    if not args.verbo:
        uso()
    eu = resolve_eu(args)
    rc = r_conn()
    try:
        rc.ping()
    except redis.exceptions.RedisError as e:
        sys.stderr.write(f"erro: nao alcancei a malha msg ({REDIS_HOST}:{REDIS_PORT}): {e}\n")
        sys.exit(1)

    if args.verbo == "status":
        cmd_status(rc, eu, args)
    elif args.verbo == "ler":
        cmd_ler(rc, eu, args)
    elif args.verbo == "consumir":
        cmd_consumir(rc, eu, args)
    elif args.verbo == "largar":
        cmd_largar(rc, eu, args)
    elif args.verbo == "enviar":
        cmd_enviar(rc, eu, args)
    else:
        uso()


if __name__ == "__main__":
    main()
