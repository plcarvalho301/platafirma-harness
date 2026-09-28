# recepcao

Pasta de `chat/` com o Application Service Matrix, o único componente que fala com o Synapse: recebe
a mensagem da sala, enfileira o giro no journal, formata, fatia e posta a resposta. Roda como o
contêiner `chat-recepcao` da stack `chat`. Não chama verbo nem gira motor: isso é do worker no host.

## Como sobe

Pré-requisitos: os tokens `AS_TOKEN` e `HS_TOKEN` em `segredos/chat/` da instância, cunhados
por `chat/prepara.sh`, e a sobreposição `deploy/chat/compose.override.yaml` no lugar (forma em
`chat/compose.override.exemplo.yaml`). A imagem se monta com contexto em `chat/`, não nesta
pasta, porque leva junto `chat/comum/`:

```
release promover platafirma-harness <sha>
infra build chat
infra up chat -d
```

Subiu quando `infra ps chat` mostra `chat-recepcao` de pé e uma mensagem na sala de um ator
volta com resposta no cliente Matrix.

## Como se testa

A prova de formatação roda dentro da imagem, onde o Markdown está pinado. A partir de `chat/`,
com a imagem já montada:

```
docker run --rm -v "$PWD/testes:/testes:ro" --entrypoint python \
  platafirma/chat-recepcao:local /testes/prova-formata.py
```

Passou quando cada critério imprime `ok` e sai com exit 0; sai com 1 na primeira falha.

O ciclo inteiro (sala, journal, worker, resposta) se prova com `chat/testes/prova-ponta-a-ponta.py`,
pela mesma imagem.
