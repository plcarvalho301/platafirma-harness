#!/usr/bin/env bash
# Testes do verbo release conforme spec_release rev 2 (arq:0110, arq:0109)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/release"

TMP_DIR="$(mktemp -d /tmp/pf-release-test.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

echo "=== Iniciando suite de testes de release (Lote 1) ==="

# 0. Verificações estáticas de bin/release
echo "--- Teste 0: Verificação de git nu no bin ---"
if grep -n '^[[:space:]]*git ' "$VERBO" | grep -v 'GIT=' | grep -v '#'; then
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

# 3. Montagem da fixture de servido
PROD_RAIZ="$TMP_DIR/var/prod"
PONTOS="$TMP_DIR/var/release"
ABERTURA_DIR="$TMP_DIR/var/abertura-publicada"
BIN_DIR="$TMP_DIR/bin"
mkdir -p "$PROD_RAIZ" "$PONTOS" "$ABERTURA_DIR" "$BIN_DIR"

export PF_PROD_RAIZ="$PROD_RAIZ"
export RELEASE_PONTOS="$PONTOS"
export PF_ABERTURA_DIR="$ABERTURA_DIR"
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
git -C "$DOC_DIR" add .
git -C "$DOC_DIR" commit -q -m "init doc"
DOC_SHA="$(git -C "$DOC_DIR" rev-parse HEAD)"

# Materializa no servido var/prod/<repo>/<sha>
# 1. platafirma-harness
mkdir -p "$PROD_RAIZ/platafirma-harness/$HARNESS_SHA"
git clone --shared -q "$HARNESS_DIR" "$PROD_RAIZ/platafirma-harness/$HARNESS_SHA"
git -C "$PROD_RAIZ/platafirma-harness/$HARNESS_SHA" checkout -q --detach "$HARNESS_SHA"
chmod -R a-w "$PROD_RAIZ/platafirma-harness/$HARNESS_SHA"
ln -s "$HARNESS_SHA" "$PROD_RAIZ/platafirma-harness/current"

# Ponto de volta para platafirma-harness
mkdir -p "$PONTOS/platafirma-harness"
echo "anterior1234567890" > "$PONTOS/platafirma-harness/anterior"
echo "2026-09-12T14:26:16Z" > "$PONTOS/platafirma-harness/atual"

# 2. platafirma-arquitetura
mkdir -p "$PROD_RAIZ/platafirma-arquitetura/$DOC_SHA"
git clone --shared -q "$DOC_DIR" "$PROD_RAIZ/platafirma-arquitetura/$DOC_SHA"
git -C "$PROD_RAIZ/platafirma-arquitetura/$DOC_SHA" checkout -q --detach "$DOC_SHA"
chmod -R a-w "$PROD_RAIZ/platafirma-arquitetura/$DOC_SHA"
ln -s "$DOC_SHA" "$PROD_RAIZ/platafirma-arquitetura/current"

# 3. abertura em var/abertura-publicada
mkdir -p "$ABERTURA_DIR/refs/aberturasha123/abertura"
printf '{"sha": "aberturasha123", "sha_curto": "abertur", "publicado_em": "2026-09-12T14:26:16Z"}' > "$ABERTURA_DIR/refs/aberturasha123/MANIFEST.json"
chmod -R a-w "$ABERTURA_DIR/refs/aberturasha123"
ln -s "refs/aberturasha123" "$ABERTURA_DIR/current"

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

echo "--- Teste 4: Forma do servido (clone com ramo, gravável, sem git, dangling) ---"
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
mkdir -p "$PROD_RAIZ/repo_com_ramo/sha_ramo"
git clone --shared -q "$HARNESS_DIR" "$PROD_RAIZ/repo_com_ramo/sha_ramo"
chmod -R a-w "$PROD_RAIZ/repo_com_ramo/sha_ramo"
ln -s "sha_ramo" "$PROD_RAIZ/repo_com_ramo/current"
set +e
out_ramo="$("$VERBO" estado repo_com_ramo 2>&1)"
rc_ramo=$?
set -e
if [ "$rc_ramo" -ne 5 ]; then
  echo "FALHA: checkout com ramo devia sair 5, saiu $rc_ramo" >&2
  exit 1
fi
if ! grep -q "não é servido" <<<"$out_ramo"; then
  echo "FALHA: mensagem de clone com ramo deve dizer 'não é servido'" >&2
  exit 1
fi

# 4c. Clone gravável -> 5
mkdir -p "$PROD_RAIZ/repo_gravavel/sha_gravavel"
git clone --shared -q "$HARNESS_DIR" "$PROD_RAIZ/repo_gravavel/sha_gravavel"
git -C "$PROD_RAIZ/repo_gravavel/sha_gravavel" checkout -q --detach "$HARNESS_SHA"
# deixa gravável
ln -s "sha_gravavel" "$PROD_RAIZ/repo_gravavel/current"
set +e
out_gravavel="$("$VERBO" estado repo_gravavel 2>&1)"
rc_gravavel=$?
set -e
if [ "$rc_gravavel" -ne 5 ]; then
  echo "FALHA: diretório gravável devia sair 5, saiu $rc_gravavel" >&2
  exit 1
fi

