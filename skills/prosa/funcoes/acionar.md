# Acionar

A seção que aciona liga uma deixa a um ato, na hora da decisão: o pedido do dono, o
retorno de outra tool ou o estado de um serviço, à chamada de uma tool ou ao começo de um
processo. É a função do gatilho, da descrição de tool e da descrição de skill.

O primeiro leitor é o modelo, que tem o pedido ou o retorno na mão e percorre a lista
inteira de tools e skills a cada turno; a primeira linha decide se ele lê o resto. O
texto é servido sozinho, e o modelo não vê a ficha, então o texto nomeia o que dispara
pelo nome natural. O último leitor é o dono, que volta quando a tool não disparou ou
disparou fora de hora.

A seção erra de dois jeitos, que não se compensam: calar onde devia disparar, porque o
modelo resolve sozinho e nem considera a tool, que é o erro mais comum; e disparar onde
não devia, porque a deixa se parece com a de outra coisa. Decida olhando os dois
separados, porque o texto que corta um costuma abrir o outro.

## O que aciona

- **Nas palavras que aparecem.** «Gestão da memória de trabalho» não aparece em pedido
  nenhum; «o que ficou para a próxima fita» aparece.
- **As várias formas do mesmo momento.** O dono diz a mesma coisa de três jeitos, e o
  texto traz os três.
- **De cada fonte que existe:** pedido do dono, desfecho de outra execução, estado do
  ambiente. A passagem de um processo a outro e o alerta são as deixas que mais faltam,
  porque aparecem num retorno, e não em voz alta.
- **O momento, antes do ato que precisa preceder:** «antes de gravar», «antes de
  commitar».
- **Mesmo sem pedido.** Quando o erro comum é o modelo resolver sozinho, diga que vale
  mesmo que ninguém peça, e nomeie a tentação de pular.
- **Caixa alta só em SEMPRE, ANTES e NÃO,** uma vez cada. Além dessas três, a marca
  vira grito.
- **A negativa com o vizinho.** Onde a deixa se confunde com a de outra coisa, diga
  quando não disparar e o que se faz no lugar.

Exemplo:

- Ruim: «use para: gestão da memória de trabalho»
- Bom: «use para: o que ficou para a próxima fita, "o que estava na mesa", anotar uma
  pendência»

## O que dispara

- **Pelo nome natural, com o verbo.** «Buscar», e não «heurística»; «anotar», e não
  «memória de trabalho».
- **Fica fora:** os passos, que moram no processo disparado; os atos e argumentos da
  tool, que são do contrato; o que a skill carrega. O modelo decide pelo momento, não
  pelo conteúdo.

Exemplo, descrição de skill:

- Ruim: «Skill de prosa com funções, gabaritos e passo a passo de revisão.»
- Bom: «Use SEMPRE que for escrever ou revisar texto da casa que uma pessoa vai ler,
  mesmo que ninguém peça revisão. Siga ANTES de gravar ou enviar. NÃO dispare para
  resposta de chat.»

## Como escrever

- **Termina num ato.** Frase que muda o tom ou o que vale, e não leva a ato nenhum, é de
  induzir.
- **Uma condição de começo por texto.** Dois começos diferentes são dois gatilhos.
- **Curto.** O texto está em toda sessão, ao lado de todas as outras tools.

## Antes de gravar

1. Entre todas as tools da lista, a primeira linha basta para o modelo saber se é esta?
2. Pense em três pedidos reais em que ela devia disparar. Cada um tem a sua deixa no
   texto, com as palavras que de fato aparecem?
3. Pense num pedido vizinho em que ela não devia disparar. A negativa o pega e diz quem
   dispara no lugar?
4. O texto diz o momento, antes do ato que precisa preceder?
