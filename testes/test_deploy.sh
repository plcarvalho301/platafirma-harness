#!/usr/bin/env bash
# Testes do verbo deploy no layout do desenho #3010 §3-§4: base do compose na arvore imutavel da
# release, sobreposicao da instancia, segredo materializado em env-file no tmpfs e apagado, projeto
# compose preservado, pontos da stack na instancia. Tudo num tmp; docker e stub; bancada inexistente.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERBO="$REPO_ROOT/bin/deploy"

TMP_DIR="$(mktemp -d /tmp/pf-deploy-test.XXXXXX)"
trap 'chmod -R u+w "$TMP_DIR" 2>/dev/null || true; rm -rf "$TMP_DIR"' EXIT
falha() { echo "FALHA: $*" >&2; exit 1; }

echo "=== deploy: release + instancia ==="

RELEASE="$TMP_DIR/opt"; INSTANCIA="$TMP_DIR/srv"; STUBS="$TMP_DIR/stubs"
export PF_RELEASE_RAIZ="$RELEASE" PLATAFIRMA_INSTANCIA="$INSTANCIA" PLATAFIRMA_BANCADA="$TMP_DIR/bancada-inexistente"
export DEPLOY_ENV_DIR="$TMP_DIR/run/platafirma" DEPLOY_TOPO_ARQUIVO="$TMP_DIR/topologia.json"
unset PLATAFIRMA_RELEASE DEPLOY_PONTOS PF_SIM 2>/dev/null || true
export DOCKER_LOG="$TMP_DIR/docker.log"; : > "$DOCKER_LOG"

SHA1="1111111111111111111111111111111111111111"
SHA2="2222222222222222222222222222222222222222"
for s in "$SHA1" "$SHA2"; do
  mkdir -p "$RELEASE/platafirma-core/$s/sem-nome" "$RELEASE/platafirma-core/$s/bin"
  printf 'name: platafirma-core\nservices:\n  app:\n    image: busybox\n' > "$RELEASE/platafirma-core/$s/docker-compose.yml"
  printf 'services:\n  app:\n    image: busybox\n' > "$RELEASE/platafirma-core/$s/sem-nome/compose.yaml"
  cat > "$RELEASE/platafirma-core/$s/bin/montar" <<'PBOF'
#!/usr/bin/env bash
touch "${SENTINELA:?}"
printf 'pre_build %s em %s\n' "$*" "$PWD" >> "${DOCKER_LOG:?}"
PBOF
  chmod +x "$RELEASE/platafirma-core/$s/bin/montar"
  cat > "$RELEASE/platafirma-core/$s/bin/montar-falha" <<'PBOF'
#!/usr/bin/env bash
printf 'pre_build falhou de proposito\n' >> "${DOCKER_LOG:?}"
exit 1
PBOF
  chmod +x "$RELEASE/platafirma-core/$s/bin/montar-falha"
  chmod -R a-w "$RELEASE/platafirma-core/$s"
done
ln -s "$SHA1" "$RELEASE/platafirma-core/current"

