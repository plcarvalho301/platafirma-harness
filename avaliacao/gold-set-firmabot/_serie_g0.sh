#!/bin/bash
# Serie G0 -- um arm por vez, sozinho na GPU. Unit unico: systemd-run --unit=g0-serie
set -u
cd /home/claudinho/AI/platafirma-harness/avaliacao/gold-set-firmabot
LOG=/home/claudinho/AI/var/log/g0
mkdir -p "$LOG"
for par in "granite4:latest G0-granite4" "qwen3.5:9b G0-qwen3.5-9b" "gemma4:12b G0-gemma4-12b"; do
  set -- $par
  echo "=== ARM $1 -> $2 inicio $(date -Is)"
  python3 g0_geracao.py "$1" "$2" > "$LOG/$(echo $2 | tr 'A-Z' 'a-z').log" 2>&1
  rc=$?
  echo "=== ARM $1 fim rc=$rc $(date -Is)"
  curl -s http://127.0.0.1:11434/api/generate -d "{\"model\":\"$1\",\"keep_alive\":0}" >/dev/null
  sleep 15
done
echo "=== SERIE COMPLETA $(date -Is)"
