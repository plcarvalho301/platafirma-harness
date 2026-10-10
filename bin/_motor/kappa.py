"""O juiz contra a primeira passada do dono (card #3350, feature #3340).

Fonte: padrao protocolo-medicao-rag rev 2, «O juiz» 2 e 3: kappa de Cohen sobre os graus e acerto na
classe enganosa, contra a PRIMEIRA passada do dono, nunca contra a conferência, e nunca concordância bruta
como medida. Os graus são os do critério que a tela mostrou (v1 tem cinco: o padrão diz quatro, a tela
acrescentou «irrelevante», que julga a pergunta; o kappa usa os graus que de fato existiram na marca).

Tudo aqui é puro: recebe eventos, lote e marcas do juiz já lidos, devolve números e listas.
"""
from __future__ import annotations

import random
import statistics

BOOTSTRAP = 2000
SEMENTE = 3350
ENGANOSA = "enganosa"


# --- o que o dono marcou -----------------------------------------------------------------------------------

def marcas_do_dono(eventos: list, passada: str = "primeira") -> dict:
    """resposta_id -> a marca mais recente da passada (decisão do dono, #3349 comentário #1884: na repetição
    acidental vale a mais recente). `repeticoes` conta quantas respostas tiveram mais de uma marca."""
    out, vistas = {}, {}
    for e in sorted((e for e in eventos if e["tipo"] == "marca" and e["passada"] == passada), key=lambda e: e["id"]):
        vistas[e["resposta_id"]] = vistas.get(e["resposta_id"], 0) + 1
        out[e["resposta_id"]] = {"qualidade": e["qualidade"], "embasamento": e["embasamento"],
                                 "ms_ativos": e.get("ms_ativos") or 0, "gravado_em": e.get("gravado_em")}
    for rid, n in vistas.items():
        out[rid]["marcas"] = n
    return out


def excluidas(eventos: list, passada: str = "primeira") -> set:
    return {e["pergunta_id"] for e in eventos if e["tipo"] == "exclusao" and e["passada"] == passada}


def preferencias(eventos: list, passada: str = "primeira") -> dict:
    out = {}
    for e in sorted((e for e in eventos if e["tipo"] == "preferencia" and e["passada"] == passada), key=lambda e: e["id"]):
        out[e["pergunta_id"]] = {"escolha": e.get("escolha"), "ms_ativos": e.get("ms_ativos") or 0}
    return out


# --- concordância --------------------------------------------------------------------------------------------

def cohen_kappa(pares: list):
    """pares: [(dono, juiz)]. None quando indefinido (sem par, ou acaso esperado = 1)."""
    n = len(pares)
    if not n:
        return None
    po = sum(1 for a, b in pares if a == b) / n
    cats = {a for a, _ in pares} | {b for _, b in pares}
    pe = sum((sum(1 for a, _ in pares if a == c) / n) * (sum(1 for _, b in pares if b == c) / n) for c in cats)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def bootstrap_por_pergunta(por_pergunta: dict, n: int = BOOTSTRAP, semente: int = SEMENTE) -> dict:
    """Intervalo de 95% do kappa reamostrando PERGUNTAS (as respostas da mesma pergunta não são independentes).
    `por_pergunta`: pergunta_id -> [(dono, juiz)]. Reamostra indefinida (todas num grau só) não entra e se conta."""
    ids = sorted(por_pergunta)
    rnd = random.Random(semente)
    vals, indef = [], 0
    for _ in range(n):
        amostra = [p for _ in ids for p in por_pergunta[rnd.choice(ids)]]
        k = cohen_kappa(amostra)
        if k is None:
            indef += 1
        else:
            vals.append(k)
    if not vals:
        return {"baixo": None, "alto": None, "reamostras": n, "indefinidas": indef}
    vals.sort()
    return {"baixo": vals[int(0.025 * (len(vals) - 1))], "alto": vals[int(round(0.975 * (len(vals) - 1)))],
            "reamostras": n, "indefinidas": indef}


