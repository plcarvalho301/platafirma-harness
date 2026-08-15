# caderno — claudinho-TI · construção e fábrica

O que este chapéu aprendeu e vale além de um expediente. Fato de negócio não mora
aqui: desce a card, commit ou wiki. Corpo lido sob demanda (`mesa caderno construcao`).

## Custo por giro é medível fora do harness do Claude (medido 14/08)

O `result` do `claude -p --output-format stream-json` traz `total_cost_usd`,
`usage` (input, output, cache criado, cache lido) e `is_error` por giro, sem
instrumentação nossa. O `rate_limit_event` traz `resetsAt`.

- **O custo não é novo — a visibilidade é.** Toda fita já paga a abertura de
  contexto hoje, em toda cadeira; dentro do harness do Claude ela some na
  assinatura. Comparar contra zero é o erro.
- **A chave de junção é a sala como fita** (`uuid5(room_id)`): é o que liga custo
  a cadeira, a chapéu e a card. Sem ela, o número existe e não agrega.
- **Onde vale mais do que aqui dentro:** no que NÃO é cadeira nossa — Jaiminho e
  qualquer harness entregue a terceiro. Medição por giro transforma "confia" em
  fatura, e é requisito de venda antes de ser conforto operacional.

## Cliente Matrix: Classic, não X (medido 14/08)

O Synapse autentica pelo `oidc_providers` embutido, que é o SSO **legado**
(`m.login.sso`). Element X só faz SSO contra Matrix Authentication Service (MAS) e
não há plano de suportar servidor sem MAS — abre e não deixa entrar. Element
Classic (o ex-Element Android) fala `m.login.sso` e é o cliente da instância.

- **Consequência de desenho:** pôr MAS na frente do Synapse é o que destrava o
  cliente que a Element trata como principal. Decisão de claudinho-seguranca
  (identidade), não minha — eu implemento.
- **Prazo alheio que corre sozinho:** o Classic avisa que a partir de out/2026
  dispositivo não verificado para de enviar e receber. E2EE é v1 na minuta 0002,
  sem data. Não é dívida técnica: é relógio de terceiro sobre o nosso escopo.
- **Localpart é irreversível.** O MXID copia o `preferred_username` do realm e vai
  assado em todo evento. Username feio no IdP vira identidade permanente no chat:
  conferir o realm ANTES do primeiro login, não depois.

## O precedente de tela da casa tem fronteira (medido 15/08, no F9)

A plataforma tinha um padrão só de tela — server-rendered em starlette, sem
framework, sem build, sem JavaScript (`harness-controle`, `acervo-api/tela.html`).
Tratei como regra geral e não é: é o padrão de UMA classe de tela.

- **A fronteira:** tela de leitura e de operação pontual (POST-redirect-GET, meta
  refresh) fica no padrão da casa. Tela de trabalho — edição concorrente, seleção
  em lote, resultado visível antes da confirmação do servidor, erro no item e não
  na página — exige estado local no cliente e reconciliação, e o padrão da casa
  não alcança.
- **Precedente da casa não vence régua posterior.** No F9 o padrão sem JS
  reproduziria exatamente o defeito que reprovou o Redmine na seleção. Quando o
  precedente é anterior ao requisito, ele é insumo, não veredito.
## Fita própria contra fita própria, mesma árvore (medido 15/08, verbo `minuta`)

A regra de worktree por fatia (`fabrica.md`, `ti/fluxo-worktree-por-fatia`) cobre
fita de fábrica contra cadeira — não cobre fita minha contra fita minha. Duas
sessões minhas (host/CLI e sala do chat) escreveram no mesmo `platafirma-harness`
ao mesmo tempo, sem coordenação. Não deu conflito porque o commit de uma fechou
antes de a outra tocar os mesmos arquivos — timing, não desenho.

Antes de editar arquivo compartilhado numa fita: `git log -3` e olhar o
timestamp do topo. Commit com poucos minutos de idade é sinal de outra sessão
viva na mesma árvore, não histórico frio.

## Card para a fábrica: fronteira sim, passo a passo não (medido 15/08, F10)

Régua do dono: dizer a ordem interna entre cards quebra a execução, porque o
orquestrador multiagente do Code fatia melhor do que o card fatia. O que o card
deve carregar é o que a fábrica NÃO pode descobrir sozinha:

