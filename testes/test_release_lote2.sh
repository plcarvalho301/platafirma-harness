#!/usr/bin/env bash
# Testes do verbo release — lote 2: promover / reverter por família e por sha (spec_release rev 2 §3, §4, §5)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/release"

TMP_DIR="$(mktemp -d /tmp/pf-release-l2.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT

echo "=== release lote 2: promover / reverter ==="

PROD_RAIZ="$TMP_DIR/var/prod"; PONTOS="$TMP_DIR/var/release"; ABERTURA_DIR="$TMP_DIR/var/abertura-publicada"
BIN_DIR="$TMP_DIR/bin"; REPO_RAIZ="$TMP_DIR/clones"; STUBS="$TMP_DIR/stubs"; FORGE="$TMP_DIR/forge"
mkdir -p "$PROD_RAIZ" "$PONTOS" "$ABERTURA_DIR" "$BIN_DIR" "$REPO_RAIZ" "$STUBS" "$FORGE"
export PF_PROD_RAIZ="$PROD_RAIZ" PF_RELEASE_RAIZ="$PONTOS" PF_ABERTURA_RAIZ="$ABERTURA_DIR" PF_BIN_DIR="$BIN_DIR" PF_REPO_RAIZ="$REPO_RAIZ"

# ---- stubs: acervo (registro de stacks), deploy (grava chamadas), systemd-run/systemctl (nunca tocam a porta real)
cat > "$STUBS/acervo" <<'EOF'
#!/usr/bin/env bash
# stub: só `ler casa stack <slug> --json`; devolve o registro inteiro, como o verbo real hoje
cat <<'J'
[
 {"slug": "harness-controle", "repo": "platafirma-harness", "reversao": {"via": "promover"}},
 {"slug": "chat", "repo": "platafirma-harness", "reversao": {"via": "up"}},
 {"slug": "core", "repo": "platafirma-core", "reversao": {"via": "promover"}}
]
J
EOF
cat > "$STUBS/deploy" <<'EOF'
#!/usr/bin/env bash
echo "deploy $*" >> "${DEPLOY_LOG:?}"
if [ "${DEPLOY_FALHA:-}" = "$1" ]; then echo "deploy: $1 recusa" >&2; exit 1; fi
exit 0
EOF
cat > "$STUBS/systemd-run" <<'EOF'
#!/usr/bin/env bash
echo "systemd-run $*" >> "${DEPLOY_LOG:?}"
exit 0
EOF
cat > "$STUBS/systemctl" <<'EOF'
#!/usr/bin/env bash
echo "n/a"
EOF
# infra: grava a chamada e responde como o verbo real sob a porta (nunca toca a porta real)
cat > "$STUBS/infra" <<'EOF'
#!/usr/bin/env bash
echo "infra $*" >> "${DEPLOY_LOG:?}"
echo "restart da unit $2 despachado destacado (stub)"
EOF
chmod +x "$STUBS"/*
# motor da familia abertura: o publicar-abertura da propria rev sob teste
ln -s "$REPO_ROOT/bin/publicar-abertura" "$STUBS/publicar-abertura"
export PATH="$STUBS:$PATH"
export DEPLOY_LOG="$TMP_DIR/deploy.log"; : > "$DEPLOY_LOG"

# ---- forge + bancada: platafirma-harness (código, 2 commits, tag no 1º) e platafirma-arquitetura (documentação)
mk_repo() {  # $1=nome $2=tag-no-primeiro-commit(0/1)
  local nome="$1" tag="$2"
  local wt="$REPO_RAIZ/$nome" bare="$FORGE/$nome.git"
  git init -q --bare "$bare"
  mkdir -p "$wt"; git -C "$wt" init -q -b main
  git -C "$wt" config user.name t; git -C "$wt" config user.email t@t
  mkdir -p "$wt/bin" "$wt/bin/_x"
  printf '#!/usr/bin/env bash\necho um\n' > "$wt/bin/foo"; chmod +x "$wt/bin/foo"; echo x > "$wt/bin/_x/a"
  echo "v1" > "$wt/README.md"
  git -C "$wt" add .; git -C "$wt" commit -q -m c1
  [ "$tag" = 1 ] && git -C "$wt" tag v0.1.0
  echo "v2" > "$wt/README.md"; git -C "$wt" commit -q -am c2
  git -C "$wt" remote add origin "$bare"
  git -C "$wt" push -q origin main --tags
}
mk_repo platafirma-harness 1
mk_repo platafirma-arquitetura 0
H_SHA1="$(git -C "$REPO_RAIZ/platafirma-harness" rev-parse HEAD~1)"
H_SHA2="$(git -C "$REPO_RAIZ/platafirma-harness" rev-parse HEAD)"
A_SHA1="$(git -C "$REPO_RAIZ/platafirma-arquitetura" rev-parse HEAD~1)"
A_SHA2="$(git -C "$REPO_RAIZ/platafirma-arquitetura" rev-parse HEAD)"

# ---- registro de famílias, venvs e terceiros: só o forge local em /tmp. Nenhum caso toca
# rede, a instância real nem o servido: PLATAFIRMA_INSTANCIA e PLATAFIRMA_RELEASE vão ao tmp.
cat > "$TMP_DIR/familias.json" <<J
{
  "platafirma-harness": "$FORGE/platafirma-harness.git",
  "platafirma-arquitetura": "$FORGE/platafirma-arquitetura.git"
}
J
echo '{}' > "$TMP_DIR/venvs.json"; echo '{}' > "$TMP_DIR/terceiros.json"
export PLATAFIRMA_FAMILIAS="$TMP_DIR/familias.json"
export PLATAFIRMA_VENVS="$TMP_DIR/venvs.json"
export PLATAFIRMA_TERCEIROS="$TMP_DIR/terceiros.json"
export PLATAFIRMA_INSTANCIA="$TMP_DIR/casa" PLATAFIRMA_RELEASE="$TMP_DIR/release"
export PF_ABERTURA_DIR="$ABERTURA_DIR"
mkdir -p "$PLATAFIRMA_INSTANCIA/var/release" "$PLATAFIRMA_RELEASE"
PONTOS_REAIS="$PLATAFIRMA_INSTANCIA/var/release"
# commit fora de origin/main (não descende)
git -C "$REPO_RAIZ/platafirma-harness" checkout -q -b fora
echo fora > "$REPO_RAIZ/platafirma-harness/fora.txt"; git -C "$REPO_RAIZ/platafirma-harness" add .; git -C "$REPO_RAIZ/platafirma-harness" commit -q -m fora
FORA_SHA="$(git -C "$REPO_RAIZ/platafirma-harness" rev-parse HEAD)"
git -C "$REPO_RAIZ/platafirma-harness" push -q origin fora
git -C "$REPO_RAIZ/platafirma-harness" checkout -q main
# idem na familia de documentacao (sem stack): o ramo que nunca entrou em main
git -C "$REPO_RAIZ/platafirma-arquitetura" checkout -q -b fabrica/3010
echo fora > "$REPO_RAIZ/platafirma-arquitetura/fora.txt"
git -C "$REPO_RAIZ/platafirma-arquitetura" add .
git -C "$REPO_RAIZ/platafirma-arquitetura" commit -q -m "topo de ramo, fora de main"
A_FORA="$(git -C "$REPO_RAIZ/platafirma-arquitetura" rev-parse HEAD)"
git -C "$REPO_RAIZ/platafirma-arquitetura" push -q origin fabrica/3010
git -C "$REPO_RAIZ/platafirma-arquitetura" checkout -q main

falha() { echo "FALHA: $*" >&2; exit 1; }
SERVIDO="$PF_RELEASE_RAIZ"   # onde o verbo serve (bin/release: PROD_RAIZ="$PF_RELEASE_RAIZ")
no_ar() { basename "$(readlink "$SERVIDO/$1/current" 2>/dev/null || echo vazio)"; }

echo "--- 1: família de código sem rev → 2; família desconhecida sem clone → 2"
set +e; out="$("$VERBO" promover platafirma-harness 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] && grep -q "promove por rev explícita" <<<"$out" || falha "promover sem rev: rc=$rc $out"
set +e; out="$("$VERBO" promover inexistente 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] || falha "família sem clone devia sair 2: rc=$rc $out"
echo "OK"

echo "--- 2: ensaio de família nova não toca nada"
set +e; out="$("$VERBO" promover platafirma-harness v0.1.0 --ensaio 2>&1)"; rc=$?; set -e
[ "$rc" -eq 0 ] && grep -q "clonaria" <<<"$out" || falha "ensaio família nova: rc=$rc $out"
[ ! -d "$PROD_RAIZ/platafirma-harness" ] || falha "ensaio criou var/prod/platafirma-harness"
echo "OK"

echo "--- 3: doc sem rev promove para origin/main (lado verde de promover)"
set +e; out="$("$VERBO" promover platafirma-arquitetura 2>&1)"; rc=$?; set -e
[ "$rc" -eq 0 ] || falha "promover doc sem rev: rc=$rc $out"
[ "$(no_ar platafirma-arquitetura)" = "$A_SHA2" ] || falha "current devia ser ${A_SHA2:0:7}, é $(no_ar platafirma-arquitetura)"
echo "OK"

echo "--- 4: promover rev fora de origin/main → 4, com caminho, current intacto"
set +e; out="$("$VERBO" promover platafirma-arquitetura "$A_FORA" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 4 ] || falha "promover fora de main devia sair 4: rc=$rc $out"
grep -q "não descende de origin/main" <<<"$out" || falha "recusa sem o motivo: $out"
grep -q "caminho: release promover platafirma-arquitetura" <<<"$out" || falha "recusa sem caminho (barreira sem saída): $out"
[ "$(no_ar platafirma-arquitetura)" = "$A_SHA2" ] || falha "recusa mexeu no current"
echo "OK"

echo "--- 5: reverter ao ponto de volta que está em main → 0 (lado verde de reverter)"
"$VERBO" promover platafirma-arquitetura "$A_SHA1" >/dev/null 2>&1 || falha "promover A_SHA1"
[ "$(no_ar platafirma-arquitetura)" = "$A_SHA1" ] || falha "current devia ser ${A_SHA1:0:7}"
set +e; out="$("$VERBO" reverter platafirma-arquitetura 2>&1)"; rc=$?; set -e
[ "$rc" -eq 0 ] || falha "reverter ao ponto de volta: rc=$rc $out"
[ "$(no_ar platafirma-arquitetura)" = "$A_SHA2" ] || falha "reverter não voltou a ${A_SHA2:0:7}"
echo "OK"

echo "--- 6: reverter a sha fora de main, já materializado → 4, current intacto"
mkdir -p "$SERVIDO/platafirma-arquitetura/$A_FORA"   # materializado antes do gate existir
set +e; out="$("$VERBO" reverter platafirma-arquitetura "$A_FORA" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 4 ] || falha "reverter para fora de main devia sair 4: rc=$rc $out"
grep -q "não descende de origin/main" <<<"$out" || falha "recusa sem o motivo: $out"
[ "$(no_ar platafirma-arquitetura)" = "$A_SHA2" ] || falha "recusa mexeu no current"
echo "OK"

echo "--- 7: ponto de volta gravado fora de main (gravado antes do gate) → 4 e diz que é o ponto"
rm -f "$SERVIDO/platafirma-arquitetura/anterior"
ln -s "$A_FORA" "$SERVIDO/platafirma-arquitetura/anterior"
printf '%s\n' "$A_FORA" > "$PONTOS_REAIS/platafirma-arquitetura/anterior"
set +e; out="$("$VERBO" reverter platafirma-arquitetura 2>&1)"; rc=$?; set -e
[ "$rc" -eq 4 ] || falha "ponto de volta fora de main devia sair 4: rc=$rc $out"
grep -q "ponto de volta gravado" <<<"$out" || falha "recusa não nomeia o ponto de volta: $out"
[ "$(no_ar platafirma-arquitetura)" = "$A_SHA2" ] || falha "recusa mexeu no current"
echo "OK"

echo "--- 8: sha de main novo (espelho desatualizado) passa o gate e cai no exit 1 de sempre"
echo "v3" > "$REPO_RAIZ/platafirma-arquitetura/README.md"
git -C "$REPO_RAIZ/platafirma-arquitetura" commit -q -am c3
A_SHA3="$(git -C "$REPO_RAIZ/platafirma-arquitetura" rev-parse HEAD)"
git -C "$REPO_RAIZ/platafirma-arquitetura" push -q origin main
set +e; out="$("$VERBO" reverter platafirma-arquitetura "$A_SHA3" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] || falha "sha de main não materializado devia sair 1 (gate não pode fechar em espelho velho): rc=$rc $out"
grep -q "não está materializado" <<<"$out" || falha "exit 1 perdeu a mensagem de sempre: $out"
echo "OK"

echo "=== lote 2: todos os testes passaram ==="
