#!/usr/bin/env bash
# Teste e ensaio do verbo release (card #3014, B1+B2+B4)
set -euo pipefail

TMP_DIR="$(mktemp -d /tmp/pf-release-test.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

echo "== Iniciando bancada de ensaio do verbo release =="
OPT_DIR="$TMP_DIR/opt/platafirma"
AI_DIR="$TMP_DIR/AI"
BIN_DIR="$AI_DIR/bin"
PONTOS="$AI_DIR/var/release"

mkdir -p "$OPT_DIR" "$AI_DIR" "$BIN_DIR" "$PONTOS"

# 1. Cria repositorios de teste
HARNESS_DIR="$AI_DIR/platafirma-harness"
CORE_DIR="$AI_DIR/platafirma-core"
CONHECIMENTO_DIR="$AI_DIR/platafirma-conhecimento"

for repo in "$HARNESS_DIR" "$CORE_DIR" "$CONHECIMENTO_DIR"; do
  mkdir -p "$repo"
  git -C "$repo" init -q
  git -C "$repo" config user.name "Claudinho Teste"
  git -C "$repo" config user.email "claudinho@platafirma.org"
  echo "conteudo inicial" > "$repo/README.md"
  git -C "$repo" add .
  git -C "$repo" commit -q -m "initial commit"
  git -C "$repo" tag "v0.0.9"
  echo "conteudo v0.1.0" >> "$repo/README.md"
  git -C "$repo" commit -q -am "release v0.1.0"
  git -C "$repo" tag "v0.1.0"
done

# Copia verbo release e cria estrutura basica
mkdir -p "$HARNESS_DIR/bin" "$HARNESS_DIR/politica-acesso" "$HARNESS_DIR/docs"
cp /home/jaiminho/harness-repo/bin/release "$HARNESS_DIR/bin/release"
cp /home/jaiminho/harness-repo/docs/procedencia-do-harness.md "$HARNESS_DIR/docs/procedencia-do-harness.md"
chmod +x "$HARNESS_DIR/bin/release"
cat > "$HARNESS_DIR/bin/exemplo-verbo" <<'EOF'
#!/usr/bin/env bash
echo "versao-release-original"
EOF
chmod +x "$HARNESS_DIR/bin/exemplo-verbo"
echo "politica: v0.1.0" > "$HARNESS_DIR/politica-acesso/politica.yaml"
git -C "$HARNESS_DIR" add .
git -C "$HARNESS_DIR" commit -q -am "adiciona bin e politica"
git -C "$HARNESS_DIR" tag -f "v0.1.0"

export PF_OPT_DIR="$OPT_DIR"
export PF_AI_DIR="$AI_DIR"
export PF_BIN_DIR="$BIN_DIR"
export RELEASE_PONTOS="$PONTOS"
export PF_HARNESS="$HARNESS_DIR"
export PF_CORE="$CORE_DIR"
export PF_CONHECIMENTO="$CONHECIMENTO_DIR"

mkdir -p "$AI_DIR/mock_bin"
cat > "$AI_DIR/mock_bin/deploy" <<'EOF'
#!/usr/bin/env bash
echo "   [deploy-real] executado: deploy $* (PF_SIM=${PF_SIM:-vazio})"
EOF
chmod +x "$AI_DIR/mock_bin/deploy"
export PATH="$AI_DIR/mock_bin:$PATH"

VERBO="$HARNESS_DIR/bin/release"

echo "== Passo 1: release estado inicial (sem current) =="
"$VERBO" estado

echo "== Passo 2: release promover v0.0.9 (versao base, modo real) =="
"$VERBO" promover "v0.0.9"

echo "== Passo 2b: teste de release promover com --ensaio =="
"$VERBO" promover "v0.0.9" --ensaio

echo "== Passo 3: release promover v0.1.0 (versao alvo, modo real) =="
"$VERBO" promover "v0.1.0"

# Verificacoes do Passo 3
[ -L "$OPT_DIR/current" ] || { echo "ERRO: $OPT_DIR/current nao e symlink"; exit 1; }
CURRENT_TARGET="$(readlink "$OPT_DIR/current")"
[ "$CURRENT_TARGET" = "v0.1.0" ] || { echo "ERRO: current aponta para $CURRENT_TARGET, esperado v0.1.0"; exit 1; }

echo "Verificando imutabilidade de /opt/platafirma/v0.1.0..."
if touch "$OPT_DIR/v0.1.0/teste.txt" 2>/dev/null; then
  echo "ERRO: /opt/platafirma/v0.1.0 nao esta em modo somente-leitura!"; exit 1
else
  echo "OK: /opt/platafirma/v0.1.0 e somente-leitura."
fi

echo "Verificando symlink ~/AI/bin/exemplo-verbo..."
[ -L "$BIN_DIR/exemplo-verbo" ] || { echo "ERRO: $BIN_DIR/exemplo-verbo nao e symlink"; exit 1; }
BIN_TARGET="$(readlink "$BIN_DIR/exemplo-verbo")"
[ "$BIN_TARGET" = "$OPT_DIR/current/harness/bin/exemplo-verbo" ] || {
  echo "ERRO: destino do bin e $BIN_TARGET, esperado $OPT_DIR/current/harness/bin/exemplo-verbo"; exit 1
}

echo "Testando isolamento de working tree (aceite #3014):"
# Edicao no working tree do clone NAO deve alterar a execucao de ~/AI/bin
cat > "$HARNESS_DIR/bin/exemplo-verbo" <<'EOF'
#!/usr/bin/env bash
echo "MODIFICADO-NO-WORKING-TREE"
EOF
SAIDA_BIN="$("$BIN_DIR/exemplo-verbo")"
if [ "$SAIDA_BIN" = "versao-release-original" ]; then
  echo "OK: edicao no working tree do clone NAO afetou ~/AI/bin (saida: $SAIDA_BIN)"
else
  echo "ERRO: ~/AI/bin executou codigo do working tree modificado! ($SAIDA_BIN)"
  exit 1
fi

echo "== Passo 4: release estado apos promover v0.1.0 =="
"$VERBO" estado

echo "== Passo 5: ensaio de reverter (plano) =="
"$VERBO" reverter

echo "== Passo 6: ensaio de reverter para v0.0.9 ida e volta =="
PF_SIM=1 "$VERBO" reverter --executar
REVERTIDO="$(readlink "$OPT_DIR/current")"
[ "$REVERTIDO" = "v0.0.9" ] || { echo "ERRO: reverter falhou, current aponta para $REVERTIDO"; exit 1; }
echo "OK: revertido para $REVERTIDO (ida realizada)"

echo "Promovendo de volta para v0.1.0 (volta realizada)..."
"$VERBO" promover "v0.1.0"
DE_VOLTA="$(readlink "$OPT_DIR/current")"
[ "$DE_VOLTA" = "v0.1.0" ] || { echo "ERRO: volta falhou, current aponta para $DE_VOLTA"; exit 1; }
echo "OK: de volta a $DE_VOLTA com sucesso."

echo "== Passo 7: teste do conferir pdp =="
PF_CURRENT_LINK="$OPT_DIR/current" python3 /home/jaiminho/harness-repo/bin/conferir pdp

echo "== Passo 8: teste do conferir procedencia (0 fora) =="
PF_AI_DIR="$AI_DIR" PF_BIN_DIR="$BIN_DIR" PF_HARNESS_DIR="$HARNESS_DIR" PF_OPT_DIR="$OPT_DIR" python3 /home/jaiminho/harness-repo/bin/conferir procedencia

echo "=== Todos os testes e ensaios de release passaram com sucesso! ==="
