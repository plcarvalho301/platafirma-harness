#!/usr/bin/env bash
# P0 #2894 — baseline e2e do gold contra /search SERVIDA, em UMA chamada.
# Mede no container (host nao alcanca o motor), grava avaliacao.run + resultado (motor-pg),
# aplicando a regua N/A: sem alvo -> rank/hit/recall = NULL (nunca 0).
# Uso: bash rodar-baseline.sh [caminho_gold.jsonl] [rotulo_conjunto]
set -euo pipefail
ROOT="/home/claudinho/AI"
GOLD="${1:-$ROOT/platafirma-harness/avaliacao/gabarito.jsonl}"
CONJ="${2:-gold-228-reancorado}"
DIR="$(cd "$(dirname "$0")" && pwd)"
C=rag-extractor-api

docker cp "$GOLD" $C:/tmp/gabarito.jsonl >/dev/null
docker cp "$DIR/runner_gold_baseline.py" $C:/tmp/ >/dev/null
docker exec -w /app -e PYTHONPATH=/app $C python /tmp/runner_gold_baseline.py | tee /tmp/baseline_agg.txt
docker cp $C:/tmp/baseline_resultados.jsonl /tmp/baseline_resultados.jsonl >/dev/null

MDSN=$(python3 -c "import urllib.parse;e={k:v.strip().strip(chr(34)).strip(chr(39)) for k,v in (l.strip().split('=',1) for l in open('$ROOT/deploy/motor/.env') if '=' in l and not l.startswith('#'))};print('postgresql://motor:%s@127.0.0.1:5433/motor'%urllib.parse.quote(e['MOTOR_PG_PASSWORD'],safe=''))")
GV=$(psql "$MDSN" -tAq -c "select id from avaliacao.gabarito_versao order by criado_em desc limit 1" | grep -Eo '[0-9a-f-]{36}')
J=$(grep '^JSON ' /tmp/baseline_agg.txt | tail -1 | cut -c6-)
P50=$(python3 -c "import json,sys;print(json.loads('''$J''')['p50'])")
P95=$(python3 -c "import json,sys;print(json.loads('''$J''')['p95'])")
RUN=$(psql "$MDSN" -tAq -c "INSERT INTO avaliacao.run (gabarito_versao_id,stack_sha,params,latencia_p50_ms,latencia_p95_ms) VALUES ('$GV','rag-servido-desconhecido','{\"conjunto\":\"$CONJ\",\"k\":8}'::jsonb,$P50,$P95) RETURNING id" | grep -Eo '[0-9a-f-]{36}' | head -1)
python3 - "$RUN" <<'PY'
import json,sys
run=sys.argv[1].strip()
def s(v):
    if v is None: return "NULL"
    if isinstance(v,bool): return "true" if v else "false"
    if isinstance(v,(int,float)): return repr(v)
    return "'"+str(v).replace("'","''")+"'"
rows=[json.loads(l) for l in open("/tmp/baseline_resultados.jsonl") if l.strip()]
open("/tmp/ins.sql","w").write("INSERT INTO avaliacao.resultado (run_id,pergunta_id,alvo_ref,k,rank,hit_k,recall_k) VALUES\n"+",\n".join(f"('{run}',{s(r['pergunta_id'])},{s(r['alvo_ref'])},{r['k']},{s(r['rank'])},{s(r['hit_k'])},{s(r['recall_k'])})" for r in rows)+";\n")
PY
psql "$MDSN" -v ON_ERROR_STOP=1 -q -f /tmp/ins.sql
echo "OK: run $RUN gravado (gabarito_versao $GV), $(wc -l < /tmp/baseline_resultados.jsonl) resultados"
