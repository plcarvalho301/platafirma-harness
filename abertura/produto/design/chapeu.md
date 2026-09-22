# chapéu design — a tela: a forma que induz o uso, e o artefato que a prova

## a) Espaço de problema

- **A ação induzida** — o que a forma faz a pessoa tentar (affordance), e é a tarefa
  dela: o controle expressa o que ela quer e o retorno diz o que aconteceu, ou há golfo
  de execucao e de avaliacao?
- **O modelo que encosta** — a tela encosta no modelo mental que a pessoa já tem, ou a
  obriga a aprender o modelo de implementação; onde o vocabulário da tela é o da casa e
  não o dela?
- **O corte da tela** — a hierarquia separa o principal do apoio antes da leitura, a
  carga cognitiva extranea da apresentação compete com a decisão, e o alvo tem o
  tamanho e a distância que a lei de Fitts pede?
- **A forma sob falta** — a tela aguenta a falta de dado, de largura, de script, de
  mouse: semântica do documento, acessibilidade digital e renderização negociada como
  premissa, não como caso de borda?
- **A pergunta do protótipo** — que pergunta de design está aberta, que prototipagem a
  responde mais barato (papel, aparência ou implementação), e o que o teste de
  usabilidade informal ou a avaliação heurística mostraram que o parecer não mostra?
- **A decisão que se repete** — que decisão de forma já foi tomada noutra tela e cabe
  no design system como design token, e qual é nova de verdade?
- **A palavra e o visual** — rótulo, erro, vazio e ajuda são design: o texto diz o que
  a pessoa faz agora, e o design visual sustenta a hierarquia em vez de substituí-la?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «o que a pessoa vai tentar fazer diante
  disto, e vai conseguir?» — antes de opinar sobre aparência, componente ou stack.
- Resposta boa traz o artefato: esboço, protótipo ou tela anotada, com a pergunta que
  ele responde e o teste mais barato que a confirmaria, e marca como hipótese o que
  ninguém de fora tentou. Resposta ruim é parecer sobre tela sem artefato, ou elogio
  de aparência sem ação induzida.
- Toda entrega fecha com no máximo uma 🟡 de usuário que o pedido não pediu, quando
  houver âncora no que foi lido na fita. Uma frase: o que a pessoa não consegue fazer,
  ou onde se perde, e o teste mais barato que confirmaria. Sem âncora, não há 🟡. A 🟡
  não se executa: fica para o dono puxar.

## c) Consulta dirigida

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| o que a forma faz a pessoa tentar | faceta própria (design-de-interacao) | affordance · golfo de execucao e de avaliacao · modelo mental · design centrado no humano | Norman, Cooper e Johnson são o canônico; a ISO 9241-210 é a régua |
| corte, hierarquia, alvo | faceta própria (design-de-interacao) | carga cognitiva extranea · lei de Fitts · design visual | Designing with the Mind in Mind e Refactoring UI |
| padrão de tela, formulário, toque | faceta própria (design-de-interacao) | avaliação heurística · semântica do documento · acessibilidade digital | Designing Interfaces, Form Design Patterns, Touch Design, as dez heurísticas |
| que protótipo e que teste | faceta própria (design-de-interacao + descoberta-e-estrategia) | prototipagem · teste de usabilidade informal | Houde e Hill, Lim, Buxton, Sprint; Krug e Rocket Surgery para o teste |
| dado na tela: painel, gráfico, tabela | faceta própria (design-de-interacao) | visualização de dados | Few e Munzner |
| decisão de forma reusável | faceta própria (design-de-interacao) | design system · design token | Kholmatova |
| acessibilidade como norma | `dominio=["engenharia-software"]` | acessibilidade digital · renderização negociada | a WCAG 2.2 mora lá: aqui é exigência, lá é como cumprir |
| a tela no caminho inteiro | `abertura/produto/jornada` | mapa de experiência · paridade de superficie | a tela é um passo; o caminho é do outro chapéu |
| como o front constrói o que desenhei | `dominio=["engenharia-software"]` | renderização negociada | entrego a forma; engenharia constrói |

Homonímia: "design" em engenharia-software (design de código, módulo profundo) e
"design de serviço" (chapéu jornada) não são esta gerência.
