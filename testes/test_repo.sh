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

# 4. #2856 linha 81: leitura sem bancada le origin/main buscado do forge, nunca a arvore do cache
echo "--- Teste 4: leitura sem bancada (#2856 linha 81) ---"
FORGE="$TMP_DIR/forge.git"
SEMENTE="$TMP_DIR/semente"
git init -q --bare -b main "$FORGE"
git clone -q "$FORGE" "$SEMENTE" 2>/dev/null
git -C "$SEMENTE" config user.name "Test Repo"
git -C "$SEMENTE" config user.email "test@platafirma.org"
echo "v1" > "$SEMENTE/a.txt"
git -C "$SEMENTE" add a.txt
git -C "$SEMENTE" commit -q -m "v1"
git -C "$SEMENTE" push -q origin main
# o clone base (cache) nasce em v1 e fica velho
git clone -q "$FORGE" "$BANCADA_TESTE/demo2"
echo "v2" > "$SEMENTE/a.txt"
echo "novo" > "$SEMENTE/novo.txt"
git -C "$SEMENTE" add a.txt novo.txt
git -C "$SEMENTE" commit -q -m "v2"
git -C "$SEMENTE" push -q origin main

err4="$TMP_DIR/err4"
out4="$("$VERBO" ler demo2 a.txt 2>"$err4")" || { echo "FALHA: repo ler sem bancada saiu $?: $(cat "$err4")" >&2; exit 1; }
[ "$out4" = "v2" ] || { echo "FALHA: repo ler sem bancada devia ler v2 de origin/main, leu '$out4'" >&2; exit 1; }
grep -q "sem bancada: lendo origin/main@" "$err4" || { echo "FALHA: repo ler sem bancada nao declarou a ref lida" >&2; exit 1; }
grep -q "versão: origin/main@" "$err4" || { echo "FALHA: repo ler sem bancada nao trouxe a versão" >&2; exit 1; }
[ "$(cat "$BANCADA_TESTE/demo2/a.txt")" = "v1" ] || { echo "FALHA: a arvore do cache mudou" >&2; exit 1; }

out4p="$("$VERBO" procurar demo2 '^v2$' 2>/dev/null)"
grep -qx "a.txt:1:v2" <<<"$out4p" || { echo "FALHA: repo procurar sem bancada devia dar 'a.txt:1:v2', deu '$out4p'" >&2; exit 1; }

out4l="$("$VERBO" listar demo2 2>/dev/null)"
grep -qx "novo.txt" <<<"$out4l" || { echo "FALHA: repo listar sem bancada nao listou novo.txt de origin/main" >&2; exit 1; }

out4h="$("$VERBO" historico demo2 a.txt 2>/dev/null)"
[ "$(grep -c . <<<"$out4h")" -eq 2 ] || { echo "FALHA: repo historico sem bancada devia ter 2 commits, teve: $out4h" >&2; exit 1; }

set +e
"$VERBO" ler demo2 ausente.txt >/dev/null 2>&1; rc_aus=$?
"$VERBO" ler demo2@outra a.txt >/dev/null 2>&1; rc_chave=$?
mv "$FORGE" "$FORGE.fora"
"$VERBO" ler demo2 a.txt >/dev/null 2>&1; rc_forge=$?
mv "$FORGE.fora" "$FORGE"
set -e
[ "$rc_aus" -eq 1 ] || { echo "FALHA: arquivo ausente em origin/main devia sair 1, saiu $rc_aus" >&2; exit 1; }
[ "$rc_chave" -eq 1 ] || { echo "FALHA: <repo>@<chave> sem bancada devia sair 1 sem cair em main, saiu $rc_chave" >&2; exit 1; }
[ "$rc_forge" -eq 5 ] || { echo "FALHA: forge fora devia sair 5, saiu $rc_forge" >&2; exit 1; }
echo "OK: sem bancada, ler/procurar/listar/historico leem origin/main do forge; chave nomeada exige bancada; forge fora sai 5"

