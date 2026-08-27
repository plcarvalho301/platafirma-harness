# caderno de portfolio — gestao-estrategica

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
- Medido em 16/08/2026, e caro: uma skill descrevia uma colaboradora externa
  ja desligada (org:0002) como se ainda tivesse canal, enquanto quem ocupou o
  lugar tinha caixa propria. Li as duas como colaboracoes distintas e quase
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

## Janela de push direto no rewrite dos chapeus (ordem do dono, 23/08/2026)

- Enquanto durar o rewrite dos chapeus (F5), mudanca de ESTRUTURA de persona e de
  diretorio de chapeu vai direto a main, SEM nova aprovacao por item. Criar/renomear
  dir de chapeu, mexer em persona.md: push na hora, relato depois.
- Fora dessa janela, estrutura volta a exigir sign-off do dono (push do dono).
- Primeiro caso sob a regra: dir `abertura/dados/ontologia` criado e empurrado sem
  sign-off (commit 23/08). Fecha o pre-requisito que travava a sessao de chapeus de dados.

## O acervo espelha o org: domínio = cadeira, subdomínio = chapéu (medido 23/08)

Correspondência declarada pelo dono nesta fita, matéria de RH mas orienta todo
sequenciamento de chapéu:

- **Todo domínio do acervo ↔ uma head/cadeira.** O domínio da Olga (dados) é
  exatamente `estudos-ontologias`.
- **Subdomínio ↔ chapéu**, quando houver. Head pode não ter subdomínio.
- **Redistribuir subdomínios para casar com os chapéus é desejável, não
  obrigatório.** É norte, não pré-requisito. Não travar escrita de chapéu à espera
  da taxonomia fechar — foi o erro que o dono cortou ("pode e é desejável ≠ deve").

## Modelo novo de ferramental não tem json (medido 23/08)

- A fonte das ferramentas de **início de sessão** é o **ofício** (L1, chamada 1,
  dono TI). Ferramental de **chapéu** é o working set do especialista (L2, chamada
  2, instância da cadeira), e só entra o que tem recorte próprio — o que o ofício
  dá não se repete. Canônico: `AB - ferramental.md` §3; molde `P3b`.
- O **catálogo de ferramentas** é um `.md` GERADO (L3 espelho humano; L4 catálogo
  de existência, contadores), análogo ao `acervo listar conceitos`. NÃO é json.
- O montador lê o catálogo da árvore `abertura/**/*.md` (peças-arquivo) + lista
  embutida (peças-verbo). Não há json de peça no fluxo — o modelo é `.md`.

## Push a main nao e entregue: o clone de deploy roda separado (medido caro 24/08)

Custou tres turnos numa fita so, o mesmo erro tres vezes: tratei o deploy
(migration + rebuild de imagem) como passo de fabrica quando era ato meu de
entrega. Empurrar pra main fecha metade; a outra metade e por o codigo no ar,
e no ar ele nao chega sozinho.

Cadeia de armadilhas, na ordem em que morde:

- **Commit local nao e push.** `git commit` deixa o card `ahead 1` de origin. So
  o push bota em main. Trivial, mas foi o primeiro degrau.
- **Push a main nao e deploy.** O que a fabrica edita e o que o container roda
  sao clones DIFERENTES. `platafirma-rastreador`/`platafirma-ui` e a fonte;
  `deploy/rastreador` e `deploy/rastreador-tela` sao os clones que o compose
  builda — e ficam parados no commit velho, em HEAD destacado, ate alguem dar
  `pull`. Conferir em qual clone o container nasceu: `docker inspect <c>
  --format '{{index .Config.Labels "com.docker.compose.project.working_dir"}}'`.
- **Codigo novo no clone nao e imagem nova.** Sem bind mount do fonte (so
  `politica-acesso` e montado), o container serve o que esta na IMAGEM. Editar
  arquivo no host nao recarrega nada. Precisa `docker compose build` + `up -d`
  do diretorio do config_files (nao do repo raiz — o compose pode morar fundo,
  ex. `deploy/rastreador-tela/app/rastreador/`).
- **Migration em .sql nao e migration aplicada.** `sql/` monta em
  `/docker-entrypoint-initdb.d`, que o Postgres SO roda com volume de dados
  VAZIO (primeira criacao). Banco populado ignora o sql novo no up. O
  `ALTER TABLE ... DROP/ADD CONSTRAINT` tem de ir a mao:
  `docker exec -i <db> psql -U <u> -d <d> <<'SQL' ... SQL`.

Teste de pronto que fecha cada degrau, no AR e nao no relato:
- FK/schema: `SELECT confdeltype FROM pg_constraint WHERE conname='...'` (c=cascade).
- rota/codigo: bater o endpoint real pelo caminho que o cliente usa (o proxy,
  nao a porta interna via `docker exec` — o 404 que me assustou era artefato de
  bater direto na 8000, a rota estava registrada).
- comportamento: o caso de uso fim a fim (apagar card COM comentario), nao o
  unit verde. Suite unit passa testando logica Python isolada; nao ve banco nem
  container.

