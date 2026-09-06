# caderno — fabrica / devops

Durável: continua verdadeiro depois que o assunto morrer, e re-derivar custaria caro.

## Teste que nasce verde não prova nada até o mutante derrubá-lo

Teste escrito DEPOIS da correção nasce verde por construção: passa tanto com o furo
fechado quanto com ele aberto, se a asserção não morde o ponto exato. Entregar assim é
entregar a aparência da trava, e a regressão volta com a suíte inteira verde.

A régua: antes de abrir o MR, **reponha o furo** e rode. O teste novo tem de ficar
VERMELHO. Só então ele vale como trava. Reponha e restaure no mesmo giro, com backup do
arquivo — a janela em que a árvore está mutada é o único risco, e ela dura segundos.

Medido no #2945 (reancorar voto por `sessao_id`, 09/2026): 6 casos novos, todos verdes.
Repondo os dois furos — o fallback temporal cego e o `sessao_id` que não era repassado —
**5 dos 6 vermelharam**. O sexto era verde vazio e teria ido no MR como trava que não
trava. Sem o mutante, ninguém veria a diferença entre os dois grupos.

Corolário do mesmo princípio, e o caso que engana mais: **falha anterior se PROVA, não se
alega**. Suíte que já vem vermelha tenta o atalho "essas falhas não são minhas". A prova
é o contrafactual: `git stash` das mudanças, rodar em HEAD, ver as mesmas falhas com os
mesmos nomes, `git stash pop`. No #2945 eram 6 (`test_sidecar` 2, `test_carga_acervo` 2,
`test_nomes` 1, `test_planilha` 1) — e só depois de medidas em HEAD é que couberam no
corpo do MR como dívida de outra frente.

O que os dois casos têm em comum: um resultado de teste é uma afirmação sobre uma
DIFERENÇA (com o bug vs sem, com minha mudança vs sem), e diferença não se lê num estado
só. Rodar uma vez e reportar a cor é opinião; rodar os dois lados é medida.

## Apontamento de linha se declara no MR, não se resolve calado

Despacho de outra cadeira fecha o desenho, mas quem executa é quem encosta no código — e
às vezes a letra do desenho, aplicada ao pé, produz regressão que o desenho não pediu.
Quando isso aparece, não são dois caminhos (obedecer cegamente ou reabrir o desenho): é
um terceiro. Implemente a leitura que preserva o comportamento, **isole a decisão num
bloco próprio do corpo do MR**, com o motivo medido e o custo de reverter ("é uma linha").
A cadeira que desenhou decide na revisão, com o código na frente, em vez de decidir no
abstrato antes.

No #2945 a §2 mandava não descer ao fallback quando `sessao_id` não casasse. Ao pé da
letra, isso matava também a busca por `ordem_id` — porque a mesma mudança fazia `_votar`
herdar `PF_SESSAO`, e voto por `ordem_id` passaria a chegar com `sessao_id` preenchido sem
ninguém pedir. Cortar só o degrau CEGO e declarar o desvio custou um parágrafo; descobrir
a regressão depois do deploy teria custado o ciclo inteiro.

## Uma recusa se mede pelo efeito, não pela mensagem

Trava que imprime "recuso" e mesmo assim executa é pior que trava nenhuma: some do
radar por parecer ativa. Testar uma contenção é tentar violá-la e conferir que a AÇÃO
não aconteceu — não que a mensagem apareceu.

Duas formas do mesmo erro, medidas no #3004 (09/2026):

- **A recusa que morre no subshell.** Validação chamada dentro de `$(...)` que recusa por
  `exit` mata só o subshell. Sem `|| exit $?` no chamador, o "não" vira string vazia e o
  fluxo segue. O alvo recusado virou alvo VAZIO, e o runner rodou o repositório inteiro,
  com a mensagem de recusa impressa no stderr logo acima. Em bash, `[ -n "$x" ] && x="$(valida)"`
  também não serve: encadeado a `|| exit`, dispara quando a condição é falsa.
- **O gate vazio, que ninguém provou.** Uma flag de retenção ficou ligada meses porque
  não havia ninguém para reter — inofensiva por vacuidade. No dia em que o primeiro
  sujeito entrou na lista, ela serviu tudo. Gate sem sujeito não está provado: prova-se
  no ato de pôr o PRIMEIRO sob ele, conferindo que reteve.

Corolário: ao pôr o primeiro item sob um controle existente, a medição não é "o controle
existe" — é "o controle reteve ESTE item". São afirmações diferentes, e só a segunda é
observável.

## Suíte que não rodou não é suíte vermelha

