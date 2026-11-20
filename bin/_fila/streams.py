#!/opt/platafirma/current/venv/harness/bin/python
# fila — caixa de mensagens entre personas da PlataFirma, sobre a malha msg (Valkey/Streams).
# capacidade: mensagem
# dono: ia
# componente: harness
# use para: caixa, carta, recado, handoff, 'o que chegou', mandar para outra cadeira
# atos: status (leitura, mensagem) · ler (leitura, mensagem) · tratar (escrita, mensagem) · enviar (escrita, mensagem) · tipos (leitura, mensagem) · contestar (escrita, mensagem)
# forma: status,tipos=lista · ler=texto · tratar=lista · enviar=objeto · contestar=objeto
# face: contestar=motor
# rotulo: contestar=Contestar o indicador
# volta: contestar=nao
# cauda: nao
# classe: B
# consome: valkey@streams (protocolo redis — sem OpenAPI)
# ambiente: FILA_REDIS_HOST[=127.0.0.1] · FILA_REDIS_PORT[=6379] · PF_CASA_RAIZ[=/opt/platafirma/current/casa-espelho] (personas em instancias/persona/*.md) · PF_CADEIRA (obrigatoria em enviar e em ler/status sem persona; porta) · PF_SESSAO (porta, so log)
# depende: modulo redis no venv; arvore abertura/<cadeira>/persona.md (fonte de destinatario); rede ao loopback da malha
# escreve: malha msg — XADD na caixa do destinatario (enviar); entrega no grupo (ler quente: move o ponteiro, carta fica pendurada); XACK (tratar); nada em status/tipos/ler frio/--penduradas
# substitui: redis-cli XADD/XREADGROUP/XRANGE na caixa; o "cola a mensagem aqui" que a conduta do dono proibe
# conforme: parcial (spec_fila §6)
# spec: spec fila
#
# Substrato: componente msg do motor (arq:0018, arq:0036). Stream por caixa,
# "caixa:<persona>", com consumer group unico "cadeira" — a cadeira dona e o unico
# consumidor. Envelope inalterado: de/tipo/assunto/ref/responde + corpo auto-contido.
#
# LEITURA, PONTEIRO E ACK (decisao do dono, 03/10/2026; revoga a de 09/08)
# Tres estados, os de toda mensageria de producao (Streams, Kafka, RabbitMQ, SQS):
#   nao lida   — depois do ponteiro do grupo (last-delivered-id);
#   pendurada  — entregue e sem XACK: esta na PEL do grupo;
#   tratada    — XACK feito.
# `ler` e XREADGROUP ">": entrega e move o ponteiro, SEM XACK. `tratar <id>` e o
# XACK, depois que a carta virou ato (resposta, card, mesa) ou foi superada. Antes
# o ack vinha na entrega (o auto-commit do Kafka), e a carta lida pela metade
# sumia sem ninguem ter tratado; por isso o `descansar` relia os 7 dias inteiros.
# `--penduradas` le PEL + nao lidas, sem mover nada — o equivalente da reentrega
# do que nao teve ack (XAUTOCLAIM, visibility timeout). O `descansar` nao le mais a caixa.
#
# `--tudo` e `--desde` sao leitura FRIA (XRANGE): nao movem o ponteiro, entao
# reler historico nunca queima carta nova.
#
# RETENCAO: 7 dias por idade, tratada ou nao, por XTRIM MINID no timer do motor
# (ti, arq:0024), como a retencao do Kafka e o XTRIM do proprio Valkey. E a unica
# coisa que apaga carta; a pendurada vencida sai tambem da PEL no mesmo timer. O
# `descansar` avisa a pendurada com mais de 5 dias. Mensagem e consumo curto; o
# que tem permanencia vira card, commit ou wiki antes de vencer.
import argparse
import json
import os
import sys
import time
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
# diverge porque e a propria morada da persona. Le-se a MORADA PUBLICADA da instancia
# (arq:0097, card #3010), nunca a arvore de um clone.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))), "lib"))
from fila_tipos import TIPOS_VALIDOS  # noqa: E402
from raizes import release  # noqa: E402

ABERTURA = os.path.join(
    os.environ.get("PF_CASA_RAIZ") or str(release() / "casa-espelho"),
    "instancias", "persona")
# Participantes (DMZ): teriam caixa na malha sem ser cadeira. Vazio desde o card
# #3117 (27/09/2026). Unificar esta lista com comum/cadeiras.py::_SAO_PARTICIPANTE
# exige a lib compartilhada (colapso 3->1, adiado pelo dono).
PERSONAS_PARTICIPANTES: tuple = ()
ESPIA = "gestao-estrategica"
# Identidade de leitura automatica: processo sem sessao, sem caixa e sem mesa.
# Nao entra no roster do ledger de proposito — assim nunca e destinatario valido.
# Pode so medir profundidade (status); qualquer outro verbo e negado em so_leitura().
LEITOR = "sonda"
GRUPO = "cadeira"
# O contestar da R16 (arq:0124 §3, mecanismo comum; card #3532): `--ref` leva o indicador contestado e o
# corpo leva o fundamento. Sem armazenamento novo: os dois campos ja existem em toda carta.
TIPO_CONTESTACAO = "contestacao"

# Persona de classe externa (DMZ): tem caixa na malha, mas nao tem par livre. A
# allowlist e o que impede que estar em PERSONAS_PARTICIPANTES signifique estar
# aberto a todas as cadeiras. Vale nos dois sentidos. Vazia desde o card #3117.
PARES_EXCLUSIVOS: dict = {}


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
    """Slugs vivos de destinatario (minusculo puro), da arvore de personas da casa nova
    (`casa-espelho/instancias/persona/*.md`, ou `PF_ABERTURA_DIR` quando explicitado)
    mais os participantes de PERSONAS_PARTICIPANTES.

    Arvore ausente/ilegivel devolve None — a lista ilegivel NAO e passe livre, e
    valida_persona ja a trata como recusa alta. Arvore presente mas sem nenhuma
    persona tambem devolve None pela mesma razao: fonte vazia nao valida ninguem."""
    try:
        cadeiras = set()
        for d in os.scandir(ABERTURA):
            if d.is_file() and d.name.endswith(".md"):
                cadeiras.add(d.name[:-3])
            elif d.is_dir() and os.path.isfile(os.path.join(d.path, "persona.md")):
                cadeiras.add(d.name)
    except OSError:
        return None
    # toda cadeira com persona.md na arvore viva e destinatario/emissor pleno
    # (dono, 03/09/2026: cadeiras flat, sem diferenca de head — a fabrica manda e
    # recebe como as demais). Participantes externos entram por PERSONAS_PARTICIPANTES.
    if not cadeiras:
        return None
    return cadeiras | set(PERSONAS_PARTICIPANTES)