Regra que fica: **entrega de codigo de app e minha ate rodar no ar.** Deploy
(pull do clone de deploy + build + up + migration a mao) NAO e passo de fabrica
nem recado pro head de TI — e a segunda metade do mesmo ato que o push comecou.
"Entregue" so depois do teste de fumaca no ar passar.

Nota lateral, mesma fita: `tarefas comentar` cria comentario que, ate o cascade
subir, era vinculo indeletavel — nao usar comentario pra anotar card em
apuracao. Anotar por `PATCH descricao` (api-corpo), que nao cria entidade filha.

## Mapa F9 do board: o que a head pode e nao pode (fita 24/08)

Faxina de board de ponta a ponta (em-lapidacao 44->1, 8 feitos presos fechados,
34 orfaos alojados). O que a proxima faxina nao precisa re-derivar:

- **A head parqueia e agrupa a vontade, cross-cadeira.** `tarefas mover` dentro
  do funil e `tarefas sub <pai> <filho>` para alojar NAO sao F9-gated: rodam em
  card de qualquer cadeira (testado em seguranca, TI, IA). Sequenciar e
  organizar o funil e ato de portfolio, nao do dono do card.
- **O gate do chefe e EXCLUSIVAMENTE o aceite.** Mover e agrupar no funil qualquer
  um faz. O que e do dono do card e so o ACEITE — o carimbo que da o trabalho por bom
  e leva ao terminal (`entregue`). E na pratica esse aceite quase sempre acontece NO
  PROPRIO CHAT: o dono le o resultado, diz "entregue", e e isso que autoriza o estado
  terminal — o board so registra o que o chat ja decidiu. `fechar`, `descartar`,
  `englobar` em card alheio -> despacha por `fila enviar <persona> --tipo pedido`
  (tipos validos: decisao, demanda, handoff, minuta, pedido, resposta).
- **Dono do card != `.cadeira`.** O `.cadeira` e a materia; o F9 checa o
  ATRIBUIDO. Os cards do envelope F0-F5 tinham `.cadeira`=IA/TI mas eram meus; so
  fecharam com PF_CADEIRA=`claudinha-gestao-estrategica` (nome canonico, com
  prefixo), nao com o slug `gestao-estrategica`. Vale ate o #2431 passar.
- **Read-side atrasa; write-side e verdade.** `tarefas listar` (abertos),
  histograma e `fila status` servem espelho velho logo apos escrita (a contagem
  de abertos deu -1 depois de 7 fechados; a fila deu "vazia" depois de um enviar
  que devolveu id). Confere no `tarefas listar-tudo --json`, no cru do card, ou
  no id que o `enviar` devolve -- nunca no relatorio de abertos.
- **Criterio do parque:** em-lapidacao = "em pauta agora". Sem movimento ha ~5
  dias -> captada (reversivel, nao cancela nada); sozinho drenou o paredao. Feito
  preso (subarvore `derivado=entregue`, card ainda no funil) -> fecha como
  entregue, que e reconciliar o pai as filhas ja assinadas.

Regra que fica: **na board, a head move e agrupa; o dono fecha.** Meu corte e
proposta ate onde toca card alheio; o carimbo terminal e sempre do dono.


## O dono le o board; a divergencia que ele traz e ordem, nao ruido (ordem do dono, 26/08/2026)

- O que o dono diz no chat SEMPRE se sobrepoe ao board. Ele sabe ler. Se ele
  afirma algo que discorda do board, e porque DISCORDA do board — de proposito.
- Diante da divergencia, so ha dois atos meus: ACEITAR, ou VERIFICAR NO CODIGO /
  na fonte. Nunca "re-conferir no board" o que ele ja disse estar errado — o board
  e o read-side que atrasa; a palavra dele e write-side.
- Ele traz a divergencia porque precisa de ajuda pra tirar a duvida, verificar e
  corrigir o ESTADO REAL. Nao pra ser checado. Transformar isso em interrogatorio
  ("tem certeza?", "no board consta X") e encher o saco, nao cautela.
- Medido caro em 26/08/2026: ele disse "o proxy foi resolvido" e eu fui ao board
  "confirmar" em vez de ao nginx.conf. A fonte era o arquivo; o board nao decide nada.

## Nao promover fala de fita a regua, nem saida de ferramenta a canone (26/08/2026)

- Resposta do dono a uma pergunta minha DENTRO de um refinamento e fala de fita,
  nao regra da casa. Citar "mas voce disse X" como se fosse norma e promover
  conversa a canone — duplo erro quando o X nem era o que ele quis dizer.
- Mensagem de recusa de um CLI e o que aquele binario retornou AGORA, nao lei viva.
  O registro proibia transicao pra tras e NAO proibe mais; li a recusa como regua.
- Raiz comum dos dois: tratei saida de ferramenta (board, mensagem do CLI) como
  ancora canonica, e a fala do dono como subordinada a ela. E o inverso: a fonte
  canonica e codigo/decisao escrita; a fala do dono manda sobre o board.
- Corolario sobre "bug": bug e card como qualquer outro, sem fluxo especial. O que
  existe e TESTE TRAVADO comendo lead time — e isso se nomeia pelo teste travado,
  nao vira uma categoria "bug".
