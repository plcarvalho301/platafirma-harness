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

# 1. Usage e Golden
echo "--- Teste 1: Usage sem argumentos e Golden ---"
set +e
out_usage="$("$VERBO" 2>&1)"
rc_usage=$?
set -e
if [ "$rc_usage" -ne 2 ]; then
  echo "FALHA: repo sem argumentos devia sair 2, saiu $rc_usage" >&2
  exit 1
fi
tam_usage="$(printf '%s\n' "$out_usage" | wc -c)"
if [ "$tam_usage" -ge 1024 ]; then
  echo "FALHA: usage tem $tam_usage bytes (teto 1 KB)" >&2
  exit 1
fi
if [ -f "$SCRIPT_DIR/repo_usage.golden" ]; then
  diff -u "$SCRIPT_DIR/repo_usage.golden" <(printf '%s\n' "$out_usage") || {
    echo "FALHA: usage divergiu do golden record" >&2
    exit 1
  }
fi
echo "OK: usage sem argumentos sai 2, < 1 KB, idêntica ao golden"

echo "--- Teste 1b: Universal --ajuda ---"
set +e
out_ajuda="$("$VERBO" --ajuda 2>&1)"
rc_ajuda=$?
set -e
if [ "$rc_ajuda" -ne 2 ]; then
  echo "FALHA: repo --ajuda devia sair 2, saiu $rc_ajuda" >&2
  exit 1
fi
diff -u "$SCRIPT_DIR/repo_usage.golden" <(printf '%s\n' "$out_ajuda") || {
  echo "FALHA: repo --ajuda divergiu do golden" >&2
  exit 1
}
echo "OK: repo --ajuda sai 2 e confere com golden"

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

# 3. Montagem da fixture com repo git temporário
RAIZ_TESTE="$TMP_DIR/AI"
mkdir -p "$RAIZ_TESTE"
export PF_REPO_RAIZ="$RAIZ_TESTE"
export PF_CADEIRA="ti"

REPO_TESTE="$RAIZ_TESTE/repo-teste"
mkdir -p "$REPO_TESTE"
git -C "$REPO_TESTE" init -q -b main
git -C "$REPO_TESTE" config user.name "Test User"
git -C "$REPO_TESTE" config user.email "test@platafirma.org"
echo "# Repo Teste" > "$REPO_TESTE/README.md"
mkdir -p "$REPO_TESTE/docs" "$REPO_TESTE/src"
echo "especificação do teste" > "$REPO_TESTE/docs/spec.md"
echo "termo_procurado_aqui" >> "$REPO_TESTE/docs/spec.md"
echo "print('hello')" > "$REPO_TESTE/src/main.py"
git -C "$REPO_TESTE" add .
git -C "$REPO_TESTE" commit -q -m "commit inicial"
git -C "$REPO_TESTE" tag "v1.0.0"

# 4. Repo desconhecido, ordem trocada e escape de raiz
echo "--- Teste 4: Repo desconhecido, ordem trocada e escape de raiz ---"
set +e
out_repo_desc="$("$VERBO" estado repo_inexistente 2>&1)"
rc_repo_desc=$?
set -e
if [ "$rc_repo_desc" -ne 2 ]; then
  echo "FALHA: repo desconhecido devia sair 2, saiu $rc_repo_desc" >&2
  exit 1
fi
if ! grep -q "repositório desconhecido" <<<"$out_repo_desc" || ! grep -q "repo-teste" <<<"$out_repo_desc"; then
  echo "FALHA: recusa de repo desconhecido deve listar repos válidos: $out_repo_desc" >&2
  exit 1
fi

set +e
out_trocada_pull="$("$VERBO" git pull repo-teste 2>&1)"
rc_trocada_pull=$?
set -e
if [ "$rc_trocada_pull" -ne 2 ]; then
  echo "FALHA: repo git pull devia sair 2, saiu $rc_trocada_pull" >&2
  exit 1
fi
if ! grep -q "ordem trocada: 'repo git pull <repo>' — use 'repo atualizar <repo>'" <<<"$out_trocada_pull"; then
  echo "FALHA: recusa de ordem trocada pull não confere: $out_trocada_pull" >&2
  exit 1
fi

