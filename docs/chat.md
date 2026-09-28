# Chat

`chat/` é a superfície de conversa da PlataFirma em `chat.platafirma.org` (Element/Matrix): uma
sala direta por ator, com o dono. Como a stack sobe e como se testa a recepção está no
[README de chat/recepcao](../chat/recepcao/README.md).

## Onde roda

- Stack `chat` (`chat/docker-compose.yml`), no daemon rootless da conta `claudinho`: `chat-synapse`
  (8008/8448), `chat-recepcao` (8080) e `chat-pg`. O túnel Cloudflare entra direto no
  `chat-synapse`; autenticação por OIDC; Admin API fechada na borda. Todo caminho da instância
  (cofre, fitas, journal, morada da abertura) vem da sobreposição
  `/srv/platafirma/casa/deploy/chat/compose.override.yaml`, com forma em
  `chat/compose.override.exemplo.yaml`.
- Worker no host: `chat/systemd/chat-worker.service`, `systemd --user`, ligado à release por
  `deploy-harness/instalar`.

## Componentes

`recepcao/` (o Application Service, único que fala Matrix) → `comum/journal.py` (fila por sala,
SQLite em WAL) → `worker/worker.py` (host) → `bin/chat` (o verbo, que gira o motor). Contrato
entre worker e verbo: uma linha JSON no stdout, uma por passo no stderr.

## Modelo de ator

Três eixos independentes, resolvidos só por `chat/comum/cadeiras.py`:

- **conta**: o usuário do SO onde o ator roda; é o perímetro de segregação.
- **provider**: a entidade por trás da conta, e o nome que aparece na sala e no MXID (`claudinho`
  é o Claude).
- **persona**: o que `monta-sessao` injeta na abertura, de `abertura/<persona>/persona.md`.

O roster da superfície (`atores()`) tem três baldes:

| balde | fonte | motor |
|---|---|---|
| cadeira | ledger de vínculo do org | Claude Code no cwd da fita |
| participante | rito de admissão | nenhum nesta superfície: `bin/chat` devolve erro limpo |
| ator interno | `_ATORES_INTERNOS` em `cadeiras.py` | Claude Code no cwd da fita |

`eh_participante(ator)` decide a rota em `bin/chat`. Cadeira e ator interno compartilham motor e
caminho; separam-se em que a cadeira tem vínculo no org (voto, remit, roteamento) e o ator interno não.

A `fabrica` é ator interno: persona de roteamento de linha (devops, blueteam, front-end), sala
`@_pf_fabrica`, conta `claudinho`, gira por Claude Code. Não entra em `cadeiras()`: não tem head,
não vota, não roteia. `slug_da_cadeira('fabrica')` devolve a persona homônima, que é a chave de
mesa, fila e Project, sem prefixo `claudinho-`.

## Fluxo de um giro

1. A recepção recebe a mensagem, identifica o ator dono da sala por `eh_de_ator`, e enfileira o job
   no journal daquela sala.
2. O worker reivindica o job (um em curso por sala, paralelismo entre salas) e chama
   `bin/chat despachar --cadeira <ator> --fita <id-ou-vazio>`, com o corpo no stdin.
3. No ramo Claude Code: fita nova (`--fita ""`) roda `monta-sessao <persona>` e o pacote entra por
   `--append-system-prompt` na mesma invocação; fita existente vai por `--resume <id>`, sem
   reinjetar o pacote.
4. O motor gira no cwd `/srv/platafirma/casa/var/fitas/<persona>`, emite um evento por passo (o
   worker vigia silêncio) e devolve uma linha JSON de resultado.
5. A recepção posta a resposta na sala.

O pacote de `monta-sessao` não se replica no `CLAUDE.md` do cwd da fita: fonte única.

## Provisionar ator

```
chat/provisiona-cadeiras.sh @<dono>:<dominio>
```

Cria o usuário no namespace da recepção, põe displayname e avatar, e abre a sala direta com o dono.
Roda depois do primeiro login OIDC do dono (antes disso o MXID dele não existe). Idempotente: o que
já está no estado desejado não é reescrito. Quem entra é `atores()`; o displayname vem do alias do
org canônico (`$PLATAFIRMA_RELEASE/arquitetura/docs/org-template-canonico.md`), e ator sem alias
sobe pelo sufixo. Displayname é reversível, MXID não.

### Avatares

`chat/avatares/` guarda um arquivo por ator, `.png`, `.jpg`, `.jpeg`, `.webp` ou `.gif`. O nome
pode ser o slug do org, o sufixo do harness ou o localpart Matrix, em caixa original ou baixa:

```
claudinho-TI.png       TI.png       _pf_ti.png
claudinha-produto.png  produto.png  _pf_produto.png
```

Ator fora da tabela do org só tem sufixo, e a imagem se nomeia por ele. Ator sem imagem não
interrompe o provisionamento: o script avisa, provisiona o resto e sai 0; uma corrida posterior põe
o avatar sem recriar usuário nem sala. A imagem só sobe ao Synapse quando muda: o `sha256` fica no
`account_data` do ator (`org.platafirma.avatar`).

## Login do Claude Code da conta

O motor exige login OAuth na conta `claudinho`; expirado, o giro volta com `OAuth session expired`.
O login é interativo (imprime URL, espera o código colado) e se conduz sem terminal local por um
driver pty: `claude auth login` num processo destacado, a URL capturada num arquivo, e o código que
o dono autoriza no navegador injetado de volta no stdin.

O trust do cwd da fita é pré-requisito à parte: `projects["<cwd>"].hasTrustDialogAccepted: true`
em `~/.claude.json`, senão o motor ignora a allowlist do `.claude/settings.json` da fita.
