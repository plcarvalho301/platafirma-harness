#!/bin/bash
# Serie limpa dos arms G0: um gerador por vez, nada concorrente no Ollama.
# Espera qualquer geracao em andamento terminar, depois toma o lock e roda os tres.
set -u
cd /home/claudinho/AI/platafirma-harness/avaliacao/gold-set-firmabot

while pgrep -f 'python3 g0_geracao\.py' >/dev/null; do
  echo "aguardando geracao em andamento... $(date -Is)"
  sleep 30
done

exec 9>/tmp/goldset-g0.lock
flock -n 9 || { echo "outro run com o lock; abortando"; exit 1; }

for par in "granite4:latest G0-granite4" "qwen3.5:9b G0-qwen3.5-9b" "gemma4:12b G0-gemma4-12b"; do
  set -- $par
  echo "=== ARM $1 -> $2  inicio $(date -Is)"
  python3 g0_geracao.py "$1" "$2"
  echo "=== ARM $1 fim rc=$? $(date -Is)"
  sleep 20
done
echo "=== SERIE COMPLETA $(date -Is)"