set +e
out_trocada_c="$("$VERBO" git -C repo-teste 2>&1)"
rc_trocada_c=$?
set -e
if [ "$rc_trocada_c" -ne 2 ]; then
  echo "FALHA: repo git -C devia sair 2, saiu $rc_trocada_c" >&2
  exit 1
fi
if ! grep -q "ordem trocada: 'repo git -C <repo>' — use 'repo <ato> <repo>'" <<<"$out_trocada_c"; then
  echo "FALHA: recusa de ordem trocada -C não confere: $out_trocada_c" >&2
  exit 1
fi

set +e
out_escape="$("$VERBO" ler ../fora arq 2>&1)"
rc_escape=$?
set -e
if [ "$rc_escape" -ne 4 ]; then
  echo "FALHA: escape de raiz devia sair 4, saiu $rc_escape" >&2
  exit 1
fi
echo "OK: repo desconhecido sai 2 com lista; ordem trocada sai 2 com cura; escape sai 4"

# 5. Atos de leitura: ler, listar, procurar, historico, diff, estado
echo "--- Teste 5: Atos de leitura ---"

# 5a. ler
out_ler="$("$VERBO" ler repo-teste docs/spec.md 2>"$TMP_DIR/ler_stderr")"
if ! grep -q "especificação do teste" <<<"$out_ler"; then
  echo "FALHA: ler arquivo existente não devolveu conteúdo correto" >&2
  exit 1
fi
err_ler="$(cat "$TMP_DIR/ler_stderr")"
if ! grep -q "versão: main@" <<<"$err_ler"; then
  echo "FALHA: stderr de ler deve conter versão: <ramo>@<sha>: $err_ler" >&2
  exit 1
fi

# ler arquivo modificado
echo "modificacao" >> "$REPO_TESTE/docs/spec.md"
"$VERBO" ler repo-teste docs/spec.md 2>"$TMP_DIR/ler_mod_stderr" >/dev/null
err_ler_mod="$(cat "$TMP_DIR/ler_mod_stderr")"
if ! grep -q "(modificado)" <<<"$err_ler_mod"; then
  echo "FALHA: stderr de ler arquivo modificado deve conter (modificado): $err_ler_mod" >&2
  exit 1
fi
git -C "$REPO_TESTE" checkout -q docs/spec.md

# ler inexistente -> exit 1 com varrido: e vizinho:
set +e
"$VERBO" ler repo-teste arq_inexistente.txt 2>"$TMP_DIR/ler_inex_stderr"
rc_ler_inex=$?
set -e
if [ "$rc_ler_inex" -ne 1 ]; then
  echo "FALHA: ler inexistente devia sair 1, saiu $rc_ler_inex" >&2
  exit 1
fi
err_ler_inex="$(cat "$TMP_DIR/ler_inex_stderr")"
if ! grep -q "varrido: bancada repo-teste/ti (main @" <<<"$err_ler_inex"; then
  echo "FALHA: linha varrido não confere com spec: $err_ler_inex" >&2
  exit 1
fi
if ! grep -q "vizinho: release ler repo-teste arq_inexistente.txt" <<<"$err_ler_inex"; then
  echo "FALHA: linha vizinho não confere com spec: $err_ler_inex" >&2
  exit 1
fi
echo "OK: repo ler funciona para existente, modificado e inexistente (exit 1 com varrido/vizinho)"

# 5b. listar
out_listar="$("$VERBO" listar repo-teste)"
if ! grep -q "README.md" <<<"$out_listar" || ! grep -q "docs/spec.md" <<<"$out_listar"; then
  echo "FALHA: listar não listou arquivos esperados: $out_listar" >&2
  exit 1
fi

out_listar_prefixo="$("$VERBO" listar repo-teste docs)"
if grep -q "README.md" <<<"$out_listar_prefixo" || ! grep -q "docs/spec.md" <<<"$out_listar_prefixo"; then
  echo "FALHA: listar com prefixo filtrou errado: $out_listar_prefixo" >&2
  exit 1
fi

