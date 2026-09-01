#!/home/claudinho/AI/.venv-harness/bin/python
# fila — caixa de mensagens entre personas da PlataFirma, sobre a malha msg (Valkey/Streams).
# capacidade: mensagem
# dono: ia
#
# Substrato: componente msg do motor (arq:0018, arq:0036). Stream por caixa,
# "caixa:<persona>", com consumer group unico "cadeira" — a cadeira dona e o unico
# consumidor. Envelope inalterado: de/tipo/assunto/ref/responde + corpo auto-contido.
#
# LEITURA E PONTEIRO (decisao do dono, 09/08/2026)
# `ler` e XREADGROUP ">" seguido de XACK na entrega: confirma ao entregar, como o
# auto-commit do Kafka. O ponteiro (last-delivered-id) vive no grupo, dentro do
# servidor — a sessao nao carrega estado nenhum entre fitas, so o proprio nome.
# Nada e apagado na leitura: o historico segue no stream ate o trim.
#
# `--tudo` e `--desde` sao leitura FRIA (XRANGE): nao movem o ponteiro, entao
# reler historico nunca queima carta nova.
#
# RETENCAO: 7 dias, por XTRIM MINID no timer do motor (ti, arq:0024).
# E a unica coisa que apaga carta. Mensagem e consumo curto; o que tem permanencia
# vira card, commit ou wiki antes de vencer.
import argparse
import json
import os
import sys
from datetime import datetime

try:
    import redis
except ImportError:
    sys.exit("erro: modulo 'redis' nao instalado neste venv (uv pip install redis)")

# Fonte UNICA de quem e destinatario valido: a ARVORE VIVA `abertura/<cadeira>/`
# (arq:0073 §1, estado vivo arq:0074), o mesmo que comum/cadeiras.py le. O ledger de
# vinculo e HISTORICO append-only, para consulta — NENHUM codigo vivo o le para
# resolver identidade (incidente, ordem do dono): o slug fossil `claudinho-<cadeira>`
# do ledger resolvia como vigente. Antes um roster mantido a mao divergia da fonte
# (faltavam engenharia e politicas-publicas), caixa fantasma (#2431); a arvore nao
# diverge porque e a propria morada da persona.
ABERTURA = os.path.join(os.environ.get("PF_RAIZ", os.path.expanduser("~/AI")),
                        "platafirma-harness", "abertura")
# Participantes (DMZ): tem caixa na malha mas NAO sao cadeira. jaiminho e destinatario
# valido do Elias (ver PARES_EXCLUSIVOS). Unificar TAMBEM esta lista com
# comum/cadeiras.py::_SAO_PARTICIPANTE exige a lib compartilhada (colapso 3->1, adiado
# pelo dono); ate la fica esta constante local.
PERSONAS_PARTICIPANTES = ("jaiminho",)
ESPIA = "gestao-estrategica"
# Identidade de leitura automatica: processo sem sessao, sem caixa e sem mesa.
# Nao entra no roster do ledger de proposito — assim nunca e destinatario valido.
# Pode so medir profundidade (status); qualquer outro verbo e negado em so_leitura().
LEITOR = "sonda"
GRUPO = "cadeira"
TIPOS_VALIDOS = {"decisao", "resposta", "pedido", "minuta", "demanda", "handoff"}

# Persona de classe externa (DMZ): tem caixa na malha, mas nao tem par livre. O
# Jaiminho existe em PERSONAS_PARTICIPANTES para ser destinatario VALIDO do Elias — sem isso o
# `fila enviar` dele falharia na validacao —, e a allowlist e o que impede que estar
# na lista signifique estar aberto as sete. Vale nos dois sentidos.
PARES_EXCLUSIVOS = {"jaiminho": {"ia"}}


def so_par_permitido(de: str, para: str, json_mode: bool = False):
    for a, b in ((para, de), (de, para)):
        permitidos = PARES_EXCLUSIVOS.get(a)
        if permitidos is not None and b not in permitidos:
            msg = (f"{a} e colaboracao externa e so troca mensagem com "
                   f"{', '.join(sorted(permitidos))} — canal exclusivo (card 344).")
            if json_mode:
                _falha_json(msg, 1)
            sys.stderr.write(f"erro: {msg}\n")
            sys.exit(1)

