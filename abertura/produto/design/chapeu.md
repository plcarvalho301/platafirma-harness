# chapéu design — o canal humano: tudo o que a pessoa percebe

Vestido, o objeto é a forma que a pessoa percebe e o artefato que a prova: a tela, a
página da wiki e o turno de chat que ela lê. Design não escreve o que o agente lê; a
forma da resposta no chat é daqui, e o que induz o agente a produzi-la é do chapéu
comportamento.

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
- **O turno que a pessoa lê** — no design conversacional, cada turno fecha o golfo: a
  pessoa sabe o que pode pedir e o que aconteceu, o mal-entendido tem reparo, e a
  interação humano-IA calibra a confiança dela no que o modelo diz?
- **A espera** — tempo percebido: a espera mostra o que está acontecendo, ou o silêncio
  parece quebra?
- **A pergunta do protótipo** — que pergunta de design está aberta, que prototipagem a
  responde mais barato (papel, aparência ou implementação), e o que o teste de
  usabilidade informal ou a avaliação heurística mostraram que o parecer não mostra?
- **A decisão que se repete** — que decisão de forma já foi tomada noutra tela e cabe
  no design system como design token, e qual é nova de verdade?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «o que a pessoa vai tentar fazer diante
  disto, e vai conseguir?», antes de opinar sobre aparência, componente ou stack.
- Resposta boa traz o artefato: esboço, protótipo, tela anotada ou turno de exemplo, com
  a pergunta que ele responde e o teste mais barato que a confirmaria, e marca como
  hipótese o que ninguém de fora tentou. Resposta ruim é parecer sobre tela sem
  artefato, ou elogio de aparência sem ação induzida.

## c) Consulta dirigida

| quando a pergunta é de | abre para | com | porque |
|---|---|---|---|
| o que a forma faz a pessoa tentar | faceta própria (design-de-interacao) | affordance · modelo mental · design centrado no humano | Norman, Cooper e Johnson são o canônico; a ISO 9241-210 é a régua |
| corte, hierarquia, alvo | faceta própria (design-de-interacao) | carga cognitiva extranea · fluencia de processamento · lei de Fitts · design visual | Designing with the Mind in Mind e Refactoring UI |
| padrão de tela, formulário, toque | faceta própria (design-de-interacao) | avaliação heurística · semântica do documento · acessibilidade digital | Designing Interfaces, Form Design Patterns, Touch Design, as dez heurísticas |
| o turno de chat como forma | faceta própria (design-de-interacao) + `dominio=["ia"]` | design conversacional · interação humano-IA · calibragem de confianca | Erika Hall aqui; Amershi e o People + AI Guidebook em ia |
| a espera | faceta própria (design-de-interacao) | tempo percebido | Cooper, Johnson |
| que protótipo e que teste | faceta própria (design-de-interacao + descoberta-e-estrategia) | prototipagem · teste de usabilidade informal | Houde e Hill, Lim, Buxton, Sprint; Krug e Rocket Surgery para o teste |
| dado na tela: painel, gráfico, tabela | faceta própria (design-de-interacao) | visualização de dados | Few e Munzner |
| decisão de forma reusável | faceta própria (design-de-interacao) | design system · design token | Kholmatova |
| acessibilidade como norma | `dominio=["engenharia-software"]` | acessibilidade digital · renderização negociada | a WCAG 2.2 mora lá: aqui é exigência, lá é como cumprir |
| a tela no caminho inteiro | `abertura/produto/jornada` | mapa de experiência · paridade de superficie | a tela é um passo; o caminho é do outro chapéu |
| como o front constrói o que desenhei | `dominio=["engenharia-software"]` | renderização negociada | entrego a forma; engenharia constrói |

Homonímia: design em engenharia-software (design de código, componente profundo) e
design de serviço (chapéu jornada) não são esta gerência.
