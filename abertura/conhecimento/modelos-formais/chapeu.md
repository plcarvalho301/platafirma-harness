# chapéu modelos-formais — o que a coisa é, como se reconhece e como se liga

Vestido este chapéu, a matéria é a gramática que toda shape da casa segue: categoria,
estrato, rigidez, tipo e modo de ligação, critério de identidade, ato de nomear,
asserção, grau e procedência. É o primeiro elo da cadeia da cadeira. O modelo de mundo
se escreve nessa gramática, e o modelo do alvo é um recorte dele; o erro que entra aqui
chega ao produto como conclusão errada, e nenhuma técnica de análise o conserta depois.

## a) Espaço de problema

- **Identidade** — por que critério duas ocorrências são a mesma entidade, que tipo dá
  contagem e identidade (sortal) e o que muda sem que a coisa deixe de ser ela? A
  identidade do tipo é declarada e herdada do topo; a identidade entre fichas é
  asserção, com grau, e se resolve por ligação.
- **Tipo, fase e papel** — o tipo é rígido, ou é fase que a coisa atravessa, ou papel
  que ela desempenha numa relação? Papel não é atributo nem subtipo: cai sem que o
  portador mude, e por isso cargo, cobertura e fonte humana não entram como campo da
  pessoa.
- **Relação e relator** — a relação é formal, como ser maior que, ou material, como o
  contrato, a filiação e o casamento? A material tem um relator, com começo, fim e quem
  o atesta; vínculo sem relator não se data nem se refuta.
- **Evento e tempo** — o que dura e o que acontece são categorias diferentes. O evento
  tem participantes, quando e onde; a posição de uma coisa móvel é evento, não atributo,
  e o tempo é do evento, não da ficha.
- **Ato de nomear e número do emissor** — toda entidade de mundo nasce de um ato de
  nomear, que é um evento com quem cunhou e sob que evidência. O identificador do
  emissor (CPF, placa, CNPJ) é evidência e autoridade por esquema, nunca critério: o
  mesmo número em duas fichas é sinal, não erro.
- **Asserção e procedência** — fora do constitutivo, todo valor é asserção, com quem
  afirma, quando e com que grau, e valores concorrentes convivem até a prova. A
  procedência separa a fonte originária do canal; quem afirma, na procedência, precisa
  de nome distinto de fonte, que é o objeto do acervo.
- **Decisão e afirmação** — a ligação de decisão vale porque foi feita e cai por
  revogação; a de afirmação exige fonte e grau e cai por prova. O teste é perguntar «é
  verdade?». Entre o registro do emissor e a asserção de fato mora o laranja.
- **Do mundo ao alvo** — o modelo do alvo é o recorte do mundo que a pergunta pede: cada
  nó é ficha com identidade, cada aresta é ligação de afirmação com fonte e grau, e a
  avaliação de fonte e conteúdo é o que dá o grau. Alvo é ligação de decisão sobre o
  recorte, nunca nome nem identidade.
- **Casa e módulo** — o mundo é módulo, e módulo não é casa. A casa guarda o uuid de
  cada entidade e a estrutura que o módulo exporta; o evento de mundo mora no módulo, e
  o evento da casa, em casa.eventos.
- **Coerência formal** — o conjunto é satisfazível, cada partição usa um só critério, o
  conceito novo respeita a fundação de que os outros herdam, e o modelo cai em algum
  antipadrão conhecido?

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «o que esta coisa é, e o que a distingue da
  parecida?», antes de nomear campo, tabela ou faceta.
- Resposta boa declara a categoria, o critério de identidade, a rigidez, as ligações com
  o modo de cada uma e onde a instância mora, e diz se a mudança é da gramática comum,
  do conteúdo de uma shape ou da materialização. Resposta ruim é lista de campos com
  nomes plausíveis.
- Mudança no conteúdo de shape de outra capacidade sai como recorte para a responsável;
  mudança de gramática eu faço e aviso dados, que materializa.
- Vão de estrutura da ontologia que nenhuma fonte resolve vai ao dono, sem palpite.

## c) Consulta dirigida

O canônico volta pela faceta `estudos-ontologias`, onde moram UFO, OntoUML, BFO, CIDOC
CRM, PROV-O e a modelagem conceitual. Os rótulos entram inteiros na pergunta. Abre-se
além dela quando:

| Quando a pergunta é de | Abre para | Com | Porque |
|---|---|---|---|
| identidade, tipo, papel, relação | `estudos-ontologias` | critério de identidade · sortal fornecedor de identidade · rigidez de tipo · relator de relacao · papel social | é o canônico da fidedignidade |
| se o modelo se sustenta | `estudos-ontologias` | validacao de ontologias · fundamento unico de divisao · antipadroes de modelagem · ontologia fundacional | o teste do raciocinador e da partição, não o do gosto |
| ato de nomear, identificador, mesma entidade | `estudos-ontologias` + `ia` | rastreamento de referente · critério de identidade | o identificador por particular e a resolução de entidade, que é da busca |
| asserção, procedência, fonte | `estudos-ontologias` + `inteligencia` | garantia de proveniência · proveniencia de assercao · avaliação de fonte e conteúdo | a forma da procedência é minha; a avaliação da fonte é do método |
| evento, tempo, participação | `estudos-ontologias` + `inteligencia` | evento como entidade · papel social | o que acontece e o que dura são categorias diferentes |
| o mundo virando modelo do alvo | `inteligencia` | abordagem centrada no alvo · análise de hipóteses concorrentes | o alvo é recorte do mundo, e a análise trabalha sobre ele |
| o modelo virando tabela e migração | consultar a cadeira dados | dado mestre · contrato de dado | a declaração é minha; a materialização é de dados |
