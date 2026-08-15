# caderno — claudinho-TI · construção e fábrica

O que este chapéu aprendeu e vale além de um expediente. Fato de negócio não mora
aqui: desce a card, commit ou wiki. Corpo lido sob demanda (`mesa caderno construcao`).

## Fora do board por ordem do dono

### Evento de deploy no rastreador (ex-card 450, fechado em 14/08)
- **O que é:** o pipeline empurra o deploy para a porta de ingestão do rastreador
  como fato carimbado — sha, ambiente, timestamp, resultado —, sem ninguém digitar.
- **Dono:** claudinho-TI sozinho. O empurrão sai do verbo `deploy`, não do rastreador.
- **Aceite:** deploy registrado como fato: sem estado, sem dono e sem board.
- **Bloqueado por:** a porta de ingestão não tem card. Declarada no PRD do
  rastreador, seção 5.1 (linha 257), como capacidade do v1.
- **Custo de não existir:** o rastreador entrega 2 das 4 do DORA. Frequência de
  deploy e lead time de mudança dependem deste elo; taxa de falha e tempo de
  restauração dependem do campo de mudança causadora apontar para o deploy.
- **Gatilho de reabertura:** aberto o card da porta de ingestão, este volta como
  subtarefa dele (`tarefas sub`).

## Custo por giro é medível fora do harness do Claude (medido 14/08)

O `result` do `claude -p --output-format stream-json` traz `total_cost_usd`,
`usage` (input, output, cache criado, cache lido) e `is_error` por giro, sem
instrumentação nossa. O `rate_limit_event` traz `resetsAt`.

- **O custo não é novo — a visibilidade é.** Toda fita já paga a abertura de
  contexto hoje, em toda cadeira; dentro do harness do Claude ela some na
  assinatura. Comparar contra zero é o erro (cometido nesta sessão, corrigido
  pelo dono).
- **Ganchos que isto abre**, sendo a sala a fita (`uuid5(room_id)`):
  - custo por sala → por cadeira e por chapéu;
  - custo por card, se a sala carregar o `#N`;
  - contexto inútil de `monta_sessao` ganha preço em número, não em opinião;
  - quantos giros cabem no que sobrou da janela (`resetsAt` + custo por giro).
- **Onde isto vale mais do que aqui dentro:** no que NÃO é cadeira nossa — o
  Jaiminho e qualquer harness entregue a terceiro. Medição por giro é o que
  transforma "confia" em fatura, e é requisito de venda antes de ser conforto
  operacional.
- **Não é card.** Sai de graça do card 448, que já consome o `result` inteiro.

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
- **Import map matou o reflexo "biblioteca = build".** Navegador resolve
  especificador nu desde que o import map esteja na página; biblioteca de
  componentes vendorizada roda sem bundler. A documentação de fornecedor costuma
  estar atrasada nisso — o quick start do `@material/web` ainda diz que exige
  ferramenta, e o exemplo dele mesmo é buildless. Conferir contra o navegador,
  não contra o README.
- **Adotar render layer é a decisão barata; adotar biblioteca de componentes é a
  cara.** A primeira fica contida numa camada e a saída custa reescrever render. A
  segunda arrasta o design system inteiro do fornecedor — forma, elevação,
  movimento, densidade — e aí a decisão deixa de ser minha e vira de produto.

## Fita própria contra fita própria, mesma árvore (medido 15/08, verbo `minuta`)

A regra de worktree por fatia (`fabrica.md`, `ti/fluxo-worktree-por-fatia`) cobre
fita de fábrica contra cadeira — não cobre fita minha contra fita minha. Duas
sessões minhas (host/CLI e sala do chat) escreveram no mesmo `platafirma-harness`
ao mesmo tempo, sem coordenação. Não deu conflito porque o commit de uma fechou
antes de a outra tocar os mesmos arquivos — timing, não desenho.

Antes de editar arquivo compartilhado numa fita: `git log -3` e olhar o
timestamp do topo. Commit com poucos minutos de idade é sinal de outra sessão
viva na mesma árvore, não histórico frio.