# listar vazio legítimo -> exit 0 com motivo:
set +e
out_listar_vazio="$("$VERBO" listar repo-teste pasta_vazia 2>&1)"
rc_listar_vazio=$?
set -e
if [ "$rc_listar_vazio" -ne 0 ] || ! grep -q "motivo:" <<<"$out_listar_vazio"; then
  echo "FALHA: listar vazio legítimo devia sair 0 com motivo: $out_listar_vazio" >&2
  exit 1
fi

out_listar_json="$("$VERBO" listar repo-teste --json)"
python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
assert d["repo"] == "repo-teste"
assert "arquivos" in d and d["total"] >= 3
' <<<"$out_listar_json"
echo "OK: repo listar funciona, prefixo funciona, vazio legítimo sai 0 com motivo, --json válido"

# 5c. procurar
set +e
"$VERBO" procurar repo-teste 2>/dev/null
rc_proc_sem_termo=$?
set -e
if [ "$rc_proc_sem_termo" -ne 2 ]; then
  echo "FALHA: procurar sem --termo devia sair 2, saiu $rc_proc_sem_termo" >&2
  exit 1
fi

out_proc="$("$VERBO" procurar repo-teste --termo "termo_procurado_aqui")"
if ! grep -q "docs/spec.md:2:termo_procurado_aqui" <<<"$out_proc"; then
  echo "FALHA: procurar com termo não achou linha esperada: $out_proc" >&2
  exit 1
fi

set +e
out_proc_vazio="$("$VERBO" procurar repo-teste --termo "termo_que_nao_existe" 2>&1)"
rc_proc_vazio=$?
set -e
if [ "$rc_proc_vazio" -ne 0 ] || ! grep -q "motivo:" <<<"$out_proc_vazio"; then
  echo "FALHA: procurar sem hit devia sair 0 com motivo: $out_proc_vazio" >&2
  exit 1
fi

out_proc_json="$("$VERBO" procurar repo-teste --termo "termo_procurado" --json)"
python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
assert d["repo"] == "repo-teste"
assert d["total"] >= 1
assert d["ocorrencias"][0]["caminho"] == "docs/spec.md"
' <<<"$out_proc_json"
echo "OK: repo procurar funciona, busca literal -F, vazio legítimo sai 0 com motivo, --json válido"

# 5d. historico
out_hist="$("$VERBO" historico repo-teste)"
if ! grep -q "commit inicial" <<<"$out_hist"; then
  echo "FALHA: historico não mostrou commit inicial: $out_hist" >&2
  exit 1
fi

set +e
"$VERBO" historico repo-teste arq_inexistente.txt 2>"$TMP_DIR/hist_inex_stderr"
rc_hist_inex=$?
set -e
if [ "$rc_hist_inex" -ne 1 ]; then
  echo "FALHA: historico de arquivo inexistente devia sair 1, saiu $rc_hist_inex" >&2
  exit 1
fi
err_hist_inex="$(cat "$TMP_DIR/hist_inex_stderr")"
if ! grep -q "varrido: bancada repo-teste" <<<"$err_hist_inex"; then
  echo "FALHA: historico de arquivo inexistente deve ter varrido: $err_hist_inex" >&2
  exit 1
fi

out_hist_json="$("$VERBO" historico repo-teste --json)"
python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
assert d["repo"] == "repo-teste"
assert d["total"] >= 1
assert "commits" in d
' <<<"$out_hist_json"
echo "OK: repo historico funciona, arquivo inexistente sai 1 com varrido, --json válido"

# 5e. diff
echo "nova linha no spec" >> "$REPO_TESTE/docs/spec.md"
out_diff="$("$VERBO" diff repo-teste)"
if ! grep -q "+nova linha no spec" <<<"$out_diff"; then
  echo "FALHA: diff não mostrou linha adicionada: $out_diff" >&2
  exit 1
fi

git -C "$REPO_TESTE" add docs/spec.md
out_diff_staged="$("$VERBO" diff repo-teste --staged)"
if ! grep -q "+nova linha no spec" <<<"$out_diff_staged"; then
  echo "FALHA: diff --staged não mostrou linha no índice: $out_diff_staged" >&2
  exit 1
fi
git -C "$REPO_TESTE" reset -q HEAD docs/spec.md
git -C "$REPO_TESTE" checkout -q docs/spec.md
echo "OK: repo diff funciona para worktree e --staged"

