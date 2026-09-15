#!/usr/bin/env bash
# Fechamento do card #3010 no harness: venvs harness/acervo declarados com lock, artefato de
# terceiro pinado materializado pelo release na arvore da rev, sem symlink autorreferente em
# bin/_<x>, log da porta num nome so, units sem python do sistema nem ~/.local/bin, segredo
# da sessao por <stack>/<NOME>, shims fora de ~/.local/bin, PAP com var/tmp absoluto na
# instancia e tokens do jaiminho obrigatorios.
#
# Hermetico: release e instancia num tmp, bancada nao declarada, HOME num tmp, forge local,
# nenhuma rede (a url do terceiro na fixture e inalcancavel de proposito).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/release"

TMP_DIR="$(mktemp -d /tmp/pf-3010-harness.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

falha() { echo "FALHA: $*" >&2; exit 1; }
command -v jq >/dev/null || falha "jq ausente (dependencia declarada do release)"

PROD_RAIZ="$TMP_DIR/opt"; INSTANCIA="$TMP_DIR/srv"; FORGE="$TMP_DIR/forge"; CLONES="$TMP_DIR/clones"
STUBS="$TMP_DIR/stubs"; CASA="$TMP_DIR/home"
mkdir -p "$PROD_RAIZ" "$INSTANCIA" "$FORGE" "$CLONES" "$STUBS" "$CASA"
unset PF_BANCADA PF_RELEASE PF_ABERTURA_DIR OPS_LOG_DIR PF_LOG_OPS PF_OPS_LOG_DIR PF_TERCEIROS PF_VENVS
export HOME="$CASA" PF_RELEASE_RAIZ="$PROD_RAIZ" PF_INSTANCIA="$INSTANCIA" \
  PF_ARQUIVO_BANCADA="$TMP_DIR/sem-bancada" PF_RELEASE_PORTA=0

echo "=== fechamento #3010 no harness ==="

# ---------------------------------------------------------------- 1. venvs declarados
echo "--- 1: registro de venvs declara harness e acervo com lock na arvore; shebangs cobertos"
REG_VENVS="$REPO_ROOT/registro/venvs.json"
filtro='to_entries[] | select(.key | startswith("_") | not)
        | select((.value | type) == "object" and .value.familia == $f) | .key'
h="$(jq -r --arg f platafirma-harness "$filtro" "$REG_VENVS" | sort | tr '\n' ' ')"
c="$(jq -r --arg f platafirma-conhecimento "$filtro" "$REG_VENVS" | sort | tr '\n' ' ')"
[ "$h" = "acervo harness ops " ] || falha "familia harness devia construir acervo, harness e ops: '$h'"
[ "$c" = "rag " ] || falha "familia conhecimento devia construir rag: '$c'"
for n in harness acervo; do
  lock="$(jq -r --arg n "$n" '.[$n].lock' "$REG_VENVS")"
  [ "$(basename "$lock")" = uv.lock ] || falha "venv $n devia ter uv.lock (uv sync --frozen): $lock"
  [ -f "$REPO_ROOT/$lock" ] || falha "lock do venv $n ausente na arvore: $lock"
  [ -f "$REPO_ROOT/$(dirname "$lock")/pyproject.toml" ] || falha "pyproject do venv $n ausente ao lado do lock"
  if command -v uv >/dev/null 2>&1; then
    uv lock --check --offline --project "$REPO_ROOT/$(dirname "$lock")" >/dev/null 2>&1 \
      || falha "venvs/$n/uv.lock nao corresponde ao pyproject (uv lock --check)"
  fi
done
# todo venv citado por shebang ou por "$PF_RELEASE/venv/<n>/bin/python" tem de estar declarado
citados="$(cd "$REPO_ROOT" && git ls-files -z bin chat controle sessao deploy-harness 2>/dev/null \
  | { xargs -0 grep -hoE '(/opt/platafirma/current|\$PF_RELEASE)/venv/[a-z0-9_-]+/bin/' 2>/dev/null || true; } \
  | sed -E 's#.*/venv/([a-z0-9_-]+)/bin/#\1#' | sort -u)"
[ -n "$citados" ] || falha "nenhum venv citado no codigo: a varredura de shebang nao achou nada"
for n in $citados; do
  jq -e --arg n "$n" 'has($n)' "$REG_VENVS" >/dev/null || falha "venv '$n' citado no codigo e nao declarado em registro/venvs.json"