Runner que monta ambiente isolado (`uvx pytest` e parentes) tira do projeto as próprias
dependências: a suíte morre no import, não no teste. A cor é vermelha e a causa é o
ambiente — reportar isso como falha do código manda a próxima fita caçar bug que não
existe.

Vale para todo instrumento de leitura, e a régua é a mesma do `situacao` (arq:0085):
fonte inalcançável responde INDETERMINÁVEL, nunca zero. Não-rodou, não-alcançou e
não-encontrou são estados distintos de falhou, e um verbo que os funde num só mente
barato. Quando o fallback isolado for o único caminho, ele sai avisado — a saída diz que
uma falha de import ali é do ambiente, não do código.

Medido no #3004: o mesmo alvo deu `No module named yaml` no ambiente isolado e 25 passed
com o interpretador do projeto. Nada no código mudou entre as duas execuções.

## Antes de abrir incidente, confira se o roadmap já condena aquilo

Serviço fora do ar nem sempre é incidente. Quando a feature em curso vai APOSENTAR aquele
componente, "está down" é o estado esperado, não um alarme — e tratá-lo como alarme gasta
a fita do dono, abre card que ninguém vai executar e enterra o achado que importava.

A pergunta antes de escalar não é "isto está quebrado?", é "alguém já decidiu que isto
morre?". Se sim, o achado vale como MEDIDA a favor da feature (o argumento dela, na
prática), e é assim que entra no card existente — não como incidente novo.

Medido no #3012 (09/2026): o braço da fábrica estava fora do ar havia dias, e a story em
curso era justamente aposentá-lo. O que era entrega — "o argumento da #3007, medido" —
subiu como alarme, e o dono teve de cortar.

## Checagem de lote/sessão não se prova por chamadas "paralelas" do cliente

Duas chamadas de tool emitidas no mesmo turno não chegam por garantia na mesma sessão de
transporte. Cada uma pode abrir conexão própria no servidor, e um mecanismo que agrupa
por sessão (`lote_id`/`lote_n`, por exemplo) fica cego para elas — não porque o
agrupamento esteja quebrado, mas porque a premissa "mesmo turno == mesmo canal" não vale
para todo cliente.

A régua: antes de reportar a checagem como falha do serviço, confirme que o CANAL usado
para testar de fato produz o que o mecanismo espera monitorar. Sem essa confirmação, o
resultado é INDETERMINÁVEL, não vermelho — mesma família do "suíte que não rodou não é
suíte vermelha" acima.

Medido na ordem-deploy economia-de-giro §3 (06/09/2026): duas chamadas `read_file` no
mesmo turno, pós-restart do `ops-mcp`, vieram com `lote_id`/`lote_n` null nas duas, cada
uma em `sessao` HTTP distinta no log. Ficou registrado como achado aberto, não como
regressão confirmada — o cliente (Code) pode nunca produzir lote literal em tool calls
"paralelas", e sem outro cliente para comparar a checagem não decide sozinha.

## Ordem de deploy que pede restart de serviço precisa se declarar como tal

Um agente de contexto fresco — sem a fita que escreveu a ordem, só o texto do runbook —
não sabe, só pela letra do passo, que reiniciar um serviço desta conta é trabalho de
devops rotineiro sobre infraestrutura própria. A régua de segurança do agente classifica
"reiniciar serviço" e "editar drop-in de systemd" como modificação de configuração de
sistema/segurança — categoria que trava mesmo com autorização explícita — porque essa é a
leitura correta por default quando não se sabe de quem é a infraestrutura. Sem uma linha
dizendo que o alvo é próprio da conta, o passo do restart tem chance real de ser
recusado, e a recusa se propaga: o rollback documentado na mesma ordem cai na mesma
categoria e também é recusado.

A régua: ordem de deploy que inclui restart de serviço ou edição de unit/drop-in nomeia,
na própria linha do passo, que o alvo é infraestrutura desta conta administrada por esta
cadeira — não configuração de sistema ou conta de terceiro. Custa uma linha; sem ela,
custa um ciclo inteiro de recusa, escalonamento e retomada manual.

Medido na ordem-deploy economia-de-giro (06/09/2026): um subagent de Workflow, com o
runbook completo no prompt mas sem o resto da fita, recusou o restart do `ops-mcp` E o
rollback documentado na mesma ordem, citando exatamente essa categoria — mesmo com o
passo anterior (env já editado e conferido por outra parte do processo) relatado como
concluído no próprio prompt. O restart só aconteceu depois de a cadeira que orquestrava
fazer a chamada direta, autorizada em chat pelo dono.
