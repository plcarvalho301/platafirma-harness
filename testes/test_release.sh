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

echo "=== Todos os testes do Lote 1 (com revisão TI) passaram com sucesso! ==="