def _json_mode(args) -> bool:
    """status e ler ganharam --json — os demais nem tem o atributo. O tela do
    harness le saida de verbo, e verbo que so imprime pra humano e lacuna a
    fechar (spec_plano-de-controle-harness §7.2)."""
    return getattr(args, "verbo", None) in ("status", "ler") and bool(getattr(args, "json", False))


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
        msg = (f"nao consegui ler as personas da casa nova ({ABERTURA}) — "
               "sem elas nao ha destinatario valido. Aponte PF_CASA_RAIZ.")
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
    """Identidade lida, nunca resolvida (arq:0110 §5, spec fila §3, DT 948).

    A porta resolve `sessao:{id}` e injeta `PF_CADEIRA`; o verbo nunca lê Valkey
    nem arquivos de sessão para descobrir a cadeira.
    """
    eu = (
        getattr(args, "eu", None)
        or os.environ.get("PF_CADEIRA", "")
        or os.environ.get("PLATAFIRMA_CADEIRA", "")
    ).strip()
    if not eu:
        sid = (
            getattr(args, "sessao_id", None)
            or os.environ.get("PF_SESSAO", "")
            or os.environ.get("PLATAFIRMA_SESSAO_ID", "")
            or os.environ.get("PF_SESSAO_ID", "")
        ).strip()
        if sid and sid != "-":
            msg = (
                f"PF_CADEIRA ausente na sessão {sid}: "
                "reabra com monta_sessao(cadeira=<slug>) ou passe --eu <cadeira>"
            )
        else:
            msg = "sem cadeira na sessão (PF_CADEIRA ausente): abra com monta_sessao(cadeira=<slug>) ou passe --eu <cadeira>"
        if _json_mode(args):
            _falha_json(msg, 3)
        sys.stderr.write(f"erro: {msg}\n")
        sys.exit(3)
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


RETENCAO_INDICE_SEG = 8 * 86400


def gerar_msgid(de: str, existentes, rc=None) -> str:
    """`<carimbo>-<remetente>`, único por carta (#2856 linha 79): não repete o que já está na caixa do
    destino (`existentes`) nem, com `rc`, o que a mesma remetente mandou a outra caixa no mesmo
    segundo: a reserva `SET NX` vale em todas as caixas e expira com a janela fria (8 dias)."""
    from datetime import timedelta, timezone
    agora = datetime.now(timezone.utc).astimezone()
    seg = 0
    while True:
        candidato = (agora + timedelta(seconds=seg)).strftime("%Y%m%dT%H%M%S") + f"-{de}"
        if candidato not in existentes and (
                rc is None or rc.set(f"msgid:{candidato}", "1", nx=True, ex=RETENCAO_INDICE_SEG)):
            return candidato
        seg += 1


def _registra_msgid(rc, msgid: str, caixa: str, tecnico: str, de: str):
    """Ponteiro O(1) em `msgid:<id>` + indice `enviadas:<de>` (TTL 8d, arq:0092)."""
    if hasattr(rc, "set"):
        meta = json.dumps({"caixa": caixa, "tecnico": tecnico, "de": de}, ensure_ascii=False)
        rc.set(f"msgid:{msgid}", meta, ex=RETENCAO_INDICE_SEG)
    if hasattr(rc, "zadd"):
        agora = time.time()
        chave_env = f"enviadas:{de}"
        rc.zadd(chave_env, {msgid: agora})
        if hasattr(rc, "zremrangebyscore"):
            rc.zremrangebyscore(chave_env, "-inf", agora - RETENCAO_INDICE_SEG)
        if hasattr(rc, "expire"):
            rc.expire(chave_env, RETENCAO_INDICE_SEG)


def _ler_meta_msgid(rc, msgid: str):
    if not hasattr(rc, "get"):
        return None
    bruto = rc.get(f"msgid:{msgid}")
    if isinstance(bruto, str) and bruto.startswith("{"):
        try:
            meta = json.loads(bruto)
            if isinstance(meta, dict) and meta.get("caixa") and meta.get("tecnico"):
                return meta
        except json.JSONDecodeError:
            pass
    return None


def _achar_na_malha(rc, msgid: str, caixas_fallback=None):
    """Resolve `msgid` para `(caixa, tecnico, carta)` via ponteiro `msgid:<id>` ou fallback."""
    meta = _ler_meta_msgid(rc, msgid)
    if meta:
        caixa = meta["caixa"]
        tecnico = meta["tecnico"]
        entradas = rc.xrange(stream_key(caixa), min=tecnico, max=tecnico)
        for t, plano in entradas:
            return caixa, t, _campos(plano, t)
        return None
    for caixa in (caixas_fallback or ()):
        for t, plano in rc.xrange(stream_key(caixa), min="-", max="+"):
            if plano.get("id", t) == msgid:
                return caixa, t, _campos(plano, t)
    return None


def _pre_tratadas(rc, persona: str) -> set:
    if not hasattr(rc, "smembers"):
        return set()
    return set(rc.smembers(f"tratadas:{persona}") or ())


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
            d_str = desde.strip()
            if len(d_str) == 10 and d_str.count("-") == 2:
                dt = datetime.strptime(d_str, "%Y-%m-%d")
            elif "T" in d_str and "-" in d_str:
                dt = datetime.fromisoformat(d_str)
            else:
                dt = datetime.strptime(d_str[:15], "%Y%m%dT%H%M%S")
            ms = int(dt.timestamp() * 1000)
            piso = f"{ms}-0"
        except (ValueError, TypeError):
            sys.stderr.write(f"erro: --desde espera carimbo AAAAMMDDTHHMMSS ou AAAA-MM-DD, recebi: {desde}\n")
            sys.exit(2)
    return [_campos(c, t) for t, c in rc.xrange(stream_key(persona), min=piso, max="+")]


def novas(rc, persona: str, quantas: int = 500):
    """XREADGROUP '>': so o que a cadeira ainda nao viu. Entrega e move o ponteiro,
    SEM XACK — a carta fica pendurada ate `tratar`. Cartas ja pre-tratadas em
    `tratadas:<persona>` recebem XACK imediato e nao sao reentregues (DT 413)."""
    garante_grupo(rc, persona)
    resp = rc.xreadgroup(GRUPO, persona, {stream_key(persona): ">"}, count=quantas)
    if not resp:
        return []
    chave = stream_key(persona)
    pre = _pre_tratadas(rc, persona)
    saida = []
    for tecnico, plano in resp[0][1]:
        if tecnico in pre:
            rc.xack(chave, GRUPO, tecnico)
            if hasattr(rc, "srem"):
                rc.srem(f"tratadas:{persona}", tecnico)
            continue
        saida.append(_campos(plano, tecnico))
    return saida

def _ids_pendurados(rc, persona: str):
    """Ids tecnicos na PEL do grupo (entregues e sem XACK), mais antigo primeiro."""
    chave = stream_key(persona)
    try:
        bruto = rc.xpending_range(chave, GRUPO, min="-", max="+", count=10_000)
    except AttributeError:
        try:
            bruto = rc.execute_command("XPENDING", chave, GRUPO, "-", "+", 10_000)
        except (AttributeError, redis.exceptions.ResponseError):
            return []
    except redis.exceptions.ResponseError:
        return []
    ids = []
    for item in bruto or []:
        if isinstance(item, dict):
            ids.append(item.get("message_id"))
        else:
            ids.append(item[0])
    return [i for i in ids if i]