# 5f. estado
out_estado="$("$VERBO" estado repo-teste)"
if ! grep -q "repo-teste  ·  ramo main" <<<"$out_estado" || ! grep -q "arvore limpa" <<<"$out_estado"; then
  echo "FALHA: estado não mostrou ramo limpo: $out_estado" >&2
  exit 1
fi

out_estado_json="$("$VERBO" estado repo-teste --json)"
python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
assert d["repo"] == "repo-teste"
assert d["ramo"] == "main"
assert d["limpo"] is True
' <<<"$out_estado_json"
echo "OK: repo estado funciona no terminal e com --json"

# 6. Atos de ciclo e mutação
echo "--- Teste 6: Atos de ciclo e mutação ---"

# 6a. ramo
set +e
out_ramo_card="$("$VERBO" ramo repo-teste 3052 --slug onda1)"
rc_ramo_card=$?
set -e
if [ "$rc_ramo_card" -ne 0 ]; then
  echo "FALHA: ramo com card e slug devia sair 0, saiu $rc_ramo_card" >&2
  exit 1
fi
if ! grep -q "ramo criado: fabrica/3052-onda1" <<<"$out_ramo_card"; then
  echo "FALHA: ramo criado não tem padrão fabrica/<card>-<slug>: $out_ramo_card" >&2
  exit 1
fi

# Ramo já lá -> exit 1
set +e
out_ramo_ja_la="$("$VERBO" ramo repo-teste 3052 --slug onda1 2>&1)"
rc_ramo_ja_la=$?
set -e
if [ "$rc_ramo_ja_la" -ne 1 ]; then
  echo "FALHA: ramo já lá devia sair 1, saiu $rc_ramo_ja_la" >&2
  exit 1
fi
if ! grep -q "ramo já em 'fabrica/3052-onda1'" <<<"$out_ramo_ja_la"; then
  echo "FALHA: mensagem de ramo já lá não confere: $out_ramo_ja_la" >&2
  exit 1
fi

# Nome livre aceito com aviso
set +e
out_ramo_livre="$("$VERBO" ramo repo-teste meu-ramo-livre 2>"$TMP_DIR/ramo_livre_stderr")"
rc_ramo_livre=$?
set -e
if [ "$rc_ramo_livre" -ne 0 ]; then
  echo "FALHA: ramo com nome livre devia ser aceito (exit 0), saiu $rc_ramo_livre" >&2
  exit 1
fi
err_ramo_livre="$(cat "$TMP_DIR/ramo_livre_stderr")"
if ! grep -q "aviso: nome livre de ramo ('meu-ramo-livre')" <<<"$err_ramo_livre"; then
  echo "FALHA: nome livre de ramo deve emitir aviso em stderr: $err_ramo_livre" >&2
  exit 1
fi
git -C "$REPO_TESTE" checkout -q main

echo "OK: repo ramo cria padrão fabrica/<card>-<slug>, ramo já lá sai 1, nome livre emite aviso"

# 6b. commitar
# Falta -m -> exit 2
set +e
"$VERBO" commitar repo-teste 2>/dev/null
rc_com_sem_m=$?
set -e
if [ "$rc_com_sem_m" -ne 2 ]; then
  echo "FALHA: commitar sem -m devia sair 2, saiu $rc_com_sem_m" >&2
  exit 1
fi

# Sem caminho e sem PF_SESSAO -> exit 3
set +e
out_com_sem_sessao="$(env -u PF_SESSAO "$VERBO" commitar repo-teste -m "msg teste" 2>&1)"
rc_com_sem_sessao=$?
set -e
if [ "$rc_com_sem_sessao" -ne 3 ]; then
  echo "FALHA: commitar sem caminho e sem PF_SESSAO devia sair 3, saiu $rc_com_sem_sessao" >&2
  exit 1
fi
if ! grep -q "PF_SESSAO ausente para commitar sem caminho" <<<"$out_com_sem_sessao"; then
  echo "FALHA: mensagem de PF_SESSAO ausente não confere: $out_com_sem_sessao" >&2
  exit 1
fi