# 5. DT 431: repo abrir em repositorio vazio cria o primeiro commit em main e abre o worktree
echo "--- Teste 5: DT 431 — repo abrir em repositorio vazio ---"
FORGE_VAZIO="$TMP_DIR/forge-vazio.git"
git init -q --bare -b main "$FORGE_VAZIO"
git clone -q "$FORGE_VAZIO" "$BANCADA_TESTE/platafirma-vazio" 2>/dev/null
out5="$("$VERBO" abrir platafirma-vazio --slug primeiro-commit 2>&1)" || {
  echo "FALHA: repo abrir em repositorio vazio saiu $?: $out5" >&2
  exit 1
}
[ -e "$BANCADA_TESTE/wt/platafirma-vazio/ti/primeiro-commit/.git" ] || {
  echo "FALHA: worktree nao nasceu em repositorio vazio ($out5)" >&2
  exit 1
}
git -C "$BANCADA_TESTE/platafirma-vazio" rev-parse --verify main >/dev/null 2>&1 || {
  echo "FALHA: ramo main nao foi criado em repositorio vazio" >&2
  exit 1
}
echo "OK: repo abrir em repositorio vazio inicializa main e abre a bancada"

# 6. DTs 814, 797, 793: regime direto em main (platafirma-casa-espelho)
echo "--- Teste 6: DT 814 — repo abrir --slug em direto_em_main sai 2 ---"
FORGE_ESPELHO="$TMP_DIR/forge-espelho.git"
SEMENTE_ESPELHO="$TMP_DIR/semente-espelho"
git init -q --bare -b main "$FORGE_ESPELHO"
git clone -q "$FORGE_ESPELHO" "$SEMENTE_ESPELHO" 2>/dev/null
git -C "$SEMENTE_ESPELHO" config user.name "Test Repo"
git -C "$SEMENTE_ESPELHO" config user.email "test@platafirma.org"
echo "base" > "$SEMENTE_ESPELHO/doc.md"
git -C "$SEMENTE_ESPELHO" add doc.md
git -C "$SEMENTE_ESPELHO" commit -q -m "base"
git -C "$SEMENTE_ESPELHO" push -q origin main
git clone -q "$FORGE_ESPELHO" "$BANCADA_TESTE/platafirma-casa-espelho"

set +e
out_slug="$(PF_SESSAO="sessao-a" "$VERBO" abrir platafirma-casa-espelho --slug nao-pode 2>&1)"
rc_slug=$?
set -e
[ "$rc_slug" -eq 2 ] || { echo "FALHA: DT 814 devia sair 2, saiu $rc_slug: $out_slug" >&2; exit 1; }
grep -q -- "--slug nao se aplica" <<< "$out_slug" || { echo "FALHA: DT 814 mensagem sem '--slug nao se aplica': $out_slug" >&2; exit 1; }
echo "OK: DT 814 — --slug em direto_em_main recusa com 2"

echo "--- Teste 7: DT 797 — repo git nao troca ramo da pasta de main; recusa diz sessao e desde ---"
PF_SESSAO="sessao-a" "$VERBO" abrir platafirma-casa-espelho >/dev/null
WT_ESPELHO="$BANCADA_TESTE/wt/platafirma-casa-espelho/ti/main"
git -C "$WT_ESPELHO" config user.name "Test Repo"
git -C "$WT_ESPELHO" config user.email "test@platafirma.org"

set +e
out_sw="$("$VERBO" git platafirma-casa-espelho switch -c outro 2>&1)"
rc_sw=$?
out_co="$("$VERBO" git platafirma-casa-espelho checkout -b outro 2>&1)"
rc_co=$?
set -e
[ "$rc_sw" -eq 4 ] || { echo "FALHA: DT 797 switch devia sair 4, saiu $rc_sw: $out_sw" >&2; exit 1; }
[ "$rc_co" -eq 4 ] || { echo "FALHA: DT 797 checkout -b devia sair 4, saiu $rc_co: $out_co" >&2; exit 1; }

# Simula pasta deixada em outro ramo com escrita suja (nao recuperavel automaticamente)
git -C "$WT_ESPELHO" checkout -q -b outro-ramo
echo "sujo" >> "$WT_ESPELHO/doc.md"
set +e
out_797="$(PF_SESSAO="sessao-b" "$VERBO" abrir platafirma-casa-espelho 2>&1)"
rc_797=$?
set -e
[ "$rc_797" -eq 4 ] || { echo "FALHA: DT 797 abrir em outro ramo sujo devia sair 4, saiu $rc_797: $out_797" >&2; exit 1; }
grep -q "sessão sessao-a desde " <<< "$out_797" || { echo "FALHA: DT 797 recusa nao informou sessao e desde: $out_797" >&2; exit 1; }
# Restaura para o proximo teste
git -C "$WT_ESPELHO" checkout -q -- doc.md
"$VERBO" git platafirma-casa-espelho checkout -B ti/main origin/main >/dev/null 2>&1
git -C "$WT_ESPELHO" branch -D outro-ramo >/dev/null 2>&1 || true
echo "OK: DT 797 — repo git bloqueia troca de ramo em main e recusa informa sessao e desde"

