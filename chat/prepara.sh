#!/usr/bin/env bash
# prepara.sh — cunha no cofre os segredos da stack `chat` e gera o que deriva deles.
# capacidade: mudanca
# dono: claudinha-fabrica (card 447)
#
# Idempotente por desenho: segredo que ja existe NAO e recunhado. Rotacao e ato
# deliberado, nao efeito colateral de reexecutar o preparo.
#
# Nada aqui ecoa valor de segredo. O que sai na tela e nome e presenca.
#
# ambiente: PF_INSTANCIA (default /srv/platafirma/casa), PF_COFRE (default
# $PF_INSTANCIA/segredos/matrix), PF_SEGREDOS_STACK (default $PF_INSTANCIA/segredos/chat).
#
# Nada nasce na arvore do codigo (card #3010): o cofre e a instancia. As variaveis que o
# compose interpola viram um arquivo cada em segredos/chat/, e o `deploy` materializa
# delas o --env-file em tmpfs. Nao ha .env na stack.
set -euo pipefail

. "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/../lib/raizes.sh"

export DOCKER_HOST="${DOCKER_HOST:-unix:///run/user/$(id -u)/docker.sock}"
COFRE="${PF_COFRE:-$PF_INSTANCIA/segredos/matrix}"
SEGREDOS_STACK="${PF_SEGREDOS_STACK:-$PF_INSTANCIA/segredos/chat}"
SYNAPSE_IMG="ghcr.io/element-hq/synapse:v1.157.2"

umask 077
# O cofre nasce no bootstrap do host e recebe o oidc-client-secret da seguranca antes
# deste preparo: ausente, para alto — criar diretorio aqui esconderia instancia faltando.
if [ ! -d "$COFRE" ]; then
  echo "erro: cofre ausente: $COFRE" >&2
  exit 1
fi

# O secret do client OIDC e ato de claudinho-seguranca. Ausente, o preparo para: gerar
# um aqui produziria stack de pe que nao autentica ninguem, e o erro so apareceria no
# login do dono.
if [ ! -s "$COFRE/oidc-client-secret" ]; then
  echo "erro: falta $COFRE/oidc-client-secret" >&2
  echo "      e do claudinho-seguranca (client FK81JZ no realm). Nao se gera aqui." >&2
  exit 1
fi

nasce_hex() {
  if [ ! -s "$1" ]; then openssl rand -hex 32 > "$1"; echo "  cunhado : $(basename "$1")"
  else echo "  ja havia: $(basename "$1")"; fi
  chmod 600 "$1"
}

echo "cofre: $COFRE"
nasce_hex "$COFRE/pg-password"
nasce_hex "$COFRE/as-token"
nasce_hex "$COFRE/hs-token"
nasce_hex "$COFRE/macaroon-secret"
nasce_hex "$COFRE/form-secret"

# Chave de assinatura: identidade do homeserver. No cofre e nao no volume, para
# sobreviver a `down -v` — chave nova invalida a assinatura de todo evento antigo.
if [ ! -s "$COFRE/signing.key" ]; then
  docker run --rm --entrypoint python "$SYNAPSE_IMG" \
    -m synapse._scripts.generate_signing_key > "$COFRE/signing.key"
  chmod 600 "$COFRE/signing.key"
  echo "  cunhado : signing.key"
else
  echo "  ja havia: signing.key"
fi

le() { cat "$COFRE/$1"; }

# Segundo `-c` do Synapse. Chave de topo aqui SOBRESCREVE a do homeserver.yaml (o merge
# e dict.update, nao fusao profunda): por isso o bloco `database` vem inteiro.
cat > "$COFRE/segredos.yaml" <<FIM
# GERADO por platafirma-harness/chat/prepara.sh — nao editar na mao.
database:
  name: psycopg2
  args:
    user: synapse
    password: $(le pg-password)
    dbname: synapse
    host: chat-pg
    port: 5432
    cp_min: 5
    cp_max: 10
macaroon_secret_key: $(le macaroon-secret)
form_secret: $(le form-secret)
FIM
chmod 600 "$COFRE/segredos.yaml"

cat > "$COFRE/registration.yaml" <<FIM
# GERADO por platafirma-harness/chat/prepara.sh — forma versionada em
# platafirma-harness/chat/conf/registration.exemplo.yaml
id: pf
url: http://chat-recepcao:8080
as_token: $(le as-token)
hs_token: $(le hs-token)
sender_localpart: _pf
rate_limited: false
namespaces:
  users:
    - exclusive: true
      regex: '@_pf.*:chat\.platafirma\.org'
FIM
chmod 600 "$COFRE/registration.yaml"

# Um arquivo por variavel que o compose interpola. O `deploy` materializa o --env-file
# a partir daqui; o valor nunca passa pela tela nem pela arvore do codigo.
[ -d "$(dirname "$SEGREDOS_STACK")" ] || {
  echo "erro: segredos da instancia ausentes: $(dirname "$SEGREDOS_STACK")" >&2
  exit 1
}
mkdir -p -m 700 "$SEGREDOS_STACK"
grava_var() {
  le "$2" > "$SEGREDOS_STACK/$1"
  chmod 600 "$SEGREDOS_STACK/$1"
}
grava_var PG_PASSWORD pg-password
grava_var AS_TOKEN as-token
grava_var HS_TOKEN hs-token

echo "gerados: segredos.yaml, registration.yaml (no cofre) e PG_PASSWORD, AS_TOKEN, HS_TOKEN em $SEGREDOS_STACK"