def _pares_respondidos_no_stream(rc: object, persona: str, remetentes: set[str]) -> set[tuple[str, str]]:
    """Coleta pares `(autor, msgid_respondido)` em `caixa:<persona>` e nas caixas dos remetentes."""
    respondidas: set[tuple[str, str]] = set()
    caixas = [persona] + [r for r in sorted(remetentes) if r != persona]
    for cx in caixas:
        for _t, plano in rc.xrange(stream_key(cx), min="-", max="+"):
            resp_id = (plano.get("responde") or "").strip()
            if resp_id:
                de_c = canoniza_persona(plano.get("de", "")) or plano.get("de", "")
                if cx == persona or de_c == persona:
                    respondidas.add((de_c, resp_id))
    return respondidas


def _reconcilia_pel_respondidas(rc: object, persona: str) -> list[dict]:
    """Devolve as cartas vivas na PEL (`estado='pendurada'`), reconciliando com XACK:
    (a) entradas na PEL que o XTRIM ja cortou do stream; e
    (b) cartas ja respondidas por `persona` (`responde == msgid` na caixa do remetente)
        ou superadas pelo proprio remetente (`responde == msgid` na caixa de `persona`)
        antes do ack automatico do DT 336 (#4289)."""
    chave = stream_key(persona)
    candidatas: list[tuple[str, dict]] = []
    remetentes: set[str] = set()
    for tecnico in _ids_pendurados(rc, persona):
        entradas = rc.xrange(chave, min=tecnico, max=tecnico)
        if not entradas:
            rc.xack(chave, GRUPO, tecnico)
            continue
        t, plano = entradas[0]
        m = _campos(plano, t)
        m["estado"] = "pendurada"
        candidatas.append((tecnico, m))
        de_canon = canoniza_persona(m["de"]) or m["de"]
        if de_canon and not de_canon.startswith(PREFIXO_BOT):
            remetentes.add(de_canon)
    if not candidatas:
        return []
    respondidas = _pares_respondidos_no_stream(rc, persona, remetentes)
    vivas: list[dict] = []
    for tecnico, m in candidatas:
        mid = m["msgid"]
        de_c = canoniza_persona(m["de"]) or m["de"]
        if (persona, mid) in respondidas or (de_c, mid) in respondidas:
            rc.xack(chave, GRUPO, tecnico)
            continue
        vivas.append(m)
    return vivas


def penduradas(rc, persona: str):
    """Leitura FRIA do que nao foi tratado: as penduradas (PEL) e as nao lidas
    (depois do ponteiro). Nao entrega, nao move ponteiro, nao confirma (salvo reconciliar
    carta ja respondida com `--responde` ou ja cortada pelo trim, #4289). Cada carta
    leva `estado` ('pendurada' | 'nao lida')."""
    garante_grupo(rc, persona)
    chave = stream_key(persona)
    saida = list(_reconcilia_pel_respondidas(rc, persona))
    ponteiro = "0-0"
    for g in rc.xinfo_groups(chave):
        if g["name"] == GRUPO:
            ponteiro = g.get("last-delivered-id", "0-0")
            break
    pre = _pre_tratadas(rc, persona)
    for t, plano in rc.xrange(chave, min=f"({ponteiro}", max="+"):
        if t in pre:
            continue
        m = _campos(plano, t)
        m["estado"] = "nao lida"
        saida.append(m)
    return saida

def tratar(rc, persona: str, msgids):
    """XACK por msgid. Devolve [(msgid, resultado)] com resultado em
    'tratada' | 'ja tratada' | 'nao lida' | 'nao existe'. Cartas lidas em modo
    frio (`--tudo`/`--desde`/`--penduradas`, ainda a frente do ponteiro) sao
    registradas em `tratadas:<persona>` para receber XACK automatico em `novas()`
    sem queimar cartas novas de outros remetentes (DT 413)."""
    garante_grupo(rc, persona)
    chave = stream_key(persona)
    por_msgid = {}
    for t, plano in rc.xrange(chave, min="-", max="+"):
        por_msgid.setdefault(plano.get("id", t), t)
    pend = set(_ids_pendurados(rc, persona))
    pre = _pre_tratadas(rc, persona)
    ponteiro = "0-0"
    for g in rc.xinfo_groups(chave):
        if g["name"] == GRUPO:
            ponteiro = g.get("last-delivered-id", "0-0")
            break

    def _id(x):
        ms, _, seq = x.partition("-")
        return (int(ms), int(seq or 0))

    saida = []
    for mid in msgids:
        tecnico = por_msgid.get(mid) or (mid if mid in pend else None)
        if tecnico is None:
            saida.append((mid, "nao existe"))
        elif tecnico in pend:
            rc.xack(chave, GRUPO, tecnico)
            saida.append((mid, "tratada"))
        elif _id(tecnico) > _id(ponteiro):
            if tecnico in pre:
                saida.append((mid, "ja tratada"))
            elif hasattr(rc, "sadd"):
                rc.sadd(f"tratadas:{persona}", tecnico)
                if hasattr(rc, "expire"):
                    rc.expire(f"tratadas:{persona}", RETENCAO_INDICE_SEG)
                pre.add(tecnico)
                saida.append((mid, "tratada"))
            else:
                saida.append((mid, "nao lida"))
        else:
            saida.append((mid, "ja tratada"))
    return saida


def _ate_normalizado(ate: str):
    """`--ate` em AAAA-MM-DD (o dia inteiro) ou AAAAMMDDTHHMMSS. Devolve o prefixo de msgid que
    se compara como texto (o msgid comeca pelo carimbo AAAAMMDDTHHMMSS), ou None se nao se le."""
    s = (ate or "").strip()
    if len(s) == 10 and s[4] == s[7] == "-" and (s[:4] + s[5:7] + s[8:]).isdigit():
        return s[:4] + s[5:7] + s[8:] + "T235959"
    if len(s) == 15 and s[8] == "T" and (s[:8] + s[9:]).isdigit():
        return s
    return None


