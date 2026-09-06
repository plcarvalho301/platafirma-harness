#!/usr/bin/env bash
# Renova a credencial git do braco jaiminho a partir do GitHub App (card #2899).
# A CHAVE (.pem) vive so no host (cofre 600); o braco recebe apenas um token de
# instalacao de ~1h. Rodar por cron. claudinho-seguranca, 29/08/2026.
#
# CONSERTO 06/09/2026 (fabrica, card #3012), depois de 3 dias parado em silencio.
# O que quebrou e por que:
#   - o destino era `docker exec -i jaiminho`, e o container `jaiminho` nao existe mais
#     em daemon nenhum. A imagem `platafirma/jaiminho:local` foi reconstruida em 02/09 —
#     mesmo dia da ultima linha OK do log — e o container nao voltou.
#   - o cron terminava em `>/dev/null 2>&1`. O erro do docker ia para o vazio, entao
#     credencial parada nao virou sinal nenhum. Tres dias.
#
# O conserto NAO e trocar o nome do container: e parar de depender de o braco estar DE
# PE para a credencial existir. O token agora vai para o VOLUME (a casa do braco), por
# contêiner efêmero, e o braco a encontra quando subir. Container vivo continua sendo
# atualizado tambem, para o token curto valer na sessao em curso.
#
# Falha agora e ALTA: log com FALHA, stderr, e `sinal` quando houver. Credencial que
# expira calada e a mesma classe de erro das 133 negativas de 31/08 — o fail-closed
# funciona, o custo e o dia que ninguem viu.
set -uo pipefail
KEY="$HOME/AI/var/secrets/jaiminho-app/app.pem"
APP_ID=4762140
INSTALL_ID=157525921
LOG="$HOME/AI/var/log/jaiminho-git-token.log"
export DOCKER_HOST="${PF_JAIMINHO_DOCKER_HOST:-unix:///run/user/1003/docker.sock}"
# Casa do braco: volume onde vive o HOME (uid 10001 dentro do contêiner).
VOLUME_CASA="${PF_JAIMINHO_VOLUME_CASA:-jaiminho-fabrica_casa}"
UID_BRACO=10001
# Container vivo, se houver. Nomes ja usados pelo braco ao longo das migracoes.
CANDIDATOS="jaiminho-fabrica jaiminho"

registra() { echo "$(date -Is) $*" >> "$LOG"; }

falha() {
  registra "FALHA $*"
  echo "jaiminho-git-token-refresh: $*" >&2
  command -v sinal >/dev/null 2>&1 && sinal incidente \
    --titulo "credencial git do braco jaiminho nao renovou" --detalhe "$*" >/dev/null 2>&1
  exit 1
}

b64(){ openssl base64 -A | tr '+/' '-_' | tr -d '='; }

[ -r "$KEY" ] || falha "chave do App ilegivel em $KEY"

now=$(date +%s)
h=$(printf '{"alg":"RS256","typ":"JWT"}' | b64)
p=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' $((now-60)) $((now+540)) "$APP_ID" | b64)
u="$h.$p"
s=$(printf '%s' "$u" | openssl dgst -sha256 -sign "$KEY" -binary | b64)
jwt="$u.$s"
tok=$(curl -sf -X POST \
  -H "Authorization: Bearer $jwt" \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "https://api.github.com/app/installations/${INSTALL_ID}/access_tokens" \
  | jq -r '.token // empty')
[ -n "${tok:-}" ] || falha "mint do token falhou na API do GitHub (token velho preservado)"

linha=$(printf 'https://x-access-token:%s@github.com\n' "$tok")
escritos=""

# (1) A CASA — vale mesmo com o braco desligado, e e o que faltava.
if docker volume inspect "$VOLUME_CASA" >/dev/null 2>&1; then
  if printf '%s' "$linha" | docker run --rm -i -v "$VOLUME_CASA":/casa alpine:3 \
       sh -c 'umask 077; cat > /casa/.git-credentials && chown '"$UID_BRACO:$UID_BRACO"' /casa/.git-credentials' \
       >/dev/null 2>&1; then
    escritos="$escritos volume:$VOLUME_CASA"
  else
    registra "AVISO escrita no volume $VOLUME_CASA falhou"
  fi
else
  registra "AVISO volume $VOLUME_CASA nao existe neste daemon ($DOCKER_HOST)"
fi

# (2) O CONTAINER, se estiver de pe — para o token curto valer na sessao em curso.
for c in $CANDIDATOS; do
  docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$c" || continue
  if printf '%s' "$linha" | docker exec -i "$c" sh -c 'umask 077; cat > "$HOME/.git-credentials"' \
       >/dev/null 2>&1; then
    escritos="$escritos container:$c"
  else
    registra "AVISO escrita no container $c falhou"
  fi
done

[ -n "$escritos" ] || falha "token mintado, mas nao havia onde grava-lo: sem volume '$VOLUME_CASA' e sem container de pe ($CANDIDATOS) em $DOCKER_HOST"

registra "OK token renovado ->$escritos"
