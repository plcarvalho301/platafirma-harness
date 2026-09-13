#!/usr/bin/env bash
# Testes do verbo release conforme spec_release rev 2 (arq:0110, arq:0109) — Lote 1
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/release"

TMP_DIR="$(mktemp -d /tmp/pf-release-test.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

echo "=== Iniciando suite de testes de release (Lote 1 — Revisão TI) ==="

# 0. Verificações estáticas de bin/release
echo "--- Teste 0: Verificação de git nu no bin (inclui \$(git …) e (git …)) ---"
if grep -n -E '([$(]|^[[:space:]]*)git[[:space:]]' "$VERBO" | grep -v 'GIT=' | grep -v '#'; then
  echo "FALHA: comando git nu encontrado em $VERBO" >&2
  exit 1
fi
echo "OK: nenhum git nu em bin/release"

# 1. Usage e Golden
echo "--- Teste 1: Usage sem argumentos e Golden ---"
set +e
out_usage="$("$VERBO" 2>&1)"
rc_usage=$?
set -e
if [ "$rc_usage" -ne 2 ]; then
  echo "FALHA: release sem argumentos devia sair 2, saiu $rc_usage" >&2
  exit 1
fi
tam_usage="$(printf '%s
' "$out_usage" | wc -c)"
if [ "$tam_usage" -ge 1024 ]; then
  echo "FALHA: usage tem $tam_usage bytes (teto 1 KB)" >&2
  exit 1