def selecionar(rc, persona: str, de: str = None, tipo: str = None, assunto: str = None,
               ate: str = None):
    """Consumidor seletivo (Hohpe e Woolf, *Enterprise Integration Patterns*, Selective
    Consumer): o seletor avalia os cabecalhos da carta e devolve so as que casam. Le o mesmo
    que `ler --penduradas` (penduradas e nao lidas) e devolve os msgids, mais antigo primeiro,
    cujo remetente, tipo, trecho de assunto (sem caixa) e carimbo (ate `ate`, inclusive) casam
    todos os criterios dados. Nao escreve nada alem do que `penduradas` ja reconcilia (DT 798)."""
    de_c = (canoniza_persona(de) or de) if de else None
    trecho = (assunto or "").lower()
    ids = []
    for m in penduradas(rc, persona):
        if de_c and (canoniza_persona(m["de"]) or m["de"]) != de_c:
            continue
        if tipo and m["tipo"] != tipo:
            continue
        if trecho and trecho not in (m["assunto"] or "").lower():
            continue
        if ate and m["msgid"][:15] > ate:
            continue
        if m["msgid"] not in ids:
            ids.append(m["msgid"])
    return ids


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
    pre = _pre_tratadas(rc, persona)
    for g in rc.xinfo_groups(chave):
        if g["name"] != GRUPO:
            continue
        # So o que nao foi entregue. A pendurada (PEL) conta a parte, em
        # conta_penduradas: lida e nao tratada nao e carta nova.
        ponteiro = g.get("last-delivered-id", "0-0")
        if g.get("lag") is not None and not pre:
            n = g["lag"]
        else:
            depois = [t for t, _ in rc.xrange(chave, min=f"({ponteiro}", max="+") if t not in pre]
            n = len(depois)
        break

    if not detalhado:
        return n, total

    idade_mais_antiga_seg = None
    if n:
        for t, campos in rc.xrange(chave, min=f"({ponteiro}", max="+"):
            if t in pre:
                continue
            idade_mais_antiga_seg = _idade_seg_do_msgid(campos.get("id", ""))
            break

    ultima_leitura_seg = _idle_consumer_seg(rc, chave, persona)
    return n, total, idade_mais_antiga_seg, ultima_leitura_seg


def conta_penduradas(rc, persona: str) -> int:
    """Entregues e sem XACK (PEL do grupo): lidas e ainda nao tratadas."""
    garante_grupo(rc, persona)
    for g in rc.xinfo_groups(stream_key(persona)):
        if g["name"] == GRUPO:
            pend_n = int(g.get("pending", 0) or 0)
            if pend_n and (hasattr(rc, "xpending_range") or hasattr(rc, "execute_command")):
                return len(_reconcilia_pel_respondidas(rc, persona))
            return pend_n
    return 0

def imprime(m: dict):
    print(f"===MSG {m['msgid']}===")
    print(f"de: {m['de']}")
    if m.get("para"):
        print(f"para: {m['para']}")
    print(f"tipo: {m['tipo']}")
    if m.get("estado"):
        print(f"estado: {m['estado']}")
    print(f"assunto: {m['assunto']}")
    contestacao = m["tipo"] == TIPO_CONTESTACAO
    if m["ref"]:
        print(f"{'indicador' if contestacao else 'ref'}: {m['ref']}")
    if m["responde"]:
        print(f"responde: {m['responde']}")
    print()
    if contestacao:
        print("fundamento:")
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
        "penduradas": conta_penduradas(rc, persona),
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
    elif eu:
        valida_persona(eu, json_mode=json_mode)
        so_minha(eu, eu, json_mode=json_mode)
        personas = [eu]
    else:
        eu = resolve_eu(args)
        valida_persona(eu, json_mode=json_mode)
        personas = [eu]

    if json_mode:
        print(json.dumps([detalhe_status(rc, p) for p in personas], ensure_ascii=False))
        return

    for p in personas:
        n, total = conta_novas(rc, p)
        pend = conta_penduradas(rc, p) if total else 0
        trecho_pend = f"{pend} pendurada(s) · " if pend else ""
        if n:
            print(f"{p}: {n} nova(s) · {trecho_pend}{total} no historico (7 dias)")
        elif pend:
            print(f"{p}: nada novo · {trecho_pend}{total} no historico (7 dias)")
        elif total:
            print(f"{p}: caixa em dia · {total} no historico (7 dias)")
        else:
            print(f"{p}: caixa vazia")


# ---------- ler ----------
def _carta_json(m: dict, chaves: tuple) -> dict:
    item = {k: m.get(k, "") for k in chaves}
    item["idade_seg"] = _idade_seg_do_msgid(m.get("msgid", ""))
    return item


def _eh_msgid(val: str) -> bool:
    """Identifica um msgid no formato AAAAMMDDTHHMMSS-<de>."""
    if not val or len(val) < 17 or "-" not in val:
        return False
    carimbo = val[:15]
    return len(carimbo) == 15 and carimbo[8] == "T" and carimbo[:8].isdigit() and carimbo[9:15].isdigit()


def _ler_enviadas(rc, remetente: str, filtro_para: str = None) -> list:
    """Leitura fria das cartas enviadas por `remetente` nos ultimos 7-8 dias (DT 188)."""
    msgs = []
    vistos = set()
    if hasattr(rc, "zrange"):
        ids = rc.zrange(f"enviadas:{remetente}", 0, -1) or []
        for mid in ids:
            achou = _achar_na_malha(rc, mid)
            if not achou:
                continue
            caixa, _t, carta = achou
            if filtro_para and caixa != filtro_para:
                continue
            carta["para"] = caixa
            msgs.append(carta)
            vistos.add(carta["msgid"])
    caixas = [filtro_para] if filtro_para else sorted(personas_validas() or set())
    for p in caixas:
        for m in frias(rc, p):
            de_canon = canoniza_persona(m["de"]) or m["de"]
            if de_canon == remetente and m["msgid"] not in vistos:
                m["para"] = p
                msgs.append(m)
                vistos.add(m["msgid"])
    msgs.sort(key=lambda m: m.get("msgid", ""))
    return msgs


def _cmd_ler_id(rc, eu: str, msgid: str, json_mode: bool, caixa_dica: str = None):
    """Leitura fria de uma carta especifica pelo `msgid`, para destinatario ou remetente (DT 60 / DT 188)."""
    todas_caixas = sorted(personas_validas() or set())
    if caixa_dica and caixa_dica in todas_caixas:
        caixas = [caixa_dica] + [c for c in todas_caixas if c != caixa_dica]
    else:
        caixas = todas_caixas
    achou = _achar_na_malha(rc, msgid, caixas)
    if not achou:
        msg = f"carta nao encontrada: {msgid} (expirada >7d ou id errado)"
        if json_mode:
            _falha_json(msg, 1)
        sys.stderr.write(f"erro: {msg}\n")
        sys.exit(1)
    caixa, _t, carta = achou
    de_canon = canoniza_persona(carta["de"]) or carta["de"]
    if eu != ESPIA and caixa != eu and de_canon != eu:
        so_minha(eu, caixa, json_mode=json_mode)
    carta["para"] = caixa
    if json_mode:
        chaves = ("msgid", "de", "para", "tipo", "assunto", "ref", "responde", "corpo")
        print(json.dumps([_carta_json(carta, chaves)], ensure_ascii=False))
        return
    imprime(carta)


