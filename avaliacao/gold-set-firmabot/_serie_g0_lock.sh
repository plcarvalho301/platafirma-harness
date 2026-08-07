#!/bin/bash
set -u
cd /home/claudinho/AI/platafirma-harness/avaliacao/gold-set-firmabot
exec 9>/tmp/goldset-g0.lock
flock -n 9 || { echo "outro run com o lock; abortando"; exit 1; }
LOG=/home/claudinho/AI/var/log/g0; mkdir -p "$LOG"
for par in "granite4:latest G0-granite4" "qwen3.5:9b G0-qwen3.5-9b" "gemma4:12b G0-gemma4-12b"; do
  set -- $par
  echo "=== ARM $1 inicio $(date -Is)"
  python3 g0_geracao.py "$1" "$2" > "$LOG/${2}.log" 2>&1; echo "=== ARM $1 fim rc=$? $(date -Is)"
  curl -s http://127.0.0.1:11434/api/generate -d "{\"model\":\"$1\",\"keep_alive\":0}" >/dev/null
  sleep 15
done
echo "=== SERIE COMPLETA $(date -Is)"
