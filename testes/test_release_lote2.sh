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
BIN_DIR="$TMP_DIR/bin"; REPO_RAIZ="$TMP_DIR/AI"; STUBS="$TMP_DIR/stubs"; FORGE="$TMP_DIR/forge"
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
chmod +x "$STUBS"/*
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
A_SHA2="$(git -C "$REPO_RAIZ/platafirma-arquitetura" rev-parse HEAD)"
# commit fora de origin/main (não descende)
git -C "$REPO_RAIZ/platafirma-harness" checkout -q -b fora
echo fora > "$REPO_RAIZ/platafirma-harness/fora.txt"; git -C "$REPO_RAIZ/platafirma-harness" add .; git -C "$REPO_RAIZ/platafirma-harness" commit -q -m fora
FORA_SHA="$(git -C "$REPO_RAIZ/platafirma-harness" rev-parse HEAD)"
git -C "$REPO_RAIZ/platafirma-harness" push -q origin fora
git -C "$REPO_RAIZ/platafirma-harness" checkout -q main

falha() { echo "FALHA: $*" >&2; exit 1; }

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

echo "--- 3: promover por tag materializa por sha, grava pontos, assenta PATH, promove só as stacks via promover, agenda porta"
out="$("$VERBO" promover platafirma-harness v0.1.0 2>&1)" || falha "promover v0.1.0: $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA1" ] || falha "current não aponta o sha da tag"
[ -f "$PROD_RAIZ/platafirma-harness/$H_SHA1/.git" ] || falha "checkout não é worktree destacado"
[ ! -w "$PROD_RAIZ/platafirma-harness/$H_SHA1" ] || falha "checkout gravável"
grep -q "^$H_SHA1 " "$PONTOS/platafirma-harness/atual" || falha "atual não gravado"
[ ! -f "$PONTOS/platafirma-harness/anterior" ] || falha "anterior gravado sem promoção anterior"
[ "$(readlink "$BIN_DIR/foo")" = "$PROD_RAIZ/platafirma-harness/current/bin/foo" ] || falha "PATH não assentado: $(readlink "$BIN_DIR/foo" || true)"
[ -L "$BIN_DIR/_x" ] || falha "diretório _x não assentado"
grep -q "deploy harness-controle promover $H_SHA1" "$DEPLOY_LOG" || falha "stack via promover não promovida"
! grep -q "deploy chat" "$DEPLOY_LOG" || falha "stack via up foi promovida"
grep -q "fora da promoção por release" <<<"$out" || falha "stack via up não declarada"
grep -q "systemd-run" "$DEPLOY_LOG" || falha "restart da porta não agendado"
[ "$(tail -1 <<<"$out")" = "$H_SHA1" ] || falha "última linha devia ser o sha"
echo "OK"

echo "--- 4: estado lê o promovido; promover o mesmo sha → 1; sha por sha resolve igual à tag"
out="$("$VERBO" estado platafirma-harness)"
grep -q "${H_SHA1:0:7}" <<<"$out" && grep -q "v0.1.0" <<<"$out" || falha "estado: $out"
set +e; out="$("$VERBO" promover platafirma-harness "$H_SHA1" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] && grep -q "já no ar" <<<"$out" || falha "mesmo sha devia sair 1: rc=$rc $out"
echo "OK"

echo "--- 5: promover sha novo grava anterior; rev fora de origin/main → 4; rev inexistente → 2 com tags"
out="$("$VERBO" promover platafirma-harness "$H_SHA2" 2>&1)" || falha "promover sha2: $out"
[ "$(cat "$PONTOS/platafirma-harness/anterior")" = "$H_SHA1" ] || falha "anterior devia ser sha1"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA2" ] || falha "current devia ser sha2"
out="$("$VERBO" estado platafirma-harness)"; grep -q "anterior: ${H_SHA1:0:7}" <<<"$out" || falha "estado sem anterior: $out"
set +e; out="$("$VERBO" promover platafirma-harness "$FORA_SHA" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 4 ] || falha "rev fora de main devia sair 4: rc=$rc $out"
set +e; out="$("$VERBO" promover platafirma-harness v9.9.9 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] && grep -q "tags recentes" <<<"$out" || falha "rev inexistente: rc=$rc $out"
echo "OK"

echo "--- 6: ensaio de reverter não toca; reverter sem rev volta ao anterior; reverter para onde já está → 1"
: > "$DEPLOY_LOG"
out="$("$VERBO" reverter platafirma-harness --ensaio 2>&1)" || falha "ensaio reverter: $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA2" ] || falha "ensaio moveu current"
[ ! -s "$DEPLOY_LOG" ] || falha "ensaio chamou deploy"
out="$("$VERBO" reverter platafirma-harness 2>&1)" || falha "reverter: $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA1" ] || falha "reverter não voltou a sha1"
[ "$(cat "$PONTOS/platafirma-harness/anterior")" = "$H_SHA2" ] || falha "anterior devia ser sha2 após reverter"
grep -q "deploy harness-controle promover $H_SHA1" "$DEPLOY_LOG" || falha "reverter não promoveu stack"
set +e; out="$("$VERBO" reverter platafirma-harness "$H_SHA1" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] || falha "reverter para onde já está devia sair 1: rc=$rc"
echo "OK"

echo "--- 7: stack que recusa → 5 e current volta"
: > "$DEPLOY_LOG"
set +e; out="$(DEPLOY_FALHA=harness-controle "$VERBO" promover platafirma-harness "$H_SHA2" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 5 ] || falha "stack recusando devia sair 5: rc=$rc $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA1" ] || falha "current não voltou após falha de stack"
[ "$(readlink "$BIN_DIR/foo")" = "$PROD_RAIZ/platafirma-harness/current/bin/foo" ] || falha "PATH não reassentado após falha"
echo "OK"

echo "--- 8: reverter sem rev e sem ponto → 2; rev não materializada → 1 com vizinho"
rm -f "$PONTOS/platafirma-harness/anterior"
set +e; out="$("$VERBO" reverter platafirma-harness 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] && grep -q "materializados" <<<"$out" || falha "sem ponto: rc=$rc $out"
git -C "$REPO_RAIZ/platafirma-harness" checkout -q main
echo v3 > "$REPO_RAIZ/platafirma-harness/README.md"; git -C "$REPO_RAIZ/platafirma-harness" commit -q -am c3; git -C "$REPO_RAIZ/platafirma-harness" push -q origin main
H_SHA3="$(git -C "$REPO_RAIZ/platafirma-harness" rev-parse HEAD)"
set +e; out="$("$VERBO" reverter platafirma-harness "$H_SHA3" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] && grep -q "vizinho: release promover" <<<"$out" || falha "rev não materializada: rc=$rc $out"
echo "OK"

echo "--- 9: família de documentação: promover sem rev avança para origin/main; sem stack, sem PATH, sem porta"
: > "$DEPLOY_LOG"
out="$("$VERBO" promover platafirma-arquitetura 2>&1)" || falha "promover doc: $out"
[ "$(readlink "$PROD_RAIZ/platafirma-arquitetura/current")" = "$A_SHA2" ] || falha "doc current devia ser origin/main"
[ ! -s "$DEPLOY_LOG" ] || falha "doc chamou deploy ou porta"
[ ! -L "$BIN_DIR/README.md" ] || falha "doc mexeu no PATH"
out="$("$VERBO" ler platafirma-arquitetura README.md 2>/dev/null)"; [ "$out" = "v2" ] || falha "ler do doc servido: $out"
set +e; out="$("$VERBO" promover platafirma-arquitetura 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] || falha "doc já em origin/main devia sair 1: rc=$rc"
echo "OK"

echo "--- 10: estado do parque lista as duas famílias sem julgar"
# abertura existe na fixture sem current: o parque sai 1 (pior exit) e lista as três linhas
set +e; out="$("$VERBO" estado)"; rc=$?; set -e
[ "$rc" -eq 1 ] || falha "parque com família sem current devia sair 1: rc=$rc $out"
grep -q "^platafirma-harness " <<<"$out" && grep -q "^platafirma-arquitetura " <<<"$out" && grep -q "^abertura .*sem current" <<<"$out" || falha "parque: $out"
! grep -q "resultado:" <<<"$out" || falha "estado julgou"
echo "OK"

echo "--- 11: deploy ausente → 3, sem tocar current"
mkdir -p "$TMP_DIR/semdeploy"; cp "$STUBS/acervo" "$STUBS/systemd-run" "$STUBS/systemctl" "$TMP_DIR/semdeploy/"
set +e; out="$(PATH="$TMP_DIR/semdeploy:/usr/bin:/bin" "$VERBO" promover platafirma-harness "$H_SHA2" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] || falha "deploy ausente devia sair 3: rc=$rc $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA1" ] || falha "current mudou com deploy ausente"
echo "OK"

echo "--- 12: gate de promoção — rev que muda verbo reprovado em conferir verbo → 4 e current intacto; rev sem conferir passa sem gate"
# rev anterior ao gate (não traz bin/_release/conferir): promove e declara que não mediu
out="$("$VERBO" promover platafirma-harness "$H_SHA3" 2>&1)" || falha "promover sha3 (sem conferir na rev): $out"
grep -q "anterior ao gate" <<<"$out" || falha "rev sem conferir devia declarar que nao mediu: $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA3" ] || falha "current devia ser sha3"
# c4: traz o conferir da casa e um verbo novo com capacidade inventada
WT="$REPO_RAIZ/platafirma-harness"
mkdir -p "$WT/bin/_release/conferir"; cp "$REPO_ROOT/bin/_release/conferir/conferir.py" "$WT/bin/_release/conferir/conferir.py"
printf '#!/usr/bin/env bash\n# bar — verbo de teste do gate\n# capacidade: inventada-no-cabecalho\n# dono: ti\necho bar\n' > "$WT/bin/bar"; chmod +x "$WT/bin/bar"
git -C "$WT" add .; git -C "$WT" commit -q -m c4; git -C "$WT" push -q origin main
H_SHA4="$(git -C "$WT" rev-parse HEAD)"
set +e; out="$("$VERBO" promover platafirma-harness "$H_SHA4" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 4 ] || falha "verbo reprovado devia segurar a promoção com 4: rc=$rc $out"
grep -q "reprova em conferir verbo: bar" <<<"$out" || falha "recusa devia nomear o verbo reprovado: $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA3" ] || falha "current mudou com gate vermelho"
[ -d "$PROD_RAIZ/platafirma-harness/$H_SHA4" ] || falha "checkout da rev reprovada devia ficar materializado (imutável, reaproveitável)"
# c5: cabeçalho conforme (capacidade lavrada no mapa) → gate verde, current move
printf '#!/usr/bin/env bash\n# bar — verbo de teste do gate\n# capacidade: construcao\n# dono: ti\necho bar\n' > "$WT/bin/bar"
git -C "$WT" commit -q -am c5; git -C "$WT" push -q origin main
H_SHA5="$(git -C "$WT" rev-parse HEAD)"
out="$("$VERBO" promover platafirma-harness "$H_SHA5" 2>&1)" || falha "promover sha5 (gate verde): $out"
grep -q "gate:      verde" <<<"$out" && grep -q "para o que ela mudou: bar" <<<"$out" || falha "gate devia medir só bar e sair verde: $out"
[ "$(readlink "$PROD_RAIZ/platafirma-harness/current")" = "$H_SHA5" ] || falha "current devia ser sha5"
# rev que não toca bin/ não mede nada
echo v6 > "$WT/README.md"; git -C "$WT" commit -q -am c6; git -C "$WT" push -q origin main
H_SHA6="$(git -C "$WT" rev-parse HEAD)"
out="$("$VERBO" promover platafirma-harness "$H_SHA6" 2>&1)" || falha "promover sha6: $out"
grep -q "nao muda verbo nenhum" <<<"$out" || falha "rev sem mudança em bin/ devia declarar nada a medir: $out"
echo "OK"

echo "=== lote 2: todos os testes passaram ==="