def cmd_ler(rc, eu: str, args):
    json_mode = bool(getattr(args, "json", False))
    msgid_alvo = getattr(args, "msgid", None)
    if not msgid_alvo and args.persona and not canoniza_persona(args.persona) and _eh_msgid(args.persona):
        msgid_alvo = args.persona
        args.persona = None
    if msgid_alvo:
        dica = canoniza_persona(args.persona) if args.persona else None
        _cmd_ler_id(rc, eu, msgid_alvo, json_mode, caixa_dica=dica)
        return

    env = bool(getattr(args, "enviadas", False))
    if env:
        filtro_para = (
            getattr(args, "para_opt", None)
            or getattr(args, "remetente", None)
            or (args.persona if args.persona and args.persona != eu else None)
        )
        if filtro_para:
            valida_persona(filtro_para, json_mode=json_mode)
            filtro_para = canoniza_persona(filtro_para)
        msgs = _ler_enviadas(rc, eu, filtro_para)
        if json_mode:
            chaves = ("msgid", "de", "para", "tipo", "assunto", "ref", "responde", "corpo")
            print(json.dumps([_carta_json(m, chaves) for m in reversed(msgs)], ensure_ascii=False))
            return
        if not msgs:
            print("nenhuma carta enviada no historico")
            return
        for m in reversed(msgs):
            imprime(m)
        return

    alvo = "--todas" if getattr(args, "todas", False) else (args.persona or eu)
    if not alvo:
        alvo = resolve_eu(args)
    if getattr(args, "remetente_opt", None):
        args.remetente = args.remetente_opt

    pend = bool(getattr(args, "penduradas", False))
    frio = args.tudo or args.desde or pend

    if alvo == "--todas":
        so_espia(eu, json_mode=json_mode)
        personas = sorted(personas_validas() or set())
    else:
        valida_persona(alvo, json_mode=json_mode)
        alvo = canoniza_persona(alvo) or alvo
        rem_canon = (canoniza_persona(args.remetente) or args.remetente) if args.remetente else None
        # DT 60: o remetente pode ler em modo frio (--tudo / --desde) as proprias cartas enviadas
        # a caixa de `<destino>` sem mover o ponteiro nem confirmar nada.
        leitura_fria_propria = bool((args.tudo or args.desde) and not pend and rem_canon == eu)
        if not leitura_fria_propria:
            so_minha(eu, alvo, json_mode=json_mode)
        personas = [alvo]

    def _carrega(p):
        if pend:
            return penduradas(rc, p)
        return frias(rc, p, args.desde) if (args.tudo or args.desde) else novas(rc, p)

    if args.remetente and not frio:
        if json_mode:
            _falha_json("filtrar por remetente so vale em leitura fria (--tudo ou --desde)", 2)
        sys.stderr.write(
            "erro: filtrar por remetente so vale em leitura fria (--tudo ou --desde).\n"
            "  no modo normal a leitura entrega (move o ponteiro), e filtrar esconderia carta ja entregue.\n"
        )
        sys.exit(2)

    rem_filtro = (canoniza_persona(args.remetente) or args.remetente) if args.remetente else None

    if json_mode:
        # Contrato de maquina pra tela: SEMPRE JSON. Sucesso = array de cartas
        # (mais nova primeiro); erro ja saiu por _falha_json acima. Cada carta
        # leva idade_seg do carimbo do msgid, como a mesa/status.
        chaves = ("msgid", "de", "tipo", "assunto", "ref", "responde", "corpo")
        if pend:
            chaves = chaves + ("estado",)
        saida = []
        for p in personas:
            msgs = _carrega(p)
            if rem_filtro:
                msgs = [m for m in msgs if (canoniza_persona(m["de"]) or m["de"]) == rem_filtro]
            for m in reversed(msgs):
                item = _carta_json(m, chaves)
                if len(personas) > 1:
                    item["caixa"] = p
                saida.append(item)
        print(json.dumps(saida, ensure_ascii=False))
        return

    vazio = True
    for p in personas:
        msgs = _carrega(p)
        if rem_filtro:
            msgs = [m for m in msgs if (canoniza_persona(m["de"]) or m["de"]) == rem_filtro]
        if not msgs:
            continue
        vazio = False
        if getattr(args, "ids", False):
            # DT 798: so os msgids, um por linha, para alimentar `fila tratar` ou um script.
            for m in reversed(msgs):
                print(f"{p} {m['msgid']}" if len(personas) > 1 else m["msgid"])
            continue
        if len(personas) > 1:
            print(f"## caixa: {p}\n")
        for m in reversed(msgs):
            imprime(m)
    if vazio:
        if pend:
            print("nada pendurado")
        elif frio:
            print("nada no historico com esse recorte")
        else:
            # Sem carta nova, mas com carta entregue e sem XACK: "caixa em dia" esconderia a
            # pendencia que `status` e `descansar` mostram (#4112). Mesma conta do status.
            penduradas_n = sum(conta_penduradas(rc, p) for p in personas)
            if penduradas_n:
                print(f"nada novo · {penduradas_n} pendurada(s) · `fila ler --penduradas` lista, "
                      "`fila tratar <msgid>` confirma")
            else:
                print("caixa em dia")


# ---------- tratar ----------
def cmd_tratar(rc, eu: str, args):
    """XACK: a carta virou ato (resposta, card, mesa) ou foi superada. Uma linha
    por msgid. Exit 0 se todas trataram (ou ja estavam), 1 se alguma nao existe
    ou ainda nao foi lida."""
    alvo = args.persona or eu
    valida_persona(alvo)
    alvo = canoniza_persona(alvo)
    so_minha(eu, alvo)
    # DT 798: tratar em lote pelo seletor (remetente, tipo, trecho de assunto, carimbo), em vez
    # de listar centenas de msgids a mao. O seletor e os msgids se excluem: a mistura deixaria
    # ambiguo o que o ack cobriu.
    filtros = {k: getattr(args, k, None) for k in ("de", "tipo", "assunto", "ate")}
    if any(filtros.values()):
        if args.msgids:
            sys.stderr.write("erro: passe msgids OU o seletor (--de, --tipo, --assunto, --ate), "
                             "nao os dois\n")
            sys.exit(2)
        ate = None
        if filtros["ate"]:
            ate = _ate_normalizado(filtros["ate"])
            if ate is None:
                sys.stderr.write(f"erro: --ate le AAAA-MM-DD ou AAAAMMDDTHHMMSS (recebi "
                                 f"{filtros['ate']!r})\n")
                sys.exit(2)
        if filtros["tipo"] and filtros["tipo"] not in TIPOS_VALIDOS:
            sys.stderr.write(f"erro: tipo invalido: {filtros['tipo']}\n  validos: "
                             f"{', '.join(sorted(TIPOS_VALIDOS))}\n")
            sys.exit(2)
        args.msgids = selecionar(rc, alvo, de=filtros["de"], tipo=filtros["tipo"],
                                 assunto=filtros["assunto"], ate=ate)
        if not args.msgids:
            print("nenhuma carta por tratar casa o seletor · `fila ler --penduradas` mostra o que ha")
            sys.exit(1)
    if not args.msgids:
        sys.stderr.write("erro: passe ao menos um msgid (o que `fila ler` imprime em ===MSG <id>===), "
                         "ou o seletor --de/--tipo/--assunto/--ate\n")
        sys.exit(2)
    falhou = nao_lida = False
    for mid, res in tratar(rc, alvo, args.msgids):
        print(f"{mid}: {res}")
        if res in ("nao existe", "nao lida"):
            falhou = True
        if res == "nao lida":
            nao_lida = True
    if nao_lida:
        # spec fila §5: recusa com a cura. `--tudo`, `--desde` e `--penduradas` sao frios e
        # nao entregam; so `fila ler <eu>` entrega a carta e deixa trata-la (#2856 linha 463).
        sys.stderr.write(
            f"cura: carta nao lida nao se trata; entregue-a com `fila ler {alvo}` (a leitura "
            "quente, sem --tudo/--desde/--penduradas) e trate de novo\n")
    if falhou:
        sys.exit(1)

