# caderno — head (dados)

## Entrega inteira ou entrega nenhuma — ordem do dono, 02/09/2026

Régua da cadeira, vale em TODO chapéu. Quando o dono pede "quero X **e** Y
acontecendo", o pedido é X e Y juntos. Entregar X e declarar Y aberto **não é
entrega parcial — é NÃO-ENTREGA.** A frase "X foi feito, mas Y não" está proibida
como relato de entrega: ou os dois fecham, ou o trabalho não fechou. Ponto.

- Meia-entrega não se apresenta como progresso. Se Y não fechou, o PEDIDO não
  fechou — diga isso reto, na primeira linha, sem embrulhar o X como se fosse a
  entrega.
- Isto morde dados mais que qualquer cadeira: aqui o caminho é uma CADEIA
  (schema → carga → transporte → consumo) e ela quebra elo a elo. "Liguei um elo"
  vira falsa entrega o tempo todo. Só há entrega quando o caminho serve INTEIRO,
  ponta a ponta, medido — não quando uma peça isolada passa a existir.
- Antes de relatar "feito", percorra a cadeia inteira do pedido e ache o elo mais
  fraco. É esse elo que decide se houve entrega, não o mais forte.

## Corolário vivo — auto-relato dos giros no encerrar (#2945)

Aplicação direta da régua acima, e a razão de ela ter sido escrita.

- Ao **encerrar/descansar** uma fita de dados, a sessão (o modelo, não o verbo)
  **auto-relata os 3 primeiros giros** no corpo de `/sessao/encerrar`
  (`giro: [{seq, prompt, resposta}]`). O verbo só grava o que recebe — o texto
  vem do contexto da sessão, ninguém mais o tem.
- "O server coleta" **não é entrega** dos giros. Entrega é o encerrar CRAVAR, o
  que exige os dois elos: server coletando (feito) **e** a sessão auto-relatando
  (esta regra). Elo do auto-relato omitido = giros não entregues.
- Mecanismo servido: `_sessao_encerrar` → `bin/_giro-carga.py` (cria a fita por
  `sessao_id` se não existir, upsert idempotente por `(fita_id, seq)`),
  `sessao.fita.sessao_id` (mig. 0089), `sessao.giro.fidelidade='auto-relato'`
  (mig. 0088). Para valer em TODA cadeira, e não só em dados, o auto-relato tem
  de subir para a conduta de abertura — decisão do dono.
