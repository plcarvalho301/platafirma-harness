#!/usr/bin/env python3
"""
runner_gold_baseline.py -- card #2894 (P0), migrado em #2896 (passo 2 do modelo #2313).
Roda o gold de 91 (modos de falha) contra o motor RAG servido e grava run + resultado
no motor-pg (schema avaliacao).

CHAVE DE CASAMENTO = OBRA (estavel), nao mais o slug section_id. O slug encurta no servido
(curto-v1) e nao sobrevive a re-extracao (defeito §1.2/§1.3 do modelo #2313); casar por ele
dava baseline falso (2/25). O motor devolve o TITULO da obra em cada fonte, entao casamos
{titulos do top-k} contra {titulos das obras-alvo}, resolvidos de OBRAS_MAP (uuid->titulo).

Baseline honesto: mede o que ha. Onde nao ha alvo (modo a/c/e ordem-consulta), rank/hit/
recall ficam NULL -- a regua e PROCURAR, nao achar (ordem do dono 27/08). Restam 3 itens
legados (d-22/23/24) com alvo_section_id e sem alvo_obra_ids: casados pelo modo section
antigo, que contra o servido curto-v1 tende a nao bater -- divida pequena, migrar o gold
desses para secao_id/obra e' curadoria separada.

stack_sha: o container nao expoe o proprio SHA (debito conhecido, falta /version). Grava o
SHA do repo do rag como PROVISORIO, marcado em params.stack_sha_origem.

Roda de dentro do rag-extractor-api (o host nao alcanca o motor). Ver caderno recuperacao.
"""
import json, os, time, statistics, urllib.request

GOLD = "/tmp/gold-proposto-modos.jsonl"
OBRAS_MAP = "/tmp/obra_titulos.json"          # uuid da obra -> titulo servido
K = 8
API = "http://localhost:8000/search"          # endpoint servido, de dentro do container
TOKEN = os.environ.get("RAG_API_TOKEN", "")

try:
    _OBRAS = json.load(open(OBRAS_MAP))
except FileNotFoundError:
    _OBRAS = {}
    print(f"[aviso] {OBRAS_MAP} ausente: casamento por obra fica cego (todo alvo_obra -> miss).")


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
    titulos = [f.get("obra") for f in fontes]
    secs = [f.get("section_id") for f in fontes]
    return titulos, secs, dur


def mede(item, titulos, secs):
    """rank/hit/recall so quando ha alvo; senao NULL (a regua e procurar).
    Preferencia: casar por OBRA (titulo). Fallback legado: por section_id base."""
    alvo_obras = item.get("alvo_obra_ids") or []
    alvo_sec = item.get("alvo_section_id")
    if not alvo_obras and not alvo_sec:
        return None, None, None          # sem alvo: N/A, nunca 0
    rank = None
    if alvo_obras:
        alvo_tit = {_OBRAS.get(u) for u in alvo_obras if _OBRAS.get(u)}
        for i, t in enumerate(titulos):
            if t and t in alvo_tit:
                rank = i + 1
                break
    elif alvo_sec:                        # legado: sem obra, so section
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
            titulos, secs, dur = busca(it["pergunta"])
        except Exception as e:
            resultados.append({"pergunta_id": it["id"], "erro": str(e)[:120],
                               "rank": None, "hit_k": None, "recall_k": None,
                               "alvo_ref": None})
            continue
        lats.append(dur)
        rank, hit, recall = mede(it, titulos, secs)
        alvo_obras = it.get("alvo_obra_ids") or []
        alvo_ref = (_OBRAS.get(alvo_obras[0]) if alvo_obras else None) or it.get("alvo_section_id")
        resultados.append({
            "pergunta_id": it["id"],
            "alvo_ref": alvo_ref,
            "rank": rank, "hit_k": hit, "recall_k": recall,
        })
    p50 = round(statistics.median(lats), 1) if lats else None
    p95 = round(sorted(lats)[int(len(lats) * 0.95)], 1) if len(lats) > 1 else None
    com_alvo = [r for r in resultados if r["hit_k"] is not None]
    hits = sum(1 for r in com_alvo if r["hit_k"])
    print(json.dumps({
        "n_executaveis": len(execut),
        "n_medidos": len(lats),
        "n_com_alvo": len(com_alvo),
        "hit_at_k": f"{hits}/{len(com_alvo)}",
        "p50_ms": p50, "p95_ms": p95,
        "resultados": resultados,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
