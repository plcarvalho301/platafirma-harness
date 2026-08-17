# caderno — claudinho-TI · construção e fábrica

O que este chapéu aprendeu e vale além de um expediente. Fato de negócio não mora
aqui: desce a card, commit ou wiki. Corpo lido sob demanda (`mesa caderno construcao`).

## Entrega de tela se aceita USANDO, não medindo (medido 16/08, custou a onda 2)

Mergeei quatro fatias da onda 2 do rastreador, rodei seis suítes de aceite — todas verdes
—, migrei o banco e promovi. O dono abriu no celular e em um minuto achou três defeitos,
dois bloqueantes: a vista board (a PADRÃO do produto, PRD §6.2) não existia, e clicar no
título editava o título em vez de abrir o item, deixando o corpo do card inalcançável.

- **Prova verde mede o que o card pediu; uso mede o que o produto é.** Antes de aceitar
  tela, EXECUTE a tarefa do usuário no aparelho dele — abrir a lista, achar um card, ler o
  texto —, não só rode a suíte e leia o diff.
- **Card de tela se recorta contra as três fontes** (PRD, navegação, affordance). Recortei
  o #468 só contra a de navegação, e a vista padrão do produto nunca entrou em card nenhum.
  A fábrica entregou o card que recebeu; a lacuna foi do despacho.
- **Defeito de layout que esconde o único caminho para o conteúdo é bloqueante**, não
  cosmético: o estouro de largura em 360px era o que escondia o verbo `abrir`.

## Merge de fatias paralelas: o self-check não enxerga SQL (medido 16/08)

Quatro fatias tocaram os mesmos três arquivos. Resolvendo conflito, uni os dois lados
dentro de uma string de SQL — e ficaram DUAS consultas na mesma constante. `python3
api/logica.py` passou (string válida é Python válido) e o Postgres recusou em runtime: 44
provas caindo em `502 falha interna (SyntaxError)`.

- **Conflito dentro de literal (SQL, HTML, template) não se resolve por união mecânica.**
  Fora do literal, colar os dois lados costuma valer; dentro dele, o texto tem gramática
  própria que nenhum self-check de módulo puro lê.
- **Depois de qualquer resolução, bancada de pé e as suítes das fatias VIZINHAS**, não só
  a da fatia que acabou de entrar. Foi a suíte do #466, alheia ao meu conflito, que
  acusou.
- **Bancada usa TAG DE IMAGEM própria.** A `:local` é compartilhada com a stack viva:
  `docker compose build` numa bancada reescreve a imagem que produção sobe no próximo
  `up -d`.
- **Suíte do rastreador ESCREVE.** Rodada contra a instância viva, criou 31 itens e 70
  transições no acervo real. A trilha é append-only por trigger — desfazer exige derrubar
  a trigger DENTRO da transação e reerguê-la antes do commit.

## Card para a fábrica: fronteira sim, passo a passo não (medido 15/08, F10)

Régua do dono: dizer a ordem interna entre cards quebra a execução — o orquestrador
multiagente do Code fatia melhor do que o card fatia. O card carrega o que a fábrica NÃO
pode descobrir sozinha: **dependência real entre cards** e só ela; **fronteira que não se
atravessa** (worktree por card, `git add <caminho>`, nada de arquivo de outra fatia, push e
para); **documento superado nomeado pelo nome**, porque o morto continua no repo e lê bem;
**parar e perguntar quando a decisão faltar**, nunca improvisar substituto; e **prova de
aceite colada em comentário, com o SHA da branch** — sem isso, card não entregue.

**Card escrito e não despachado é papel.** Achado de uso vira card E despacho no mesmo
giro; parar no card, no fim do ciclo, é burocracia com aparência de método.

## O precedente de tela da casa tem fronteira (medido 15/08, no F9)

A casa tinha um padrão só de tela — server-rendered em starlette, sem framework, sem
build, sem JS. É o padrão de UMA classe de tela, não regra geral.

- Tela de leitura e operação pontual fica no padrão da casa. Tela de trabalho — edição
  concorrente, lote, resultado antes da confirmação, erro no item — exige estado local e
  reconciliação, e o padrão não alcança.
- **Precedente anterior ao requisito é insumo, não veredito.**

## Instrumento mede o PRODUTOR, nunca a instância viva (medido 16/08, custou a sessão)

`conferir superficie` julgava as superfícies lendo os `.mcp.json` dos cwd vivos. O arquivo
é rastreado no repo: o gate lia N cópias do mesmo arquivo e chamava aquilo de medição. Ao
limpar as worktrees, o veredito virou sozinho e passou a reprovar commit de toda cadeira.

**Antes de escrever a medição, pergunte quem PRODUZ o que você vai medir.** Se a resposta
for "o próprio disco", o instrumento reporta arqueologia. Não havendo produtor, ISSO é o
achado — declarar a ausência vale mais que medir a sobra. Forma que ficou: cada superfície
declara `produtor` em `superficies.json`; instância viva vira observação de deriva e não
muda veredito.

E o par: **quem mede tem de perguntar com a chave que o verbo usa.** `conferir sessao`
dava "não medida" porque perguntava `TI` onde `fila` exige `claudinho-TI`. Instrumento e
coisa medida resolvem a chave pela MESMA fonte.

## O canal engole a chamada, e o comando roda assim mesmo (medido 15/08, duas vezes)

`run_command` que volta como "Error occurred during tool execution" **executou no host**: o
erro é do canal, a resposta não chega e a sessão não guarda memória da chamada. Cheguei a
acusar "ator não identificado commitando neste tree"; o ator era eu.

REGRA: erro de execução do canal → antes de qualquer teoria,
`~/AI/var/log/ops/ops-AAAA-MM-DD.jsonl` e `git reflog`. Vale sobretudo para comando com
efeito colateral, onde supor que não rodou leva a rodar duas vezes.

E a metade que faltava: **o audit diz O QUE rodou, nunca QUEM rodou** — `sessao` é a conexão
do conector, não a fita, e `sujeito` é sempre o token do dono. Quando o QUEM não aparece, o
primeiro candidato sou eu.

## Duas fitas minhas na mesma árvore não têm regra (medido 15/08)

A regra de worktree por fatia cobre fábrica contra cadeira, não fita minha contra fita
minha. Antes de editar arquivo compartilhado: `git log -3` e olhar o timestamp do topo.
Commit com poucos minutos de idade é outra sessão viva, não histórico frio.

## Diretório descartável vai em `~/AI/var/`, nunca em `/tmp` (medido 15/08)

`/tmp` é terreno comum entre agentes com o mesmo uid, e o slug converge porque sai do nome
do card que os dois leram. Rodei `rm -rf` num caminho que outro usava e apaguei o trabalho
dele. Não há lock e não há aviso.

## `tarefas sub` é composição, não dependência (medido 15/08)

`sub` cria `parenttask`/`subtask`. Usá-la para dizer "A fecha antes de B" mente sobre a
estrutura e engana quem lê o board. Dependência é pela escotilha:

```
echo '{"other_task_id":<B>,"relation_kind":"precedes"}' | tarefas api-corpo PUT /tasks/<A>/relations
tarefas api DELETE /tasks/<B>/relations/parenttask/<A>     # desfaz o sub errado
```
