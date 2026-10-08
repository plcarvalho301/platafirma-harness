"""`motor rag sortear biblioteca` — o sorteio do estrato sentido da escada (card #3349, feature #3340).

Fonte: padrao protocolo-medicao-rag rev 2, «Estratos e tamanho» e «Fonte e filtros». Sorteia do log de
perguntas que as cadeiras fizeram ao motor (acervo.evento_recuperacao), aplica os filtros do padrão
contando cada exclusão por motivo, propõe o estrato por máquina (o dono confirma) e devolve a lista
em ordem sorteada: 200 de sentido, mais 20 de reserva; as 20 primeiras da ordem são o piloto.

Trava do padrão: a pergunta nunca se escolhe olhando o retorno da busca. Este módulo lê o texto da
pergunta e a metadata do evento (ordem, origem, partição, sessão) e nada do que o motor devolveu,
exceto o fato de o evento ter servido seção de impressão da biblioteca (inferência de partição).
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import unicodedata
from collections import Counter

PILOTO = 20
PRINCIPAL = 200
RESERVA = 20
MIN_POR_CADEIRA = 5
ORIGENS_FORA = ("abertura", "bench", "sombra", "autoteste")
SEM_CADEIRA = "desconhecida"

# Identificador (estrato à parte, rotulado por construção): expressão de código ou chave de documento.
_IDENTIFICADOR = re.compile(
    r"(?:\b(?:arq|seg|ont|min|dec)[:\-]\s?\d+|#\d{3,5}\b"
    r"|\b(?:adr|spec|guia|padrao|padrão|runbook|minuta|levantamento|benchmark|parecer)\s+[a-z0-9][a-z0-9\-]+)",
    re.IGNORECASE,
)
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def normalizar(texto: str) -> str:
    """Forma normalizada da duplicata: NFC, caixa e espaço (padrão, «Fonte e filtros» 4)."""
    return " ".join(unicodedata.normalize("NFC", texto or "").casefold().split())


def estrato_proposto(pergunta: str) -> str:
    return "identificador" if _IDENTIFICADOR.search(pergunta or "") else "sentido"


def filtrar(eventos, cadeiras, textos_fora, *, aceitar_sem_ordem=False, aceitar_sem_cadeira=False):
    """(candidatos, excluidas). `eventos` ordenados por criado_em; cada um traz id, ordem_id, pergunta,
    particao, origem, sessao_id, criado_em e secao_em_impressao (servida de impressão da biblioteca).
    `cadeiras` mapeia sessao_id -> cadeira. `textos_fora`: formas normalizadas de pergunta que são da
    bateria (gabarito e eventos de bench/sombra/autoteste), para tirar do log o que não é demanda.
    """
    ex: Counter = Counter()
    vistos_ordem: set = set()
    vistos_texto: set = set()
    candidatos = []
    for e in eventos:
        origem = e.get("origem")
        if origem in ORIGENS_FORA:
            ex[f"origem {origem}"] += 1
            continue
        part = e.get("particao")
        if part is None:
            if not e.get("secao_em_impressao"):
                ex["sem partição inferível (sem seção servida da biblioteca)"] += 1
                continue
        elif part != "biblioteca":
            ex[f"partição {part}"] += 1
            continue
        ordem = (e.get("ordem_id") or "").strip()
        if ordem:
            if ordem in vistos_ordem:
                ex["reformulação na mesma ordem"] += 1
                continue
            vistos_ordem.add(ordem)
        elif not aceitar_sem_ordem:
            ex["sem ordem_id"] += 1
            continue
        forma = normalizar(e["pergunta"])
        if not forma:
            ex["pergunta vazia"] += 1
            continue
        if forma in textos_fora:
            ex["igual a pergunta da bateria (gabarito, bench, sombra ou autoteste)"] += 1
            continue
        if forma in vistos_texto:
            ex["duplicata por forma normalizada"] += 1
            continue
        cadeira = cadeiras.get((e.get("sessao_id") or "").strip())
        if not cadeira:
            if not aceitar_sem_cadeira:
                ex["sem cadeira (sessao_id nulo ou sem linha em sessao.sessao)"] += 1
                continue
            cadeira = SEM_CADEIRA
        vistos_texto.add(forma)
        candidatos.append({**e, "cadeira": cadeira, "estrato": estrato_proposto(e["pergunta"])})
    return candidatos, ex


def separar_estratos(candidatos, excluidas: Counter):
    """Fica o sentido; o identificador e o que tem cadeira com menos de cinco saem, contados."""
    sentido = []
    for c in candidatos:
        if c["estrato"] == "identificador":
            excluidas["estrato identificador (rotulado por construção, fora deste sorteio)"] += 1
        else:
            sentido.append(c)
    por_cadeira = Counter(c["cadeira"] for c in sentido)
    pequenas = {k for k, n in por_cadeira.items() if n < MIN_POR_CADEIRA}
    if pequenas:
        excluidas[f"cadeira com menos de {MIN_POR_CADEIRA} no estrato sentido"] += sum(por_cadeira[k] for k in pequenas)
        sentido = [c for c in sentido if c["cadeira"] not in pequenas]
    return sentido, sorted(pequenas)


def alocar(contagem: dict, total: int) -> dict:
    """Cota por cadeira, proporcional ao pool, pelo maior resto; nunca acima do que a cadeira tem."""
    soma = sum(contagem.values())
    if soma <= total:
        return dict(contagem)
    base = {c: int(total * n / soma) for c, n in contagem.items()}
    falta = total - sum(base.values())
    for c in sorted(contagem, key=lambda c: (-(total * contagem[c] / soma - base[c]), c))[:falta]:
        base[c] += 1
    return {c: min(v, contagem[c]) for c, v in base.items()}


def sortear(sentido, semente: str, total: int = PRINCIPAL + RESERVA):
    """Sorteio estratificado por cadeira e ordem sorteada. Cada item ganha `posicao` (1..n) e `papel`:
    piloto (as 20 primeiras), principal (até 200) e reserva (as que sobram, até 20)."""
    rng = random.Random(semente)
    por_cadeira: dict = {}
    for c in sorted(sentido, key=lambda c: (c["cadeira"], c["id"])):
        por_cadeira.setdefault(c["cadeira"], []).append(c)
    cotas = alocar({k: len(v) for k, v in por_cadeira.items()}, total)
    escolhidas = []
    for cadeira in sorted(por_cadeira):
        lista = por_cadeira[cadeira][:]
        rng.shuffle(lista)
        escolhidas.extend(lista[: cotas[cadeira]])
    rng.shuffle(escolhidas)
    n_principal = max(0, len(escolhidas) - RESERVA) if len(escolhidas) > PRINCIPAL else len(escolhidas)
    n_principal = min(n_principal, PRINCIPAL)
    saida = []
    for i, c in enumerate(escolhidas, 1):
        papel = "reserva" if i > n_principal else ("piloto" if i <= PILOTO else "principal")
        saida.append({**c, "posicao": i, "papel": papel})
    return saida


def linhas_jsonl(lista) -> bytes:
    """A lista que vai ao git: copia o texto da pergunta, evento_id, ordem_id, data e cadeira, para o
    gabarito não expirar com o log (padrão, «Fonte e filtros»)."""
    out = []
    for c in lista:
        out.append(json.dumps({
            "id": "esc-" + c["id"][:8],
            "evento_id": c["id"],
            "ordem_id": c.get("ordem_id") or None,
            "pergunta": c["pergunta"],
            "data": (c.get("criado_em") or "")[:10],
            "cadeira": c["cadeira"],
            "estrato": c["estrato"],
            "estrato_proposto_por": "maquina",
            "estrato_confirmado_pelo_dono": None,
            "posicao": c["posicao"],
            "papel": c["papel"],
        }, ensure_ascii=False, sort_keys=True))
    return ("\n".join(out) + "\n").encode("utf-8")


def sha_blob_git(conteudo: bytes) -> str:
    """O sha que o git daria ao arquivo (`git hash-object`): é o sha_git da gabarito_versao antes do commit."""
    return hashlib.sha1(b"blob %d\0" % len(conteudo) + conteudo).hexdigest()


def relatorio(eventos_n, candidatos, excluidas, sentido, pequenas, lista, semente, flags) -> dict:
    return {
        "semente": semente,
        "flags": flags,
        "eventos_lidos": eventos_n,
        "candidatos": len(candidatos),
        "excluidas": dict(sorted(excluidas.items(), key=lambda kv: -kv[1])),
        "sentido": len(sentido),
        "cadeiras_fora_por_menos_de_cinco": pequenas,
        "por_cadeira_no_pool": dict(sorted(Counter(c["cadeira"] for c in sentido).items())),
        "sorteadas": len(lista),
        "piloto": sum(1 for c in lista if c["papel"] == "piloto"),
        "principal": sum(1 for c in lista if c["papel"] in ("piloto", "principal")),
        "reserva": sum(1 for c in lista if c["papel"] == "reserva"),
        "por_cadeira_sorteadas": dict(sorted(Counter(c["cadeira"] for c in lista).items())),
    }


def e_uuid(valor: str) -> bool:
    return bool(_UUID.match(valor or ""))
