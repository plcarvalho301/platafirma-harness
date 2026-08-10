#!/usr/bin/env python3
"""Bancada #393 — de onde vem o ruido na recuperacao: blend do revisor, pool, beta do metadado.

Uma variavel por rodada, mesmo gold set, duas familias medidas SEPARADAS:

  det : gold-deterministico.jsonl (118) — a pergunta cita codigo; alvo e o section_id exato
  t2  : gold-t2-obraid-20260805.jsonl   — a pergunta NAO cita codigo; alvo e a obra

O base de Settings espelha o que esta SERVIDO no container rag-extractor-api, medido em
10/08/2026 — nao o default do codigo. Toda config e um override declarado sobre esse base.

  gabarito: avaliacao/gabarito.jsonl (unico, desde o expurgo de 10/08)
  venv: ~/AI/.venv-embed  (torch, sentence-transformers, psycopg, pgvector)
  uso : ~/AI/.venv-embed/bin/python bancada_ruido.py --eixo blend|pool|beta|todos
"""

import argparse
import json
import os
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path

RAG = Path.home() / "AI/platafirma-conhecimento/rag"
GABARITO = Path.home() / "AI/platafirma-harness/avaliacao/gabarito.jsonl"
SAIDA = Path(__file__).resolve().parent

sys.path.insert(0, str(RAG))

from rag_extractor.config import RECOMMENDED_RERANKER, load_settings  # noqa: E402
from rag_extractor.runtime import retrieve  # noqa: E402
from rag_extractor.store.db import get_conn  # noqa: E402

K = 10  # recupera 10 e mede recall@1/3/5/10 sobre o mesmo run


def _env_do_servido() -> None:
    """Reproduz o ambiente do container medido. Sem isto a bancada mede outro sistema."""
    for linha in (RAG / ".env").read_text().splitlines():
        if linha.startswith("POSTGRES_") and "=" in linha:
            ch, v = linha.split("=", 1)
            os.environ.setdefault(ch.strip(), v.strip().strip('"').strip("'"))
    os.environ["POSTGRES_HOST"] = "127.0.0.1"
    servido = {
        "EMBED_MODEL": "Qwen/Qwen3-Embedding-0.6B",
        "EMBED_BACKEND": "torch",
        "EMBED_DEVICE": "cuda",
        "EMBED_META_BETA": "0.15",
        "EMBED_QUERY_INSTRUCTION":
            "Given a search query, retrieve relevant passages that answer the query",
        "HYBRID_VEC_POOL": "150",
        "RERANK_POOL": "10",
        "RERANK_BLEND": "0",
        "DEDUP_JACCARD": "0.5",
    }
    for ch, v in servido.items():
        os.environ[ch] = v


def carregar_gold():
    """Le o gabarito unico. `det` = quem tem section_id alvo; `t2` = quem tem obra alvo.

    Nao pontuavel fica de fora dos dois: item marcado assim existe para nao sumir do
    registro, nao para entrar em conta de recall.
    """
    det, t2 = [], []
    for l in GABARITO.read_text().splitlines():
        if not l.strip():
            continue
        d = json.loads(l)
        if not d.get("pontuavel"):
            continue
        if d.get("alvo_section_id"):
            det.append({"pergunta": d["pergunta"], "alvo": d["alvo_section_id"], "id": d["id"]})
        elif d.get("alvo_obra_ids"):
            t2.append({"pergunta": d["pergunta"], "alvo": set(d["alvo_obra_ids"]), "id": d["id"]})
    return det, t2


def _base_section(sid: str) -> str:
    """section_id do banco vem com sufixo de parte (~2). O gold guarda a base."""
    return (sid or "").split("~")[0]


def posicao_do_acerto(fontes, item, familia):
    for i, f in enumerate(fontes, start=1):
        if familia == "det":
            if _base_section(f.section_id) == _base_section(item["alvo"]):
                return i
        else:
            if str(f.obra_id) in item["alvo"]:
                return i
    return None


