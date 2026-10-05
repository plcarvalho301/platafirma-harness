"""Braço-sombra do embedder (guia escolha-de-llm §11; card #2925).

Roda DENTRO do contêiner do rag (rag-extractor-api), lançado por
`motor rag medir <particao> --sombra <modelo>[,<modelo>]`. Nunca toca o servido: não escreve
em banco nenhum, não muda env do serviço, carrega os candidatos num processo à parte, num venv
que herda o torch da imagem e só sobe transformers/sentence-transformers.

O que mede, por partição:
- o braço de significado ISOLADO (os outros braços da fusão não dependem do embedder): top-k
  exato do servido (vetores gravados em motor.vetor + embed_query do próprio serviço, com a
  instrução da pergunta servida) contra o top-k exato de cada candidato, com o corpus inteiro da
  partição reembeddado em memória, no mesmo teto de 512 tokens do serviço;
- no gabarito (biblioteca): hit@k e MRR por família, e o piso de abstenção que melhor separa
  positivas de negativas, por modelo — o piso é do embedder, não do motor;
- no replay das perguntas reais do log (acervo.evento_recuperacao): um juiz de fora das duas
  famílias (cross-encoder BAAI/bge-reranker-v2-m3, base XLM-R) pontua o pool unido; nDCG@k por
  modelo e vitória/empate/derrota contra o servido. O juiz é conferido contra o gabarito na
  mesma rodada: concordância de sinal com o MRR do gabarito.

Saída: <saida>/log.txt (progresso) e <saida>/resultado.json (tudo que o verbo resume).
"""
import gc
import json
import math
import os
import random
import re
import sys
import time
import traceback

ARGS = json.loads(os.environ["SOMBRA_ARGS"])
SAIDA = ARGS["saida"]
K = int(ARGS.get("k", 8))
MAX_PERGUNTAS = int(ARGS.get("max_perguntas", 1000))
_LOG = open(os.path.join(SAIDA, "log.txt"), "a", buffering=1)


def log(msg):
    _LOG.write(time.strftime("%H:%M:%S ") + msg + "\n")


import numpy as np  # noqa: E402
import psycopg  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"

# Por candidato: prefixo da pergunta e do trecho (o do cartão do modelo), dimensões a medir
# (a primeira é a que caberia no esquema servido, vetor_d1024), dtype e trust_remote_code.
CANDIDATOS = {
    "nvidia/Nemotron-3-Embed-1B-BF16": {
        "curto": "Nemotron-3-Embed-1B", "q": "query: ", "p": "passage: ",
        "dims": [1024, 2048], "dtype": "bfloat16", "trust": False},
    "perplexity-ai/pplx-embed-v1-0.6b": {
        "curto": "pplx-embed-v1-0.6b", "q": "", "p": "",
        "dims": [1024], "dtype": "float16", "trust": True},
}
SERVIDO = "servido"
_API = {"biblioteca": "obra", "casa": "casa", "obra": "obra"}

SQL_TXT = {
    "obra": """SELECT t.id::text, t.texto, o.id::text, s.ancora, o.arquivo
                 FROM acervo.trecho t
                 JOIN acervo.impressao i ON i.id = t.impressao_id
                 JOIN acervo.obra o ON o.id = i.obra_id
                 JOIN acervo.secao s ON s.id = t.secao_id
                WHERE t.id = ANY(%s::uuid[])""",
    "casa": """SELECT t.id::text, t.texto, c.id::text, s.ancora, coalesce(c.chave, c.path)
                 FROM acervo.casa_trecho t
                 JOIN acervo.casa_impressao i ON i.id = t.casa_impressao_id
                 JOIN acervo.casa c ON c.id = i.casa_id
                 JOIN acervo.casa_secao s ON s.id = t.casa_secao_id
                WHERE t.id = ANY(%s::uuid[])""",
}


def _base(sid):
    return re.sub(r"~\d+$", "", sid or "")