# ---------- enviar ----------
def _assunto_do_corpo(corpo: str, limite: int = 120) -> str:
    """Primeira linha não vazia do corpo, normalizada e truncada ao limite."""
    for linha in corpo.splitlines():
        texto = " ".join(linha.split())
        if texto:
            return texto if len(texto) <= limite else texto[:limite - 3].rstrip() + "..."
    return ""


def _separa_destinatarios_e_corpo_pos(destinatarios: list, corpo_inicial: str = None):
    """Suporta `fila enviar <dest> "<msg>"` (DT 357): quando nenhum `--corpo` foi
    passado e o ultimo argumento posicional nao e uma persona valida (mas os
    anteriores sao), separa-o como candidato a corpo posicional sem tocar stdin
    antes de validar os destinatarios."""
    if (
        not (corpo_inicial or "").strip()
        and len(destinatarios) >= 2
        and personas_validas() is not None
        and all(canoniza_persona(d) for d in destinatarios[:-1])
        and not canoniza_persona(destinatarios[-1])
        and not destinatarios[-1].startswith(PREFIXO_BOT)
    ):
        return destinatarios[:-1], destinatarios[-1]
    return destinatarios, None


def _resolve_corpo_enviar(corpo_opt: str = None, corpo_pos: str = None) -> str:
    if (corpo_opt or "").strip():
        return corpo_opt
    corpo_stdin = ""
    try:
        if not sys.stdin.isatty():
            corpo_stdin = sys.stdin.read()
    except OSError:
        corpo_stdin = ""
    if corpo_stdin.strip():
        if corpo_pos is not None:
            valida_persona(corpo_pos)
        return corpo_stdin
    if corpo_pos is not None:
        return corpo_pos
    return corpo_stdin


def _valida_responde(rc, responde: str, eu: str = None):
    """Recusa `--responde` cujo msgid nao existe na malha (DT 439)."""
    if hasattr(rc, "get") and rc.get(f"msgid:{responde}") is not None:
        return
    caixas = []
    if eu:
        caixas.append(eu)
    for p in sorted(personas_validas() or set()):
        if p not in caixas:
            caixas.append(p)
    if _achar_na_malha(rc, responde, caixas):
        return
    sys.stderr.write(
        f'erro: --responde "{responde}" nao existe na malha (expirado >7d ou id errado).\n'
    )
    sys.exit(1)


def cmd_enviar(rc, eu: str, args):
    de = args.de or eu
    if de != eu:
        sys.stderr.write(
            f'erro: --de "{de}" nao bate com a identidade da sessao ({eu}) — remetente nao se forja.\n'
        )
        sys.exit(1)
    tipo = args.tipo or "pedido"
    if tipo not in TIPOS_VALIDOS:
        sys.stderr.write(f"erro: tipo invalido: {tipo}\n  validos: {', '.join(sorted(TIPOS_VALIDOS))}\n")
        sys.exit(1)
    contestacao = tipo == TIPO_CONTESTACAO
    if contestacao and not args.ref:
        sys.stderr.write("erro: --tipo contestacao exige --ref <indicador contestado>\n")
        sys.exit(2)
    destinatarios = list(getattr(args, "destinatarios", None) or [args.destinatario])
    corpo_opt = getattr(args, "corpo_opt", None)
    destinatarios, corpo_pos = _separa_destinatarios_e_corpo_pos(destinatarios, corpo_opt)
    for dest in destinatarios:
        valida_persona(dest)
    valida_persona(de)
    # Grava sempre o nome canonico: a caixa e uma so, qualquer que seja a caixa
    # alta que o chamador digitou.
    destinatarios = [canoniza_persona(d) for d in destinatarios]
    de = canoniza_persona(de)
    for dest in destinatarios:
        so_par_permitido(de, dest, _json_mode(args))
    if args.responde:
        _valida_responde(rc, args.responde, eu)

    corpo = _resolve_corpo_enviar(corpo_opt, corpo_pos)
    if not corpo.strip():
        sys.stderr.write("erro: fundamento vazio (corpo em stdin)\n" if contestacao else "erro: corpo vazio\n")
        sys.exit(1)
    assunto = (args.assunto or "").strip() or _assunto_do_corpo(corpo)

    for dest in destinatarios:
        stream = stream_key(dest)
        existentes = {m["msgid"] for m in frias(rc, dest)}
        msgid = gerar_msgid(de, existentes, rc)
        tecnico = rc.xadd(stream, {
            "id": msgid, "de": de, "tipo": tipo, "assunto": assunto,
            "ref": args.ref or "", "responde": args.responde or "", "corpo": corpo,
        })
        _registra_msgid(rc, msgid, dest, tecnico, de)
        print(msgid)

    # DT 336: responder uma carta da propria caixa ja a da por tratada (at-least-once: ack apos XADD).
    if args.responde:
        for mid, res in tratar(rc, eu, [args.responde]):
            if res == "tratada":
                sys.stderr.write(f"responde: {mid} tratada\n")
            elif res == "ja tratada":
                sys.stderr.write(f"responde: {mid} ja estava tratada\n")
            elif res == "nao existe":
                for dest in destinatarios:
                    achou = _achar_na_malha(rc, mid, [dest])
                    if achou and (canoniza_persona(achou[2].get("de", "")) or achou[2].get("de", "")) == eu:
                        tratar(rc, dest, [mid])


# ---------- carta de bot (#3884) ----------
# O bot e ficha da raiz de classe automacao (spec automacao-gestao): nao tem sessao, nao tem
# caixa e nao e persona. Assina como `bot:<slug>`, o mesmo ator que o `bot` grava nos eventos, e
# so de dentro do proprio `bot rodar <slug>`, que poe o slug em PF_BOT_SLUGS no ambiente do
# filho: o remetente segue sem se forjar, porque a porta nao deixa sessao definir PF_*. Resposta
# a bot nao existe: quem responde e a cadeira dona, e a carta diz qual.
PREFIXO_BOT = "bot:"


