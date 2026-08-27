"""Baseline central do P0 (#2894): gold re-ancorado inteiro contra /search servida.
Roda no container. Casa alvo (section_id p/ T1, titulo de obra p/ T2), aplica a regua N/A
(sem alvo -> rank/hit/recall = None, nunca 0), mede abstencao das negativas e latencia.
Emite /tmp/baseline_resultados.jsonl (uma linha por pergunta) para gravar em avaliacao.resultado."""
import json, os, time, urllib.request
from rag_extractor.store.db import get_conn
from rag_extractor.ajustes_do_trilho import load_settings

API = "http://localhost:8000/search"; TOKEN = os.environ["RAG_API_TOKEN"]
def search(p, k=8):
    body = json.dumps({"pergunta": p, "k": k, "texto": "nenhum"}).encode()
    req = urllib.request.Request(API, data=body, headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read()), (time.perf_counter()-t0)*1000

gold = [json.loads(l) for l in open("/tmp/gabarito.jsonl") if l.strip()]
ids = {a for d in gold for a in (d.get("alvo_obra_ids") or [])}
st = load_settings(); titulo = {}
if ids:
    with get_conn(st) as c:
        for r in c.execute("select id::text,titulo from acervo.obra where id=any(%s)", (list(ids),)).fetchall():
            titulo[r[0]] = r[1]

res, lat = [], []
neg_tot = neg_ok = 0
for d in gold:
    p = d.get("pergunta")
    if not p: continue
    resp, dt = search(p); lat.append(dt)
    fontes = resp.get("fontes", [])[:8]
    cob = resp.get("cobertura")
    est = d.get("estrato", "")
    rank = hit = recall = None; alvo_ref = None
    if d.get("relevancia") == "negativa":
        neg_tot += 1; neg_ok += 1 if cob in ("fraca", "nenhuma") else 0
    elif d.get("ancoragem_invalida") or (not d.get("alvo_section_id") and not d.get("alvo_obra_ids")):
        pass  # N/A: T3 sem alvo, ou T1 com ancora invalida
    else:
        secs = {d["alvo_section_id"]} if d.get("alvo_section_id") else set()
        tits = {titulo.get(a) for a in (d.get("alvo_obra_ids") or [])} - {None}
        alvo_ref = d.get("alvo_section_id") or ";".join(sorted(tits)) or None
        got, posic = set(), []
        for i, f in enumerate(fontes):
            key = f.get("section_id") if f.get("section_id") in secs else (f.get("obra") if f.get("obra") in tits else None)
            if key is not None:
                posic.append(i+1); got.add(key)
        rank = posic[0] if posic else None
        hit = rank is not None
        denom = len(secs) + len(tits)
        recall = (len(got)/denom) if denom else None
    res.append({"pergunta_id": d.get("id"), "estrato": est, "alvo_ref": alvo_ref,
                "k": 8, "rank": rank, "hit_k": hit, "recall_k": recall})

lat.sort()
p50 = lat[len(lat)//2]; p95 = lat[max(0, int(len(lat)*0.95)-1)]
open("/tmp/baseline_resultados.jsonl", "w").write("\n".join(json.dumps(x) for x in res)+"\n")
# agregados por estrato, filtrando N/A (a regua)
from collections import defaultdict
h = defaultdict(lambda: [0, 0]); rc = defaultdict(lambda: [0.0, 0])
for x in res:
    if x["hit_k"] is not None:
        k = x["estrato"][:2]; h[k][0] += int(x["hit_k"]); h[k][1] += 1
    if x["recall_k"] is not None:
        k = x["estrato"][:2]; rc[k][0] += x["recall_k"]; rc[k][1] += 1
print(f"N={len(res)}  (avaliaveis por hit: {sum(v[1] for v in h.values())}; N/A filtrado)")
for k in sorted(h):
    print(f"  {k}: hit@8 {h[k][0]}/{h[k][1]} ({100*h[k][0]/h[k][1]:.1f}%)  recall@8_medio {rc[k][0]/rc[k][1]:.3f}")
print(f"negativas: abstencao {neg_ok}/{neg_tot}")
print(f"latencia p50={p50:.0f}ms p95={p95:.0f}ms")
print("JSON " + json.dumps({"n": len(res), "neg_ok": neg_ok, "neg_tot": neg_tot, "p50": round(p50,1), "p95": round(p95,1)}))