# 4d. Sem .git -> 5
mkdir -p "$PROD_RAIZ/repo_sem_git/sha_sem_git"
chmod -R a-w "$PROD_RAIZ/repo_sem_git/sha_sem_git"
ln -s "sha_sem_git" "$PROD_RAIZ/repo_sem_git/current"
set +e
out_sem_git="$("$VERBO" estado repo_sem_git 2>&1)"
rc_sem_git=$?
set -e
if [ "$rc_sem_git" -ne 5 ]; then
  echo "FALHA: diretório sem .git devia sair 5, saiu $rc_sem_git" >&2
  exit 1
fi
echo "OK: current pendurado, com ramo, gravável e sem .git todos saem 5"

# Limpa repositórios de teste inválidos para os testes de leitura
chmod -R u+w "$PROD_RAIZ/repo_com_ramo" "$PROD_RAIZ/repo_sem_git" "$PROD_RAIZ/repo_gravavel" 2>/dev/null || true
rm -rf "$PROD_RAIZ/repo_pendurado" "$PROD_RAIZ/repo_com_ramo" "$PROD_RAIZ/repo_sem_git" "$PROD_RAIZ/repo_gravavel"

echo "--- Teste 5: release estado ---"
out_estado="$("$VERBO" estado)"
echo "$out_estado"
if grep -q "resultado:" <<<"$out_estado"; then
  echo "FALHA: release estado não pode julgar (linha resultado: proibida)" >&2
  exit 1
fi
if ! grep -q "${HARNESS_SHA:0:7}" <<<"$out_estado" || ! grep -q "v0.1.0" <<<"$out_estado"; then
  echo "FALHA: harness deve mostrar sha curto e tag" >&2
  exit 1
fi
if ! grep -q "${DOC_SHA:0:7}" <<<"$out_estado"; then
  echo "FALHA: doc repo deve mostrar sha curto" >&2
  exit 1
fi
if ! grep -q "anterior: anterio" <<<"$out_estado"; then
  echo "FALHA: harness deve mostrar ponto anterior" >&2
  exit 1
fi

# estado com repo específico
out_est_harness="$("$VERBO" estado platafirma-harness)"
if ! grep -q "platafirma-harness" <<<"$out_est_harness" || grep -q "platafirma-arquitetura" <<<"$out_est_harness"; then
  echo "FALHA: release estado <repo> deve imprimir apenas a linha da família" >&2
  exit 1
fi

# estado --json
out_est_json="$("$VERBO" estado --json)"
python3 -c '
import sys, json
data = json.loads(sys.stdin.read())
assert "familias" in data, "json deve conter familias no topo"
assert "platafirma-harness" in data["familias"]
assert data["familias"]["platafirma-harness"]["tag"] == "v0.1.0"
' <<<"$out_est_json"
echo "OK: release estado exibe sha, tag, anterior, sem veredito; --json válido"

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

echo "--- Teste 8: release procurar ---"
# Falta --termo -> 2
set +e
out_proc_sem_termo="$("$VERBO" procurar platafirma-arquitetura 2>&1)"
rc_proc_sem_termo=$?
set -e
if [ "$rc_proc_sem_termo" -ne 2 ]; then
  echo "FALHA: procurar sem --termo devia sair 2, saiu $rc_proc_sem_termo" >&2
  exit 1
fi

# Termo encontrado
out_proc="$("$VERBO" procurar platafirma-arquitetura --termo termo_procurado)"
if ! grep -q "docs/spec_teste.md:2:termo_procurado_aqui" <<<"$out_proc"; then
  echo "FALHA: procurar não achou ocorrência esperada: $out_proc" >&2
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
echo "OK: release procurar funciona, vazio legítimo sai 0 com motivo; --json válido"

echo "--- Teste 9: Dependência ausente (git -> 3) ---"
set +e
out_git_ausente="$(PF_GIT_BIN="/caminho/inexistente/git" "$VERBO" estado 2>&1)"
rc_git_ausente=$?
set -e
if [ "$rc_git_ausente" -ne 3 ]; then
  echo "FALHA: git ausente devia sair 3, saiu $rc_git_ausente" >&2
  exit 1
fi
if ! grep -q "dependência ausente: git" <<<"$out_git_ausente"; then
  echo "FALHA: mensagem de erro de dependência git ausente não confere: $out_git_ausente" >&2
  exit 1
fi
echo "OK: git ausente sai 3 com mensagem"

echo "--- Teste 10: promover e reverter (compatibilidade vigente na nova raiz) ---"
export PF_HARNESS="$HARNESS_DIR"
export PF_CORE="$HARNESS_DIR"
export PF_CONHECIMENTO="$HARNESS_DIR"
mkdir -p "$TMP_DIR/mock_bin"
printf '#!/usr/bin/env bash
echo "mock deploy $*"
' > "$TMP_DIR/mock_bin/deploy"
chmod +x "$TMP_DIR/mock_bin/deploy"
export PATH="$TMP_DIR/mock_bin:$PATH"

"$VERBO" promover "v0.1.0" --ensaio
"$VERBO" promover "v0.1.0"

if [ ! -L "$PROD_RAIZ/current" ]; then
  echo "FALHA: current não é symlink após promover" >&2
  exit 1
fi
if [ "$(readlink "$PROD_RAIZ/current")" != "v0.1.0" ]; then
  echo "FALHA: current aponta para $(readlink "$PROD_RAIZ/current"), esperado v0.1.0" >&2
  exit 1
fi

# Reverter
PF_SIM=1 "$VERBO" reverter --executar "v0.1.0"
echo "OK: promover e reverter operam na nova raiz PF_PROD_RAIZ"

echo "=== Todos os testes do Lote 1 passaram com sucesso! ==="
