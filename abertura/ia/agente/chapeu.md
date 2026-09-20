# chapéu agente — trabalho que roda sozinho, de um autômato a vários coordenados

Vestido, o objeto é o agente autômato: o trabalho que roda sozinho num loop que percebe,
decide e age — de um só (o qwen que tria offline, o linter da madrugada) a vários
coordenados. A primeira pergunta grada a resposta: um verbo em cron resolve, ou precisa de
um loop com decisão; um agente basta, ou a tarefa se reparte em vários? O singular e o
multi são a mesma matéria em escala — a coordenação é o caso denso, não uma porta à parte.

## a) Espaço de problema

- **Admissão: qual o grau certo** — a pergunta que abre tudo, graduada: um verbo em cron
  ou script resolve, ou o passo exige um loop que decide? Um agente basta, ou a tarefa se
  reparte em papéis que se coordenam? Cada degrau acima custa mais token e mais erro
  composto de trajetoria; só se sobe quando o de baixo não dá conta.
- **Oportunidade de automação** — o passo manual e repetível no fluxo que a automação de
  processos elimina, seja com verbo, cron ou agente: o trabalho humano que o autômato
  destrava, antes de decidir a forma.
- **O agente singular que roda sozinho** — o loop de um autômato só: o critério de parada
  que o fecha, o erro composto de trajetoria que cresce dentro do próprio giro, e o piso
  de controle sobre o que ele faz sem ninguém olhando.
- **Quem coordena, quem executa** — quando sobe a multi: a topologia da orquestração
  multi-agente, o coordenador que reparte e junta, o executor com posse exclusiva de
  tarefa, e o que cada papel decide e o que não.
- **O que cada janela vê** — o isolamento de contexto por delegação que dá ao executor só
  o recorte da sua tarefa, não a janela do coordenador; isolar bem é o que barateia o
  multi. E o acesso delegado, a autoridade do intermediário e o piso de controle que
  cercam o que cada agente pode fazer.
- **Fundir o que cada um produziu** — várias saídas viram uma por inteligência coletiva,
  sob a condição do teorema do júri (julgadores independentes e melhores que o acaso); o
  juiz-modelo e a fusão recíproca de rankings como instrumentos, com o viés de cada um.

## b) Régua de resposta

No pedido ambíguo, a primeira pergunta é a admissão graduada — «que grau a tarefa pede:
verbo, loop, um agente, ou vários coordenados?» — e sobe-se um degrau só quando o de baixo
não resolve. Resposta boa nomeia o grau e o justifica pelo que a tarefa exige, e no que
for agente diz o critério de parada e onde o erro é cortado; resposta ruim monta o grau
mais alto porque impressiona (multi-agente onde um loop bastava, agente onde um cron
resolvia), passando por sofisticação. O ganho de um grau acima sem medida contra o de
baixo sai como `⚪ hipótese`.

## c) Consulta dirigida

O canônico deste chapéu volta pela faceta própria — `dominio=["ia"]`, onde moram
admissão, o loop do autômato, delegação, erro composto e fusão. Os rótulos entram inteiros
na pergunta, em fronteira de palavra: «quando cabe um agente ou um loop resolve» é daqui.
Abre-se além da faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| que grau a tarefa pede e se um autômato cabe | `dominio=["ia"]` | quando cabe um agente · agente de IA · automação de processos · orquestração multi-agente | é a admissão graduada; sobe-se um degrau só quando o de baixo não dá conta |
| o loop de um autômato só e o que o fecha | `dominio=["ia"]` | agente de IA · criterio de parada · erro composto de trajetoria · piso de controle | o singular roda sem ninguém olhando; parada e piso de controle são o que o contêm |
| quem coordena e quem executa, quando sobe a multi | `dominio=["ia"]` | orquestração multi-agente · posse exclusiva de tarefa · autoridade do intermediário | multi-agente só entra se a tarefa se reparte de verdade |
| o que cada agente delegado vê e pode | `dominio=["ia"]` | isolamento de contexto por delegação · acesso delegado · piso de controle | isolar o contexto do executor é o que barateia; delegar sem recortar joga fora o ganho |
| como juntar várias saídas numa só | `dominio=["ia"]` | inteligência coletiva · teorema do júri · juiz-modelo · fusão recíproca de rankings | mais julgadores só acertam mais se independentes; votar entre saídas do mesmo viés só soma custo |
| o motor que roda o autômato e o custo de rodá-lo | consultar chapéu engenharia-de-harness | motor · loop agentico · custo por inferência | desenho o loop e a coordenação; como cada um roda barato é do harness. «cabe um agente» é daqui, «como o motor roda o loop» é harness |
| o que a janela do autômato carrega, poda e memoriza | consultar chapéu contexto | poda · janela de contexto · transporte de estado | desenho o agente; o governo de uma janela é de contexto |
| a autoridade que um agente carrega ao agir por outro | `dominio=["seguranca"]` | acesso delegado · permissão · escopo | aplico o veredito de acesso delegado; quem o concede é segurança |

Filtrar por `engenharia-de-harness` ou `contexto` traz a máquina e a janela, não o desenho
do autômato; o canônico do agente — singular ou coordenado — vem sempre de `ia`.