# Com caminhos nomeados: commita só eles
echo "conteudo1" >> "$REPO_TESTE/docs/spec.md"
echo "conteudo2" >> "$REPO_TESTE/README.md"
"$VERBO" commitar repo-teste -m "commit apenas docs/spec.md" docs/spec.md
# README.md continua modificado no working tree
st_readme="$(git -C "$REPO_TESTE" status --porcelain)"
if ! grep -q "README.md" <<<"$st_readme"; then
  echo "FALHA: commitar com caminho nomeado commitiu mais arquivos do que o especificado" >&2
  exit 1
fi

# Arquivo sujo de terceiro na árvore -> exit 4
# README.md está sujo na árvore. Configuramos log de ops para sessão-teste tocando src/main.py.
LOG_OPS_DIR="$TMP_DIR/AI/var/log/ops"
mkdir -p "$LOG_OPS_DIR"
export PF_OPS_LOG_DIR="$LOG_OPS_DIR"
echo '{"tool": "write_file", "sessao_id": "sessao-1", "path": "'"$REPO_TESTE"'/src/main.py"}' > "$LOG_OPS_DIR/ops-2026-09-13.jsonl"
echo "# mudanca src" >> "$REPO_TESTE/src/main.py"

set +e
out_terceiro="$(PF_SESSAO="sessao-1" "$VERBO" commitar repo-teste -m "commit da sessao" 2>&1)"
rc_terceiro=$?
set -e
if [ "$rc_terceiro" -ne 4 ]; then
  echo "FALHA: commitar com arquivo de terceiro devia sair 4, saiu $rc_terceiro" >&2
  exit 1
fi
if ! grep -q "arquivo sujo de terceiro na árvore: 'README.md'" <<<"$out_terceiro"; then
  echo "FALHA: mensagem de arquivo de terceiro deve nomear README.md: $out_terceiro" >&2
  exit 1
fi

# Agora limpa o arquivo de terceiro e commita pela sessão
git -C "$REPO_TESTE" checkout -q README.md
PF_SESSAO="sessao-1" "$VERBO" commitar repo-teste -m "commit limpo da sessao"
st_depois="$(git -C "$REPO_TESTE" status --porcelain)"
if [ -n "$st_depois" ]; then
  echo "FALHA: árvore devia estar limpa após commit da sessão: $st_depois" >&2
  exit 1
fi

# Nada a commitar -> exit 1
set +e
out_nada="$("$VERBO" commitar repo-teste -m "nada" docs/spec.md 2>&1)"
rc_nada=$?
set -e
if [ "$rc_nada" -ne 1 ]; then
  echo "FALHA: nada a commitar devia sair 1, saiu $rc_nada" >&2
  exit 1
fi

# --tudo: deprecado mas funciona
echo "# alteracao tudo" >> "$REPO_TESTE/README.md"
set +e
out_tudo="$("$VERBO" commitar repo-teste -m "commit tudo" --tudo 2>"$TMP_DIR/tudo_stderr")"
rc_tudo=$?
set -e
if [ "$rc_tudo" -ne 0 ]; then
  echo "FALHA: commitar --tudo devia sair 0, saiu $rc_tudo" >&2
  exit 1
fi
err_tudo="$(cat "$TMP_DIR/tudo_stderr")"
if ! grep -q "deprecado: --tudo" <<<"$err_tudo"; then
  echo "FALHA: commitar --tudo deve avisar deprecado em stderr: $err_tudo" >&2
  exit 1
fi
echo "OK: repo commitar sem add -A, PF_SESSAO ausente sai 3, arquivo de terceiro sai 4, nada a commitar sai 1, --tudo avisa deprecado"

# 6c. atualizar
# Já em dia -> exit 1
set +e
out_atualizar="$("$VERBO" atualizar repo-teste 2>&1)"
rc_atualizar=$?
set -e
# Sem upstream sai 3
if [ "$rc_atualizar" -ne 3 ]; then
  echo "FALHA: atualizar sem upstream devia sair 3, saiu $rc_atualizar" >&2
  exit 1
fi

# 6d. abrir -> exit 2 informando que aguarda release
set +e
out_abrir="$("$VERBO" abrir repo-teste 2>&1)"
rc_abrir=$?
set -e
if [ "$rc_abrir" -ne 2 ]; then
  echo "FALHA: abrir devia sair 2, saiu $rc_abrir" >&2
  exit 1