done
echo "OK ($(echo $citados | tr '\n' ' '))"

# ---------------------------------------------------------------- 2. terceiro pinado
echo "--- 2: registro real do tokenizador e bem formado e casa com o caminho do codigo"
REG_T="$REPO_ROOT/registro/terceiros.json"
jq -e '."qwen2.5-tokenizer" | .familia == "platafirma-harness" and (.sha256 | test("^[0-9a-f]{64}$"))
       and (.url | startswith("https://")) and .destino == "terceiros/tokenizers/qwen2.5.json"' "$REG_T" >/dev/null \
  || falha "registro/terceiros.json: qwen2.5-tokenizer mal declarado"
grep -q '"terceiros", "tokenizers", "qwen2.5.json"' "$REPO_ROOT/bin/monta-sessao" || falha "monta-sessao nao le o destino pinado"
grep -q '"terceiros" / "tokenizers" / "qwen2.5.json"' "$REPO_ROOT/recuperacao/_raizes.py" || falha "recuperacao nao le o destino pinado"
(cd "$REPO_ROOT" && git check-ignore -q terceiros/tokenizers/qwen2.5.json) || falha "terceiros/ devia estar fora do git"
echo "OK"

echo "--- 3: release materializa o terceiro na arvore da rev a partir do cache pinado"
cat > "$STUBS/acervo" <<'EOF'
#!/usr/bin/env bash
echo '[]'
EOF
for s in deploy infra systemd-run systemctl; do printf '#!/usr/bin/env bash\nexit 0\n' > "$STUBS/$s"; done
chmod +x "$STUBS"/*
export PATH="$STUBS:$PATH"

wt="$CLONES/platafirma-harness"; bare="$FORGE/platafirma-harness.git"
git init -q --bare "$bare"; mkdir -p "$wt/bin"; git -C "$wt" init -q -b main
git -C "$wt" config user.name t; git -C "$wt" config user.email t@t
printf '#!/usr/bin/env bash\necho um\n' > "$wt/bin/foo"; chmod +x "$wt/bin/foo"; echo v1 > "$wt/README.md"
git -C "$wt" add .; git -C "$wt" commit -q -m c1
echo v2 > "$wt/README.md"; git -C "$wt" commit -q -am c2
git -C "$wt" remote add origin "$bare"; git -C "$wt" push -q origin main
SHA1="$(git -C "$wt" rev-parse HEAD~1)"; SHA2="$(git -C "$wt" rev-parse HEAD)"

printf '{"platafirma-harness": "%s"}\n' "$bare" > "$TMP_DIR/familias.json"
printf '{"_leia": "fixture sem venv"}\n' > "$TMP_DIR/venvs.json"
printf 'tokenizador de fixture\n' > "$TMP_DIR/artefato"
PINO="$(sha256sum "$TMP_DIR/artefato" | cut -d' ' -f1)"
printf '{"_leia": "fixture", "tok.fixture": {"familia": "platafirma-harness", "destino": "terceiros/tokenizers/fixture.json", "sha256": "%s", "url": "https://127.0.0.1:9/inalcancavel"}}\n' "$PINO" > "$TMP_DIR/terceiros.json"
export PF_FAMILIAS="$TMP_DIR/familias.json" PF_VENVS="$TMP_DIR/venvs.json" PF_TERCEIROS="$TMP_DIR/terceiros.json"
CACHE="$PROD_RAIZ/terceiros/sha256"

set +e; out="$("$VERBO" promover platafirma-harness "$SHA1" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] || falha "cache vazio e url inalcancavel devia sair 3: rc=$rc $out"
grep -q "não baixou" <<<"$out" || falha "falha de download devia ser declarada: $out"
[ ! -e "$PROD_RAIZ/platafirma-harness/current" ] || falha "current nasceu com o terceiro ausente"
echo "OK: sem cache e sem rede recusa 3, current intacto"

mkdir -p "$CACHE"; cp "$TMP_DIR/artefato" "$CACHE/$PINO"
out="$("$VERBO" promover platafirma-harness "$SHA1" 2>&1)" || falha "promover com cache semeado: $out"
alvo="$PROD_RAIZ/platafirma-harness/$SHA1/terceiros/tokenizers/fixture.json"
[ -f "$alvo" ] && [ "$(sha256sum "$alvo" | cut -d' ' -f1)" = "$PINO" ] || falha "terceiro nao chegou na arvore com o pino: $out"
[ ! -w "$alvo" ] && [ ! -w "$(dirname "$alvo")" ] && [ ! -w "$PROD_RAIZ/platafirma-harness/$SHA1" ] \
  || falha "arvore da rev ficou gravavel depois de por o terceiro"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$SHA1" ] || falha "current nao trocou"
[ "$(readlink -f "$PROD_RAIZ/current/harness/terceiros/tokenizers/fixture.json")" = "$(readlink -f "$alvo")" ] \
  || falha "atalho current/harness nao serve o terceiro"
echo "OK: cache semeado -> terceiro na arvore, somente-leitura, servido pelo atalho"

printf 'adulterado\n' > "$TMP_DIR/ruim"; chmod u+w "$CACHE/$PINO" 2>/dev/null || true; cp "$TMP_DIR/ruim" "$CACHE/$PINO"
set +e; out="$("$VERBO" promover platafirma-harness "$SHA2" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] || falha "cache fora do pino (e sem rede) devia sair 3: rc=$rc $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$SHA1" ] || falha "current mudou com cache adulterado"
[ ! -e "$PROD_RAIZ/platafirma-harness/$SHA2/terceiros/tokenizers/fixture.json" ] || falha "conteudo adulterado entrou na arvore"
echo "OK: cache que nao bate o pino nao serve, current intacto"

cp "$TMP_DIR/artefato" "$CACHE/$PINO"
out="$("$VERBO" promover platafirma-harness "$SHA2" 2>&1)" || falha "promover SHA2 com cache bom: $out"
[ -f "$PROD_RAIZ/platafirma-harness/$SHA2/terceiros/tokenizers/fixture.json" ] || falha "SHA2 sem terceiro"
out="$("$VERBO" reverter platafirma-harness 2>&1)" || falha "reverter: $out"
grep -q "tok.fixture já na árvore" <<<"$out" || falha "reverter devia conferir o terceiro na arvore de volta: $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$SHA1" ] || falha "reverter nao voltou"
echo "OK: promover e reverter conferem o terceiro"

printf '{"x": {"familia": "platafirma-harness", "destino": "../fora", "sha256": "%s", "url": "https://a"}}\n' "$PINO" > "$TMP_DIR/terceiros-ruim.json"
set +e; out="$(PF_TERCEIROS="$TMP_DIR/terceiros-ruim.json" "$VERBO" promover platafirma-harness "$SHA2" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] && grep -q "terceiro mal declarado" <<<"$out" || falha "destino com .. devia ser recusado: rc=$rc $out"
echo "OK: declaracao que sai da arvore e recusada"

# ---------------------------------------------------------------- 4. symlinks autorreferentes
echo "--- 4: nenhum symlink em bin/ aponta para a propria release"
achados="$(find "$REPO_ROOT/bin" -type l -lname '/opt/platafirma/current/harness/bin/*' 2>/dev/null)"
[ -z "$achados" ] || falha "symlink autorreferente em bin/: $achados"
echo "OK"

# ---------------------------------------------------------------- 5. log da porta
echo "--- 5: OPS_LOG_DIR e o nome do log da porta; aliases so lidos"
ler_log() { python3 - "$REPO_ROOT/bin/metrica" <<'PY'
import importlib.machinery, importlib.util, sys
l = importlib.machinery.SourceFileLoader("metrica", sys.argv[1])
s = importlib.util.spec_from_loader("metrica", l); m = importlib.util.module_from_spec(s); l.exec_module(m)
print(m.LOG_OPS)
PY
}
[ "$(OPS_LOG_DIR="$TMP_DIR/a" PF_LOG_OPS="$TMP_DIR/b" ler_log)" = "$TMP_DIR/a" ] || falha "metrica: OPS_LOG_DIR devia vencer o alias"
[ "$(PF_LOG_OPS="$TMP_DIR/b" ler_log)" = "$TMP_DIR/b" ] || falha "metrica: alias PF_LOG_OPS devia seguir lido"
[ "$(ler_log)" = "$INSTANCIA/var/log/ops" ] || falha "metrica: default devia ser \$PF_INSTANCIA/var/log/ops"
grep -q 'log_dir="${OPS_LOG_DIR:-${PF_OPS_LOG_DIR:-$PF_INSTANCIA/var/log/ops}}"' "$REPO_ROOT/bin/repo" \
  || falha "repo: OPS_LOG_DIR devia vir primeiro, PF_OPS_LOG_DIR so como alias"
echo "OK"

# ---------------------------------------------------------------- 6. units
echo "--- 6: units sem python do sistema e sem ~/.local/bin"
while IFS= read -r u; do
  ! grep -qE '^ExecStart=/usr/bin/python3?( |$)' "$u" || falha "unit com python do sistema: $u"
  ! grep -qE '^[^#]*\.local/bin' "$u" || falha "unit com ~/.local/bin: $u"
done < <(find "$REPO_ROOT" -path "$REPO_ROOT/.git" -prune -o -type f \( -name '*.service' -o -name '*.timer' \) -print)
grep -q '^ExecStart=/opt/platafirma/current/venv/harness/bin/python /opt/platafirma/current/harness/chat/worker/worker.py$' \
  "$REPO_ROOT/chat/systemd/chat-worker.service" || falha "chat-worker devia rodar no venv harness da release"
! grep -qE '^[^#]*setenv=PATH=[^ ]*\.local/bin' "$REPO_ROOT/bin/longjob" || falha "longjob poe ~/.local/bin no PATH da unit"
echo "OK"

# ---------------------------------------------------------------- 7. segredo da sessao
echo "--- 7: sessao e expediente leem harness-sessao/SESSAO_PG_PASSWORD"
grep -q '"ler", "harness-sessao/SESSAO_PG_PASSWORD"' "$REPO_ROOT/bin/sessao" || falha "bin/sessao sem stack no segredo"
grep -q 'seg segredo ler harness-sessao/SESSAO_PG_PASSWORD"' "$REPO_ROOT/bin/expediente" || falha "bin/expediente sem stack no segredo"
! grep -qE '"ler", "SESSAO_PG_PASSWORD"|segredo ler SESSAO_PG_PASSWORD"' "$REPO_ROOT/bin/sessao" "$REPO_ROOT/bin/expediente" \
  || falha "sobrou leitura de segredo sem stack"
echo "OK"

# ---------------------------------------------------------------- 8. shims
echo "--- 8: shims de instancia vao para a instancia, nunca ~/.local/bin"
out="$(PF_SHIMS_PARES='rastreador|tarefas' bash "$REPO_ROOT/bin/_shims-instancia" 2>&1)" || falha "_shims-instancia: $out"
[ -x "$INSTANCIA/var/shims/rastreador" ] || falha "shim nao nasceu em \$PF_INSTANCIA/var/shims: $out"
[ ! -e "$CASA/.local" ] || falha "_shims-instancia criou ~/.local"
! grep -qE '^[^#]*\.local/bin' "$REPO_ROOT/bin/_shims-instancia" "$REPO_ROOT/agente/instala.sh" \
  || falha "codigo ainda grava em ~/.local/bin"
echo "OK"

# ---------------------------------------------------------------- 9. PAP e compose
echo "--- 9: PAP com var/tmp absoluto; tokens do jaiminho obrigatorios"
python3 - "$REPO_ROOT/politica-acesso/politica.yaml" "$REPO_ROOT/jaiminho/docker-compose.yml" <<'PY'
import sys, yaml
pap = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
regras = {r["id"]: r for r in pap["regras"]} if isinstance(pap, dict) and "regras" in pap else None
if regras is None:
    def acha(no):
        if isinstance(no, dict):
            if no.get("id") == "fornecedor-usa-verbo-operacional":
                return no
            for v in no.values():
                r = acha(v)
                if r: return r
        elif isinstance(no, list):
            for v in no:
                r = acha(v)
                if r: return r
    regra = acha(pap)
else:
    regra = regras["fornecedor-usa-verbo-operacional"]
assert regra, "regra fornecedor-usa-verbo-operacional ausente"
sobre = regra["sobre"]
assert "var/tmp/*" not in sobre, sobre
assert "/srv/platafirma/*/var/tmp/*" in sobre, sobre
comp = yaml.safe_load(open(sys.argv[2], encoding="utf-8"))
env = comp["services"]["jaiminho-server"]["environment"]
for nome in ("WIKI_MCP_TOKEN", "RAG_API_TOKEN"):
    assert str(env[nome]).startswith("${%s:?" % nome), (nome, env[nome])
PY
echo "OK"

echo "=== fechamento #3010 no harness: todos os casos passaram ==="
