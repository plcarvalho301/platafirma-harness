# chapéu agente — várias janelas se coordenando

Vestido, o objeto é o que emerge de vários agentes coordenados: quem coordena e quem
executa, o que cada janela vê, e como o erro de um não se compõe pela cadeia. Antes de
tudo, a admissão — cabe um agente, ou um loop único resolve mais barato?

## a) Espaço de problema

- **Quando cabe um agente** — a pergunta de admissão que abre tudo: a tarefa se reparte
  em papéis que se coordenam, ou é loop único vestido de orquestração? Multi-agente é
  caro em token e em erro composto de trajetoria; só entra se a tarefa se reparte de
  verdade.
- **Quem coordena, quem executa** — a topologia da orquestração multi-agente: o
  coordenador que reparte e junta, o executor com posse exclusiva de tarefa que fecha sua
  parte, e o que cada papel decide e o que não.
- **O que cada janela vê** — o isolamento de contexto por delegação que dá ao executor só
  o recorte da sua tarefa, não a janela do coordenador; isolar bem é o que barateia o
  multi-agente. E o acesso delegado, a autoridade do intermediário e o piso de controle
  que cercam o que cada agente pode fazer.
- **Erro que se compõe pela cadeia** — o erro composto de trajetoria que entra no próximo
  agente e cresce, o critério de parada que fecha a coordenação antes que ela gire sem
  convergir, e a assimetria entre gerar e julgar que deixa um agente conferir outro barato.
- **Fundir o que cada um produziu** — várias saídas viram uma por inteligência coletiva,
  sob a condição do teorema do júri (julgadores independentes e melhores que o acaso); o
  juiz-modelo e a fusão recíproca de rankings como instrumentos, com o viés de cada um.
- **Oportunidade de automação** — antes de coordenar, o passo manual e repetível no fluxo
  que a automação de processos elimina: o trabalho humano que o agente ou o verbo destrava.

## b) Régua de resposta

No pedido ambíguo, a primeira pergunta é a admissão — «cabe um agente, ou um loop único
resolve mais barato?» — antes de desenhar qualquer topologia. Resposta boa começa pela
admissão e, havendo coordenação, diz quem coordena, quem executa, o que cada um vê e onde
o erro é cortado; resposta ruim monta orquestração porque impressiona, pula a admissão e
dá a cada agente a janela inteira, passando por sofisticação. O ganho de uma topologia
multi-agente sem medida contra o loop único sai como `⚪ hipótese`.

## c) Consulta dirigida

O canônico deste chapéu volta pela faceta própria — `dominio=["ia"]`, onde moram
admissão, delegação, erro composto e fusão. Os rótulos entram inteiros na pergunta, em
fronteira de palavra: «quando cabe um agente ou um loop resolve» é daqui. Abre-se além da
faceta assim:

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| se a tarefa se reparte e como coordenar | `dominio=["ia"]` | quando cabe um agente · orquestração multi-agente · agente de IA · posse exclusiva de tarefa | é a admissão e a topologia; multi-agente só entra se a tarefa se reparte de verdade |
| o que cada agente delegado vê e pode | `dominio=["ia"]` | isolamento de contexto por delegação · acesso delegado · autoridade do intermediário · piso de controle | isolar o contexto do executor é o que barateia; delegar sem recortar joga fora o ganho |
| onde o erro cresce e o que fecha a cadeia | `dominio=["ia"]` | erro composto de trajetoria · criterio de parada · assimetria entre gerar e julgar | o erro de um entra no próximo; julgar é mais barato que gerar, e serve para um conferir outro |
| como juntar várias saídas numa só | `dominio=["ia"]` | inteligência coletiva · teorema do júri · juiz-modelo · fusão recíproca de rankings | mais julgadores só acertam mais se independentes; votar entre saídas do mesmo viés só soma custo |
| o passo manual que a coordenação elimina | `dominio=["ia"]` | automação de processos | o alvo que justifica o agente; coordenar é automatizar trabalho hoje manual |
| o motor que roda cada agente e o custo de rodá-lo | consultar chapéu engenharia-de-harness | motor · loop agentico · custo por inferência | coordeno vários; como cada um roda barato é do harness. «cabe um agente» é daqui, «como o motor roda o loop» é harness |
| o que uma janela sozinha carrega, poda e memoriza | consultar chapéu contexto | poda · janela de contexto · transporte de estado | coordeno o que emerge de várias; o governo de uma janela é de contexto |
| a autoridade que um agente carrega ao agir por outro | `dominio=["seguranca"]` | acesso delegado · permissão · escopo | aplico o veredito de acesso delegado; quem o concede é segurança |

Filtrar por `engenharia-de-harness` ou `contexto` traz a máquina e a janela única, não a
coordenação; o canônico do que emerge de várias vem sempre de `ia`.
