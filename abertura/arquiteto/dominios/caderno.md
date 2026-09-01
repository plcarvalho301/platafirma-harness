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
