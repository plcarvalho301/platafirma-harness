# caderno — domínios (arquiteto)

Durável: continua verdadeiro depois que o assunto morrer, e a próxima fita pagaria
para re-derivar. Entrada nova substitui a que contradiz; o histórico é o git.

## Pedido de exceção se testa primeiro contra o ALCANCE, e alcance mora na ADR-mãe

Quando uma cadeira chega pedindo "lavra a exceção para o meu caso", a primeira pergunta
não é se a exceção se justifica — é se a regra alcança o caso. As duas respostas são
registros diferentes, e escolher o errado deixa a próxima varredura re-marcando o mesmo
ponto como dívida.

- **Exceção** = a regra alcançaria, e se abre mão com fundamento. Custa os campos de
  registro que a ADR exigir — inclusive onde mora o contrato substituto. **Fora de
  alcance** = a regra nunca alcançou; não há contrato substituto a nomear porque não há
  consumidor. Pedir exceção para um caso fora de alcance é pedir para inventar um
  contrato que ninguém consome.
- **Sintoma de que o pedido veio na forma errada:** o campo "onde mora o contrato" (ou o
  equivalente da ADR em questão) fica sem resposta possível. Isso não é lacuna do pedido;
  é o registro certo se anunciando.
- **Alcance se emenda na ADR-mãe (a que constitui a regra), nunca na ADR de forma que
  dela herda.** A ADR de forma no máximo espelha uma linha de escopo apontando para a
  mãe. Lavrar alcance nas duas produz duas fontes que divergem na primeira revisão de uma
  delas. Caso medido: `arq:0089` (constitui) × `arq:0090` (forma REST) — a exclusão de
  estado de trabalho privado entrou na 0089; a 0090 só aponta.
- **Classifique DADO, não arquivo.** O corte de alcance passa por dentro de um módulo:
  metade privada, metade servida, no mesmo `.py`. Varredura de conformidade que lista
  arquivos erra os dois lados — libera o que devia estrangular e marca como dívida o que
  nunca esteve na regra.
- **Cortar um caso do alcance não fecha o item aberto vizinho.** Tirar algo por *não ser
  servido* não decide nada sobre o que é servido por outro transporte. Fechar o vizinho de
  carona é a economia que produz decisão não-deliberada.

## Aresta da teia se confere contra a frase-molde, e o motivo do lavrador denuncia a família errada

Conferir aresta que outra cadeira lavrou é leitura de forma antes de leitura de mérito. A
intuição sobre o par chega primeiro e erra; o molde da família e o motivo já escrito
decidem quase tudo.

- **Molde antes da intuição.** `generica` inclui "A é B aplicado a X" — não é só "A é um
  tipo de B". Caso medido: opus a `titularidade-do-core -generica-> dominio-central` por
  achar que titularidade não é *espécie* de domínio central, e o motivo lavrado estava
  exatamente na segunda forma do molde. Objeção levantada antes de ler a cartilha custa
  retratação por carta.
- **O motivo do lavrador é o melhor delator da família errada.** Quando uma aresta
  `relacionada` traz motivo com "é uma das inscrições de", "é X assumido no destino", "é o
  veículo de" — há direção, e a simétrica é definida como *sem* direção nem hierarquia. A
  família certa costuma ser `instrumental`. Caso: `registro-de-decisao`, que saiu de
  relacionada para instrumental sem que uma palavra do sentido mudasse.
- **Consistência no `<para>` é evidência, não estética.** Antes de escolher família, olhe
  as arestas que já chegam no mesmo alvo com o mesmo papel. Duas famílias diferentes para
  o mesmo papel no mesmo alvo é o defeito que se vê de fora, e sustenta a objeção melhor
  que argumento de definição.
- **Homonímia contra massa de corpus não se conserta com `disjunta`.** Disjunta exige dois
  conceitos *lavrados*; quando o segundo sentido da palavra não é conceito e sim volume de
  obra no acervo, não há `<para>` para apontar. O instrumento é o qualificador no rótulo
  alternativo — o apelido ambíguo é que puxa o corpus errado.
- **Definição frouxa enfraquece toda aresta que se apoia nela.** Conceito com definição
  circular deixa a aresta sustentada pelo entendimento de quem confere, não pelo texto
  lavrado. Ao conferir, olhe também a definição do `<de>` e do `<para>`: achado de
  curadoria vale carta separada, não vira objeção à aresta.