def enganosa(pares: list) -> dict:
    """Acerto na classe enganosa nos dois sentidos, com o n de cada: das que o dono marcou, quantas o juiz marcou
    (sensibilidade); das que o juiz marcou, quantas o dono marcou (precisão)."""
    dono = [b for a, b in pares if a == ENGANOSA]
    juiz = [a for a, b in pares if b == ENGANOSA]
    return {"dono_marcou": len(dono), "juiz_acompanhou": sum(1 for b in dono if b == ENGANOSA),
            "juiz_marcou": len(juiz), "dono_confirmou": sum(1 for a in juiz if a == ENGANOSA)}


def por_grau(pares: list) -> dict:
    cats = sorted({a for a, _ in pares} | {b for _, b in pares})
    return {c: {"dono": sum(1 for a, _ in pares if a == c), "juiz": sum(1 for _, b in pares if b == c),
                "os_dois": sum(1 for a, b in pares if a == b == c)} for c in cats}


def concordancia(lote: dict, dono: dict, juiz: dict, fora: set) -> dict:
    """O pacote do ato `--kappa`. `lote`: o lote com braço (respostas com pergunta_id); `dono`: marcas_do_dono;
    `juiz`: resposta_id -> {qualidade, embasamento}; `fora`: perguntas excluídas pelo dono."""
    por_pergunta, sem_dono, sem_juiz = {}, [], []
    for r in lote["respostas"]:
        rid, pid = r["resposta_id"], r["pergunta_id"]
        if pid in fora:
            continue
        if rid not in dono:
            sem_dono.append(rid)
            continue
        if rid not in juiz:
            sem_juiz.append(rid)
            continue
        por_pergunta.setdefault(pid, []).append((dono[rid]["qualidade"], juiz[rid]["qualidade"]))
    pares = [p for v in por_pergunta.values() for p in v]
    return {"n_respostas": len(pares), "n_perguntas": len(por_pergunta), "kappa": cohen_kappa(pares),
            "intervalo": bootstrap_por_pergunta(por_pergunta), "enganosa": enganosa(pares), "por_grau": por_grau(pares),
            "sem_marca_do_dono": sem_dono, "sem_marca_do_juiz": sem_juiz, "perguntas_excluidas": sorted(fora)}


# --- divergências e tempo ------------------------------------------------------------------------------------

def divergencias(lote: dict, dono: dict, juiz: dict, fora: set) -> list:
    """Divergência é qualidade diferente. O embasamento saiu da avaliação por ordem do dono (09/10/2026, #3352): a tela
    mostra só o título das seções e ele não tem como conferir sem abrir a obra. Sem braço: a linha leva o
    resposta_id opaco, a pergunta e os dois graus."""
    perg = {p["pergunta_id"]: p["texto"] for p in lote["corpo"]["perguntas"]}
    out = []
    for r in lote["respostas"]:
        rid, pid = r["resposta_id"], r["pergunta_id"]
        if pid in fora or rid not in dono or rid not in juiz:
            continue
        d, j = dono[rid], juiz[rid]
        if d["qualidade"] != j["qualidade"]:
            out.append({"resposta_id": rid, "pergunta_id": pid, "pergunta": perg.get(pid, ""),
                        "dono": {"qualidade": d["qualidade"]}, "juiz": {"qualidade": j["qualidade"]}})
    return out


def matriz(lote: dict, dono: dict, juiz: dict, fora: set, graus: tuple) -> dict:
    """grau do dono -> grau do juiz -> quantas respostas: a tabela que mostra PARA ONDE o juiz desvia."""
    m = {a: {b: 0 for b in graus} for a in graus}
    for r in lote["respostas"]:
        rid = r["resposta_id"]
        if r["pergunta_id"] in fora or rid not in dono or rid not in juiz:
            continue
        m.setdefault(dono[rid]["qualidade"], {b: 0 for b in graus})
        m[dono[rid]["qualidade"]][juiz[rid]["qualidade"]] = m[dono[rid]["qualidade"]].get(juiz[rid]["qualidade"], 0) + 1
    return m


