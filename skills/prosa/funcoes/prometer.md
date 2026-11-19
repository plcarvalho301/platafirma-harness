# Prometer

A seção que promete fixa o que cada lado de um acordo deve ao outro, enquanto o acordo
durar: o que quem chama se obriga a fazer, e o que recebe em troca. É a função do
contrato e das filhas dele: a interface, a integração, o plano, o pacto de serviço e o
contrato da porta. Não é regra: é compromisso.

O que separa a promessa das outras funções é que ela pode ser descumprida por um dos
lados, e mudá-la quebra quem contava com ela. Por isso cada frase é algo que alguém de
fora consegue conferir, e que, se mudar, faz outro acordo.

Três leitores chegam ao texto. Quem chama, que não pode abrir o código do outro lado e
precisa saber o que fazer e o que recebe. Quem presta, que vai mudar algo e precisa
saber o que quebra quem chama. E o dono, que volta quando algo quebrou, para saber quem
descumpriu o quê.

## O que o texto de um acordo cobre

A shape diz as seções. Quando ela não as declara, o texto cobre estes pontos.

### O objeto

- **O que se troca, em uma ou duas frases,** pelo lado de quem chama.
- **A fronteira.** O que parece fazer parte e não faz, quando a confusão é real. É a
  frase que impede quem chama de contar com o que ninguém prometeu.

Exemplo:

- Ruim: «Este documento descreve a API de busca, que usa embeddings e um índice
  vetorial.»
- Bom: «O que a API de busca devolve a quem a chama, campo a campo, sem precisar abrir o
  código. As rotas que escrevem no motor não fazem parte deste acordo.»

### As obrigações de quem chama

- **O que ele faz antes de receber:** a credencial que apresenta, a forma da entrada, o
  limite que respeita, o aviso que dá.
- **No presente, e conferível.** Quem presta consegue ver se a obrigação foi cumprida.
- **O que acontece com quem não cumpre:** a recusa e a forma dela.
- **Só o que se cobra.** Obrigação que ninguém confere e cujo descumprimento não muda a
  resposta sai.

### A contrapartida

- **Promessa no presente, pelo lado de quem recebe:** «devolve», «responde em», «traz o
  campo». «Procura», «tenta» e «sempre que possível» não prometem nada.
- **Cada promessa conferível de fora.** Quando o próprio acordo dá o meio de conferir,
  diga isso.
- **Só o que você trataria como quebra.** O que pode mudar sem aviso não se promete, e
  quando quem chama tenderia a contar com isso, diga que não é prometido.
- **A resposta na falha também é contrapartida:** o que volta quando o erro é de quem
  presta, e quando o serviço ainda não está pronto.
- **O porquê da escolha que surpreende, numa oração.** Sem ele, quem presta desfaz a
  escolha achando que é descuido.
- **O que está em retirada se diz assim,** com o que o substitui.
- **Nível com número e com a medida,** e com a janela em que vale. Promessa de nível sem
  número não se quebra, e por isso não promete.

Exemplo:

- Ruim: «O serviço trata erros adequadamente e procura responder rápido.»
- Bom: «Falha interna devolve 502 só com o tipo do erro, sem trecho de consulta. Com o
  modelo ainda carregando, devolve 503 dizendo isso, e não 200 com resposta pior.»

## Como escrever

- **Mudança que quebra é outro acordo.** Se a revisão quebra quem chama, o texto não se
  reescreve no lugar: nasce outro documento.
- **Lista para o que se enumera:** rotas, campos e códigos, um item por linha, aberto
  pelo nome ou pelo código, na seção a que pertencem. Cada código mora num lugar só.
- **Fica fora:** o mecanismo interno, onde o serviço responde e a versão em uso.

## Antes de gravar

1. Quem chama, lendo só o objeto, sabe o que pode pedir e o que não faz parte?
2. As obrigações dizem o que quem chama faz, e o que acontece se não fizer?
3. Cada promessa é algo que quem chama consegue ver se recebeu? O texto diz o que volta
   na falha?
4. Esta revisão quebra quem já conta com o acordo? Se quebra, é outro documento.
