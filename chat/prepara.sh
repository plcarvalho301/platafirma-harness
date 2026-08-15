#!/usr/bin/env bash
# prepara.sh — cunha no cofre os segredos da stack `chat` e gera o que deriva deles.
# capacidade: mudanca
# dono: claudinha-fabrica (card 447)
#
# Idempotente por desenho: segredo que ja existe NAO e recunhado. Rotacao e ato
# deliberado, nao efeito colateral de reexecutar o preparo.
#
# Nada aqui ecoa valor de segredo. O que sai na tela e nome e presenca.
set -euo pipefail

export DOCKER_HOST="${DOCKER_HOST:-unix:///run/user/$(id -u)/docker.sock}"
COFRE="${PF_COFRE:-$HOME/AI/var/secrets/matrix}"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYNAPSE_IMG="ghcr.io/element-hq/synapse:v1.157.2"

umask 077
mkdir -p "$COFRE"

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
url: http://chat-as:8080
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

cat > "$AQUI/.env" <<FIM
# GERADO por ./prepara.sh a partir de $COFRE — fora do git.
PG_PASSWORD=$(le pg-password)
AS_TOKEN=$(le as-token)
HS_TOKEN=$(le hs-token)
FIM
chmod 600 "$AQUI/.env"

echo "gerados: segredos.yaml, registration.yaml (no cofre) e .env (na stack)"