echo "--- Teste 8: DT 793 — sincronizar_direto_em_main empurra quando atras 0 mesmo com arvore suja ---"
echo "commit-novo" > "$WT_ESPELHO/novo.md"
git -C "$WT_ESPELHO" add novo.md
git -C "$WT_ESPELHO" commit -q -m "commit novo"
echo "sujo-alheio" >> "$WT_ESPELHO/doc.md"

out_793_ok="$("$VERBO" sincronizar platafirma-casa-espelho 2>&1)" || {
  echo "FALHA: DT 793 devia empurrar com atras 0 mesmo com arvore suja: $out_793_ok" >&2
  exit 1
}
grep -q "sincronizado: main =" <<< "$out_793_ok" || { echo "FALHA: DT 793 saida inesperada: $out_793_ok" >&2; exit 1; }
grep -q "sujo-alheio" "$WT_ESPELHO/doc.md" || { echo "FALHA: DT 793 tocou escrita alheia" >&2; exit 1; }

# Agora com atras > 0, deve recusar como antes
git -C "$SEMENTE_ESPELHO" pull -q origin main
echo "remoto" >> "$SEMENTE_ESPELHO/doc.md"
git -C "$SEMENTE_ESPELHO" add doc.md
git -C "$SEMENTE_ESPELHO" commit -q -m "remoto"
git -C "$SEMENTE_ESPELHO" push -q origin main
set +e
out_793_atras="$("$VERBO" sincronizar platafirma-casa-espelho 2>&1)"
rc_793_atras=$?
set -e
[ "$rc_793_atras" -eq 4 ] || { echo "FALHA: DT 793 com atras > 0 e sujo devia sair 4, saiu $rc_793_atras: $out_793_atras" >&2; exit 1; }
echo "OK: DT 793 — empurra com atras 0 sem tocar escrita alheia e recusa com atras > 0"

echo "--- Teste 8b: incidente 4371 — abrir refaz a worktree de main órfã e guarda a pasta ---"
rm -rf "$BANCADA_TESTE/platafirma-casa-espelho/.git/worktrees"
set +e
out_orfa_antes="$("$VERBO" estado platafirma-casa-espelho 2>&1)"
rc_orfa_antes=$?
out_orfa="$(PF_SESSAO="sessao-a" "$VERBO" abrir platafirma-casa-espelho 2>&1)"
rc_orfa=$?
set -e
[ "$rc_orfa_antes" -eq 5 ] || { echo "FALHA: 4371 a worktree órfã devia sair 5 no estado, saiu $rc_orfa_antes: $out_orfa_antes" >&2; exit 1; }
[ "$rc_orfa" -eq 0 ] || { echo "FALHA: 4371 abrir devia refazer a worktree órfã, saiu $rc_orfa: $out_orfa" >&2; exit 1; }
grep -q "worktree órfã" <<< "$out_orfa" || { echo "FALHA: 4371 abrir não disse que achou a órfã: $out_orfa" >&2; exit 1; }
"$VERBO" estado platafirma-casa-espelho >/dev/null 2>&1 || { echo "FALHA: 4371 a worktree refeita não responde ao estado" >&2; exit 1; }
grep -qs "sujo-alheio" "$BANCADA_TESTE/wt/platafirma-casa-espelho/ti/main/doc.md" || { echo "FALHA: 4371/DT-879 a árvore da worktree órfã não foi preservada" >&2; exit 1; }
echo "OK: 4371/DT-879 — worktree de main órfã religada a origin/main com árvore preservada"

