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
