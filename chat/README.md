# chat

Pasta de `platafirma-harness` com o chat da PlataFirma (`chat.platafirma.org`, Matrix): uma sala
direta por ator com o dono, e o giro que leva a mensagem ao motor e traz a resposta. Roda como a
stack `chat` (Synapse, banco e recepção) mais o worker `chat-worker` no host da conta `claudinho`.

## Como sobe

Pré-requisitos na instância, fora do git:

- o cofre `segredos/matrix/` com o `oidc-client-secret`, que é da cadeira de segurança;
- os segredos da stack, cunhados uma vez por `chat/prepara.sh` (idempotente: o que já existe não é
  recunhado);
- a sobreposição `deploy/chat/compose.override.yaml`, na forma de `chat/compose.override.exemplo.yaml`.

Da release:

```
release promover platafirma-harness <sha>
infra build chat
infra up chat -d
/opt/platafirma/current/harness/deploy-harness/instalar
```

`instalar` liga o `chat-worker.service` à release. Subiu quando `infra ps chat` mostra
`chat-synapse`, `chat-recepcao` e `chat-pg` de pé, `infra estado` lista `chat-worker.service`
`running`, e uma mensagem na sala de um ator volta com resposta.

Ator novo na superfície: `chat/provisiona-cadeiras.sh @<dono>:<dominio>`, depois do primeiro login
do dono. O locale do banco se decide na criação do volume (`C`): errado, só recriando o volume.

## Como se testa

As provas rodam dentro da imagem da recepção. A do ciclo inteiro, com homeserver e verbo de
mentira e receptor, worker e journal de verdade, a partir de `chat/`:

```
docker run --rm --network none -e PYTHONUNBUFFERED=1 \
  -e PF_ABERTURA_DIR=/abertura-publicada \
  -v "$PWD:/chat:ro" -v "<morada publicada da abertura>:/abertura-publicada:ro" \
  --entrypoint python platafirma/chat-recepcao:local /chat/testes/prova-ponta-a-ponta.py
```

Passou quando cada critério imprime `ok` e sai com exit 0. A prova de formatação está no
[README da recepção](recepcao/README.md).

## Onde está o quê

| pasta | o que tem |
|---|---|
| `recepcao/` | o Application Service, único que fala Matrix; [README](recepcao/README.md) |
| `worker/` | o worker do host, que reivindica o job e chama `bin/chat` |
| `comum/` | journal, costura de cadeira e MXID, comuns a recepção e worker |
| `conf/` | configuração versionada do Synapse, sem segredo |
| `testes/` | as provas |

Modelo de ator, fluxo do giro, avatares e login do motor: `docs/chat.md` na raiz do repositório.
