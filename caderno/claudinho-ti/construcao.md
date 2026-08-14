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
