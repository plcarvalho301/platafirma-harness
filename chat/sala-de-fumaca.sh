#!/usr/bin/env bash
# sala-de-fumaca.sh <mxid-do-dono> — cria UMA sala pelo bot da recepcao e convida o dono.
# capacidade: mudanca
# dono: claudinha-fabrica (card 447)
#
# Existe so para o aceite 5 do card 447 ("a sala existe"). As sete salas por cadeira,
# com alias e avatar, sao o card 448 — este script nao e o embriao delas, e sai quando
# o 448 entrar.
#
# Roda DEPOIS do primeiro login OIDC do dono: antes disso o MXID dele nao existe.
set -euo pipefail

MXID="${1:?uso: ./sala-de-fumaca.sh @pedro:chat.platafirma.org}"
export DOCKER_HOST="${DOCKER_HOST:-unix:///run/user/$(id -u)/docker.sock}"
COFRE="${PF_COFRE:-$HOME/AI/var/secrets/matrix}"

# O token nao passa por linha de comando (ps mostra argv): entra por variavel de
# ambiente do exec, e o corpo do pedido por stdin.
docker exec -i -e MXID="$MXID" -e AS_TOKEN="$(cat "$COFRE/as-token")" chat-recepcao python - <<'PYSALA'
import json, os, urllib.request

pedido = urllib.request.Request(
    "http://chat-synapse:8008/_matrix/client/v3/createRoom",
    data=json.dumps({
        "name": "PlataFirma — sala de fumaca",
        "topic": "Card 447: prova de que a stack esta no ar. Descartavel.",
        "preset": "private_chat",
        "invite": [os.environ["MXID"]],
    }).encode(),
    headers={"Authorization": f"Bearer {os.environ['AS_TOKEN']}", "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(pedido, timeout=30) as r:
    print(r.status, json.load(r))
PYSALA
