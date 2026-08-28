#!/usr/bin/env python3
"""
runner_gold_baseline.py -- card #2894 (P0). Roda o gold de 91 (modos de falha) contra
o motor RAG servido e grava run + resultado no motor-pg (schema avaliacao).

Baseline honesto: mede o que ha. Onde nao ha alvo (modo a/c/e ordem-consulta), rank/
hit/recall ficam NULL -- a regua e PROCURAR, nao achar (ordem do dono 27/08).

stack_sha: o container nao expoe o proprio SHA (debito conhecido, falta /version). Grava
o SHA do repo do rag como PROVISORIO, marcado em params.stack_sha_origem.

Roda de dentro do rag-extractor-api (o host nao alcanca o motor). Ver caderno recuperacao.
"""
import json, os, time, uuid, urllib.request, statistics, subprocess

GOLD = "/tmp/gold-proposto-modos.jsonl"
K = 8
API = "http://localhost:8000/search"          # endpoint servido, de dentro do container
TOKEN = os.environ.get("RAG_API_TOKEN", "")

# motor-pg alcancavel de dentro da rede docker como indice:5432? nao: gravamos via
# stdin do psql no host. Aqui o runner SO mede e cospe JSON; a gravacao e no host.

def busca(pergunta):
    corpo = {"pergunta": pergunta, "k": K}
    req = urllib.request.Request(
        API, data=json.dumps(corpo).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"})
    t0 = time.monotonic()
    with urllib.request.urlopen(req, timeout=300) as r:
        resp = json.loads(r.read().decode())
    dur = (time.monotonic() - t0) * 1000
    fontes = resp.get("fontes") or resp.get("hits") or []
    obras = [f.get("obra") for f in fontes]
    secs = [f.get("section_id") for f in fontes]
    return obras, secs, dur

def mede(item, obras, secs):
    """rank/hit/recall so quando ha alvo; senao NULL (a regua e procurar)."""
    alvo_obras = item.get("alvo_obra_ids") or []
    alvo_sec = item.get("alvo_section_id")
    if not alvo_obras and not alvo_sec:
        return None, None, None          # sem alvo: N/A, nunca 0
    rank = None
    if alvo_obras:
        # resolve UUID->titulo nao e possivel aqui; o motor devolve titulo. Casa por
        # section_id base quando ha; senao marca sem_rank (o join fino fica p/ julgamento).
        pass
    if alvo_sec:
        base = alvo_sec.split("#")[0]
        for i, s in enumerate(secs):
            if s and s.split("#")[0] == base:
                rank = i + 1
                break
    hit = rank is not None and rank <= K
    recall = (1.0 if hit else 0.0)
    return rank, hit, recall

def main():
    rows = [json.loads(l) for l in open(GOLD) if l.strip()]
    execut = [r for r in rows if r.get("executavel", True)]
    resultados = []
    lats = []
    for it in execut:
        try:
            obras, secs, dur = busca(it["pergunta"])
        except Exception as e:
            resultados.append({"pergunta_id": it["id"], "erro": str(e)[:120],
                               "rank": None, "hit_k": None, "recall_k": None,
                               "alvo_ref": None})
            continue
        lats.append(dur)
        rank, hit, recall = mede(it, obras, secs)
        resultados.append({
            "pergunta_id": it["id"],
            "alvo_ref": it.get("alvo_section_id") or (it.get("alvo_obra_ids") or [None])[0],
            "rank": rank, "hit_k": hit, "recall_k": recall,
        })
    p50 = round(statistics.median(lats), 1) if lats else None
    p95 = round(sorted(lats)[int(len(lats) * 0.95)], 1) if len(lats) > 1 else None
    print(json.dumps({
        "n_executaveis": len(execut),
        "n_medidos": len(lats),
        "p50_ms": p50, "p95_ms": p95,
        "resultados": resultados,
    }, ensure_ascii=False))

if __name__ == "__main__":
    main()