def rodar(conn, settings, itens, familia):
    posicoes, tempos = [], []
    for it in itens:
        t0 = time.perf_counter()
        try:
            fontes = retrieve(conn, settings, it["pergunta"], k=K)
        except Exception as e:                      # falha de uma pergunta nao derruba a rodada
            print(f"    ! {it['id']}: {type(e).__name__}: {e}", file=sys.stderr)
            posicoes.append(None)
            continue
        tempos.append((time.perf_counter() - t0) * 1000)
        posicoes.append(posicao_do_acerto(fontes, it, familia))
    n = len(posicoes)
    achou = [p for p in posicoes if p]
    return {
        "n": n,
        "recall@1": round(sum(1 for p in achou if p <= 1) / n, 3) if n else 0,
        "recall@3": round(sum(1 for p in achou if p <= 3) / n, 3) if n else 0,
        "recall@5": round(sum(1 for p in achou if p <= 5) / n, 3) if n else 0,
        "recall@10": round(len(achou) / n, 3) if n else 0,
        "mrr": round(sum(1 / p for p in achou) / n, 3) if n else 0,
        "ms_mediana": round(statistics.median(tempos), 1) if tempos else None,
    }


def configs(eixo, base):
    """Cada entrada: (rotulo, Settings). O rotulo diz a variavel que mudou."""
    ligado = base.rerank_model or RECOMMENDED_RERANKER
    if eixo == "blend":
        yield "servido (sem revisor)", replace(base, rerank_model="")
        for b in (0.0, 0.3, 0.5, 1.0):
            yield f"revisor blend={b}", replace(base, rerank_model=ligado, rerank_blend=b)
    elif eixo == "pool":
        for p in (25, 50, 100, 150):
            yield f"pool={p} (sem revisor)", replace(base, rerank_model="", hybrid_vec_pool=p)
    elif eixo == "beta":
        for b in (0.0, 0.15, 0.30, 0.45, 0.60, 0.80, 1.00):
            yield f"beta_meta={b}", replace(base, rerank_model="", embed_meta_beta=b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eixo", default="todos", choices=["blend", "pool", "beta", "todos"])
    ap.add_argument("--limite", type=int, default=0, help="corta o gold para ensaio rapido")
    args = ap.parse_args()

    _env_do_servido()
    base = load_settings()
    det, t2 = carregar_gold()
    if args.limite:
        det, t2 = det[:args.limite], t2[:args.limite]
    print(f"gold: det={len(det)} · t2={len(t2)} · k={K}", flush=True)
    print(f"base servido: pool={base.hybrid_vec_pool} beta={base.embed_meta_beta} "
          f"rerank_pool={base.rerank_pool} blend={base.rerank_blend} "
          f"dedup={base.dedup_jaccard}", flush=True)

    eixos = ["blend", "pool", "beta"] if args.eixo == "todos" else [args.eixo]
    resultado = {"medido_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "k": K,
                 "gold": {"det": len(det), "t2": len(t2)}, "eixos": {}}

    with get_conn(base) as conn:
        for eixo in eixos:
            print(f"\n=== eixo {eixo}", flush=True)
            resultado["eixos"][eixo] = []
            for rotulo, cfg in configs(eixo, base):
                linha = {"config": rotulo,
                         "det": rodar(conn, cfg, det, "det"),
                         "t2": rodar(conn, cfg, t2, "t2")}
                resultado["eixos"][eixo].append(linha)
                d, t = linha["det"], linha["t2"]
                print(f"  {rotulo:<26} det r@1={d['recall@1']:.3f} r@5={d['recall@5']:.3f} "
                      f"mrr={d['mrr']:.3f} {d['ms_mediana']}ms | "
                      f"t2 r@1={t['recall@1']:.3f} r@5={t['recall@5']:.3f} "
                      f"mrr={t['mrr']:.3f}", flush=True)

    destino = SAIDA / f"bancada-ruido-{time.strftime('%Y%m%d')}.json"
    destino.write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
    print(f"\nsalvo: {destino}", flush=True)


if __name__ == "__main__":
    main()