def _p90(vals: list):
    if not vals:
        return None
    s = sorted(vals)
    return s[max(0, -(-9 * len(s) // 10) - 1)]       # posição de ordem ceil(0,9 n), base 1


def tempo(lote: dict, dono: dict, prefs: dict, fora: set) -> dict:
    """Tempo ativo, em segundos: por resposta (a marca final) e por pergunta (as marcas mais a preferência)."""
    por_resp, por_perg = [], {}
    for r in lote["respostas"]:
        rid, pid = r["resposta_id"], r["pergunta_id"]
        if pid in fora or rid not in dono:
            continue
        s = dono[rid]["ms_ativos"] / 1000
        por_resp.append(s)
        por_perg[pid] = por_perg.get(pid, 0.0) + s
    for pid, p in prefs.items():
        if pid in por_perg:
            por_perg[pid] += p["ms_ativos"] / 1000
    pp = list(por_perg.values())
    return {"por_resposta": {"n": len(por_resp), "mediana": statistics.median(por_resp) if por_resp else None,
                             "p90": _p90(por_resp), "total": sum(por_resp)},
            "por_pergunta": {"n": len(pp), "mediana": statistics.median(pp) if pp else None, "p90": _p90(pp),
                             "total": sum(pp)}}


# --- o lote de conferência -----------------------------------------------------------------------------------

def lote_de_conferencia(lote: dict, divs: list, lote_id: str, rid_novo, semente: str) -> dict:
    """O envelope de `motor marcacao lote gravar` com só as respostas divergentes, passada conferencia, mesma
    criterio_versao, ordem nova (perguntas e respostas embaralhadas pela semente). O resposta_id é chave do banco,
    então cada resposta ganha id novo (`rid_novo()`), e o carimbo interno guarda o de origem. A nota do juiz não
    entra em lugar nenhum do lote (padrão, «O juiz» §2)."""
    alvo = {d["resposta_id"] for d in divs}
    interna = {r["resposta_id"]: r for r in lote["respostas"]}
    perguntas = []
    respostas = []
    rnd = random.Random(semente)
    for p in lote["corpo"]["perguntas"]:
        escolhidas = [r for r in p["respostas"] if r["resposta_id"] in alvo]
        if not escolhidas:
            continue
        rnd.shuffle(escolhidas)
        novas = []
        for r in escolhidas:
            novo = rid_novo()
            novas.append({"resposta_id": novo, "texto": r["texto"], "secoes": r["secoes"]})
            o = interna[r["resposta_id"]]
            respostas.append({"resposta_id": novo, "pergunta_id": p["pergunta_id"], "braco": o["braco"],
                              "secoes": o["secoes"], "mapa": o["mapa"],
                              "carimbo": {**(o.get("carimbo") or {}), "conferencia_de": r["resposta_id"],
                                          "lote_de_origem": lote["lote_id"]}})
        perguntas.append({"pergunta_id": p["pergunta_id"], "texto": p["texto"], "cadeira": p["cadeira"],
                          "data": p["data"], "respostas": novas})
    rnd.shuffle(perguntas)
    corpo = {"lote_id": lote_id, "criterio_versao": lote["criterio_versao"], "passada": "conferencia",
             "perguntas": perguntas}
    return {"lote_id": lote_id, "gabarito_versao_id": lote["gabarito_versao_id"], "criterio_versao": lote["criterio_versao"],
            "passada": "conferencia", "ativo": False, "corpo": corpo,
            "carimbo": {**(lote.get("carimbo") or {}), "conferencia_de": lote["lote_id"]}, "respostas": respostas}
