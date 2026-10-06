#!/usr/bin/env bash
# Testes de bancada dos verbos `teste` e `lint` (card #3010): a raiz vem de pf_bancada,
# sem default; sem declaracao sai 3; worktree em <bancada>/wt/<repo>/<cadeira>; nenhum
# ato cria diretorio. Tudo em diretorio temporario — nao depende de bancada real.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
TESTE="$REPO_ROOT/bin/teste"
LINT="$REPO_ROOT/bin/lint"

TMP_DIR="$(mktemp -d /tmp/pf-teste-lint.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

unset PLATAFIRMA_BANCADA PF_CADEIRA PF_TESTE_PYTHON
export PLATAFIRMA_ARQUIVO_BANCADA="$TMP_DIR/config/bancada"   # nao existe
export PLATAFIRMA_RELEASE="$TMP_DIR/release"                  # nao existe

falha() { echo "FALHA: $*" >&2; exit 1; }
roda() { set +e; OUT="$("$@" 2>&1)"; RC=$?; set -e; }

echo "=== teste/lint: bancada declarada ==="

# 1. uso nao depende de bancada
for v in "$TESTE" "$LINT"; do
  roda "$v"
  [ "$RC" -eq 2 ] || falha "$(basename "$v") sem argumento devia sair 2, saiu $RC"
  grep -q "PLATAFIRMA_BANCADA" <<<"$OUT" || falha "uso de $(basename "$v") devia nomear PLATAFIRMA_BANCADA: $OUT"
done
echo "OK: uso sai 2 sem bancada e nomeia PLATAFIRMA_BANCADA"

# Do passo 2 em diante, so o lint: o `teste` resolve o nome pelo registro antes da bancada,
# sem escada de interpretador nem fallback ao clone base (#3152), e o contrato dele mora em
# controle/tests/test_contrato_teste.py e test_registro_chave.py (#3326).
# 2. sem PLATAFIRMA_BANCADA e sem arquivo -> exit 3, nada criado
for v in "$LINT"; do
  for ato in detectar rodar; do
    roda "$v" "$ato" platafirma-fixture
    [ "$RC" -eq 3 ] || falha "$(basename "$v") $ato sem bancada devia sair 3, saiu $RC: $OUT"
    grep -q "bancada nao declarada" <<<"$OUT" || falha "mensagem de bancada nao declarada ausente: $OUT"
  done
done
[ ! -e "$TMP_DIR/config" ] || falha "verbo criou o diretorio do arquivo de bancada"
echo "OK: sem declaracao sai 3 com causa"

# 3. bancada declarada mas inexistente -> recusa sem criar
export PLATAFIRMA_BANCADA="$TMP_DIR/bancada-inexistente"
for v in "$LINT"; do
  roda "$v" detectar platafirma-fixture
  [ "$RC" -ne 0 ] || falha "$(basename "$v") detectar em bancada inexistente devia recusar, saiu 0: $OUT"
done
[ ! -e "$PLATAFIRMA_BANCADA" ] || falha "leitura criou a bancada $PLATAFIRMA_BANCADA"
echo "OK: bancada inexistente recusa e nao e criada"

# 4. bancada declarada por arquivo; clone base e worktree por cadeira
unset PLATAFIRMA_BANCADA
BANC="$TMP_DIR/bancada"
mkdir -p "$(dirname "$PLATAFIRMA_ARQUIVO_BANCADA")"
printf '%s\n' "$BANC" > "$PLATAFIRMA_ARQUIVO_BANCADA"
FIX="$BANC/platafirma-fixture"
mkdir -p "$FIX"
git -C "$FIX" init -q -b main
printf '[project]\nname = "fixture"\nversion = "0"\n' > "$FIX/pyproject.toml"
git -C "$FIX" add . && git -C "$FIX" -c user.name=t -c user.email=t@t commit -q -m inicial

# sem PF_CADEIRA, o lint mede o clone base da bancada declarada
for v in "$LINT"; do
  roda "$v" detectar platafirma-fixture
  [ "$RC" -eq 0 ] || falha "$(basename "$v") detectar com bancada do arquivo devia sair 0, saiu $RC: $OUT"
  grep -q "stack python" <<<"$OUT" || falha "detectar devia achar stack python: $OUT"
done

git -C "$FIX" worktree add -q --detach "$BANC/wt/platafirma-fixture/ti" main
for v in "$LINT"; do
  roda env PF_CADEIRA=ti "$v" detectar platafirma-fixture
  [ "$RC" -eq 0 ] || falha "$(basename "$v") detectar no worktree devia sair 0, saiu $RC: $OUT"
  roda env PF_CADEIRA=dados "$v" detectar platafirma-fixture
  echo "  (cadeira sem worktree: rc=$RC)"
done
[ ! -e "$BANC/wt/platafirma-fixture/dados" ] || falha "leitura criou worktree de cadeira"
echo "OK: bancada do arquivo, clone base e worktree em wt/<repo>/<cadeira>; leitura nao cria worktree"

# 6. contencao: nome com barra sai 4
roda "$LINT" detectar ../fora
[ "$RC" -eq 4 ] || falha "lint com nome que escapa devia sair 4, saiu $RC"
echo "OK: escape sai 4"

echo "=== teste/lint: todos passaram ==="
