# caderno de portfolio — claudinha-gestao-estrategica

Duravel: o que continua verdadeiro depois que o assunto morre, e que a proxima
fita pagaria para re-derivar. Fato de negocio vai para card, commit ou wiki.

## Quebra de card (ordem do dono, 14/08/2026)

- Card por ENTREGAVEL, nunca por criterio de aceite.
- FUNDE quando e o mesmo caminho tecnico E o mesmo dono de ponta a ponta.
- NAO FUNDE quando o card e gate de outro e tem dono sozinho: fundido, some o
  marco "esta no ar" e o card so fecha quando o dono mais lento terminar. Card
  que compra sequenciamento visivel se paga.
- Criterio que e fronteira, ou decisao ja tomada, vira ACEITE — nao vira card.
- Dezenove criterios num card so e o que faz o dono nao conseguir ler a board.

## Espelho atrasa; canonico decide

- `skills/` e `dist/` sao copia. `docs/org-regras.md` e `personas/` sao fonte.
  Ordem sobre persona — baixa, troca, remit — se confere no canonico ANTES de
  agir pelo que a skill afirma.
- Medido em 16/08/2026, e caro: a skill `platafirma` dizia que a
  `claudinha-osint` "nao tem caixa na fila". Ela estava desligada desde 15/08
  (org:0002) e o Jaiminho, que ocupou o lugar, tem `caixa:jaiminho` exclusiva
  com claudinho-IA. Li os dois como colaboracoes externas distintas e quase
  despachei o corte do canal vivo.
- Metodo que fica: texto morto que descreve o presente nao e sujeira cosmetica,
  e premissa de decisao. Dando baixa em persona, o MESMO giro varre quem a
  descreve no presente — e o que nao for meu sai por mensagem no mesmo giro.

## Opção se avalia por capacidade construída, não por conflito resolvido

Quatro desenhos para a mesma disputa de fronteira (minuta arbitrada, sign-off mútuo,
chapéu cross, arbitragem do dono). O que ordena não é qual encerra a briga: é o que cada
um constrói de capacidade permanente e o que consome do recurso escasso. Aqui o escasso
não é competência — as cadeiras são a mesma cabeça — e sim a atenção do dono e o contexto
que cabe na janela de quem responde.

Consequências que sobreviveram ao debate:
- Regime que obriga duas cadeiras a assinar o mesmo trabalho as obriga a carregar o mesmo
  contexto. O custo não é tempo, é janela.
- Mecanismo de coordenação com prazo declarado é sensor; sem prazo de saída, vira regime.
- Teste de parada antes de arbitrar: zona que não gerou trabalho conjunto no período não
  era fronteira disputada, era vácuo — e vácuo se apaga, não se arbitra.

## Como apresentar card ao dono (convencao com o dono, 18/08/2026)

SEMPRE em arvore ASCII, uma linha por card: `numero - short-title`.
Nao e o titulo do rastreador: e um apelido de 2 a 5 palavras que o dono
reconheca de relance. Titulo longo serve ao card; short-title serve a conversa.

    #296 - rastreador serve ao dono
    |-- #287 - maquina de estados
    |   |-- #347 - verbo de sign-off
    |   `-- #356 - matar refinada
    `-- #351 - prova nao escreve em producao

Regras que a arvore carrega sem dizer:
- so galho aberto. Card em terminal nao entra, salvo quando o assunto E ele.
- cadeira entre colchetes quando a arvore mistura donos; sem colchete quando o
  recorte ja e de uma cadeira so.
- pai sem filho aberto aparece como folha: e informacao, nao lacuna.

O ganho: o dono trabalha em epico e feature, e a arvore mostra a granularidade
dele com a filha embaixo sem custo de leitura. Tabela nao mostra profundidade;
lista corrida perde a hierarquia; a arvore da as duas de graca.

## O que a cadeira afirma se confere na fonte, antes de virar ato meu

Medido caro em 20/08/2026, na fita do acervo cego. Tres afirmacoes de cadeira,
todas de boa-fe, todas erradas no ponto que decidia:

- FASE FECHADA. O IA reportou F1 e F2 fechados e o dono deu a fita por resolvida.
  No board, os nove cards estavam em `em-homologacao` e o derivado das duas features
  tambem. Entregue e um estado, nao um adjetivo: se confere em
  `estado_derivado` do PAI, nao no cru e nao na carta.
- CAUSA DO DEFEITO. Tres cartas atribuiram a cegueira da fabrica ao indice ancorado
  em impressao aposentada. Era verdade e nao era a causa: o que zerava tudo era um
  filtro carimbado em codigo. Quando duas superficies divergem, reproduzir a MESMA
  consulta nas duas mudando UM argumento vale mais que qualquer diagnostico — aqui,
  3 fontes contra zero, em 30 segundos.
- FUNDAMENTO DA DECISAO. O codigo citava uma decisao de seguranca ao lado da linha,
  como se a implementasse. A decisao mandava NEGAR uma colecao; a linha PERMITIA so
  uma. Negativa e allowlist parecem a mesma frase e tem efeito oposto quando o
  universo cresce. Numero de decisao citado em comentario de codigo nao e prova de
  que o codigo a segue: ler a decisao.

O que estas tres tem em comum e o que fica: a cadeira relata o que ela mediu, e o que
ela mediu depende da porta que ela usa. O meu ato pede a fonte, nao o relato.