def remetente_bot(de: str):
    """O slug do bot que assina, se `de` e `bot:<slug>` e o processo roda dentro dele; senao sai 1."""
    slug = de[len(PREFIXO_BOT):]
    cadeia = [s for s in os.environ.get("PF_BOT_SLUGS", "").split(",") if s]
    if not slug or slug not in cadeia:
        sys.stderr.write(f'erro: --de "{de}" so vale dentro de `bot rodar {slug or "<slug>"}` '
                         "— remetente nao se forja.\n")
        sys.exit(1)
    return slug


def cmd_enviar_bot(rc, args):
    de = PREFIXO_BOT + remetente_bot(args.de)
    tipo = args.tipo or "pedido"
    destinatarios = list(getattr(args, "destinatarios", None) or [args.destinatario])
    corpo_opt = getattr(args, "corpo_opt", None)
    destinatarios, corpo_pos = _separa_destinatarios_e_corpo_pos(destinatarios, corpo_opt)
    for dest in destinatarios:
        valida_persona(dest)
    destinatarios = [canoniza_persona(d) for d in destinatarios]
    corpo = _resolve_corpo_enviar(corpo_opt, corpo_pos)
    if not corpo.strip():
        sys.stderr.write("erro: corpo vazio\n")
        sys.exit(1)
    assunto = (args.assunto or "").strip() or _assunto_do_corpo(corpo)
    if args.responde:
        _valida_responde(rc, args.responde)
    for dest in destinatarios:
        existentes = {m["msgid"] for m in frias(rc, dest)}
        msgid = gerar_msgid(de.replace(":", "-"), existentes, rc)
        tecnico = rc.xadd(stream_key(dest), {
            "id": msgid, "de": de, "tipo": tipo, "assunto": assunto,
            "ref": args.ref or "", "responde": args.responde or "", "corpo": corpo,
        })
        _registra_msgid(rc, msgid, dest, tecnico, de)
        print(msgid)


# ---------- contestar ----------
# Quem manda a contestacao pela face e o dono: a porta abre a chamada da face sem cadeira e com o `sub` dele em
# PF_SUJEITO, e entrega o fundamento em PF_FUNDAMENTO (R22). Chamada por cadeira, o remetente e a cadeira e o
# fundamento vem no stdin, como no `enviar`. O destinatario e a cadeira que configurou o indicador (R24).
REMETENTE_DA_FACE = "dono"


def cmd_contestar(rc, args):
    cadeira = os.environ.get("PF_CADEIRA", "").strip()
    if cadeira:
        valida_persona(cadeira)
        de = canoniza_persona(cadeira)
    elif os.environ.get("PF_SUJEITO", "").strip():
        de = REMETENTE_DA_FACE
    else:
        sys.stderr.write("erro: contestar sem cadeira nem sujeito: quem contesta e uma cadeira ou o dono pela face\n")
        sys.exit(2)
    indicador = (args.indicador or "").strip()
    if not indicador:
        sys.stderr.write("erro: contestar exige --indicador <nome do indicador contestado>\n")
        sys.exit(2)
    valida_persona(args.destinatario)
    para = canoniza_persona(args.destinatario)
    fundamento = (os.environ.get("PF_FUNDAMENTO") or "").strip()
    if not fundamento and not sys.stdin.isatty():
        fundamento = sys.stdin.read().strip()
    if not fundamento:
        sys.stderr.write("erro: contestar pede o fundamento (pela face, o texto do dono; por cadeira, no stdin)\n")
        sys.exit(2)
    existentes = {m["msgid"] for m in frias(rc, para)}
    msgid = gerar_msgid(de, existentes, rc)
    tecnico = rc.xadd(stream_key(para), {
        "id": msgid, "de": de, "tipo": TIPO_CONTESTACAO, "assunto": f"contestacao do indicador: {indicador}",
        "ref": indicador, "responde": "", "corpo": fundamento,
    })
    _registra_msgid(rc, msgid, para, tecnico, de)
    print(json.dumps({"msgid": msgid, "de": de, "para": para, "tipo": TIPO_CONTESTACAO, "indicador": indicador},
                     ensure_ascii=False))


def build_parser():
    ap = argparse.ArgumentParser(prog="fila", add_help=False)
    ap.add_argument("--eu", default=None)
    ap.add_argument("--sessao-id", dest="sessao_id", default=None)
    sub = ap.add_subparsers(dest="verbo")

    p_status = sub.add_parser("status", add_help=False)
    p_status.add_argument("persona", nargs="?", default=None)
    p_status.add_argument("--todas", action="store_true")
    p_status.add_argument("--json", action="store_true")
    p_status.add_argument("--eu", default=None)
    p_status.add_argument("--sessao-id", dest="sessao_id", default=None)

    p_ler = sub.add_parser("ler", add_help=False)
    p_ler.add_argument("persona", nargs="?", default=None)
    p_ler.add_argument("remetente", nargs="?", default=None)
    p_ler.add_argument("--tudo", nargs="?", const=True, default=False)
    p_ler.add_argument("--desde", default=None)
    p_ler.add_argument("--remetente", "--de", dest="remetente_opt", default=None)
    p_ler.add_argument("--para", dest="para_opt", default=None)
    p_ler.add_argument("--todas", action="store_true")
    p_ler.add_argument("--penduradas", action="store_true")
    p_ler.add_argument("--enviadas", action="store_true")
    p_ler.add_argument("--id", dest="msgid", default=None)
    p_ler.add_argument("--ids", action="store_true")
    p_ler.add_argument("--json", action="store_true")
    p_ler.add_argument("--eu", default=None)
    p_ler.add_argument("--sessao-id", dest="sessao_id", default=None)

    p_tratar = sub.add_parser("tratar", add_help=False)
    p_tratar.add_argument("msgids", nargs="*")
    p_tratar.add_argument("--caixa", dest="persona", default=None)
    p_tratar.add_argument("--de", "--remetente", dest="de", default=None)
    p_tratar.add_argument("--tipo", default=None)
    p_tratar.add_argument("--assunto", default=None)
    p_tratar.add_argument("--ate", default=None)
    p_tratar.add_argument("--eu", default=None)
    p_tratar.add_argument("--sessao-id", dest="sessao_id", default=None)

    p_tipos = sub.add_parser("tipos", add_help=False)
    p_tipos.add_argument("--eu", default=None)

    p_enviar = sub.add_parser("enviar", add_help=False)
    p_enviar.add_argument("destinatarios", nargs="+", metavar="destinatario")
    p_enviar.add_argument("--de", default=None)
    p_enviar.add_argument("--tipo", default=None)
    p_enviar.add_argument("--assunto", default=None)
    p_enviar.add_argument("--corpo", "-m", dest="corpo_opt", default=None)
    p_enviar.add_argument("--ref", default=None)
    p_enviar.add_argument("--responde", default=None)
    p_enviar.add_argument("--eu", default=None)
    p_enviar.add_argument("--sessao-id", dest="sessao_id", default=None)

    p_contestar = sub.add_parser("contestar", add_help=False)
    p_contestar.add_argument("destinatario")
    p_contestar.add_argument("--indicador", default=None)

    return ap