- **Dependência real entre cards**, e só ela — o que não pode começar antes do
  quê. Paralelismo interno, ordem de ataque e uso de subagente são dela.
- **Fronteira que não se atravessa**: worktree por card, `git add <caminho>`,
  nenhuma edição de arquivo de outra fatia, push da branch e para.
- **Documento superado nomeado pelo nome.** Card que aponta canônico novo sem
  dizer qual documento morreu deixa a fábrica construir contra o morto — ele
  continua no repo e lê bem.
- **O que fazer quando a decisão faltar**: parar e perguntar ao dono, nunca
  improvisar substituto. Vale sobretudo para "o componente que o card pede só
  existe na versão paga".
- **Prova de aceite colada em comentário**, com o SHA da branch. Card sem a saída
  da régua colada é card não entregue.

## `tarefas sub` é composição, não dependência (medido 15/08)

`tarefas sub <pai> <filho>` cria relação `parenttask`/`subtask`. Usá-la para dizer
"A precisa fechar antes de B" mente sobre a estrutura do trabalho e engana quem lê
o board. Dependência se declara pela escotilha:

```
echo '{"other_task_id":<B>,"relation_kind":"precedes"}' | tarefas api-corpo PUT /tasks/<A>/relations
tarefas api DELETE /tasks/<B>/relations/parenttask/<A>     # desfaz o sub errado
```

A relação inversa (`follows`) aparece sozinha no outro card; não se cria duas
vezes.

## O audit do ops diz O QUE rodou, nunca QUEM rodou (medido 15/08)

`~/AI/var/log/ops/ops-AAAA-MM-DD.jsonl` grava todo `run_command` com o comando
inteiro — é a melhor fonte para reconstruir o que aconteceu no host. Mas o campo
`sessao` **não identifica a fita**: é a conexão do conector, e conversas
diferentes do mesmo cliente saem com o mesmo id. Medido: minha fita e outra
apareceram ambas como `s7675515b1c40`, intercaladas no mesmo segundo. `sujeito`
também não separa — é sempre o token do dono.

Consequência prática: dá para afirmar *que existe outro agente ativo* (comando
que eu não emiti, no meu id de sessão) e **não** dá para dizer *qual cadeira é*.
Atribuir cadeira a partir daí é chute, e custa a sessão inteira quando erra.
Card 457 nomeia o defeito; enquanto ele não fechar, a leitura correta é essa.

## Diretório de trabalho descartável vai em `~/AI/var/`, nunca em `/tmp` (medido 15/08)

`/tmp` é terreno comum entre agentes que rodam com o mesmo uid. Dois agentes
convergem no mesmo `/tmp/<slug>` porque o slug sai do nome do card, que os dois
leram. Rodei `rm -rf` num caminho que outro já usava e apaguei o trabalho dele.
Não há lock e não há aviso. `~/AI/var/<algo-meu>` resolve, e foi para lá que o
outro agente se mudou sozinho depois do estrago.

## O canal engole a chamada, e o comando roda assim mesmo (medido 15/08, duas vezes)

`run_command` que volta ao claude.ai como "Error occurred during tool execution"
**executou no host**. O erro é do canal, não do comando: a resposta não chega, e a
sessão também não guarda memória de ter feito a chamada — o efeito é indistinguível
de nunca ter mandado nada.

Medido: às 18:46:11 despachei `git commit -q -F -` com a mensagem inteira do card 464.
O canal não devolveu. Trinta segundos depois eu li o tree, achei um commit meu com os
meus dez arquivos e a mensagem certa, **não me reconheci nele**, e escrevi ao dono que
havia "um ator não identificado commitando neste tree". O ator era eu. Ele já tinha
dito que o gargalo existia, e eu tinha pedido evidência em vez de procurar a minha.

REGRA, e ela é barata: canal que devolve erro de execução → antes de qualquer teoria,
`~/AI/var/log/ops/ops-AAAA-MM-DD.jsonl` e `git reflog`. O audit grava toda chamada com
o comando inteiro, e resolve em dez segundos o que eu tratei como mistério. Vale
especialmente para comando com efeito colateral (commit, push, deploy, docker): supor
que não rodou é o caminho para rodar duas vezes.

E o par disto já estava neste caderno, escrito 2h antes: "o audit diz O QUE rodou,
nunca QUEM rodou". Faltava a metade que me mordeu — quando o QUEM não aparece, o
primeiro candidato sou eu.
