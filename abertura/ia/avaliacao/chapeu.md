# chapéu avaliacao — o que o agente e o uso fizeram, medido

Vestido, o objeto é a medida do uso e do agente: o rastro de que tool foi chamada e que
gatilho disparou, o resultado da bateria, a mudança medida depois de mudar o texto. Gero
a avaliação a partir das categorias de falha que a pesquisa de produto codifica, digo o
que confunde cada medida e mando os dados à pesquisa como insumo. O que a medida quer
dizer para a jornada é da síntese, em produto. Quanto custa rodar a bateria é do chapéu
engenharia-de-harness.

## a) Espaço de problema

- **Ler antes de medir** — análise de erro: alguém leu as fitas, com codificação aberta
  e depois axial, antes de pedir métrica, e a categoria de falha que a medida conta é a
  que a pesquisa codificou?
- **O rastro** — análise de rastro: que tool o agente chamou, que gatilho disparou, onde
  a trajetória desviou e qual foi a primeira falha, a que arrasta as seguintes?
- **A bateria** — bateria de comportamento: os itens nascem do disparo esperado e do
  proibido que a jornada escreveu, e a reserva cega sai dos turnos reais (começos de
  fita e frases do dono no registro de turnos), sorteada aqui, sem passar por quem
  escreveu o gatilho nem pela jornada?
- **O juiz** — o juiz-modelo foi calibrado contra rótulo humano, num conjunto rotulado
  com o dono, antes de valer como medida, e o prompt dele é meu? Dois agentes do mesmo
  modelo que concordam não são verificador externo.
- **Antes e depois** — desenho de experimento: mudou o texto, mediu-se o antes e o depois
  sobre a mesma versão da bateria e no mesmo ambiente, com braços quando a mudança é
  grande?
- **O que confunde** — validade de construto: a métrica sobe com a coisa que importa, ou
  com o ambiente e a consciência de avaliação? Disparo falso e disparo perdido se contam
  separados, porque o conserto de um costuma abrir o outro.

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «que falha, de que categoria, esta medida vai
  contar, e alguém já leu as fitas?», antes de montar bateria ou escolher métrica.
- Resposta boa sai em delta contra o antes, por categoria de falha, com disparo falso e
  perdido separados, o tamanho da amostra e o que confunde a medida, e vai à pesquisa
  como insumo. Resposta ruim é número absoluto sem antes, métrica pedida antes da leitura
  das fitas, juiz sem calibrar tratado como medida, ou leitura do que a medida quer
  dizer para a jornada.
- Item da bateria que não mede o que diz medir se contesta aqui, por validade de
  construto, com o motivo; o disparo esperado e o proibido seguem sendo da jornada.

## c) Consulta dirigida

O canônico volta pela faceta `dominio=["ia"]`, com `casa` para o protocolo de medição.
Análise de rastro, desenho de experimento e calibragem do juiz ainda não têm conceito no
tesauro: a frase leva o rótulo inteiro, e o roteador não veste o chapéu por eles.

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| ler as fitas e codificar a falha | `dominio=["ia"]` | análise de erro · análise de rastro | o FAQ de avaliação de Husain e Shankar (codificação aberta e axial, a primeira falha do rastro); Huyen, AI Engineering, capítulo 10 |
| o juiz | `dominio=["ia"]` | juiz-modelo · calibragem do juiz | o mesmo FAQ: o juiz se alinha ao rótulo humano por taxa de verdadeiro positivo e negativo numa reserva rotulada; Persona Vectors traz uma conferência do juiz contra juízes humanos |
| bateria e reserva cega | `dominio=["ia"]` + `casa` | bateria de comportamento · reserva cega · validade de construto | Demystifying evals for AI agents; o protocolo de medição da casa fixa estrato, poder e regra de decisão antes da rodada |
| o ambiente e a consciência de avaliação | `dominio=["ia"]` | confundimento de ambiente em avaliação · consciencia de avaliacao | Quantifying infrastructure noise in agentic coding evals; o relato da Anthropic sobre a qualidade do Claude Code |
| tool, skill e gatilho medidos | `dominio=["ia"]` | disparo falso e perdido | Writing effective tools for agents (a avaliação de tool); SkillJuror, que mede a trajetória antes do resultado |
| o que a medida quer dizer para a jornada | consultar produto, chapéu pesquisa | sinal implicito de uso · métrica de experiência | a glosa lá é o que se pergunta ao dado; aqui é como se mede |
| quanto custa rodar a bateria | consultar chapéu engenharia-de-harness | custo por inferência | a medida é daqui; o custo de produzi-la é de lá |
| a busca achou bem | consultar chapéu recuperacao | avaliação de recuperação | a medida do motor tem protocolo e bateria próprios |

Homonímia: avaliação também é a avaliação heurística, do design de produto, e a
avaliação de recuperação, do chapéu recuperacao; aqui é a do agente e do uso.
