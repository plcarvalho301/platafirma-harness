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

# 2. sem PLATAFIRMA_BANCADA e sem arquivo -> exit 3, nada criado
for v in "$TESTE" "$LINT"; do
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
for v in "$TESTE" "$LINT"; do
  roda "$v" detectar platafirma-fixture
  [ "$RC" -eq 3 ] || falha "$(basename "$v") detectar em bancada inexistente devia sair 3, saiu $RC: $OUT"
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

for v in "$TESTE" "$LINT"; do
  roda "$v" detectar platafirma-fixture
  [ "$RC" -eq 0 ] || falha "$(basename "$v") detectar com bancada do arquivo devia sair 0, saiu $RC: $OUT"
  grep -q "stack python" <<<"$OUT" || falha "detectar devia achar stack python: $OUT"
  grep -q "aviso: PF_CADEIRA nao definida — usando fallback $BANC/platafirma-fixture" <<<"$OUT" \
    || falha "fallback ao clone base devia avisar: $OUT"
done

git -C "$FIX" worktree add -q --detach "$BANC/wt/platafirma-fixture/ti" main
for v in "$TESTE" "$LINT"; do
  roda env PF_CADEIRA=ti "$v" detectar platafirma-fixture
  [ "$RC" -eq 0 ] || falha "$(basename "$v") detectar no worktree devia sair 0, saiu $RC: $OUT"
  grep -q "aviso" <<<"$OUT" && falha "worktree wt/<repo>/<cadeira> existe e ainda assim caiu no fallback: $OUT"
  roda env PF_CADEIRA=dados "$v" detectar platafirma-fixture
  grep -q "aviso: worktree wt/platafirma-fixture/dados nao existe" <<<"$OUT" \
    || falha "cadeira sem worktree devia avisar com wt/<repo>/<cadeira>: $OUT"
done
[ ! -e "$BANC/wt/platafirma-fixture/dados" ] || falha "leitura criou worktree de cadeira"
echo "OK: bancada do arquivo, fallback ao clone base e worktree em wt/<repo>/<cadeira>"

# 5. teste: interpretador da release quando nao ha venv na bancada
mkdir -p "$PLATAFIRMA_RELEASE/venv/fixture/bin"
printf '#!/bin/sh\nexit 0\n' > "$PLATAFIRMA_RELEASE/venv/fixture/bin/python"
chmod +x "$PLATAFIRMA_RELEASE/venv/fixture/bin/python"
roda "$TESTE" detectar platafirma-fixture
grep -q "interpretador do projeto: $PLATAFIRMA_RELEASE/venv/fixture/bin/python" <<<"$OUT" \
  || falha "teste devia cair no venv da release: $OUT"
roda env PF_CADEIRA=ti "$TESTE" detectar platafirma-fixture
grep -q "interpretador do projeto: $PLATAFIRMA_RELEASE/venv/fixture/bin/python" <<<"$OUT" \
  || falha "no worktree wt/<repo>/<cadeira> o sufixo do venv vem do repo, nao da cadeira: $OUT"
mkdir -p "$BANC/.venv-fixture/bin"
cp "$PLATAFIRMA_RELEASE/venv/fixture/bin/python" "$BANC/.venv-fixture/bin/python"
roda "$TESTE" detectar platafirma-fixture
grep -q "interpretador do projeto: $BANC/.venv-fixture/bin/python" <<<"$OUT" \
  || falha "venv da bancada devia vencer o da release: $OUT"
echo "OK: escada de interpretador bancada -> release"

# 6. contencao: nome com barra sai 4
roda "$LINT" detectar ../fora
[ "$RC" -eq 4 ] || falha "lint com nome que escapa devia sair 4, saiu $RC"
echo "OK: escape sai 4"

echo "=== teste/lint: todos passaram ==="