fi
if ! grep -q "abrir depende de a porta servir main" <<<"$out_abrir"; then
  echo "FALHA: mensagem de abrir não confere: $out_abrir" >&2
  exit 1
fi

# 6e. clonar
"$VERBO" clonar "$REPO_TESTE" repo-clonado >/dev/null
if [ ! -d "$RAIZ_TESTE/repo-clonado/.git" ]; then
  echo "FALHA: clonar não criou repo-clonado" >&2
  exit 1
fi
set +e
"$VERBO" clonar "$REPO_TESTE" repo-clonado 2>/dev/null
rc_clonar_dup=$?
set -e
if [ "$rc_clonar_dup" -ne 3 ]; then
  echo "FALHA: clonar destino existente devia sair 3, saiu $rc_clonar_dup" >&2
  exit 1
fi

# 6f. git (passthrough)
out_git="$("$VERBO" git repo-teste status)"
if ! grep -q "On branch main" <<<"$out_git"; then
  echo "FALHA: repo git passthrough não funcionou: $out_git" >&2
  exit 1
fi

# 6g. pr-* com gh ausente -> exit 3
echo "--- Teste 6g: Atos pr-* com gh ausente ---"
# Simulando PATH sem gh
PATH_SEM_GH="/usr/bin:/bin"
set +e
out_pr_abrir="$(env PATH="$PATH_SEM_GH" "$VERBO" pr-abrir repo-teste --titulo "PR" 2>&1)"
rc_pr_abrir=$?
set -e
if [ "$rc_pr_abrir" -ne 3 ] || ! grep -q "'gh' nao esta no PATH" <<<"$out_pr_abrir"; then
  echo "FALHA: pr-abrir sem gh devia sair 3 com erro: $out_pr_abrir" >&2
  exit 1
fi

set +e
out_pr_listar="$(env PATH="$PATH_SEM_GH" "$VERBO" pr-listar repo-teste 2>&1)"
rc_pr_listar=$?
set -e
if [ "$rc_pr_listar" -ne 3 ]; then
  echo "FALHA: pr-listar sem gh devia sair 3, saiu $rc_pr_listar" >&2
  exit 1
fi

set +e
out_pr_ver="$(env PATH="$PATH_SEM_GH" "$VERBO" pr-ver repo-teste 1 2>&1)"
rc_pr_ver=$?
set -e
if [ "$rc_pr_ver" -ne 3 ]; then
  echo "FALHA: pr-ver sem gh devia sair 3, saiu $rc_pr_ver" >&2
  exit 1
fi

set +e
out_pr_diff="$(env PATH="$PATH_SEM_GH" "$VERBO" pr-diff repo-teste 1 2>&1)"
rc_pr_diff=$?
set -e
if [ "$rc_pr_diff" -ne 3 ]; then
  echo "FALHA: pr-diff sem gh devia sair 3, saiu $rc_pr_diff" >&2
  exit 1
fi

set +e
out_pr_merge="$(env PATH="$PATH_SEM_GH" "$VERBO" pr-merge repo-teste 1 2>&1)"
rc_pr_merge=$?
set -e
if [ "$rc_pr_merge" -ne 3 ]; then
  echo "FALHA: pr-merge sem gh devia sair 3, saiu $rc_pr_merge" >&2
  exit 1
fi
echo "OK: atos pr-* saem 3 quando gh está ausente"

# 7. --json devolve {"erro": ...} na falha
echo "--- Teste 7: --json devolve {\"erro\": ...} na falha ---"
set +e
out_json_falha="$("$VERBO" procurar repo-teste --json 2>&1)"
rc_json_falha=$?
set -e
if [ "$rc_json_falha" -ne 2 ]; then
  echo "FALHA: procurar sem termo devia sair 2, saiu $rc_json_falha" >&2
  exit 1
fi
python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
assert "erro" in d, "falha com --json deve devolver objeto {\"erro\": ...}"
' <<<"$out_json_falha"
echo "OK: falha com --json devolve {\"erro\": ...}"

echo "=== Todos os testes do verbo repo passaram com sucesso! ==="
