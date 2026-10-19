"""A poda do caderno de chapeu (arq:0120, Emenda de 19/10/2026; card #3884).

Duas vezes por dia o bot `caderno-poda` (Tito Tesourinha) roda `mesa podar` sobre os cadernos de
todas as cadeiras. Este modulo decide; quem grava e o `mesa`. A decisao e pura sobre as entradas
servidas, com as conferencias que olham fora dela (busca no canone, estado de card, verbo)
passadas como funcao, para o teste trocar por stub.

Toda saida e retirada com volta por `mesa restaurar`, ou marca de tombamento; nada se apaga
(arq:0120 §6). A preferencia do dono nao sai pela maquina: e a palavra dele (§7).

As conferencias vieram do `descansar fita` (#3498), que so apontava e so no chapeu tocado.
Limiares medidos em 13/10/2026 sobre os cadernos da ia (comentario no #3498): o canone tirou
0,48-0,66 nas 16 vigentes sas e 0,69-0,73 nas parafrases de ADR e guia; o par lexico tirou ate
0,23 entre vigentes distintas e 0,46-0,56 nas parafrases.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata

PRAZO_LICAO = 30  # dias sem confirmacao: a licao sai retirada (arq:0120 §7, Emenda de 19/10/2026)
CONFIRMACOES_TOMBA = 2  # confirmada duas vezes ou mais: candidata a tombar (§9)
LIMIAR_CANONE = float(os.environ.get("PF_PODA_LIMIAR_CANONE", "0.68"))
LIMIAR_PAR = float(os.environ.get("PF_PODA_LIMIAR_PAR", "0.40"))
# A busca devolve `arquivo` como "<especie> <chave>" ou a chave de ADR (arq:, org:). Parecer,
# levantamento e nota sao material, nao canone: repetir um deles nao faz a entrada duplicata.
CANONE = re.compile(r"^(?:(?:arq|org):\S+|(?:adr|guia|spec|padrao|runbook|lista-de-verificacao) \S+)$")
RE_CARD_CITADO = re.compile(r"(?<![\w/])#(\d{3,5})\b")
RE_VERBO_CITADO = re.compile(r"`([a-z][a-z0-9-]*) [a-z][^`]*`")
RE_CHAPEU_CITADO = re.compile(r"\bchapeu:([a-z0-9-]+)/([a-z0-9-]+)")
RE_ESTADO_CARD = re.compile(r"· ([^·(]+?) \((\w+)\)")
# O que foi ao debito tecnico ja tem morada duravel: a linha do balde (o dono, 13/10/2026, #3501:
# «Se foi pra DT tem que tirar do caderno»).
RE_DEBITO = re.compile(r"#2856\W{0,3}linha\s+(\d+)", re.IGNORECASE)
FORA_DO_PATH = {"git", "docker", "python", "python3", "bash", "sh", "psql", "uv", "pip", "curl",
                "jq", "sudo", "systemctl", "journalctl", "grep", "sed", "awk", "ls", "cat",
                "claude", "npm", "node", "make", "pytest", "ssh", "rg", "find"}
STOP_PAR = set("para pela pelo como mais quando onde antes depois sobre entre cada todo toda nunca "
               "sempre isso esta este essa esse aqui nada fica vira deve pode sem com que nao uma "
               "umas uns dos das nos nas ate".split())

_HARNESS = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def _bin():
    """Verbos irmaos: bin/ da propria release. PF_BIN so aponta outro diretorio (teste com stub)."""
    return os.environ.get("PF_BIN") or os.path.join(_HARNESS, "bin")


def _verbo(nome, *args, timeout=30):
    """(exit, stdout) de um verbo irmao; (None, "") quando nao roda: indeterminado, nao negativa."""
    try:
        p = subprocess.run([os.path.join(_bin(), nome), *args], capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None, ""
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def _palavras(texto):
    s = unicodedata.normalize("NFKD", (texto or "").lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return {w for w in re.findall(r"[a-z0-9_]+", s) if len(w) >= 4 and w not in STOP_PAR}


def semelhanca(a, b):
    """Jaccard das palavras de conteudo: a mesma licao dita duas vezes, nao o mesmo assunto."""
    pa, pb = _palavras(a), _palavras(b)
    return len(pa & pb) / len(pa | pb) if pa and pb else 0.0


def duplicata_do_canone(texto):
    """'<arquivo> (sim X)' do documento de canone que ja diz o mesmo, ou None."""
    rc, out = _verbo("motor", "rag", "buscar", "casa", texto, "--k", "3", "--texto", "nenhum",
                     "--origem", "autoteste")
    if rc != 0:
        return None
    try:
        fontes = json.loads(out.strip().splitlines()[0]).get("fontes") or []
    except (ValueError, IndexError, AttributeError):
        return None
    for f in fontes:
        arq, sim = (f.get("arquivo") or "").strip(), f.get("sim") or 0
        if sim >= LIMIAR_CANONE and CANONE.match(arq):
            return f"{arq} (sim {sim:.2f})"
    return None


def estado_card(n, cache):
    """('vivo'|'morto'|None, rotulo). Morto: apagado, ou terminal sem herdeiro (englobada tem)."""
    if n in cache:
        return cache[n]
    rc, out = _verbo("tarefas", "ler", n)
    if rc is None:
        r = (None, "")
    elif "foi apagado" in out:
        r = ("morto", "apagado")
    else:
        m = RE_ESTADO_CARD.search(out)
        if not m:
            r = (None, "")
        else:
            rotulo, fase = m.group(1).strip(), m.group(2)
            r = (("morto" if fase == "terminal" and rotulo.lower() != "englobada" else "vivo"),
                 rotulo.lower())
    cache[n] = r
    return r


def chapeus_declarados(abertura, cadeira):
    """(slugs, erro) dos chapeus que a persona declara: um subdir por chapeu na abertura publicada."""
    base = os.path.join(abertura, cadeira.lower())
    if not os.path.isdir(base):
        return None, f"abertura da cadeira nao encontrada em {base}"
    return {n for n in os.listdir(base) if os.path.isdir(os.path.join(base, n))}, None


def referencias_mortas(texto, cache, declarados_de):
    """O que o texto cita e nao existe mais. So o texto: o caso e a procedencia da licao, e
    card de procedencia fecha por natureza."""
    mortas = []
    for n in sorted(set(RE_CARD_CITADO.findall(texto or "")), key=int):
        estado, rotulo = estado_card(n, cache)
        if estado == "morto":
            mortas.append(f"#{n} ({rotulo})")
    for v in sorted(set(RE_VERBO_CITADO.findall(texto or "")) - FORA_DO_PATH):
        chave = ("verbo", v)
        if chave not in cache:
            cache[chave] = _verbo("conferir", "existe", "verbo", v)[0]
        if cache[chave] == 1:
            mortas.append(f"verbo {v}")
    for cad, ch in sorted(set(RE_CHAPEU_CITADO.findall(texto or ""))):
        slugs, _ = declarados_de(cad)
        if slugs is not None and ch not in slugs:
            mortas.append(f"chapéu {cad}/{ch}")
    return mortas


def foi_ao_debito(texto):
    """'#2856 linha N' da primeira linha do balde que o texto cita, ou None."""
    m = RE_DEBITO.search(texto or "")
    return f"#2856 linha {m.group(1)}" if m else None


def _br(d):
    return d.strftime("%d/%m/%Y") if d else "?"


def _motivo_de_saida(e, hoje, canone, mortas, cache):
    """O motivo da retirada de uma entrada servida, na ordem da Emenda de 19/10/2026, ou None."""
    cat = e["categoria"]
    if cat == "preferencia":
        return None
    if cat == "premissa" and e.get("vale_ate") and e["vale_ate"] < hoje:
        return f"premissa vencida em {_br(e['vale_ate'])}"
    debito = foi_ao_debito(e["texto"])
    if debito:
        return f"foi ao débito técnico: {debito}"
    conf = e.get("confirmada_em")
    if cat == "licao" and conf and (hoje - conf).days > PRAZO_LICAO:
        return f"venceu sem confirmação desde {_br(conf)} ({PRAZO_LICAO} dias)"
    dup = canone(e["texto"])
    if dup:
        return f"duplicata do cânone {dup}"
    morta = mortas(e["texto"], cache)
    if morta:
        return "referência morta " + ", ".join(morta)
    return None


def decide(entradas, hoje, confirmacoes=None, canone=duplicata_do_canone, mortas=None,
           cache=None):
    """O que a passada faz nas entradas servidas (vigente, fora da aresta, fora de tombamento),
    de todas as cadeiras. Cada entrada e dict com id, cadeira, chapeu, categoria, texto,
    confirmada_em (date) e vale_ate (date ou None). Devolve (retirar, tombar): listas de
    (entrada, motivo). Primeiro sai o que tem motivo de saida; o par de tombamento se procura
    so entre as que ficaram, em qualquer caderno de qualquer cadeira."""
    confirmacoes = confirmacoes or {}
    cache = {} if cache is None else cache
    mortas = mortas or (lambda texto, c: [])
    retirar, ficam = [], []
    for e in entradas:
        motivo = _motivo_de_saida(e, hoje, canone, mortas, cache)
        (retirar.append((e, motivo)) if motivo else ficam.append(e))
    tombar = []
    licoes = [e for e in ficam if e["categoria"] == "licao"]
    for e in licoes:
        n = confirmacoes.get(e["id"], 0)
        if n >= CONFIRMACOES_TOMBA:
            tombar.append((e, f"confirmada {n} vezes"))
            continue
        sim, par = max(((semelhanca(e["texto"], o["texto"]), o) for o in licoes
                        if (o["cadeira"], o["chapeu"]) != (e["cadeira"], e["chapeu"])),
                       key=lambda x: x[0], default=(0.0, None))
        if par is not None and sim >= LIMIAR_PAR:
            tombar.append((e, f"a mesma lição em {par['cadeira']}/{par['chapeu']} c{par['id']} "
                              f"({sim:.2f})"))
    return retirar, tombar