mkdir -p "$INSTANCIA/deploy/core" "$INSTANCIA/segredos/core"
printf 'services:\n  app:\n    volumes:\n      - %s/dados/app:/dados\n' "$INSTANCIA" > "$INSTANCIA/deploy/core/compose.override.yaml"
chmod 700 "$INSTANCIA/segredos" "$INSTANCIA/segredos/core"
printf 'valor-de-teste' > "$INSTANCIA/segredos/core/POSTGRES_PASSWORD"
printf -- '-----BEGIN-----\nx\n-----END-----\n' > "$INSTANCIA/segredos/core/chave.pem"
printf 'linha1\nlinha2\n' > "$INSTANCIA/segredos/core/MULTI"
chmod 600 "$INSTANCIA/segredos/core"/*

cat > "$DEPLOY_TOPO_ARQUIVO" <<'EOF'
{"stacks": {
  "core": {"slug": "core", "papel": "teste", "critico": false, "repo": "platafirma-core",
           "compose": "docker-compose.yml", "segredos": ["POSTGRES_PASSWORD"], "rotas": "cloudflared.yml",
           "reversao": {"via": "promover", "quem": "ti", "janela_min": 1, "estado": "nada"}},
  "com_pb": {"slug": "com_pb", "repo": "platafirma-core", "projeto": "platafirma-core",
             "compose": "docker-compose.yml", "pre_build": "bin/montar",
             "reversao": {"via": "promover", "quem": "ti", "janela_min": 1, "estado": "nada"}},
  "falha_pb": {"slug": "falha_pb", "repo": "platafirma-core", "projeto": "platafirma-core",
               "compose": "docker-compose.yml", "pre_build": "bin/montar-falha",
               "reversao": {"via": "promover", "quem": "ti", "janela_min": 1, "estado": "nada"}},
  "fora_pb": {"slug": "fora_pb", "repo": "platafirma-core", "projeto": "platafirma-core",
              "compose": "docker-compose.yml", "pre_build": "../fora",
              "reversao": {"via": "promover", "quem": "ti", "janela_min": 1, "estado": "nada"}},
  "naoexec_pb": {"slug": "naoexec_pb", "repo": "platafirma-core", "projeto": "platafirma-core",
                 "compose": "docker-compose.yml", "pre_build": "bin/nao-existe",
                 "reversao": {"via": "promover", "quem": "ti", "janela_min": 1, "estado": "nada"}},
  "fora":  {"slug": "fora", "repo": "platafirma-core", "compose": "~/deploy/core/docker-compose.yml"},
  "legado": {"slug": "legado", "repo": "platafirma-core", "compose": "docker-compose.yml",
             "rotas": "~/deploy/core/cloudflared.yml", "gate": "/etc/gate/docker-compose.yml", "segredos": ["~/segredos/core/TOKEN"]},
  "semnome": {"slug": "semnome", "repo": "platafirma-core", "compose": "sem-nome/compose.yaml"},
  "atalho": {"slug": "atalho", "repo": "platafirma-core", "projeto": "platafirma-core",
             "compose": "PLACEHOLDER/core/docker-compose.yml"}
}}
EOF
sed -i "s|PLACEHOLDER|$RELEASE/current|" "$DEPLOY_TOPO_ARQUIVO"

mkdir -p "$STUBS"
cat > "$STUBS/docker" <<'EOF'
#!/usr/bin/env bash
printf 'docker %s\n' "$*" >> "${DOCKER_LOG:?}"
prev=""
for a in "$@"; do
  if [ "$prev" = "--env-file" ]; then
    printf 'envfile %s modo=%s nomes=%s\n' "$a" "$(stat -c %a "$a")" "$(cut -d= -f1 "$a" | tr '\n' ',')" >> "$DOCKER_LOG"
  fi
  prev="$a"
done
case " $* " in *" config --services "*) echo app ;; esac
exit 0
EOF
chmod +x "$STUBS/docker"
export PATH="$STUBS:$PATH"

echo "--- 1: up sobe da arvore do current (sha), com sobreposicao, env-file em tmpfs 0600 apagado, projeto preservado"
out="$("$VERBO" core up -d 2>&1)" || falha "up: $out"
BASE1="$RELEASE/platafirma-core/$SHA1/docker-compose.yml"
grep -qF "docker compose -p platafirma-core -f $BASE1 -f $INSTANCIA/deploy/core/compose.override.yaml --env-file $DEPLOY_ENV_DIR/core.env up -d" "$DOCKER_LOG" \
  || falha "invocacao do compose: $(cat "$DOCKER_LOG")"
grep -q "^envfile $DEPLOY_ENV_DIR/core.env modo=600 nomes=POSTGRES_PASSWORD,$" "$DOCKER_LOG" || falha "env-file: $(grep envfile "$DOCKER_LOG")"
[ ! -e "$DEPLOY_ENV_DIR/core.env" ] || falha "env-file sobreviveu ao deploy"
[ -z "$(ls -A "$DEPLOY_ENV_DIR")" ] || falha "sobrou arquivo no tmpfs: $(ls -A "$DEPLOY_ENV_DIR")"
[ "$(stat -c %a "$DEPLOY_ENV_DIR")" = "700" ] || falha "diretorio do env-file devia ser 0700"
[ "$(cat "$INSTANCIA/var/deploy/core.atual")" = "$SHA1" ] || falha "sha que subiu nao gravado na instancia"
! grep -q "valor-de-teste" <<<"$out" || falha "valor de segredo impresso"
find "$RELEASE" -name '.env' | grep -q . && falha ".env escrito em arvore da release"
echo "OK"

echo "--- 2: compose fora da release → 3; compose sob os atalhos da release vale"
set +e; out="$("$VERBO" fora up -d 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] && grep -q "fora da release" <<<"$out" || falha "compose fora da release: rc=$rc $out"
: > "$DOCKER_LOG"
mkdir -p "$RELEASE/current"; ln -s "$RELEASE/platafirma-core/current" "$RELEASE/current/core"
out="$("$VERBO" atalho ps 2>&1)" || falha "compose sob atalho: $out"
grep -qF -- "-p platafirma-core -f $BASE1 " "$DOCKER_LOG" || falha "atalho devia resolver para a arvore do sha: $(cat "$DOCKER_LOG")"
echo "OK"

echo "--- 3: sem projeto declarado nem name: no compose → 3 (nunca nome inventado)"
set +e; out="$("$VERBO" semnome up -d 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] && grep -q "projeto compose" <<<"$out" || falha "projeto ausente: rc=$rc $out"
echo "OK"

echo "--- 4: segredo declarado ausente → up recusa 1, nada sobe"
mv "$INSTANCIA/segredos/core/POSTGRES_PASSWORD" "$TMP_DIR/guardado"
: > "$DOCKER_LOG"
set +e; out="$("$VERBO" core up -d 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] && grep -q "faltam 1 segredo" <<<"$out" || falha "segredo ausente: rc=$rc $out"
[ ! -s "$DOCKER_LOG" ] || falha "subiu com segredo ausente"
set +e; out="$("$VERBO" core segredos 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] && grep -q "AUSENTE : POSTGRES_PASSWORD" <<<"$out" || falha "segredos devia acusar ausente: rc=$rc $out"
mv "$TMP_DIR/guardado" "$INSTANCIA/segredos/core/POSTGRES_PASSWORD"
out="$("$VERBO" core segredos 2>&1)" || falha "segredos presente: $out"
grep -q "ok      : POSTGRES_PASSWORD" <<<"$out" && grep -q "cofre da stack: $INSTANCIA/segredos/core" <<<"$out" || falha "segredos: $out"
echo "OK"

echo "--- 5: promover <sha> sobe da arvore desse sha e grava o ponto de volta; rev nao materializada → 1"
: > "$DOCKER_LOG"
out="$("$VERBO" core promover "$SHA2" 2>&1)" || falha "promover sha2: $out"
grep -qF "docker compose -p platafirma-core -f $RELEASE/platafirma-core/$SHA2/docker-compose.yml -f $INSTANCIA/deploy/core/compose.override.yaml --env-file $DEPLOY_ENV_DIR/core.env up -d --build --force-recreate" "$DOCKER_LOG" \
  || falha "promover invocou: $(cat "$DOCKER_LOG")"
[ "$(cat "$INSTANCIA/var/deploy/core.anterior")" = "$SHA1" ] || falha "anterior devia ser sha1"
[ "$(cat "$INSTANCIA/var/deploy/core.atual")" = "$SHA2" ] || falha "atual devia ser sha2"
set +e; out="$("$VERBO" core promover 3333333333333333333333333333333333333333 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] && grep -q "release promover platafirma-core" <<<"$out" || falha "rev nao materializada: rc=$rc $out"
echo "OK"

echo "--- 6: mostrar o declarado aponta o projeto e o desalinhamento com o current"
out="$("$VERBO" core 2>&1)" || falha "mostrar: $out"
grep -q "^projeto : platafirma-core" <<<"$out" || falha "projeto: $out"
grep -q "conteineres em 2222222, current de platafirma-core em 1111111" <<<"$out" || falha "servido: $out"
grep -q "^pre_build: nenhum" <<<"$out" || falha "pre_build core: $out"
out_pb="$("$VERBO" com_pb 2>&1)" || falha "mostrar com_pb: $out_pb"
grep -q "^pre_build: bin/montar" <<<"$out_pb" || falha "pre_build com_pb: $out_pb"
echo "OK"

echo "--- 7: reverter --executar volta ao ponto gravado (sem gate de confirmacao)"
: > "$DOCKER_LOG"
out="$("$VERBO" core reverter --executar 2>&1)" || falha "reverter: $out"
grep -qF -- "-f $BASE1 " "$DOCKER_LOG" || falha "reverter devia subir da arvore do sha1: $(cat "$DOCKER_LOG")"
[ "$(cat "$INSTANCIA/var/deploy/core.revertido-de")" = "$SHA2" ] || falha "revertido-de devia ser sha2"
[ "$(cat "$INSTANCIA/var/deploy/core.atual")" = "$SHA1" ] || falha "atual devia voltar a sha1"
[ ! -e "$DEPLOY_ENV_DIR/core.env" ] || falha "env-file sobreviveu ao reverter"
echo "OK"

echo "--- 8b: rotas relativas resolvem na sobreposicao da instancia; ~ e absoluto fora das raizes → 3, nada sobe"
printf 'ingress:\n  - hostname: a.exemplo\n    service: http://app:80\n  - service: http_status:404\n' > "$INSTANCIA/deploy/core/cloudflared.yml"
out="$("$VERBO" core rotas 2>&1)" || falha "rotas: $out"
grep -qF "ingress : $INSTANCIA/deploy/core/cloudflared.yml" <<<"$out" && grep -q "a.exemplo" <<<"$out" || falha "rotas relativas: $out"
for ato in rotas acessos segredos; do
  set +e; out="$("$VERBO" legado "$ato" 2>&1)"; rc=$?; set -e
  [ "$rc" -eq 3 ] && grep -q "fora das raizes de producao" <<<"$out" || falha "legado $ato devia recusar 3: rc=$rc $out"
done
: > "$DOCKER_LOG"
set +e; out="$("$VERBO" legado up -d 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] && grep -q "fora das raizes de producao" <<<"$out" || falha "legado up devia recusar 3: rc=$rc $out"
[ ! -s "$DOCKER_LOG" ] || falha "legado subiu com segredo fora das raizes"
echo "OK"

echo "--- 8: stack fora do registro → 2"
set +e; out="$("$VERBO" inexistente up 2>&1)"; rc=$?; set -e
[ "$rc" -eq 2 ] && grep -q "nao esta no registro" <<<"$out" || falha "stack desconhecida: rc=$rc $out"
echo "OK"

echo "--- 9: pre_build: promover roda pre_build antes de compose up; falha propaga rc != 0 e nao sobe; stack sem pre_build promove normal"
export SENTINELA="$TMP_DIR/sentinela"

# (a) promover roda pre_build (stub toca arquivo-sentinela) ANTES do compose up, com cwd na raiz da arvore da release
rm -f "$SENTINELA"; : > "$DOCKER_LOG"
out="$("$VERBO" com_pb promover "$SHA2" 2>&1)" || falha "promover com_pb: $out"
[ -f "$SENTINELA" ] || falha "sentinela nao foi tocada pelo pre_build"
grep -qF "pre_build  em $RELEASE/platafirma-core/$SHA2" "$DOCKER_LOG" || falha "pre_build nao rodou na arvore da release: $(cat "$DOCKER_LOG")"
linha_pb="$(grep -n "pre_build " "$DOCKER_LOG" | head -n1 | cut -d: -f1)"
linha_up="$(grep -n "docker compose .*up -d --build --force-recreate" "$DOCKER_LOG" | head -n1 | cut -d: -f1)"
[ -n "$linha_pb" ] && [ -n "$linha_up" ] && [ "$linha_pb" -lt "$linha_up" ] \
  || falha "pre_build (linha $linha_pb) devia rodar antes do compose up (linha $linha_up): $(cat "$DOCKER_LOG")"

# (b) pre_build exit 1 faz promover recusar rc != 0 e o docker stub NAO e chamado para up
: > "$DOCKER_LOG"
set +e; out="$("$VERBO" falha_pb promover "$SHA2" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 1 ] || falha "falha_pb devia recusar rc=1: rc=$rc $out"
grep -qF 'recusa: pre_build de "falha_pb" falhou (rc=1) — nada subiu' <<<"$out" || falha "msg recusa: $out"
! grep -q "docker compose .*up" "$DOCKER_LOG" || falha "docker compose up nao devia ter sido chamado: $(cat "$DOCKER_LOG")"

# (c) stack sem pre_build promove igual a hoje
: > "$DOCKER_LOG"
out="$("$VERBO" core promover "$SHA2" 2>&1)" || falha "promover core sem pre_build: $out"
grep -qF "docker compose -p platafirma-core -f $RELEASE/platafirma-core/$SHA2/docker-compose.yml -f $INSTANCIA/deploy/core/compose.override.yaml --env-file $DEPLOY_ENV_DIR/core.env up -d --build --force-recreate" "$DOCKER_LOG" \
  || falha "core sem pre_build devia promover normal: $(cat "$DOCKER_LOG")"
! grep -q "pre_build" "$DOCKER_LOG" || falha "pre_build nao devia rodar para core"

# pre_build fora da arvore ou nao executavel -> recusa exit 3
set +e; out="$("$VERBO" fora_pb promover "$SHA2" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] && grep -q "fora da arvore da release" <<<"$out" || falha "fora_pb: rc=$rc $out"

set +e; out="$("$VERBO" naoexec_pb promover "$SHA2" 2>&1)"; rc=$?; set -e
[ "$rc" -eq 3 ] && grep -q "nao e executavel" <<<"$out" || falha "naoexec_pb: rc=$rc $out"

# up tambem roda pre_build antes do compose
rm -f "$SENTINELA"; : > "$DOCKER_LOG"
out="$("$VERBO" com_pb up -d 2>&1)" || falha "up com_pb: $out"
[ -f "$SENTINELA" ] || falha "sentinela nao foi tocada pelo up"
linha_pb="$(grep -n "pre_build " "$DOCKER_LOG" | head -n1 | cut -d: -f1)"
linha_up="$(grep -n "docker compose .*up -d" "$DOCKER_LOG" | head -n1 | cut -d: -f1)"
[ -n "$linha_pb" ] && [ -n "$linha_up" ] && [ "$linha_pb" -lt "$linha_up" ] \
  || falha "up: pre_build (linha $linha_pb) devia rodar antes do compose up (linha $linha_up): $(cat "$DOCKER_LOG")"
echo "OK"

echo "=== deploy: todos os testes passaram ==="
