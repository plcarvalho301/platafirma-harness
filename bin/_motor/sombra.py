"""Braço-sombra do embedder (guia escolha-de-llm §11; card #2925).

Roda DENTRO do contêiner do rag (rag-extractor-api), lançado por
`motor rag medir <particao> --sombra <modelo>[,<modelo>]`. Nunca toca o servido: não escreve
em banco nenhum, não muda env do serviço, carrega os candidatos num processo à parte, num venv
que herda o torch da imagem e só sobe transformers/sentence-transformers.

Duas regras que a primeira rodada (05/10/2026) ensinou a escrever:
- o banco se lê em autocommit: transação aberta por horas segura AccessShareLock e trava
  qualquer DDL do acervo;
- o corpus nunca se junta na memória: embeda um bloco, compara com todas as perguntas, guarda o
  top-k corrente e descarta o bloco. A matriz inteira de 261 mil trechos derrubou a máquina.

Corpus da biblioteca: um SUBCORPUS, não a partição inteira — os trechos-alvo do gabarito, até 300
trechos de cada obra-alvo, o top-50 do servido (vetor) e da palavra exata para cada pergunta, e
uma amostra aleatória como distração. Viés declarado: o pool do servido entra, o dos candidatos
não (montá-lo exigiria embedar tudo); acerto de candidato fora do pool não conta. A casa é pequena
e entra inteira.

O que mede, por partição:
- o braço de significado ISOLADO: top-k exato de cada variante sobre o mesmo corpus;
- no gabarito (biblioteca): hit@k e MRR por família, e o piso de abstenção que melhor separa
  positivas de negativas, por modelo — o piso é do embedder, não do motor;
- no replay das perguntas reais do log: juiz de fora das duas famílias (cross-encoder
  BAAI/bge-reranker-v2-m3) pontua o pool unido; nDCG@k e vitória/empate/derrota contra o
  servido; o juiz é conferido contra o gabarito na mesma rodada.

Saída: <saida>/log.txt (progresso) e <saida>/resultado.json (o que o verbo resume).
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
from types import SimpleNamespace

ARGS = json.loads(os.environ["SOMBRA_ARGS"])
SAIDA = ARGS["saida"]
K = int(ARGS.get("k", 8))
MAX_PERGUNTAS = int(ARGS.get("max_perguntas", 1000))
POOL = 50            # candidatos por pergunta, por braço, no subcorpus
AMOSTRA = 10000      # trechos aleatórios de distração
POR_OBRA = 300       # teto de trechos por obra-alvo do gabarito
BLOCO = 2048         # trechos por bloco de embed: é o que vive na memória
_LOG = open(os.path.join(SAIDA, "log.txt"), "a", buffering=1)


def log(msg):
    _LOG.write(time.strftime("%H:%M:%S ") + msg + "\n")


import numpy as np  # noqa: E402
import psycopg  # noqa: E402
import torch  # noqa: E402
import torch.nn.functional as F  # noqa: E402
from pgvector.psycopg import register_vector  # noqa: E402

DEV = "cuda" if torch.cuda.is_available() else "cpu"

CANDIDATOS = {
    "nvidia/Nemotron-3-Embed-1B-BF16": {
        "curto": "Nemotron-3-Embed-1B", "q": "query: ", "p": "passage: ",
        "dims": [1024, 2048], "dtype": "bfloat16", "trust": False},
    "perplexity-ai/pplx-embed-v1-0.6b": {
        "curto": "pplx-embed-v1-0.6b", "q": "", "p": "",
        "dims": [1024], "dtype": "float16", "trust": True},
}
SERVIDO = "servido"
_API = {"biblioteca": "biblioteca", "casa": "casa", "obra": "biblioteca"}

_SQL_TRECHO = """SELECT t.id::text, t.texto, o.id::text, s.ancora, o.arquivo
                 FROM acervo.trecho t
                 JOIN acervo.impressao i ON i.id = t.impressao_id
                 JOIN acervo.obra o ON o.id = i.obra_id
                 JOIN acervo.secao s ON s.id = t.secao_id
                WHERE t.id = ANY(%s::uuid[])"""

SQL_TXT = {
    "biblioteca": _SQL_TRECHO,
    "obra": _SQL_TRECHO,
    "casa": """SELECT t.id::text, t.texto, c.id::text, s.ancora, coalesce(c.chave, c.path)
                 FROM acervo.casa_trecho t
                 JOIN acervo.casa_impressao i ON i.id = t.casa_impressao_id
                 JOIN acervo.casa c ON c.id = i.casa_id
                 JOIN acervo.casa_secao s ON s.id = t.casa_secao_id
                WHERE t.id = ANY(%s::uuid[])""",
}


# O balde da view acervo.bateria_recuperacao para o evento anterior a 085 (sem particao declarada).
BALDE_ANTIGO = "sem partição (anterior a 085)"

def _normaliza(texto):
    """A mesma normalizacao da view: espacos colapsados, bordas e caixa."""
    return re.sub(r"\s+", " ", texto or "").strip().lower()

def _base(sid):
    return re.sub(r"~\d+$", "", sid or "")


def _arr(emb):
    # pgvector recente devolve Vector, nao ndarray
    return np.asarray(emb.to_numpy() if hasattr(emb, "to_numpy") else emb, dtype=np.float16)


def versoes():
    out = {"torch": torch.__version__, "cuda": DEV}
    for mod in ("transformers", "sentence_transformers"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception as e:  # noqa: BLE001
            out[mod] = f"erro: {e}"
    return out


def conectar_motor(st):
    cm = psycopg.connect(st.motor_dsn, autocommit=True)
    register_vector(cm)
    return cm


def indices_servindo(cm, api):
    return [str(r[0]) for r in cm.execute(
        "SELECT id FROM motor.indice WHERE estado = 'servindo' AND remissao = 'vetorial' "
        "AND particao = %s", (api,)).fetchall()]


def subcorpus_biblioteca(conn, cm, ind, perguntas, Qs, gold):
    """ids de trecho do subcorpus da biblioteca (ver docstring do módulo)."""
    sel = set()
    secs = sorted({_base(g["alvo_section_id"]) for g in gold if g.get("alvo_section_id")})
    obras = sorted({o for g in gold for o in (g.get("alvo_obra_ids") or [])})
    if secs:
        sel |= {r[0] for r in conn.execute(
            """SELECT t.id::text FROM acervo.trecho t
                 JOIN acervo.secao s ON s.id = t.secao_id
                 JOIN acervo.impressao i ON i.id = t.impressao_id
                WHERE i.estado = 'servindo'
                  AND regexp_replace(s.ancora, '~[0-9]+$', '') = ANY(%s)""", (secs,)).fetchall()}
    if obras:
        sel |= {r[0] for r in conn.execute(
            """SELECT id FROM (
                 SELECT t.id::text AS id,
                        row_number() OVER (PARTITION BY i.obra_id ORDER BY random()) AS rn
                   FROM acervo.trecho t JOIN acervo.impressao i ON i.id = t.impressao_id
                  WHERE i.estado = 'servindo' AND i.obra_id = ANY(%s::uuid[])) x
                WHERE rn <= %s""", (obras, POR_OBRA)).fetchall()}
    n_gold = len(sel)
    from motor_acervo.store import acervo_store as acs
    from motor_acervo.store import motor_store as ms
    escopo = SimpleNamespace(particao="obra", dominios=[], subdominios=[], serve_a=[], colecoes=[])
    n_vet = n_lex = 0
    for qi, q in enumerate(perguntas):
        try:
            v = ms._ann(cm, ind, Qs[qi].float().numpy(), 1024, POOL)
            n_vet += len(v)
            sel |= set(v)
        except Exception as e:  # noqa: BLE001
            log(f"  ann falhou na pergunta {qi}: {e}")
        try:
            lx = acs.candidatos_lexicais(conn, escopo, q[:500], POOL)
            n_lex += len(lx)
            sel |= set(lx)
        except Exception as e:  # noqa: BLE001
            log(f"  lexical falhou na pergunta {qi}: {e}")
    sel |= {r[0] for r in cm.execute(
        "SELECT alvo_id::text FROM motor.vetor WHERE indice_id = ANY(%s::uuid[]) "
        "AND dimensao = 1024 ORDER BY random() LIMIT %s", (ind, AMOSTRA)).fetchall()}
    log(f"subcorpus biblioteca: {len(sel)} trechos (gabarito {n_gold}, "
        f"pool vetor {n_vet}, pool lexical {n_lex}, amostra {AMOSTRA})")
    return sel


def carrega_corpus(conn, cm, api, ind, sel=None):
    """ids, textos e vetores do servido. `sel` restringe a um conjunto de ids."""
    ids, vecs = [], []
    if sel is None:
        rows = cm.execute("SELECT alvo_id::text, embedding::vector(1024) FROM motor.vetor "
                          "WHERE indice_id = ANY(%s::uuid[]) AND dimensao = 1024", (ind,)).fetchall()
        for a, e in rows:
            ids.append(a)
            vecs.append(_arr(e))
    else:
        lista = sorted(sel)
        for i in range(0, len(lista), 5000):
            for a, e in cm.execute(
                    "SELECT alvo_id::text, embedding::vector(1024) FROM motor.vetor "
                    "WHERE indice_id = ANY(%s::uuid[]) AND dimensao = 1024 "
                    "AND alvo_id = ANY(%s::uuid[])", (ind, lista[i:i + 5000])).fetchall():
                ids.append(a)
                vecs.append(_arr(e))
    vistos, uniq, uvec = set(), [], []
    for a, v in zip(ids, vecs):
        if a not in vistos:
            vistos.add(a)
            uniq.append(a)
            uvec.append(v)
    meta = {}
    for i in range(0, len(uniq), 5000):
        for r in conn.execute(SQL_TXT[api], (uniq[i:i + 5000],)).fetchall():
            meta[r[0]] = {"texto": r[1] or "", "obra": r[2], "ancora": r[3] or "", "arquivo": r[4]}
    manter = [j for j, a in enumerate(uniq) if a in meta and meta[a]["texto"].strip()]
    return {"ids": [uniq[j] for j in manter], "meta": meta,
            "servido": np.stack([uvec[j] for j in manter])}


def _norm(t):
    return F.normalize(t.float(), dim=-1)


class TopK:
    """top-k corrente por pergunta, atualizado bloco a bloco: a memória é a de um bloco."""

    def __init__(self, Q, k):
        self.Q = Q.to(DEV).half()
        n = Q.shape[0]
        self.k = k
        self.v = torch.full((n, k), -float("inf"), device=DEV)
        self.i = torch.full((n, k), -1, dtype=torch.long, device=DEV)

    def bloco(self, offset, E):
        s = (self.Q @ E.to(DEV).half().T).float()
        kk = min(self.k, s.shape[1])
        v, ix = torch.topk(s, kk, dim=1)
        cv = torch.cat([self.v, v], 1)
        ci = torch.cat([self.i, ix + offset], 1)
        self.v, pos = torch.topk(cv, self.k, dim=1)
        self.i = torch.gather(ci, 1, pos)

    def fim(self):
        return self.v.cpu().numpy(), self.i.cpu().numpy()


def carrega_candidato(nome, cfg):
    import transformers
    from sentence_transformers import SentenceTransformer
    dt = getattr(torch, cfg["dtype"]) if DEV == "cuda" else torch.float32
    chave = "dtype" if int(transformers.__version__.split(".")[0]) >= 5 else "torch_dtype"
    m = SentenceTransformer(nome, device=DEV, trust_remote_code=cfg["trust"],
                            model_kwargs={chave: dt, "attn_implementation": "sdpa"})
    m.max_seq_length = 512
    return m


def _enc(m, textos, prefixo):
    """prompt='' desliga o prompt default do modelo; o prefixo do cartão vai à mão, uma vez."""
    return m.encode([prefixo + t for t in textos], batch_size=32, prompt="",
                    convert_to_tensor=True, normalize_embeddings=False, show_progress_bar=False)


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
    acima) — o critério do ajuste aviso-de-cobertura-fraca."""
    if not pos or not neg:
        return None
    melhor = None
    for t in sorted(set(pos) | set(neg)):
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
    conn.autocommit = True     # nada de transação aberta segurando lock no acervo
    cm = conectar_motor(st)
    res = {"id": ARGS["id"], "em": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "k": K,
           "versoes": versoes(), "instrucao_servida": os.environ.get("EMBED_QUERY_INSTRUCTION", ""),
           "embedder_servido": st.embed_model, "modelos": {}, "corpus": {},
           "subcorpus": {"pool_por_braco": POOL, "amostra": AMOSTRA, "por_obra_alvo": POR_OBRA}}
    log(f"versoes: {res['versoes']}")

    gold = [json.loads(l) for l in open(ARGS["gabarito"], encoding="utf-8") if l.strip()]
    gold = [g for g in gold if g.get("pergunta")]
    # O replay le a bateria do log (acervo.bateria_recuperacao, #3314) pela particao pedida, mais o
    # balde dos eventos anteriores a 085, que nao declaram particao. A view ja tira o canario e so
    # traz as origens busca e abertura; o gabarito, que e arquivo daqui, sai neste ponto, pelo
    # texto normalizado como a view o normaliza.
    parts_log = sorted({_API[p] for p in ARGS["particoes"]} | {BALDE_ANTIGO})
    linhas = conn.execute("SELECT particao, pergunta_normalizada, pergunta_exemplo "
                          "FROM acervo.bateria_recuperacao WHERE particao = ANY(%s)",
                          (parts_log,)).fetchall()
    gold_txt = {_normaliza(g["pergunta"]) for g in gold}
    por_particao, vistas = {}, {}
    for part, norm, exemplo in linhas:
        if norm in gold_txt or len((norm or "").strip()) < 8:
            continue
        por_particao[part] = por_particao.get(part, 0) + 1
        vistas.setdefault(norm, (exemplo or norm).strip())
    replay = sorted(vistas.values())
    total_log = len(replay)
    random.Random(42).shuffle(replay)
    replay = replay[:MAX_PERGUNTAS]
    res["perguntas"] = {"gabarito": len(gold), "log_unicas": total_log, "replay": len(replay),
                        "por_particao": por_particao}
    log(f"perguntas: gabarito {len(gold)}, log {total_log} unicas, replay {len(replay)}; "
        f"por particao da bateria (a mesma pergunta pode contar em mais de uma): {por_particao}")
    perguntas = [g["pergunta"] for g in gold] + replay
    n_gold = len(gold)

    from motor_acervo.ingestao.embedding import embed_query
    Qs = _norm(torch.tensor(np.stack([embed_query(q, st) for q in perguntas])))

    particoes = list(ARGS["particoes"])
    corpus = {}
    for p in particoes:
        api = _API[p]
        ind = indices_servindo(cm, api)
        sel = subcorpus_biblioteca(conn, cm, ind, perguntas, Qs, gold) if p == "biblioteca" else None
        corpus[p] = carrega_corpus(conn, cm, api, ind, sel)
        res["corpus"][p] = len(corpus[p]["ids"])
        log(f"particao {p}: {len(ind)} indices servindo, {res['corpus'][p]} trechos no corpus da medida")

    ranking = {}
    variante = f"{SERVIDO}:{st.embed_model.split('/')[-1]}"
    ranking[variante] = {}
    for p in particoes:
        tk = TopK(Qs, K)
        mat = corpus[p]["servido"]
        for off in range(0, len(mat), BLOCO):
            tk.bloco(off, _norm(torch.tensor(mat[off:off + BLOCO])))
        ranking[variante][p] = tk.fim()
    log(f"{variante}: rankings prontos")

    for nome in ARGS["modelos"]:
        cfg = CANDIDATOS.get(nome)
        if not cfg:
            res["modelos"][nome] = {"erro": "candidato sem configuracao em sombra.py (prefixos, dims)"}
            continue
        try:
            log(f"{nome}: carregando")
            m = carrega_candidato(nome, cfg)
            Q = torch.cat([_enc(m, perguntas[i:i + 256], cfg["q"]).float().cpu()
                           for i in range(0, len(perguntas), 256)])
            info = {}
            for p in particoes:
                ids = corpus[p]["ids"]
                textos = [corpus[p]["meta"][a]["texto"] for a in ids]
                dims = [d for d in cfg["dims"]]
                tks = {d: TopK(_norm(Q[:, :d]), K) for d in dims}
                t0 = time.time()
                for off in range(0, len(textos), BLOCO):
                    E = _enc(m, textos[off:off + BLOCO], cfg["p"])
                    for d in dims:
                        if d <= E.shape[1]:
                            tks[d].bloco(off, _norm(E[:, :d]))
                    del E
                    feito = min(off + BLOCO, len(textos))
                    taxa = feito / max(time.time() - t0, 1e-6)
                    log(f"    {nome} {p}: {feito}/{len(textos)} ({taxa:.0f}/s)")
                info[p] = {"segundos": round(time.time() - t0, 1),
                           "trechos_por_s": round(len(textos) / max(time.time() - t0, 1e-6), 1)}
                for d in dims:
                    ranking.setdefault(f"{cfg['curto']}@{d}", {})[p] = tks[d].fim()
                del tks
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

    res["gabarito"] = {}
    rank_gold = {}
    if "biblioteca" in particoes:
        cp = corpus["biblioteca"]
        for v in variantes:
            if "biblioteca" not in ranking[v]:
                continue
            sims, idx = ranking[v]["biblioteca"]
            fam = {"codigo": [], "sentido": []}
            pos, neg, rk = [], [], []
            for gi, g in enumerate(gold):
                ids = [cp["ids"][j] for j in idx[gi] if j >= 0]
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

    log("juiz: carregando BAAI/bge-reranker-v2-m3")
    from sentence_transformers import CrossEncoder
    ce = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512, device=DEV)
    try:
        if DEV == "cuda":
            ce.model.half()
    except Exception:  # noqa: BLE001
        pass
    res["juiz"] = {"modelo": "BAAI/bge-reranker-v2-m3"}

    def top_ids(v, p, qi):
        ids_p = corpus[p]["ids"]
        return [ids_p[j] for j in ranking[v][p][1][qi] if j >= 0]

    ganho, pares, chaves = {}, [], []
    for p in particoes:
        meta = corpus[p]["meta"]
        faixa = range(len(perguntas)) if p == "biblioteca" else range(n_gold, len(perguntas))
        for qi in faixa:
            pool = set()
            for v in variantes:
                if p in ranking[v]:
                    pool.update(top_ids(v, p, qi))
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
    res["replay"], amostra, nd = {}, [], {}
    for p in particoes:
        faixa = list(range(n_gold, len(perguntas)))
        out = {}
        for qi in range(len(perguntas)):
            if p != "biblioteca" and qi < n_gold:
                continue
            pool = {a for v in variantes if p in ranking[v] for a in top_ids(v, p, qi)}
            pg = [ganho[(p, qi, a)] for a in pool]
            for v in variantes:
                if p in ranking[v]:
                    nd[(v, p, qi)] = ndcg(p, qi, top_ids(v, p, qi), pg)
        for v in variantes:
            if p not in ranking[v]:
                continue
            vit = emp = der = 0
            jac = []
            for qi in faixa:
                a_set, s_set = set(top_ids(v, p, qi)), set(top_ids(serv, p, qi))
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
                          max(ganho[(p, qi, a)] for a in top_ids(v, p, qi)[:3]) for qi in faixa])), 4)
                      if faixa else None}
        res["replay"][p] = out
        cands = [v for v in variantes[1:] if p in ranking[v]]
        if cands and faixa:
            melhor = max(cands, key=lambda v: out[v]["ndcg_medio"] or 0)
            difs = sorted(faixa, key=lambda qi: -abs(nd[(melhor, p, qi)] - nd[(serv, p, qi)]))[:12]
            meta = corpus[p]["meta"]
            for qi in difs:
                def tops(v):
                    return [{"arquivo": meta[a]["arquivo"], "ancora": meta[a]["ancora"],
                             "juiz": round(ganho[(p, qi, a)], 3), "texto": meta[a]["texto"][:200]}
                            for a in top_ids(v, p, qi)[:3]]
                amostra.append({"particao": p, "pergunta": perguntas[qi][:300],
                                "servido": {"ndcg": round(nd[(serv, p, qi)], 3), "top3": tops(serv)},
                                melhor: {"ndcg": round(nd[(melhor, p, qi)], 3), "top3": tops(melhor)}})
    res["amostra"] = amostra

    conc = {}
    if serv in rank_gold:
        ms_ = {gi: (1.0 / r if r else 0.0) for gi, r in rank_gold[serv]}
        for v in variantes[1:]:
            if v not in rank_gold:
                continue
            ok = tot = 0
            for gi, r in rank_gold[v]:
                dm = (1.0 / r if r else 0.0) - ms_.get(gi, 0.0)
                dj = nd[(v, "biblioteca", gi)] - nd[(serv, "biblioteca", gi)]
                if dm == 0 or abs(dj) < 0.02:
                    continue
                tot += 1
                ok += int((dm > 0) == (dj > 0))
            conc[v] = {"concordam": ok, "comparaveis": tot, "taxa": round(ok / tot, 3) if tot else None}
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
