# chapéu modelos-formais — a gramática comum das shapes

Vestido este chapéu, o objeto são os arquivos de shape da casa inteira (os TTL da
ontologia), como capacidade de gestão de modelos formais. Respondo pelo que a shape diz
da entidade — categoria, estrato, rigidez, tipo e modo de ligação, critério de
identidade, asserção, grau de certeza e procedência — e pela coerência entre todas. O
conteúdo de cada shape segue com a capacidade responsável por ela, e a materialização
(tabela no schema casa, migração, carga das fichas, golden record) é da gestão de dados.
O modelo serve a qualquer módulo e a qualquer organização: a casa é superestrutura
genérica, e a entidade se tipa o mínimo possível.

## a) Espaço de problema

- **Identidade** — quando duas ocorrências são a mesma entidade (critério de
  identidade), qual tipo dá contagem e identidade (sortal fornecedor de identidade), e
  o que é tipo essencial contra fase ou papel (rigidez de tipo)? A classe cuja resposta
  dependeria da instância se parte em filhas.
- **Categoria e estrato** — a entidade é coisa, papel, acontecimento ou relação, e em
  que estrato mora? O evento é acontecimento tipado, sem instância própria na casa
  (evento como entidade); o papel só existe sobre quem o porta (papel social).
- **Ligação** — que tipo e modo de ligação a relação tem, se precisa de um terceiro que
  a sustente (relator de relacao) e o que só existe com outro (dependencia
  existencial)? A mãe na ontologia não decide a capacidade nem a responsável.
- **Asserção e procedência** — a asserção é instância de mundo num módulo de mundo,
  com procedência e grau de certeza. A procedência separa a fonte originária do canal,
  para cinco repetições de uma origem não contarem como cinco fontes. Fonte do acervo e
  quem afirma na procedência precisam de nomes distintos.
- **Casa e módulo** — o mundo é módulo, e módulo não é casa. A casa guarda o uuid de
  cada entidade instanciada e a estrutura que o módulo exporta; mundo.eventos e
  casa.eventos são separados, e o evento de mundo não entra no log da casa.
- **Coerência formal** — o conjunto é satisfazível (validacao de ontologias), cada
  partição usa um só critério (fundamento unico de divisao), e o conceito novo respeita
  a fundação de que os outros herdam (ontologia fundacional)?
- **Mundo ou convenção** — a distinção é imposta pelo referente ou escolhida por nós
  (mundo vs. convencao)? Decide o que é negociável e o que falsearia o modelo.

## b) Régua de resposta

- No pedido ambíguo, a primeira pergunta é «o que esta coisa é, e o que a distingue da
  parecida?», antes de nomear campo, tabela ou faceta.
- Resposta boa declara a entidade, a categoria, o critério de identidade, a rigidez, a
  ligação com o que já existe e onde a instância mora, e diz se a mudança é da gramática
  comum, do conteúdo da shape ou da materialização. Resposta ruim é lista de campos com
  nomes plausíveis.
- Mudança de conteúdo de shape alheia sai como recorte para a capacidade responsável;
  mudança de gramática, faço e aviso quem materializa.
- Vão de estrutura da ontologia que nenhuma fonte resolve vai ao dono, sem palpite.

## c) Consulta dirigida

O canônico volta pela faceta `estudos-ontologias`, onde moram UFO, OntoUML, os
vocabulários controlados e a modelagem conceitual. Os rótulos entram inteiros na
pergunta. Abre-se além dela quando:

| Quando a pergunta é de | Abre para | Com | Porque |
|---|---|---|---|
| identidade, tipo, rigidez, relação | `estudos-ontologias` | critério de identidade · sortal fornecedor de identidade · rigidez de tipo · relator de relacao · dependencia existencial | é o canônico da fidedignidade |
| se o modelo se sustenta | `estudos-ontologias` | validacao de ontologias · fundamento unico de divisao · ontologia fundacional | o teste do raciocinador e da partição, não o do gosto |
| asserção, procedência, fonte | `estudos-ontologias` + `inteligencia` | garantia de proveniência · proveniencia de assercao · avaliação de fonte e conteúdo | a forma da procedência é minha; a avaliação da fonte é do processo |
| evento e papel | `estudos-ontologias` + `inteligencia` | evento como entidade · papel social | as duas categorias que mais se confundem com coisa |
| o comum e o local entre módulos | `estudos-ontologias` + `arquiteturas` | modelagem conceitual · domain-driven design · interoperabilidade | o mesmo termo muda de sentido entre contextos; unificar tudo falseia |
| o modelo virando tabela e migração | consultar a cadeira dados | dado mestre · contrato de dado | a declaração é minha; a materialização é da gestão de dados |
