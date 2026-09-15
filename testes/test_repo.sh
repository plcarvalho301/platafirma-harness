#!/usr/bin/env bash
# Testes do verbo repo conforme spec_repo rev 2 (arq:0110, arq:0109, spec_verbologia_onda1)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/repo"

TMP_DIR="$(mktemp -d /tmp/pf-repo-test.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

echo "=== Iniciando suite de testes de repo (conforme spec_repo rev 2) ==="

# 0. Verificações estáticas de bin/repo
echo "--- Teste 0: Verificação de git e gh nu no bin ---"
if grep -n -E '([$(]|^[[:space:]]*)git[[:space:]]' "$VERBO" | grep -v 'GIT=' | grep -v '#'; then
  echo "FALHA: comando git nu encontrado em $VERBO" >&2
  exit 1
fi
if grep -n -E '([$(]|^[[:space:]]*)gh[[:space:]]' "$VERBO" | grep -v 'GH=' | grep -v '#'; then
  echo "FALHA: comando gh nu encontrado em $VERBO" >&2
  exit 1
fi
echo "OK: nenhum git ou gh nu em bin/repo"

# 2. Ato desconhecido
echo "--- Teste 2: Ato desconhecido ---"
set +e
out_desconhecido="$("$VERBO" ato_inexistente 2>&1)"
rc_desconhecido=$?
set -e
if [ "$rc_desconhecido" -ne 2 ]; then
  echo "FALHA: ato desconhecido devia sair 2, saiu $rc_desconhecido" >&2
  exit 1
fi
if ! grep -q "ato desconhecido" <<<"$out_desconhecido" || ! grep -q "atos:" <<<"$out_desconhecido"; then
  echo "FALHA: mensagem de erro não menciona 'ato desconhecido' ou lista de atos: $out_desconhecido" >&2
  exit 1
fi
echo "OK: ato desconhecido sai 2 com causa e lista de atos"

echo "=== Todos os testes do verbo repo passaram com sucesso! ==="
