# chat — superfície de conversa da PlataFirma

- **O que é:** a quarta superfície de acesso aos atores da casa, em `chat.platafirma.org` (Element/Matrix). Uma sala direta por ator, com o dono.
- **Onde roda:** contêineres `chat-synapse` (8008/8448), `chat-recepcao` (8080), `chat-pg`, no daemon rootless da conta `claudinho`. Tunnel Cloudflare entra direto no `chat-synapse`; auth por OIDC/realm; Admin API fechada na borda.
- **Componentes:** `recepcao/` (o Application Service, único que fala Matrix) → `comum/journal.py` (fila por sala) → `worker/worker.py` (host, systemd --user) → `bin/chat` (o verbo, que gira o motor). Contrato entre worker e verbo: uma linha JSON no stdout, uma por passo no stderr.

## Modelo de ator

Três eixos independentes, resolvidos só por `comum/cadeiras.py`. Nenhum se calcula dos outros.

- **conta** — o usuário do SO onde o ator roda. É o perímetro de segregação.
- **provider** — a entidade por trás da conta, e o nome afetivo do ator: `claudinho` é o Claude, `jaiminho` é o Antigravity. É o que aparece na sala e o que o MXID carrega.
- **persona** — o que `monta-sessao` injeta na abertura, de `abertura/<persona>/persona.md`.

O roster da superfície (`atores()`) tem três baldes, e a rota de motor sai do balde:

| balde | fonte | motor | exemplo |
|---|---|---|---|
| cadeira | ledger de vínculo (`registro/eventos-org.jsonl`) | Claude Code no cwd da fita | TI, dados, produto |
| ator interno | `_ATORES_INTERNOS` em `cadeiras.py` | Claude Code no cwd da fita | fabrica |
| participante | `_SAO_PARTICIPANTE` em `cadeiras.py` | verbo próprio do motor externo | jaiminho (agy) |

`eh_participante(ator)` decide a rota em `bin/chat`: verdadeiro gira pelo verbo do participante; falso gira por Claude Code. Cadeira e ator interno compartilham motor e caminho; separam-se em que a cadeira tem vínculo no org (voto, remit, roteamento) e o ator interno não.

## A fábrica no chat

A `fabrica` é uma persona fungível — roteador de linha (devops/blueteam/front-end) que recebe card e entrega código. Encarna uma vez por conta/provider, e todas as encarnações montam a mesma `abertura/fabrica/persona.md`.

- **Encarnação `claude`, conta `claudinho`:** o ator interno `fabrica` (`_ATORES_INTERNOS`), sala `@_pf_fabrica`, gira por Claude Code. Serve pedido de qualquer origem, na conta do stack. Wiring em `9a79a8b`.
- **Encarnação `agy`, conta `jaiminho`:** o participante `jaiminho-fabrica`, sala `@_pf_jaiminho-fabrica`, gira pelo `bin/jaiminho-fabrica`, na conta isolada uid 1003. A mesma persona, outro provider, outra conta, outro perímetro.

O ator interno não entra em `cadeiras()` do org: a fábrica não tem head, não vota, não roteia. `slug_da_cadeira('fabrica')` devolve a persona homônima, que é a chave de mesa, fila e Project — sem prefixo `claudinho-`, porque fábrica é persona, não vínculo.

## Fluxo de abertura de um giro

1. A recepção recebe a mensagem na sala, aprende de quem é a sala por `eh_de_ator`, e enfileira o job no journal daquela sala.
2. O worker (host) reivindica o job — um em curso por sala, paralelismo entre salas — e chama `bin/chat despachar --cadeira <ator> --fita <id-ou-vazio>`, com o corpo no stdin.
3. `bin/chat` ramifica por `eh_participante`. No ramo Claude Code:
   - **fita nova** (`--fita ""`) → `monta-sessao <persona>` roda, e o pacote de abertura entra por `--append-system-prompt`, na mesma invocação. Uma chamada.
   - **fita existente** → `--resume <id>`, sem reinjetar o pacote (já está na fita).
4. O motor gira no cwd `~/AI/fitas/<persona>`, emite um evento por passo (o worker observa por watchdog de silêncio), e devolve uma linha JSON de resultado.
5. A recepção posta a resposta na sala.

O pacote de `monta-sessao` não se replica no `CLAUDE.md` do cwd: fonte única, senão duas personas divergem no dia em que uma não for regenerada.

## Provisionar um ator novo na superfície

`./provisiona-cadeiras.sh @<dono>:<dominio>` — cria usuário no namespace da recepção, põe displayname e avatar, e abre a sala direta com o dono. Idempotente: rodar de novo não recria nada que já esteja no estado desejado.

- Quem entra é `atores()` (cadeiras + participantes + atores internos), lido do harness. Ator novo com persona entra sozinho; sem lista de exceção neste script.
- Displayname vem do alias do ledger; ator sem alias sobe pelo próprio sufixo, e o alias entra numa corrida posterior. Displayname é reversível, MXID não.

## Autenticar o Claude Code da conta sem terminal local

O motor Claude Code exige login OAuth na conta `claudinho`. Quando expira, o giro volta com `OAuth session expired`. O login é interativo (imprime URL, espera o código colado), e se conduz remotamente por um driver pty: sobe `claude auth login` num processo destacado, captura a URL de autorização num arquivo, e injeta no stdin o código que o dono cola de volta. O dono abre a URL no navegador dele, autoriza pela conta do stack, e devolve o código — sem precisar de terminal na máquina. O login `claude.ai` renova sozinho depois disso.

O trust do cwd da fita é pré-requisito à parte: `projects["<cwd>"].hasTrustDialogAccepted: true` em `~/.claude.json`, senão o motor ignora a allowlist do `.claude/settings.json` da fita.