def uso(codigo: int = 2):
    out = sys.stdout if codigo == 0 else sys.stderr
    out.write(
        "uso:\n"
        "  fila status [<persona>] [--todas] [--json]\n"
        "  fila ler [<persona>] [--json]            so o que chegou desde a ultima leitura (fica pendurada ate tratar)\n"
        "  fila ler [<persona>] --penduradas        o que nao foi tratado: lidas sem ack + nao lidas; nao move nada\n"
        "  fila ler [<persona>] --tudo [remetente]  historico dos 7 dias, nao move o ponteiro (ou --remetente / --de <slug>)\n"
        "  fila ler [<persona>] --desde <data> [remetente]   historico desde AAAA-MM-DD ou AAAAMMDDTHHMMSS (ou --remetente / --de <slug>)\n"
        "  fila ler --enviadas [destinatario]       cartas que voce enviou nos 7 dias (frio; aceita --para <slug>)\n"
        "  fila ler --id <msgid>                    le uma carta especifica (destinatario ou remetente, sem mover ponteiro)\n"
        "  fila ler ... --ids                       so os msgids, um por linha (vale com --penduradas, --tudo, --desde)\n"
        "  fila tratar <msgid>... [--caixa <p>]     ack: a carta virou ato (resposta, card, mesa) ou foi superada\n"
        "  fila tratar --de <remetente> [--tipo <t>] [--assunto <trecho>] [--ate <data>] [--caixa <p>]\n"
        "              ack em lote do que nao foi tratado e casa o seletor; --ate AAAA-MM-DD ou AAAAMMDDTHHMMSS\n"
        "  fila enviar <destinatario>... [--tipo <t>] [--assunto <a>] [--ref <r>] [--responde <id>] [--corpo <txt>]\n"
        "              (corpo em stdin ou posicional final `fila enviar <dest> \"<msg>\"`; default: --tipo pedido, --assunto = 1a linha)\n"
        "              --tipo contestacao: --ref e o indicador contestado, o corpo e o fundamento\n"
        "  fila tipos                               lista os tipos validos de --tipo\n"
        "  fila contestar <cadeira> --indicador <nome>   contestacao a cadeira que configurou o indicador;\n"
        "              o fundamento vem no stdin (pela face, no envelope da porta)\n"
        "  opcoes comuns: --eu <cadeira> · --sessao-id <id> · --help / -h\n"
    )
    sys.exit(codigo)


def main():
    argv = sys.argv[1:]
    if any(a in ("-h", "--help", "--ajuda") for a in argv) or (argv and argv[0] in ("ajuda", "help")):
        uso(0)
    ap = build_parser()
    args, _resto = ap.parse_known_args()
    if _resto:
        resto_limpo = []
        idx = 0
        while idx < len(_resto):
            tok = _resto[idx]
            if tok == "--eu" and idx + 1 < len(_resto):
                if not getattr(args, "eu", None):
                    args.eu = _resto[idx + 1]
                idx += 2
                continue
            if tok.startswith("--eu="):
                if not getattr(args, "eu", None):
                    args.eu = tok.split("=", 1)[1]
                idx += 1
                continue
            if tok == "--sessao-id" and idx + 1 < len(_resto):
                if not getattr(args, "sessao_id", None):
                    args.sessao_id = _resto[idx + 1]
                idx += 2
                continue
            if tok.startswith("--sessao-id="):
                if not getattr(args, "sessao_id", None):
                    args.sessao_id = tok.split("=", 1)[1]
                idx += 1
                continue
            if tok.startswith("-"):
                sys.stderr.write(f"fila: erro: opção desconhecida: '{tok}'\n")
                uso(2)
            resto_limpo.append(tok)
            idx += 1
        _resto = resto_limpo
    if not args.verbo:
        uso(2)
    if args.verbo == "ler":
        if getattr(args, "remetente_opt", None):
            args.remetente = args.remetente_opt
        elif isinstance(args.tudo, str):
            if not args.remetente:
                args.remetente = args.tudo
            args.tudo = True
        elif not args.remetente and _resto:
            args.remetente = _resto[0]
        elif (
            args.desde
            and args.persona
            and not args.remetente
            and "--desde" in argv
        ):
            # `fila ler --desde <data> <remetente>` sem `<persona>` antes de `--desde`:
            # o unico posicional depois de `--desde <data>` e o filtro de remetente.
            idx_desde = argv.index("--desde")
            pos_antes = [
                t for t in argv[1:idx_desde]
                if not t.startswith("-")
            ]
            if not pos_antes and argv[idx_desde + 2:] and argv[idx_desde + 2] == args.persona:
                args.remetente = args.persona
                args.persona = None
    # `tipos` responde ANTES de tocar a malha: e info estatica e deve funcionar offline.
    if args.verbo == "tipos":
        sys.stdout.write("\n".join(sorted(TIPOS_VALIDOS)) + "\n")
        sys.exit(0)
    if args.verbo == "enviar":
        if args.tipo and args.tipo not in TIPOS_VALIDOS:
            sys.stderr.write(f"erro: tipo invalido: {args.tipo}\n  validos: {', '.join(sorted(TIPOS_VALIDOS))}\n")
            sys.exit(1)
        destinatarios = list(getattr(args, "destinatarios", None) or [args.destinatario])
        for dest in destinatarios:
            if dest.startswith(PREFIXO_BOT):
                sys.stderr.write("erro: bot nao tem caixa; responda a cadeira dona dele, que a carta "
                                 "nomeia (`bot listar` diz o dono)\n")
                sys.exit(1)
        if (args.de or "").startswith(PREFIXO_BOT):
            # o bot chega sem cadeira: o remetente se resolve no ato, e nao por resolve_eu
            rc = r_conn()
            try:
                rc.ping()
            except redis.exceptions.RedisError as e:
                sys.stderr.write(f"erro: nao alcancei a malha msg ({REDIS_HOST}:{REDIS_PORT}): {e}\n")
                sys.exit(1)
            cmd_enviar_bot(rc, args)
            return
    if args.verbo == "contestar":
        # a face chega sem cadeira: o remetente se resolve dentro do ato, e nao por resolve_eu
        rc = r_conn()
        try:
            rc.ping()
        except redis.exceptions.RedisError as e:
            sys.stderr.write(f"erro: nao alcancei a malha msg ({REDIS_HOST}:{REDIS_PORT}): {e}\n")
            sys.exit(1)
        cmd_contestar(rc, args)
        return
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
    elif args.verbo == "tratar":
        cmd_tratar(rc, eu, args)
    elif args.verbo == "enviar":
        cmd_enviar(rc, eu, args)
    else:
        uso(2)


if __name__ == "__main__":
    main()
