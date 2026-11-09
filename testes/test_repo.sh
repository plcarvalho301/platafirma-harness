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

# 0.1 Verificação de poda cosmética no ato git (DT 10)
echo "--- Teste 0.1: Verificação de declaração de poda cosmética para o ato git (DT 10) ---"
if ! grep -q '^# poda: cosmetica@git' "$VERBO"; then
  echo "FALHA: # poda: cosmetica@git ausente no cabeçalho de $VERBO" >&2
  exit 1
fi
echo "OK: # poda: cosmetica@git declarado no cabeçalho de bin/repo"

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

# 3. Testes funcionais de leitura e busca (DTs 426, 213, 420)
echo "--- Teste 3: Fixture de bancada para testes de leitura e busca ---"
BANCADA_TESTE="$TMP_DIR/bancada"
export PLATAFIRMA_BANCADA="$BANCADA_TESTE"
export PF_CADEIRA="claudinho-ti"

WT_TESTE="$BANCADA_TESTE/wt/demo/ti/card1"
mkdir -p "$WT_TESTE"
git -C "$WT_TESTE" init -q -b main
git -C "$WT_TESTE" config user.name "Test Repo"
git -C "$WT_TESTE" config user.email "test@platafirma.org"

# Gera arquivo com 30 linhas numeradas
for i in $(seq 1 30); do
  echo "Linha $i de conteúdo" >> "$WT_TESTE/arquivo.txt"
done

# Gera arquivo com código e termos
cat > "$WT_TESTE/code.py" <<'EOF'
import os
def alpha():
    return 1
def beta():
    return 2
class Omega:
    pass
EOF

cat > "$WT_TESTE/Dockerfile" <<'EOF'
FROM python:3.12-slim
WORKDIR /app
FROM node:20-alpine
EOF

mkdir -p "$WT_TESTE/bin"
cat > "$WT_TESTE/bin/curar" <<'EOF'
# script de curar
opcoes: --titulo e --autor
EOF

git -C "$WT_TESTE" add .
git -C "$WT_TESTE" commit -q -m "initial commit"

echo "OK: fixture criada em $WT_TESTE"

# 3.1 DT 426: repo ler com --linhas
echo "--- Teste 3.1: DT 426 — repo ler com --linhas ---"
out_linhas="$("$VERBO" ler demo@card1 arquivo.txt --linhas 5-10)"
linhas_contadas=$(echo "$out_linhas" | grep -c "Linha ")
if [ "$linhas_contadas" -ne 6 ]; then
  echo "FALHA: --linhas 5-10 devia retornar 6 linhas, retornou $linhas_contadas" >&2
  exit 1
fi
if ! grep -q "Linha 5 de conteúdo" <<<"$out_linhas" || ! grep -q "Linha 10 de conteúdo" <<<"$out_linhas"; then
  echo "FALHA: --linhas 5-10 não continha Linha 5 e Linha 10" >&2
  exit 1
fi
if grep -q "Linha 4 de conteúdo" <<<"$out_linhas" || grep -q "Linha 11 de conteúdo" <<<"$out_linhas"; then
  echo "FALHA: --linhas 5-10 vazou linhas fora da faixa" >&2
  exit 1
fi

# Últimas 5 linhas: --linhas -5
out_cauda="$("$VERBO" ler demo@card1 arquivo.txt --linhas -5)"
if ! grep -q "Linha 26 de conteúdo" <<<"$out_cauda" || ! grep -q "Linha 30 de conteúdo" <<<"$out_cauda"; then
  echo "FALHA: --linhas -5 não continha linhas 26 a 30" >&2
  exit 1
fi

# Linha 25 até o fim: --linhas 25-
out_ate_fim="$("$VERBO" ler demo@card1 arquivo.txt --linhas 25-)"
if ! grep -q "Linha 25 de conteúdo" <<<"$out_ate_fim" || ! grep -q "Linha 30 de conteúdo" <<<"$out_ate_fim"; then
  echo "FALHA: --linhas 25- falhou" >&2
  exit 1
fi

# Faixa inválida sai 2
set +e
"$VERBO" ler demo@card1 arquivo.txt --linhas 10-5 >/dev/null 2>&1
rc_invalido=$?
set -e
if [ "$rc_invalido" -ne 2 ]; then
  echo "FALHA: --linhas 10-5 devia sair 2, saiu $rc_invalido" >&2
  exit 1
fi
echo "OK: repo ler --linhas funciona para faixas 'a-b', '-n' e 'a-', e recusa faixa inválida com 2"

# 3.2 DT 213: repo ler com --offset e repo procurar com termos iniciados por traço
echo "--- Teste 3.2: DT 213 — repo ler --offset e repo procurar --termo com traço ---"
out_offset="$("$VERBO" ler demo@card1 arquivo.txt --offset 0)"
if ! grep -q "Linha 1 de conteúdo" <<<"$out_offset"; then
  echo "FALHA: repo ler com --offset 0 não retornou início" >&2
  exit 1
fi

# repo procurar --termo --titulo
out_proc_termo="$("$VERBO" procurar demo@card1 --termo --titulo)"
if ! grep -q "bin/curar" <<<"$out_proc_termo" || ! grep -q "\-\-titulo" <<<"$out_proc_termo"; then
  echo "FALHA: repo procurar --termo --titulo não achou o termo em bin/curar" >&2
  exit 1
fi

# repo procurar com -- delimitando opções
out_proc_dd="$("$VERBO" procurar demo@card1 -- --titulo bin/curar)"
if ! grep -q "bin/curar" <<<"$out_proc_dd" || ! grep -q "\-\-titulo" <<<"$out_proc_dd"; then
  echo "FALHA: repo procurar demo -- --titulo bin/curar falhou" >&2
  exit 1
fi
echo "OK: repo ler --offset e repo procurar com termos iniciados por traço funcionam"

# 3.3 DT 420: repo procurar com regex (ERE), âncoras e filtro de caminho
echo "--- Teste 3.3: DT 420 — regex (ERE), âncoras e --caminho em repo procurar ---"
# Alternância regex: python|node
out_regex="$("$VERBO" procurar demo@card1 'python|node')"
if ! grep -q "python" <<<"$out_regex" || ! grep -q "node" <<<"$out_regex"; then
  echo "FALHA: repo procurar com regex 'python|node' não casou alternância" >&2
  exit 1
fi

# Âncora de início de linha: ^FROM
out_ancora="$("$VERBO" procurar demo@card1 '^FROM ')"
if ! grep -q "FROM python" <<<"$out_ancora" || ! grep -q "FROM node" <<<"$out_ancora"; then
  echo "FALHA: repo procurar com âncora '^FROM ' não casou início de linha" >&2
  exit 1
fi

# Filtro de caminho com --caminho
out_caminho="$("$VERBO" procurar demo@card1 --caminho code.py 'def')"
if ! grep -q "code.py" <<<"$out_caminho"; then
  echo "FALHA: repo procurar --caminho code.py não retornou ocorrência de code.py" >&2
  exit 1
fi
if grep -q "Dockerfile" <<<"$out_caminho" || grep -q "bin/curar" <<<"$out_caminho"; then
  echo "FALHA: repo procurar --caminho code.py filtrou incorretamente outros arquivos" >&2
  exit 1
fi
echo "OK: repo procurar suporta regex ERE, âncoras e --caminho"

echo "=== Todos os testes do verbo repo passaram com sucesso! ==="