echo "--- Teste 8c: colisão de gitdir (outra cadeira apontando para o gitdir de ti/main) ---"
WT_COL="$BANCADA_TESTE/wt/platafirma-casa-espelho/dados/main"
mkdir -p "$WT_COL"
cp "$BANCADA_TESTE/wt/platafirma-casa-espelho/ti/main/.git" "$WT_COL/.git"
echo "rascunho-dados" > "$WT_COL/nota-dados.txt"
set +e
out_col_antes="$(PF_CADEIRA=dados "$VERBO" estado platafirma-casa-espelho 2>&1)"
rc_col_antes=$?
out_col_san="$("$VERBO" sanear platafirma-casa-espelho 2>&1)"
rc_col_san=$?
set -e
[ "$rc_col_antes" -eq 5 ] || { echo "FALHA: colisão de gitdir devia sair 5 no estado, saiu $rc_col_antes: $out_col_antes" >&2; exit 1; }
[ "$rc_col_san" -eq 0 ] || { echo "FALHA: sanear devia religar worktree colidida, saiu $rc_col_san: $out_col_san" >&2; exit 1; }
ramo_col="$(git -C "$WT_COL" rev-parse --abbrev-ref HEAD 2>/dev/null)"
[ "$ramo_col" = "dados/main" ] || { echo "FALHA: worktree colidida devia ficar em dados/main, ficou em '$ramo_col'" >&2; exit 1; }
[ -f "$WT_COL/nota-dados.txt" ] || { echo "FALHA: árvore da worktree colidida não foi preservada" >&2; exit 1; }
echo "OK: colisão de gitdir detectada e religada ao ramo próprio sem tocar a outra cadeira"

# 9. DT 826: ramo divergido de origin/<ramo>
echo "--- Teste 9: DT 826 — repo sincronizar mescla ramo divergido de origin/<ramo> ---"
FORGE_DIV="$TMP_DIR/forge-div.git"
SEMENTE_DIV="$TMP_DIR/semente-div"
git init -q --bare -b main "$FORGE_DIV"
git clone -q "$FORGE_DIV" "$SEMENTE_DIV" 2>/dev/null
git -C "$SEMENTE_DIV" config user.name "Test Repo"
git -C "$SEMENTE_DIV" config user.email "test@platafirma.org"
echo "base" > "$SEMENTE_DIV/base.txt"
git -C "$SEMENTE_DIV" add base.txt
git -C "$SEMENTE_DIV" commit -q -m "base"
git -C "$SEMENTE_DIV" push -q origin main
git clone -q "$FORGE_DIV" "$BANCADA_TESTE/demo3"

"$VERBO" abrir demo3 --slug div-teste >/dev/null
WT_DIV="$BANCADA_TESTE/wt/demo3/ti/div-teste"
git -C "$WT_DIV" config user.name "Test Repo"
git -C "$WT_DIV" config user.email "test@platafirma.org"
echo "local" > "$WT_DIV/local.txt"
git -C "$WT_DIV" add local.txt
git -C "$WT_DIV" commit -q -m "local"
"$VERBO" empurrar demo3 >/dev/null

# Outro clone empurra commit proprio no mesmo ramo
git -C "$SEMENTE_DIV" fetch -q origin
git -C "$SEMENTE_DIV" checkout -q -b ti/div-teste origin/ti/div-teste
echo "remoto" > "$SEMENTE_DIV/remoto.txt"
git -C "$SEMENTE_DIV" add remoto.txt
git -C "$SEMENTE_DIV" commit -q -m "remoto"
git -C "$SEMENTE_DIV" push -q origin ti/div-teste

# Local tambem faz commit proprio -> divergido
echo "local2" > "$WT_DIV/local2.txt"
git -C "$WT_DIV" add local2.txt
git -C "$WT_DIV" commit -q -m "local2"

set +e
out_atu="$("$VERBO" atualizar demo3 2>&1)"
rc_atu=$?
set -e
[ "$rc_atu" -eq 4 ] || { echo "FALHA: DT 826 atualizar divergido devia sair 4, saiu $rc_atu: $out_atu" >&2; exit 1; }
grep -q "vizinho: repo sincronizar demo3" <<< "$out_atu" || { echo "FALHA: DT 826 atualizar sem vizinho repo sincronizar: $out_atu" >&2; exit 1; }

out_826="$("$VERBO" sincronizar demo3 2>&1)" || {
  echo "FALHA: DT 826 sincronizar divergido saiu $?: $out_826" >&2
  exit 1
}
grep -q "mesclou origin/ti/div-teste" <<< "$out_826" || { echo "FALHA: DT 826 saida sem mescla de origin/ramo: $out_826" >&2; exit 1; }
[ -f "$WT_DIV/remoto.txt" ] && [ -f "$WT_DIV/local2.txt" ] || { echo "FALHA: DT 826 arquivos faltando apos mescla" >&2; exit 1; }
echo "OK: DT 826 — atualizar aponta para sincronizar e sincronizar mescla ramo divergido"

echo "=== Todos os testes do verbo repo passaram com sucesso! ==="