def versoes():
    out = {"torch": torch.__version__, "cuda": DEV}
    for mod in ("transformers", "sentence_transformers"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception as e:  # noqa: BLE001
            out[mod] = f"erro: {e}"
    return out


def carrega_particao(st, conn, particao):
    """ids, textos e matriz do servido (vetores gravados) dos trechos servindo da partição."""
    api = _API[particao]
    cm = psycopg.connect(st.motor_dsn)
    register_vector(cm)
    ind = [str(r[0]) for r in cm.execute(
        "SELECT id FROM motor.indice WHERE estado = 'servindo' AND remissao = 'vetorial' "
        "AND particao = %s", (api,)).fetchall()]
    ids, vecs = [], []
    with cm.cursor(name=f"sombra_{api}") as cur:
        cur.itersize = 5000
        cur.execute("SELECT alvo_id::text, embedding::vector(1024) FROM motor.vetor "
                    "WHERE indice_id = ANY(%s::uuid[]) AND dimensao = 1024", (ind,))
        for alvo, emb in cur:
            ids.append(alvo)
            vecs.append(np.asarray(emb, dtype=np.float16))
    cm.close()
    meta = {}
    for i in range(0, len(ids), 5000):
        for r in conn.execute(SQL_TXT[api], (ids[i:i + 5000],)).fetchall():
            meta[r[0]] = {"texto": r[1] or "", "obra": r[2], "ancora": r[3] or "", "arquivo": r[4]}
    manter = [j for j, a in enumerate(ids) if a in meta and meta[a]["texto"].strip()]
    ids = [ids[j] for j in manter]
    mat = np.stack([vecs[j] for j in manter]) if manter else np.zeros((0, 1024), np.float16)
    log(f"particao {particao}: {len(ind)} indices servindo, {len(ids)} trechos com texto")
    return {"ids": ids, "meta": meta, "servido": mat}


def topk(Q, C, k):
    """top-k exato por cosseno (Q e C normalizados). Devolve (sims, indices) em numpy."""
    sims, idx = [], []
    C = C.to(DEV)
    for i in range(0, Q.shape[0], 256):
        s = (Q[i:i + 256].to(DEV, C.dtype) @ C.T).float()
        v, ix = torch.topk(s, min(k, C.shape[0]), dim=1)
        sims.append(v.cpu().numpy())
        idx.append(ix.cpu().numpy())
    del C
    return np.concatenate(sims), np.concatenate(idx)


def _norm(t):
    return F.normalize(t.float(), dim=-1)


def carrega_candidato(nome, cfg):
    import transformers
    from sentence_transformers import SentenceTransformer
    dt = getattr(torch, cfg["dtype"]) if DEV == "cuda" else torch.float32
    chave = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    m = SentenceTransformer(nome, device=DEV, trust_remote_code=cfg["trust"],
                            model_kwargs={chave: dt, "attn_implementation": "sdpa"})
    m.max_seq_length = 512
    return m


def encode(m, textos, prefixo, lote=4096):
    """Encode em blocos, devolvido em fp16 na CPU; prompt='' desliga prompt default do modelo
    (o prefixo do cartão vai à mão, uma vez só)."""
    partes, t0 = [], time.time()
    for i in range(0, len(textos), lote):
        e = m.encode([prefixo + t for t in textos[i:i + lote]], batch_size=32, prompt="",
                     convert_to_tensor=True, normalize_embeddings=False, show_progress_bar=False)
        partes.append(e.float().cpu().half())
        if len(textos) > lote:
            feito = min(i + lote, len(textos))
            taxa = feito / max(time.time() - t0, 1e-6)
            log(f"    {feito}/{len(textos)} ({taxa:.0f}/s, faltam ~{(len(textos) - feito) / taxa / 60:.0f} min)")
    return torch.cat(partes) if partes else torch.zeros((0, 1))


def agrega(ranks):
    n = len(ranks) or 1
    return {"n": len(ranks),
            "hit@1": round(sum(1 for r in ranks if r == 1) / n, 3),
            "hit@3": round(sum(1 for r in ranks if r and r <= 3) / n, 3),
            "hit@5": round(sum(1 for r in ranks if r and r <= 5) / n, 3),
            f"hit@{K}": round(sum(1 for r in ranks if r and r <= K) / n, 3),
            "mrr": round(sum((1.0 / r) if r else 0.0 for r in ranks) / n, 3)}


def melhor_piso(pos, neg):
    """Piso único de similaridade do 1º lugar que minimiza erro total (positiva abaixo + negativa
    acima). É o mesmo critério do ajuste aviso-de-cobertura-fraca."""
    if not pos or not neg:
        return None
    cands = sorted(set(pos) | set(neg))
    melhor = None
    for t in cands:
        err = sum(1 for p in pos if p < t) + sum(1 for x in neg if x >= t)
        if melhor is None or err < melhor[0]:
            melhor = (err, t)
    err050 = sum(1 for p in pos if p < 0.5) + sum(1 for x in neg if x >= 0.5)
    tot = len(pos) + len(neg)
    return {"piso": round(melhor[1], 3), "erro": round(melhor[0] / tot, 3),
            "erro_em_0_50": round(err050 / tot, 3), "positivas": len(pos), "negativas": len(neg),
            "sim_mediana_pos": round(float(np.median(pos)), 3),
            "sim_mediana_neg": round(float(np.median(neg)), 3)}


def main():
    t_ini = time.time()
    from motor_acervo.config.settings import load_settings
    from motor_acervo.store.db import get_conn
    st = load_settings()
    conn = get_conn(st)
    res = {"id": ARGS["id"], "em": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "k": K,
           "versoes": versoes(), "instrucao_servida": os.environ.get("EMBED_QUERY_INSTRUCTION", ""),
           "embedder_servido": st.embed_model, "modelos": {}, "corpus": {}}
    log(f"versoes: {res['versoes']}")

    particoes = [p for p in ARGS["particoes"]]
    corpus = {}
    for p in particoes:
        corpus[p] = carrega_particao(st, conn, p)
        res["corpus"][p] = len(corpus[p]["ids"])

    # perguntas: gabarito (só biblioteca) e replay do log (todas as partições)
    gold = [json.loads(l) for l in open(ARGS["gabarito"], encoding="utf-8") if l.strip()]
    gold = [g for g in gold if g.get("pergunta")]
    linhas = conn.execute("SELECT pergunta FROM acervo.evento_recuperacao "
                          "WHERE disparou GROUP BY pergunta").fetchall()
    gold_txt = {g["pergunta"].strip() for g in gold}
    replay = sorted({(r[0] or "").strip() for r in linhas} - gold_txt)
    replay = [q for q in replay if len(q) >= 8]
    total_log = len(replay)
    random.Random(42).shuffle(replay)
    replay = replay[:MAX_PERGUNTAS]
    res["perguntas"] = {"gabarito": len(gold), "log_unicas": total_log, "replay": len(replay)}
    log(f"perguntas: gabarito {len(gold)}, log {total_log} unicas, replay {len(replay)}")
    perguntas = [g["pergunta"] for g in gold] + replay
    n_gold = len(gold)

    # ranking[variante][particao] = (sims, idx) sobre `perguntas`
    ranking = {}

    # servido: embed_query do próprio serviço (instrução servida) + vetores gravados
    from motor_acervo.ingestao.embedding import embed_query
    t0 = time.time()
    Qs = torch.tensor(np.stack([embed_query(q, st) for q in perguntas])).half()
    Qs = _norm(Qs)
    variante = f"{SERVIDO}:{st.embed_model.split('/')[-1]}"
    ranking[variante] = {}
    for p in particoes:
        C = _norm(torch.tensor(corpus[p]["servido"]))
        ranking[variante][p] = topk(Qs, C.half(), K)
        del C
    res["modelos"][variante] = {"perguntas_s": round(time.time() - t0, 1)}
    log(f"{variante}: rankings prontos")
    gc.collect()
    torch.cuda.empty_cache()

    for nome in ARGS["modelos"]:
        cfg = CANDIDATOS.get(nome)
        if not cfg:
            res["modelos"][nome] = {"erro": "candidato sem configuracao em sombra.py (prefixos, dims)"}
            log(f"{nome}: sem configuracao, pulado")
            continue
        try:
            log(f"{nome}: carregando")
            m = carrega_candidato(nome, cfg)
            Q = encode(m, perguntas, cfg["q"])
            info = {}
            for p in particoes:
                t0 = time.time()
                log(f"{nome}: embeddando {len(corpus[p]['ids'])} trechos de {p}")
                E = encode(m, [corpus[p]["meta"][a]["texto"] for a in corpus[p]["ids"]], cfg["p"])
                dur = time.time() - t0
                info[p] = {"segundos": round(dur, 1),
                           "trechos_por_s": round(len(corpus[p]["ids"]) / max(dur, 1e-6), 1),
                           "dim_nativa": int(E.shape[1])}
                for d in cfg["dims"]:
                    if d > E.shape[1]:
                        continue
                    v = f"{cfg['curto']}@{d}"
                    ranking.setdefault(v, {})[p] = topk(_norm(Q[:, :d]).half(), _norm(E[:, :d]).half(), K)
                del E
                gc.collect()
                torch.cuda.empty_cache()
            res["modelos"][nome] = info
            del m, Q
        except Exception as e:  # noqa: BLE001
            res["modelos"][nome] = {"erro": f"{type(e).__name__}: {e}"[:500]}
            log(f"{nome}: ERRO {traceback.format_exc()[-1500:]}")
        gc.collect()
        torch.cuda.empty_cache()

    variantes = list(ranking)

    # gabarito (biblioteca): hit@k, MRR por família, piso de abstenção
    res["gabarito"] = {}
    rank_gold = {}  # variante -> lista de rank (None) por item positivo, na mesma ordem
    if "biblioteca" in particoes:
        cp = corpus["biblioteca"]
        for v in variantes:
            if "biblioteca" not in ranking[v]:
                continue
            sims, idx = ranking[v]["biblioteca"]
            fam = {"codigo": [], "sentido": []}
            pos, neg, rk = [], [], []
            for gi, g in enumerate(gold):
                ids = [cp["ids"][j] for j in idx[gi]]
                top1 = float(sims[gi][0])
                if g.get("relevancia") == "negativa":
                    neg.append(top1)
                    continue
                if not g.get("pontuavel", True):
                    continue
                alvo = g.get("alvo_section_id")
                obras = set(g.get("alvo_obra_ids") or [])
                r = None
                if alvo:
                    for pos_i, a in enumerate(ids, 1):
                        if _base(cp["meta"][a]["ancora"]) == _base(alvo):
                            r = pos_i
                            break
                    fam["codigo"].append(r)
                elif obras:
                    for pos_i, a in enumerate(ids, 1):
                        if cp["meta"][a]["obra"] in obras:
                            r = pos_i
                            break
                    fam["sentido"].append(r)
                else:
                    continue
                pos.append(top1)
                rk.append((gi, r))
            rank_gold[v] = rk
            res["gabarito"][v] = {"codigo": agrega(fam["codigo"]), "sentido": agrega(fam["sentido"]),
                                  "geral": agrega(fam["codigo"] + fam["sentido"]),
                                  "abstencao": melhor_piso(pos, neg)}

    # juiz: cross-encoder de outra família sobre o pool unido de cada pergunta
    log("juiz: carregando BAAI/bge-reranker-v2-m3")
    from sentence_transformers import CrossEncoder
    ce = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512, device=DEV)
    try:
        if DEV == "cuda":
            ce.model.half()
    except Exception:  # noqa: BLE001
        pass
    res["juiz"] = {"modelo": "BAAI/bge-reranker-v2-m3"}
    ganho = {}  # (p, qi, alvo) -> prob
    pares, chaves = [], []
    for p in particoes:
        meta = corpus[p]["meta"]
        ids_p = corpus[p]["ids"]
        faixa = range(len(perguntas)) if p == "biblioteca" else range(n_gold, len(perguntas))
        for qi in faixa:
            pool = set()
            for v in variantes:
                if p in ranking[v]:
                    pool.update(ids_p[j] for j in ranking[v][p][1][qi])
            for a in pool:
                chaves.append((p, qi, a))
                pares.append((perguntas[qi][:1000], meta[a]["texto"][:1500]))
    log(f"juiz: {len(pares)} pares")
    t0 = time.time()
    for i in range(0, len(pares), 2048):
        s = np.asarray(ce.predict(pares[i:i + 2048], batch_size=32, show_progress_bar=False),
                       dtype=np.float64)
        if s.size and (s.max() > 1.0 or s.min() < 0.0):
            s = 1.0 / (1.0 + np.exp(-s))
        for ch, val in zip(chaves[i:i + 2048], s):
            ganho[ch] = float(val)
        feito = min(i + 2048, len(pares))
        log(f"    juiz {feito}/{len(pares)} ({feito / max(time.time() - t0, 1e-6):.0f}/s)")
    del ce
    gc.collect()
    torch.cuda.empty_cache()

    def ndcg(p, qi, ids, pool_ganhos):
        dcg = sum(ganho[(p, qi, a)] / math.log2(r + 2) for r, a in enumerate(ids[:K]))
        ideal = sorted(pool_ganhos, reverse=True)[:K]
        idcg = sum(g / math.log2(r + 2) for r, g in enumerate(ideal))
        return dcg / idcg if idcg > 0 else 0.0

    serv = variantes[0]
    res["replay"], amostra = {}, []
    nd = {}  # (v, p, qi) -> ndcg
    for p in particoes:
        ids_p = corpus[p]["ids"]
        faixa = list(range(n_gold, len(perguntas)))
        out = {}
        for qi in range(len(perguntas)):
            if p != "biblioteca" and qi < n_gold:
                continue
            pool = {ids_p[j] for v in variantes if p in ranking[v] for j in ranking[v][p][1][qi]}
            pg = [ganho[(p, qi, a)] for a in pool]
            for v in variantes:
                if p in ranking[v]:
                    nd[(v, p, qi)] = ndcg(p, qi, [ids_p[j] for j in ranking[v][p][1][qi]], pg)
        for v in variantes:
            if p not in ranking[v]:
                continue
            vit = emp = der = 0
            jac = []
            for qi in faixa:
                a_set = {ids_p[j] for j in ranking[v][p][1][qi]}
                s_set = {ids_p[j] for j in ranking[serv][p][1][qi]}
                jac.append(len(a_set & s_set) / max(len(a_set | s_set), 1))
                d = nd[(v, p, qi)] - nd[(serv, p, qi)]
                if a_set == s_set or abs(d) < 0.02:
                    emp += 1
                elif d > 0:
                    vit += 1
                else:
                    der += 1
            out[v] = {"ndcg_medio": round(float(np.mean([nd[(v, p, qi)] for qi in faixa])), 4) if faixa else None,
                      "vitorias": vit, "empates": emp, "derrotas": der,
                      "jaccard_com_servido": round(float(np.mean(jac)), 3) if jac else None,
                      "melhor_trecho_top3_medio": round(float(np.mean([
                          max(ganho[(p, qi, ids_p[j])] for j in ranking[v][p][1][qi][:3])
                          for qi in faixa])), 4) if faixa else None}
        res["replay"][p] = out
        # amostra: as perguntas em que o melhor candidato e o servido mais discordam
        cands = [v for v in variantes[1:] if p in ranking[v]]
        if cands and faixa:
            melhor = max(cands, key=lambda v: out[v]["ndcg_medio"] or 0)
            difs = sorted(faixa, key=lambda qi: -abs(nd[(melhor, p, qi)] - nd[(serv, p, qi)]))[:12]
            meta = corpus[p]["meta"]
            for qi in difs:
                def tops(v):
                    return [{"arquivo": meta[ids_p[j]]["arquivo"], "ancora": meta[ids_p[j]]["ancora"],
                             "juiz": round(ganho[(p, qi, ids_p[j])], 3),
                             "texto": meta[ids_p[j]]["texto"][:200]}
                            for j in ranking[v][p][1][qi][:3]]
                amostra.append({"particao": p, "pergunta": perguntas[qi][:300],
                                "servido": {"ndcg": round(nd[(serv, p, qi)], 3), "top3": tops(serv)},
                                melhor: {"ndcg": round(nd[(melhor, p, qi)], 3), "top3": tops(melhor)}})
    res["amostra"] = amostra

    # o juiz contra o gabarito: concordância de sinal entre ΔnDCG do juiz e ΔMRR do gabarito
    conc = {}
    if serv in rank_gold:
        ms = {gi: (1.0 / r if r else 0.0) for gi, r in rank_gold[serv]}
        for v in variantes[1:]:
            if v not in rank_gold:
                continue
            ok = tot = 0
            for gi, r in rank_gold[v]:
                dm = (1.0 / r if r else 0.0) - ms.get(gi, 0.0)
                dj = nd[(v, "biblioteca", gi)] - nd[(serv, "biblioteca", gi)]
                if dm == 0 or abs(dj) < 0.02:
                    continue
                tot += 1
                ok += int((dm > 0) == (dj > 0))
            conc[v] = {"concordam": ok, "comparaveis": tot,
                       "taxa": round(ok / tot, 3) if tot else None}
    res["juiz"]["concordancia_com_gabarito"] = conc
    res["segundos"] = round(time.time() - t_ini, 1)
    with open(os.path.join(SAIDA, "resultado.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    log(f"fim: {res['segundos']} s")


if __name__ == "__main__":
    try:
        main()
    except Exception:  # noqa: BLE001
        log("ERRO FATAL\n" + traceback.format_exc())
        sys.exit(1)