fi
if [ -f "$SCRIPT_DIR/release_usage.golden" ]; then
  diff -u "$SCRIPT_DIR/release_usage.golden" <(printf '%s
' "$out_usage") || {
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
  echo "FALHA: release --ajuda devia sair 2, saiu $rc_ajuda" >&2
  exit 1
fi
diff -u "$SCRIPT_DIR/release_usage.golden" <(printf '%s
' "$out_ajuda") || {
  echo "FALHA: release --ajuda divergiu do golden" >&2
  exit 1
}
echo "OK: release --ajuda sai 2 e confere com golden"

# 2. Atos inválidos e erros de uso
echo "--- Teste 2: Ato desconhecido ---"
set +e
out_desconhecido="$("$VERBO" naoexiste 2>&1)"
rc_desconhecido=$?
set -e
if [ "$rc_desconhecido" -ne 2 ]; then
  echo "FALHA: ato desconhecido devia sair 2, saiu $rc_desconhecido" >&2
  exit 1
fi
if ! grep -q "ato desconhecido" <<<"$out_desconhecido"; then
  echo "FALHA: mensagem de erro não menciona 'ato desconhecido'" >&2
  exit 1
fi
echo "OK: ato desconhecido sai 2 com causa e usage"

# 3. Montagem da fixture de servido com SHAs reais
PROD_RAIZ="$TMP_DIR/var/prod"
PONTOS="$TMP_DIR/var/release"
ABERTURA_DIR="$TMP_DIR/var/abertura-publicada"
BIN_DIR="$TMP_DIR/bin"
mkdir -p "$PROD_RAIZ" "$PONTOS" "$ABERTURA_DIR" "$BIN_DIR"

export PF_PROD_RAIZ="$PROD_RAIZ"
export PF_RELEASE_RAIZ="$PONTOS"
export PF_ABERTURA_RAIZ="$ABERTURA_DIR"
export PF_BIN_DIR="$BIN_DIR"

# Repo 1: platafirma-harness (CÓDIGO, com tag v0.1.0)
HARNESS_DIR="$TMP_DIR/repos/platafirma-harness"
mkdir -p "$HARNESS_DIR"
git -C "$HARNESS_DIR" init -q -b main
git -C "$HARNESS_DIR" config user.name "Test Harness"
git -C "$HARNESS_DIR" config user.email "test@platafirma.org"
echo "harness initial" > "$HARNESS_DIR/README.md"
mkdir -p "$HARNESS_DIR/bin"
echo '#!/usr/bin/env bash' > "$HARNESS_DIR/bin/foo"
echo 'echo foo' >> "$HARNESS_DIR/bin/foo"
git -C "$HARNESS_DIR" add .
git -C "$HARNESS_DIR" commit -q -m "init harness"
git -C "$HARNESS_DIR" tag "v0.1.0"
HARNESS_SHA="$(git -C "$HARNESS_DIR" rev-parse HEAD)"

# Repo 2: platafirma-arquitetura (DOCUMENTAÇÃO, sem tag)
DOC_DIR="$TMP_DIR/repos/platafirma-arquitetura"
mkdir -p "$DOC_DIR"
git -C "$DOC_DIR" init -q -b main
git -C "$DOC_DIR" config user.name "Test Doc"
git -C "$DOC_DIR" config user.email "test@platafirma.org"
echo "arquitetura doc" > "$DOC_DIR/README.md"
mkdir -p "$DOC_DIR/docs"
echo "# Spec de teste" > "$DOC_DIR/docs/spec_teste.md"
echo "termo_procurado_aqui" >> "$DOC_DIR/docs/spec_teste.md"
echo "termo.com[regex]*literal" >> "$DOC_DIR/docs/spec_teste.md"
git -C "$DOC_DIR" add .
git -C "$DOC_DIR" commit -q -m "init doc"
DOC_SHA="$(git -C "$DOC_DIR" rev-parse HEAD)"

# Materializa no servido var/prod/<repo>/<sha real de 40 hex>
# 1. platafirma-harness
mkdir -p "$PROD_RAIZ/platafirma-harness/$HARNESS_SHA"
git clone --shared -q "$HARNESS_DIR" "$PROD_RAIZ/platafirma-harness/$HARNESS_SHA"
git -C "$PROD_RAIZ/platafirma-harness/$HARNESS_SHA" checkout -q --detach "$HARNESS_SHA"
chmod -R a-w "$PROD_RAIZ/platafirma-harness/$HARNESS_SHA"
ln -s "$HARNESS_SHA" "$PROD_RAIZ/platafirma-harness/current"

# Ponto de volta e atual para platafirma-harness (com sha de 40 hex e ISO-8601 UTC)
mkdir -p "$PONTOS/platafirma-harness"
ANTERIOR_REAL_SHA="88d0993881b68f5acc699b11e8831d489d4f432b"
echo "$ANTERIOR_REAL_SHA" > "$PONTOS/platafirma-harness/anterior"
echo "$HARNESS_SHA 2026-09-12T14:26:16Z" > "$PONTOS/platafirma-harness/atual"

# 2. platafirma-arquitetura
mkdir -p "$PROD_RAIZ/platafirma-arquitetura/$DOC_SHA"
git clone --shared -q "$DOC_DIR" "$PROD_RAIZ/platafirma-arquitetura/$DOC_SHA"
git -C "$PROD_RAIZ/platafirma-arquitetura/$DOC_SHA" checkout -q --detach "$DOC_SHA"
chmod -R a-w "$PROD_RAIZ/platafirma-arquitetura/$DOC_SHA"
ln -s "$DOC_SHA" "$PROD_RAIZ/platafirma-arquitetura/current"

# 3. abertura em var/abertura-publicada com sha real de 40 hex
ABERTURA_REAL_SHA="d299099a10b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
mkdir -p "$ABERTURA_DIR/refs/$ABERTURA_REAL_SHA/abertura"
printf '{"sha": "%s", "sha_curto": "%s", "publicado_em": "2026-09-12T14:26:16Z"}' \
  "$ABERTURA_REAL_SHA" "${ABERTURA_REAL_SHA:0:7}" > "$ABERTURA_DIR/refs/$ABERTURA_REAL_SHA/MANIFEST.json"
chmod -R a-w "$ABERTURA_DIR/refs/$ABERTURA_REAL_SHA"
ln -s "refs/$ABERTURA_REAL_SHA" "$ABERTURA_DIR/current"

echo "--- Teste 3: Família desconhecida e escape de raiz ---"
set +e
out_fam_desc="$("$VERBO" estado familia_inexistente 2>&1)"
rc_fam_desc=$?
set -e
if [ "$rc_fam_desc" -ne 2 ]; then
  echo "FALHA: família desconhecida devia sair 2, saiu $rc_fam_desc" >&2
  exit 1
fi
if ! grep -q "família desconhecida" <<<"$out_fam_desc" || ! grep -q "platafirma-harness" <<<"$out_fam_desc"; then
  echo "FALHA: recusa de família desconhecida deve listar famílias: $out_fam_desc" >&2
  exit 1
fi

set +e
out_escape="$("$VERBO" ler ../fora arq 2>&1)"
rc_escape=$?
set -e
if [ "$rc_escape" -ne 4 ]; then
  echo "FALHA: escape de raiz na família devia sair 4, saiu $rc_escape" >&2
  exit 1
fi
echo "OK: família desconhecida sai 2 com lista; escape sai 4"

echo "--- Teste 4: Forma do servido (clone com ramo, gravável, sem git, dangling, nome difere de HEAD) ---"
# 4a. current pendurado (dangling symlink) -> 5
mkdir -p "$PROD_RAIZ/repo_pendurado"
ln -s "sha_nao_existe" "$PROD_RAIZ/repo_pendurado/current"
set +e
out_pendurado="$("$VERBO" estado repo_pendurado 2>&1)"
rc_pendurado=$?
set -e
if [ "$rc_pendurado" -ne 5 ]; then
  echo "FALHA: current pendurado devia sair 5, saiu $rc_pendurado" >&2
  exit 1
fi

# 4b. Clone com ramo (não destacado) -> 5
mkdir -p "$PROD_RAIZ/repo_com_ramo/$HARNESS_SHA"
git clone --shared -q "$HARNESS_DIR" "$PROD_RAIZ/repo_com_ramo/$HARNESS_SHA"
chmod -R a-w "$PROD_RAIZ/repo_com_ramo/$HARNESS_SHA"
ln -s "$HARNESS_SHA" "$PROD_RAIZ/repo_com_ramo/current"
set +e
out_ramo="$("$VERBO" estado repo_com_ramo 2>&1)"
rc_ramo=$?
set -e
if [ "$rc_ramo" -ne 5 ]; then
  echo "FALHA: checkout com ramo devia sair 5, saiu $rc_ramo" >&2
  exit 1
fi

# 4c. Clone gravável -> 5
mkdir -p "$PROD_RAIZ/repo_gravavel/$HARNESS_SHA"
git clone --shared -q "$HARNESS_DIR" "$PROD_RAIZ/repo_gravavel/$HARNESS_SHA"
git -C "$PROD_RAIZ/repo_gravavel/$HARNESS_SHA" checkout -q --detach "$HARNESS_SHA"
ln -s "$HARNESS_SHA" "$PROD_RAIZ/repo_gravavel/current"
set +e
out_gravavel="$("$VERBO" estado repo_gravavel 2>&1)"
rc_gravavel=$?
set -e
if [ "$rc_gravavel" -ne 5 ]; then
  echo "FALHA: diretório gravável devia sair 5, saiu $rc_gravavel" >&2
  exit 1
fi

# 4d. Sem .git -> 5
mkdir -p "$PROD_RAIZ/repo_sem_git/$HARNESS_SHA"
chmod -R a-w "$PROD_RAIZ/repo_sem_git/$HARNESS_SHA"
ln -s "$HARNESS_SHA" "$PROD_RAIZ/repo_sem_git/current"
set +e
out_sem_git="$("$VERBO" estado repo_sem_git 2>&1)"
rc_sem_git=$?
set -e
if [ "$rc_sem_git" -ne 5 ]; then
  echo "FALHA: diretório sem .git devia sair 5, saiu $rc_sem_git" >&2
  exit 1
fi

# 4e. Nome do diretório difere do sha de HEAD -> 5 (Item 5)
mkdir -p "$PROD_RAIZ/repo_nome_errado/1111111111111111111111111111111111111111"
git clone --shared -q "$HARNESS_DIR" "$PROD_RAIZ/repo_nome_errado/1111111111111111111111111111111111111111"
git -C "$PROD_RAIZ/repo_nome_errado/1111111111111111111111111111111111111111" checkout -q --detach "$HARNESS_SHA"
chmod -R a-w "$PROD_RAIZ/repo_nome_errado/1111111111111111111111111111111111111111"
ln -s "1111111111111111111111111111111111111111" "$PROD_RAIZ/repo_nome_errado/current"
set +e
out_nome_errado="$("$VERBO" estado repo_nome_errado 2>&1)"
rc_nome_errado=$?
set -e
if [ "$rc_nome_errado" -ne 5 ]; then
  echo "FALHA: diretório cujo nome difere de HEAD devia sair 5, saiu $rc_nome_errado" >&2
  exit 1
fi
echo "OK: current pendurado, com ramo, gravável, sem .git e nome diferente do HEAD todos saem 5"

# Limpa repositórios de teste inválidos
chmod -R u+w "$PROD_RAIZ/repo_com_ramo" "$PROD_RAIZ/repo_sem_git" "$PROD_RAIZ/repo_gravavel" "$PROD_RAIZ/repo_nome_errado" 2>/dev/null || true
rm -rf "$PROD_RAIZ/repo_pendurado" "$PROD_RAIZ/repo_com_ramo" "$PROD_RAIZ/repo_sem_git" "$PROD_RAIZ/repo_gravavel" "$PROD_RAIZ/repo_nome_errado"

echo "--- Teste 5: release estado e não abortar o parque (Item 1) ---"
# Adiciona uma família pendurada e uma família sem current ao parque
mkdir -p "$PROD_RAIZ/repo_quebrado"
ln -s "sha_nao_existe" "$PROD_RAIZ/repo_quebrado/current"
mkdir -p "$PROD_RAIZ/repo_sem_current"

set +e
out_parque="$("$VERBO" estado)"
rc_parque=$?
set -e
if ! grep -q "platafirma-harness" <<<"$out_parque"; then
  echo "FALHA: estado do parque não listou platafirma-harness" >&2
  exit 1
fi
if ! grep -q "repo_quebrado[[:space:]]*indeterminável: current pendurado" <<<"$out_parque"; then
  echo "FALHA: repo_quebrado não saiu como 'indeterminável: current pendurado'" >&2
  exit 1
fi
if ! grep -q "repo_sem_current[[:space:]]*sem current" <<<"$out_parque"; then
  echo "FALHA: repo_sem_current não saiu como 'sem current'" >&2
  exit 1
fi
if [ "$rc_parque" -ne 5 ]; then
  echo "FALHA: pior exit do parque devia ser 5 (havia repo pendurado), saiu $rc_parque" >&2
  exit 1
fi
echo "OK: release estado lista todo o parque com o estado de cada família e sai o pior exit (5)"

# Limpa os quebrados para os testes de leitura limpa
rm -rf "$PROD_RAIZ/repo_quebrado" "$PROD_RAIZ/repo_sem_current"

out_estado="$("$VERBO" estado)"
if grep -q "resultado:" <<<"$out_estado"; then
  echo "FALHA: release estado não pode julgar (linha resultado: proibida)" >&2
  exit 1
fi
if ! grep -q "${HARNESS_SHA:0:7}" <<<"$out_estado" || ! grep -q "v0.1.0" <<<"$out_estado"; then
  echo "FALHA: harness deve mostrar sha curto e tag" >&2
  exit 1
fi
if ! grep -q "anterior: ${ANTERIOR_REAL_SHA:0:7}" <<<"$out_estado"; then
  echo "FALHA: harness deve mostrar anterior curto de sha hex real" >&2
  exit 1
fi

# Teste Item 5: anterior ilegível
echo "nao_eh_hex_123" > "$PONTOS/platafirma-harness/anterior"
out_ant_ilegivel="$("$VERBO" estado platafirma-harness)"
if ! grep -q "anterior: ilegível" <<<"$out_ant_ilegivel"; then
  echo "FALHA: anterior não-hex deve sair 'anterior: ilegível'" >&2
  exit 1
fi
# Restaura anterior real
echo "$ANTERIOR_REAL_SHA" > "$PONTOS/platafirma-harness/anterior"

# estado --json
out_est_json="$("$VERBO" estado --json)"
python3 -c '
import sys, json
data = json.loads(sys.stdin.read())
assert "familias" in data, "json deve conter familias no topo"
assert "platafirma-harness" in data["familias"]
assert data["familias"]["platafirma-harness"]["tag"] == "v0.1.0"
assert data["familias"]["platafirma-harness"]["anterior"] == "'"$ANTERIOR_REAL_SHA"'"
' <<<"$out_est_json"
echo "OK: release estado exibe sha, tag, anterior hex validado, sem veredito; --json válido"

echo "--- Teste 6: release ler ---"
# Ler existente
set +e
out_ler="$("$VERBO" ler platafirma-arquitetura docs/spec_teste.md 2>"$TMP_DIR/ler_stderr")"
rc_ler=$?
set -e
if [ "$rc_ler" -ne 0 ]; then
  echo "FALHA: ler arquivo existente devia sair 0, saiu $rc_ler" >&2
  exit 1
fi
if ! grep -q "termo_procurado_aqui" <<<"$out_ler"; then
  echo "FALHA: conteúdo de spec_teste.md não confere" >&2
  exit 1
fi
err_ler="$(cat "$TMP_DIR/ler_stderr")"
if ! grep -q "versão: current@${DOC_SHA:0:7}" <<<"$err_ler"; then
  echo "FALHA: stderr de ler deve conter versão: current@<sha>" >&2
  exit 1
fi

# Ler existente com tag (harness)
set +e
out_ler_h="$("$VERBO" ler platafirma-harness README.md 2>"$TMP_DIR/ler_h_stderr")"
rc_ler_h=$?
set -e
if [ "$rc_ler_h" -ne 0 ]; then
  echo "FALHA: ler harness README.md falhou" >&2
  exit 1
fi
err_ler_h="$(cat "$TMP_DIR/ler_h_stderr")"
if ! grep -q "versão: current@${HARNESS_SHA:0:7} (v0.1.0)" <<<"$err_ler_h"; then
  echo "FALHA: stderr de ler com tag deve conter versão: current@<sha> (tag)" >&2
  exit 1
fi

# Ler inexistente -> 1 com varrido e vizinho
set +e
"$VERBO" ler platafirma-arquitetura arquivo_que_nao_existe.txt 2>"$TMP_DIR/ler_inex_stderr"
rc_ler_inex=$?
set -e
if [ "$rc_ler_inex" -ne 1 ]; then
  echo "FALHA: ler arquivo inexistente devia sair 1, saiu $rc_ler_inex" >&2
  exit 1
fi
err_ler_inex="$(cat "$TMP_DIR/ler_inex_stderr")"
if ! grep -q "varrido: servido platafirma-arquitetura ($PROD_RAIZ/platafirma-arquitetura/$DOC_SHA" <<<"$err_ler_inex"; then
  echo "FALHA: linha varrido não confere com o padrão da spec: $err_ler_inex" >&2
  exit 1
fi
if ! grep -q "vizinho: repo ler platafirma-arquitetura arquivo_que_nao_existe.txt" <<<"$err_ler_inex"; then
  echo "FALHA: linha vizinho não confere com o padrão da spec: $err_ler_inex" >&2
  exit 1
fi

# Ler com caminho fora da raiz / escape
set +e
"$VERBO" ler platafirma-arquitetura ../fora 2>/dev/null
rc_ler_esc=$?
set -e
if [ "$rc_ler_esc" -ne 4 ]; then
  echo "FALHA: ler com caminho fora da raiz devia sair 4, saiu $rc_ler_esc" >&2
  exit 1
fi
echo "OK: release ler devolve arquivo cru + versão em stderr; inexistente sai 1 com varrido/vizinho"

echo "--- Teste 7: release listar ---"
out_listar="$("$VERBO" listar platafirma-arquitetura)"
if ! grep -q "README.md" <<<"$out_listar" || ! grep -q "docs/spec_teste.md" <<<"$out_listar"; then
  echo "FALHA: listar não listou arquivos esperados: $out_listar" >&2
  exit 1
fi

# Listar com prefixo
out_listar_prefixo="$("$VERBO" listar platafirma-arquitetura docs)"
if grep -q "README.md" <<<"$out_listar_prefixo" || ! grep -q "docs/spec_teste.md" <<<"$out_listar_prefixo"; then
  echo "FALHA: listar com prefixo filtrou errado: $out_listar_prefixo" >&2
  exit 1
fi

# Listar vazio legítimo -> exit 0 com motivo:
set +e
out_listar_vazio="$("$VERBO" listar platafirma-arquitetura pasta_vazia 2>&1)"
rc_listar_vazio=$?
set -e
if [ "$rc_listar_vazio" -ne 0 ]; then
  echo "FALHA: listar vazio legítimo devia sair 0, saiu $rc_listar_vazio" >&2
  exit 1
fi
if ! grep -q "motivo:" <<<"$out_listar_vazio"; then
  echo "FALHA: listar vazio legítimo deve conter 'motivo:'" >&2
  exit 1
fi

# Listar --json
out_listar_json="$("$VERBO" listar platafirma-arquitetura --json)"
python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
assert "arquivos" in d and d["total"] >= 2
' <<<"$out_listar_json"
echo "OK: release listar funciona, prefixo funciona, vazio legítimo sai 0 com motivo; --json válido"

echo "--- Teste 8: release procurar e busca literal -F (Item 6) ---"
# Falta --termo -> 2
set +e
out_proc_sem_termo="$("$VERBO" procurar platafirma-arquitetura 2>&1)"
rc_proc_sem_termo=$?
set -e
if [ "$rc_proc_sem_termo" -ne 2 ]; then
  echo "FALHA: procurar sem --termo devia sair 2, saiu $rc_proc_sem_termo" >&2
  exit 1
fi

# Termo literal com caracteres especiais (prova uso de -F)
out_proc_literal="$("$VERBO" procurar platafirma-arquitetura --termo "termo.com[regex]*literal")"
if ! grep -q "docs/spec_teste.md:3:termo.com\[regex\]\*literal" <<<"$out_proc_literal"; then
  echo "FALHA: procurar com termo literal falhou: $out_proc_literal" >&2
  exit 1
fi

# Termo não encontrado (vazio legítimo) -> 0 com motivo:
set +e
out_proc_vazio="$("$VERBO" procurar platafirma-arquitetura --termo termo_que_nao_existe 2>&1)"
rc_proc_vazio=$?
set -e
if [ "$rc_proc_vazio" -ne 0 ]; then
  echo "FALHA: procurar sem ocorrências devia sair 0, saiu $rc_proc_vazio" >&2
  exit 1
fi
if ! grep -q "motivo:" <<<"$out_proc_vazio"; then
  echo "FALHA: procurar vazio legítimo deve conter 'motivo:'" >&2
  exit 1
fi

# Procurar --json
out_proc_json="$("$VERBO" procurar platafirma-arquitetura --termo termo_procurado --json)"
python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
assert "ocorrencias" in d and d["total"] == 1
assert d["ocorrencias"][0]["caminho"] == "docs/spec_teste.md"
assert d["ocorrencias"][0]["linha"] == 2
' <<<"$out_proc_json"
echo "OK: release procurar funciona com -F, vazio legítimo sai 0 com motivo; --json válido"

echo "--- Teste 9: release conferir e filtro de classes (Item 7) ---"
# Sem classe -> exit 2
set +e
out_conf_sem_classe="$("$VERBO" conferir 2>&1)"
rc_conf_sem_classe=$?
set -e
if [ "$rc_conf_sem_classe" -ne 2 ]; then
  echo "FALHA: conferir sem classe devia sair 2, saiu $rc_conf_sem_classe" >&2
  exit 1
fi

# Classe 'existe' recusada apontando conferir existe -> exit 2
set +e
out_conf_existe="$("$VERBO" conferir existe verbo foo 2>&1)"
rc_conf_existe=$?
set -e
if [ "$rc_conf_existe" -ne 2 ] || ! grep -q "conferir existe" <<<"$out_conf_existe"; then
  echo "FALHA: conferir existe devia sair 2 apontando 'conferir existe'" >&2
  exit 1
fi

# Classe de bancada 'repo' recusada apontando lint/conferir -> exit 2
set +e
out_conf_bancada="$("$VERBO" conferir repo 2>&1)"
rc_conf_bancada=$?
set -e
if [ "$rc_conf_bancada" -ne 2 ] || ! grep -q "classe de bancada" <<<"$out_conf_bancada"; then
  echo "FALHA: conferir repo devia sair 2 apontando classe de bancada" >&2
  exit 1
fi

# Classe desconhecida recusada com lista das 11 classes do servido -> exit 2
set +e
out_conf_desconhecida="$("$VERBO" conferir classe_inexistente 2>&1)"
rc_conf_desconhecida=$?
set -e
if [ "$rc_conf_desconhecida" -ne 2 ] || ! grep -q "classes do servido" <<<"$out_conf_desconhecida"; then
  echo "FALHA: classe desconhecida devia sair 2 listando classes do servido" >&2
  exit 1
fi
echo "OK: release conferir valida classes do servido e rejeita existe e bancada com exit 2"

echo "--- Teste 10: forma velha de promover/reverter (sem família) sai 2 e ensina a nova ---"
# `release promover <tag>` (forma vigente, sem família) e `release reverter` (sem família) saem 2.
# O comportamento de promover/reverter por família e por sha mora em testes/test_release_lote2.sh.
set +e
out_prom_velho="$("$VERBO" promover v0.1.0 2>&1)"
rc_prom_velho=$?
set -e
if [ "$rc_prom_velho" -ne 2 ]; then
  echo "FALHA: promover na forma velha (tag sem família) devia sair 2, saiu $rc_prom_velho: $out_prom_velho" >&2
  exit 1
fi
set +e
out_rev_velho="$("$VERBO" reverter 2>&1)"
rc_rev_velho=$?
set -e
if [ "$rc_rev_velho" -ne 2 ]; then
  echo "FALHA: reverter sem família devia sair 2, saiu $rc_rev_velho" >&2
  exit 1
fi
echo "OK: forma velha de promover/reverter sai 2"

echo "=== Todos os testes do Lote 1 (com revisão TI) passaram com sucesso! ==="
