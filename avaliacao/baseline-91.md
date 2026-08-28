# Baseline do gold-91 (modos de falha) — run 671ed1a4

Gravado em motor-pg, schema avaliacao (run + 89 resultados), 28/08.

- executaveis medidos: 89
- com alvo: 25 | hit@8: 18 (72%)
- sem alvo (N/A, regra procurar-nao-achar): 64
- latencia p50 73.8ms / p95 204.7ms
- stack_sha: e1d30f6-provisorio (container nao expoe /version; debito TI/IA)

Reproduz: docker cp runner_gold_baseline.py + gold-proposto-modos.jsonl -> rag-extractor-api; roda; grava com grava-baseline.sql.
