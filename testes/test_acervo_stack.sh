#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/_acervo/stack"

echo "=== Iniciando suite de testes de acervo stack ==="

TMP_JSON=$(mktemp)
trap 'rm -f "$TMP_JSON"' EXIT

# Test 1: import com pre_build
cat <<EOF > "$TMP_JSON"
{
  "stacks": {
    "test-stack-prebuild": {
      "papel": "test",
      "critico": false,
      "repo": "test-repo",
      "compose": "docker-compose.yml",
      "pre_build": "wiki/montar-wiki"
    }
  }
}
EOF

echo "--- Teste 1: import com pre_build ---"
"$VERBO" import "$TMP_JSON" > /dev/null

out_ver=$("$VERBO" ver --json)
if ! echo "$out_ver" | grep -q '"pre_build": "wiki/montar-wiki"'; then
  echo "FALHA: pre_build nao foi projetado corretamente." >&2
  exit 1
fi
echo "OK: import e projecao de pre_build"

# Test 2: stack sem pre_build
cat <<EOF > "$TMP_JSON"
{
  "stacks": {
    "test-stack-noprebuild": {
      "papel": "test",
      "critico": false,
      "repo": "test-repo",
      "compose": "docker-compose.yml"
    }
  }
}
EOF

echo "--- Teste 2: stack sem pre_build ---"
"$VERBO" import "$TMP_JSON" > /dev/null

out_ver=$("$VERBO" ver --json)
# Assuming test-stack-noprebuild has pre_build: null
# we can check specifically for the stack
if ! echo "$out_ver" | grep -A 15 '"slug": "test-stack-noprebuild"' | grep -q '"pre_build": null'; then
  echo "FALHA: pre_build nao projetado como null quando ausente." >&2
  exit 1
fi
echo "OK: stack sem pre_build projeta null"

# Limpeza
"$VERBO" rm test-stack-prebuild > /dev/null
"$VERBO" rm test-stack-noprebuild > /dev/null

echo "=== Todos os testes do verbo acervo stack passaram com sucesso! ==="