REDIS_HOST = os.environ.get("FILA_REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.environ.get("FILA_REDIS_PORT", "6379"))


def r_conn():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def stream_key(persona: str) -> str:
    return f"caixa:{persona}"


def garante_grupo(rc, persona: str):
    """Grupo por caixa, criado no piso do stream. Idempotente."""
    try:
        rc.xgroup_create(stream_key(persona), GRUPO, id="0", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def personas_validas():
    """Slugs vivos de destinatario (minusculo puro), da ARVORE `abertura/<cadeira>/`
    mais os participantes de PERSONAS_PARTICIPANTES. Mesma fonte que comum/cadeiras.py
    (arq:0073 §1) — o ledger de vinculo NAO se le aqui (incidente, ordem do dono).

    Arvore ausente/ilegivel devolve None — a lista ilegivel NAO e passe livre, e
    valida_persona ja a trata como recusa alta. Arvore presente mas sem nenhuma
    persona tambem devolve None pela mesma razao: fonte vazia nao valida ninguem."""
    try:
        cadeiras = {
            d.name
            for d in os.scandir(ABERTURA)
            if d.is_dir() and os.path.isfile(os.path.join(d.path, "persona.md"))
        }
    except OSError:
        return None
    # atores internos nao-cadeira (fabrica) tem persona.md mas nao sao destinatario
    # de fila entre cadeiras; participantes entram por PERSONAS_PARTICIPANTES.
    cadeiras.discard("fabrica")
    if not cadeiras:
        return None
    return cadeiras | set(PERSONAS_PARTICIPANTES)


def _json_mode(args) -> bool:
    """So o subcomando 'status' ganhou --json — os demais nem tem o atributo."""
    return getattr(args, "verbo", None) == "status" and bool(getattr(args, "json", False))


def _falha_json(msg: str, code: int):
    """Regra dura do --json: falha e {'erro': ...} em stdout, nunca stdout vazio
    nem mensagem solta em stderr. Exit code preservado pelo chamador."""
    print(json.dumps({"erro": msg}, ensure_ascii=False))
    sys.exit(code)


def canoniza_persona(p: str):
    """Devolve o slug vivo (minusculo puro) do roster, ou None.

    Resolve duas fossilizacoes de digitacao contra o roster vivo (`personas_validas`,
    da arvore `abertura/`):
    - case: "TI"/"Ti" -> "ti" (divergencia de caixa nao vira caixa nova);
    - prefixo fossil na ENTRADA: "claudinho-ia" -> "ia". O prefixo ainda em transito
      (formas antigas guardadas por ai) e descartado; nunca e produzido de volta.
      O slug puro e a forma que as cadeiras e os verbos passam (minuta --convoca,
      fila enviar).

    Match e sempre contra o roster (nunca inventa nome): so retorna valor que esta
    em personas_validas().
    """
    validas = personas_validas()
    if not validas:
        return None
    if p in validas:
        return p
    baixo = p.lower()
    for pref in ("claudinho-", "claudinha-"):
        if baixo.startswith(pref):
            baixo = baixo[len(pref):]
            break
    for v in validas:
        if v.lower() == baixo:
            return v
    return None


def valida_persona(p: str, json_mode: bool = False):
    validas = personas_validas()
    # Lista ilegivel NAO e passe livre. Antes, fonte ausente devolvia None e esta
    # funcao retornava calada: dentro de container HOME nao e /home/claudinho, o
    # ledger nao era alcancado, e a validacao ficava DESLIGADA — destinatario com
    # erro de digitacao virava caixa nova, com o remetente vendo sucesso.
    if validas is None:
        msg = (f"nao consegui ler o ledger de vinculo ({LEDGER}) — "
               "sem ele nao ha destinatario valido. Aponte PF_RAIZ.")
        if json_mode:
            _falha_json(msg, 2)
        sys.stderr.write(f"erro: {msg}\n")
        sys.exit(2)
    if canoniza_persona(p):
        return
    if json_mode:
        _falha_json(f"persona desconhecida: {p} (validas: {', '.join(sorted(validas))})", 1)
    sys.stderr.write(f"erro: persona desconhecida: {p}\n  validas: {', '.join(sorted(validas))}\n")
    sys.exit(1)


def resolve_eu(args) -> str:
    eu = args.eu or os.environ.get("PF_CADEIRA", "")
    if not eu:
        if _json_mode(args):
            _falha_json(
                "nao sei quem esta operando a fila — exporte PF_CADEIRA=<cadeira> "
                "(ex.: PF_CADEIRA=IA) ou passe --eu <persona>.",
                2,
            )
        sys.stderr.write(
            "erro: nao sei quem esta operando a fila.\n"
            "  exporte PF_CADEIRA=<cadeira>  (ex.: PF_CADEIRA=ia)  ou passe --eu <persona>.\n"
            "  sem isso a fila nao abre caixa nenhuma — foi assim que uma caixa alheia ja foi\n"
            "  sobrescrita.\n"
        )
        sys.exit(2)
    # Case/prefixo fossil na entrada (PF_CADEIRA legado, --eu digitado) -> slug puro.
    canon = canoniza_persona(eu)
    return canon if canon else eu


def so_minha(eu: str, alvo: str, json_mode: bool = False):
    if eu != alvo and eu != ESPIA:
        if json_mode:
            _falha_json(f"{eu} nao opera a caixa de {alvo} — caixa alheia nao se le nem se confirma.", 1)
        sys.stderr.write(f"erro: {eu} nao opera a caixa de {alvo} — caixa alheia nao se le nem se confirma.\n")
        sys.exit(1)


def so_espia(eu: str, json_mode: bool = False):
    if eu not in (ESPIA, LEITOR):
        if json_mode:
            _falha_json(f"--todas e de {ESPIA} ou {LEITOR}, nao de {eu}.", 1)
        sys.stderr.write(f"erro: --todas e de {ESPIA} ou {LEITOR}, nao de {eu}.\n")
        sys.exit(1)


def so_leitura(eu: str, verbo: str, json_mode: bool = False):
    """LEITOR mede profundidade e nada mais. Ler consome (XACK) e enviar escreve —
    os dois movem estado, e leitura automatica nao move estado de ninguem."""
    if eu == LEITOR and verbo != "status":
        msg = f"{LEITOR} so faz status — {verbo} move estado e nao e de leitura automatica."
        if json_mode:
            _falha_json(msg, 1)
        sys.stderr.write(f"erro: {msg}\n")
        sys.exit(1)


def gerar_msgid(de: str, existentes) -> str:
    from datetime import timedelta, timezone
    agora = datetime.now(timezone.utc).astimezone()
    seg = 0
    while True:
        candidato = (agora + timedelta(seconds=seg)).strftime("%Y%m%dT%H%M%S") + f"-{de}"
        if candidato not in existentes:
            return candidato
        seg += 1


def _campos(plano: dict, tecnico: str) -> dict:
    return {
        "tecnico": tecnico,
        "msgid": plano.get("id", tecnico),
        "de": plano.get("de", ""),
        "tipo": plano.get("tipo", ""),
        "assunto": plano.get("assunto", ""),
        "ref": plano.get("ref", ""),
        "responde": plano.get("responde", ""),
        "corpo": plano.get("corpo", ""),
    }


def frias(rc, persona: str, desde: str = None):
    """Historico por XRANGE — NAO move o ponteiro do grupo."""
    piso = "-"
    if desde:
        try:
            ms = int(datetime.strptime(desde[:15], "%Y%m%dT%H%M%S").timestamp() * 1000)
            piso = f"{ms}-0"
        except ValueError:
            sys.stderr.write(f"erro: --desde espera carimbo AAAAMMDDTHHMMSS, recebi: {desde}\n")
            sys.exit(2)
    return [_campos(c, t) for t, c in rc.xrange(stream_key(persona), min=piso, max="+")]


def novas(rc, persona: str, quantas: int = 500):
    """XREADGROUP '>' + XACK: so o que a cadeira ainda nao viu, confirmado na entrega."""
    garante_grupo(rc, persona)
    resp = rc.xreadgroup(GRUPO, persona, {stream_key(persona): ">"}, count=quantas)
    if not resp:
        return []
    saida = []
    for tecnico, plano in resp[0][1]:
        rc.xack(stream_key(persona), GRUPO, tecnico)
        saida.append(_campos(plano, tecnico))
    return saida


def _idade_seg_do_msgid(msgid: str):
    """Idade em segundos a partir do carimbo embutido no msgid (formato
    AAAAMMDDTHHMMSS-<de>, ver gerar_msgid). Mesma leitura de fuso que `frias()`
    ja faz para --desde: strptime devolve naive e .timestamp() reinterpreta como
    hora local — e assim que o carimbo foi escrito. None se o msgid nao bater
    com o formato esperado (defensivo, nunca derruba o verbo por causa disso)."""
    try:
        ts = datetime.strptime(msgid[:15], "%Y%m%dT%H%M%S").timestamp()
    except (ValueError, TypeError):
        return None
    return max(0, int(datetime.now().timestamp() - ts))


def _parse_xinfo_consumers(bruto):
    """Fallback para redis-py sem xinfo_consumers pronto: RESP2 devolve lista de
    listas achatadas [campo, valor, campo, valor, ...] por consumer."""
    saida = []
    for item in bruto:
        if isinstance(item, dict):
            saida.append(item)
            continue
        it = iter(item)
        saida.append(dict(zip(it, it)))
    return saida


def _idle_consumer_seg(rc, chave: str, persona: str):
    """Idle time (segundos) do consumer da cadeira, via XINFO CONSUMERS. O nome
    do consumer e a propria persona (novas() chama XREADGROUP(GRUPO, persona,
    ...)). None se a persona nunca apareceu como consumer — nunca leu a caixa."""
    try:
        consumidores = rc.xinfo_consumers(chave, GRUPO)
    except AttributeError:
        bruto = rc.execute_command("XINFO", "CONSUMERS", chave, GRUPO)
        consumidores = _parse_xinfo_consumers(bruto)
    except redis.exceptions.ResponseError:
        return None
    for c in consumidores:
        if c.get("name") == persona:
            idle_ms = c.get("idle")
            return None if idle_ms is None else int(idle_ms) // 1000
    return None


def conta_novas(rc, persona: str, detalhado: bool = False):
    """(novas, total no historico) sem mover o ponteiro.

    `lag` do XINFO vem NULO quando o stream ja sofreu XDEL — o servidor perde a
    conta de entradas e devolve indefinido em vez de zero. Contar zero ali diria
    "caixa em dia" com carta nova dentro, entao o caminho seguro e contar por
    XRANGE exclusivo a partir do ponteiro, que nao depende de entries-read.

    Com detalhado=True devolve uma 4-tupla, acrescida de:
    - idade_mais_antiga_seg: idade da carta pendente mais antiga (None se nao
      houver pendente).
    - ultima_leitura_seg: idle do consumer da cadeira (None se nunca leu).
    Usado pelo bloco 2 (Caixas) via `fila status --json`; o caminho sem
    detalhado e o que a saida de texto sempre usou, byte a byte igual.
    """
    garante_grupo(rc, persona)
    chave = stream_key(persona)
    total = rc.xlen(chave)
    n = total
    ponteiro = "0-0"
    for g in rc.xinfo_groups(chave):
        if g["name"] != GRUPO:
            continue
        pendentes = g.get("pending", 0)
        ponteiro = g.get("last-delivered-id", "0-0")
        if g.get("lag") is not None:
            n = g["lag"] + pendentes
        else:
            depois = rc.xrange(chave, min=f"({ponteiro}", max="+")
            n = len(depois) + pendentes
        break

    if not detalhado:
        return n, total

    idade_mais_antiga_seg = None
    if n:
        entradas = rc.xrange(chave, min=f"({ponteiro}", max="+", count=1)
        if entradas:
            _tecnico, campos = entradas[0]
            idade_mais_antiga_seg = _idade_seg_do_msgid(campos.get("id", ""))

    ultima_leitura_seg = _idle_consumer_seg(rc, chave, persona)
    return n, total, idade_mais_antiga_seg, ultima_leitura_seg


def imprime(m: dict):
    print(f"===MSG {m['msgid']}===")
    print(f"de: {m['de']}")
    print(f"tipo: {m['tipo']}")
    print(f"assunto: {m['assunto']}")
    if m["ref"]:
        print(f"ref: {m['ref']}")
    if m["responde"]:
        print(f"responde: {m['responde']}")
    print()
    print(m["corpo"])
    print()


# ---------- status ----------
def detalhe_status(rc, persona: str) -> dict:
    """Um objeto por persona para `fila status --json` — bloco 2 (Caixas) da
    spec. Estado e so tres valores aqui: 'vazia'/'em_dia'/'parada' — o quarto
    valor do mapa do card ('fechada', porteiro) nao existe nesta versao
    Streams (sem conceito de caixa encerrada neste arquivo; ver relatorio)."""
    n, total, idade_mais_antiga_seg, ultima_leitura_seg = conta_novas(rc, persona, detalhado=True)
    if n:
        estado = "parada"
    elif total:
        estado = "em_dia"
    else:
        estado = "vazia"
    return {
        "persona": persona,
        "pendentes": n,
        "total_historico": total,
        "estado": estado,
        "idade_mais_antiga_seg": idade_mais_antiga_seg,
        "ultima_leitura_seg": ultima_leitura_seg,
    }


def cmd_status(rc, eu: str, args):
    json_mode = getattr(args, "json", False)

    if args.todas:
        so_espia(eu, json_mode=json_mode)
        personas = sorted(personas_validas() or set())
    elif args.persona:
        valida_persona(args.persona, json_mode=json_mode)
        so_minha(eu, args.persona, json_mode=json_mode)
        personas = [args.persona]
    elif os.environ.get("PF_CADEIRA", "").strip():
        # Sem alvo, a caixa e a de quem opera. Peca de abertura servida por execucao
        # (`verbo:fila status`, catalogo do #189) nao carrega argumento: o sujeito ja
        # viaja em PF_CADEIRA, e exigi-lo de novo era a terceira forma da mesma coisa.
        alvo = os.environ["PF_CADEIRA"].strip()
        valida_persona(alvo, json_mode=json_mode)
        so_minha(eu, alvo, json_mode=json_mode)
        personas = [alvo]
    else:
        # Achado no LOTE 1 (card #390): argparse recusa "--todas" como valor do
        # positional "persona" (parece opção, não é aceito por padrão) — a régua
        # `args.persona == "--todas"` nunca era alcançável pela CLI de verdade.
        # "persona" virou opcional e "--todas" virou flag de verdade; este ramo
        # cobre "nem um nem outro" (uso incorreto), que antes o argparse pegava
        # sozinho por "persona" ser obrigatório.
        msg = "uso: fila status <persona> | --todas (ou PF_CADEIRA no ambiente)"
        if json_mode:
            _falha_json(msg, 2)
        sys.stderr.write(f"erro: {msg}\n")
        sys.exit(2)

    if json_mode:
        print(json.dumps([detalhe_status(rc, p) for p in personas], ensure_ascii=False))
        return

    for p in personas:
        n, total = conta_novas(rc, p)
        if n:
            print(f"{p}: {n} nova(s) · {total} no historico (7 dias)")
        elif total:
            print(f"{p}: caixa em dia · {total} no historico (7 dias)")
        else:
            print(f"{p}: caixa vazia")


# ---------- ler ----------
def cmd_ler(rc, eu: str, args):
    if args.persona == "--todas":
        so_espia(eu)
        personas = sorted(personas_validas() or set())
    else:
        valida_persona(args.persona)
        so_minha(eu, args.persona)
        personas = [args.persona]

    frio = args.tudo or args.desde
    if args.remetente and not frio:
        sys.stderr.write(
            "erro: filtrar por remetente so vale em leitura fria (--tudo ou --desde).\n"
            "  no modo normal a entrega e confirmada, e filtrar esconderia carta ja confirmada.\n"
        )
        sys.exit(2)

    vazio = True
    for p in personas:
        msgs = frias(rc, p, args.desde) if frio else novas(rc, p)
        if args.remetente:
            msgs = [m for m in msgs if m["de"] == args.remetente]
        if not msgs:
            continue
        vazio = False
        if len(personas) > 1:
            print(f"## caixa: {p}\n")
        for m in reversed(msgs):
            imprime(m)
    if vazio:
        if frio:
            print("nada no historico com esse recorte")
        else:
            print("caixa em dia")


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
        sys.stderr.write(f"erro: tipo invalido: {args.tipo}\n  validos: {', '.join(sorted(TIPOS_VALIDOS))}\n")
        sys.exit(1)
    valida_persona(args.destinatario)
    valida_persona(de)
    # Grava sempre o nome canonico: a caixa e uma so, qualquer que seja a caixa
    # alta que o chamador digitou.
    args.destinatario = canoniza_persona(args.destinatario)
    de = canoniza_persona(de)
    so_par_permitido(de, args.destinatario, _json_mode(args))

    corpo = sys.stdin.read()
    if not corpo.strip():
        sys.stderr.write("erro: corpo vazio\n")
        sys.exit(1)

    stream = stream_key(args.destinatario)
    existentes = {m["msgid"] for m in frias(rc, args.destinatario)}
    msgid = gerar_msgid(de, existentes)
    rc.xadd(stream, {
        "id": msgid, "de": de, "tipo": args.tipo, "assunto": args.assunto,
        "ref": args.ref or "", "responde": args.responde or "", "corpo": corpo,
    })
    print(msgid)


def build_parser():
    ap = argparse.ArgumentParser(prog="fila", add_help=False)
    ap.add_argument("--eu", default=None)
    sub = ap.add_subparsers(dest="verbo")

    p_status = sub.add_parser("status", add_help=False)
    p_status.add_argument("persona", nargs="?", default=None)
    p_status.add_argument("--todas", action="store_true")
    p_status.add_argument("--json", action="store_true")

    p_ler = sub.add_parser("ler", add_help=False)
    p_ler.add_argument("persona")
    p_ler.add_argument("remetente", nargs="?", default=None)
    p_ler.add_argument("--tudo", action="store_true")
    p_ler.add_argument("--desde", default=None)

    # `tipos` — card #2274, defeito 5: a lista de tipos validos so aparecia na mensagem de
    # erro do `enviar`. Sem verbo que a liste, descobri-la exigia errar de proposito. Agora
    # ha um ato que a imprime, e ele NAO toca a malha (info estatica: TIPOS_VALIDOS).
    sub.add_parser("tipos", add_help=False)

    p_enviar = sub.add_parser("enviar", add_help=False)
    p_enviar.add_argument("destinatario")
    p_enviar.add_argument("--de", default=None)
    p_enviar.add_argument("--tipo", default=None)
    p_enviar.add_argument("--assunto", default=None)
    p_enviar.add_argument("--ref", default=None)
    p_enviar.add_argument("--responde", default=None)

    return ap


def uso():
    sys.stderr.write(
        "uso:\n"
        "  fila status <persona> | --todas\n"
        "  fila ler <persona>                     so o que chegou desde a ultima leitura\n"
        "  fila ler <persona> --tudo [remetente]  historico dos 7 dias, nao move o ponteiro\n"
        "  fila ler <persona> --desde AAAAMMDDTHHMMSS [remetente]\n"
        "  fila enviar <destinatario> --tipo <t> --assunto <a> [--ref <r>] [--responde <id>]\n"
        "              (corpo em stdin)\n"
        "  fila tipos                             lista os tipos validos de --tipo\n"
    )
    sys.exit(2)


def main():
    ap = build_parser()
    args, _resto = ap.parse_known_args()
    if not args.verbo:
        uso()
    # `tipos` responde ANTES de tocar a malha: e info estatica e deve funcionar offline.
    if args.verbo == "tipos":
        sys.stdout.write("\n".join(sorted(TIPOS_VALIDOS)) + "\n")
        sys.exit(0)
    eu = resolve_eu(args)
    rc = r_conn()
    try:
        rc.ping()
    except redis.exceptions.RedisError as e:
        msg = f"nao alcancei a malha msg ({REDIS_HOST}:{REDIS_PORT}): {e}"
        if _json_mode(args):
            _falha_json(msg, 1)
        sys.stderr.write(f"erro: {msg}\n")
        sys.exit(1)

    so_leitura(eu, args.verbo, _json_mode(args))

    if args.verbo == "status":
        cmd_status(rc, eu, args)
    elif args.verbo == "ler":
        cmd_ler(rc, eu, args)
    elif args.verbo == "enviar":
        cmd_enviar(rc, eu, args)
    else:
        uso()


if __name__ == "__main__":
    main()
