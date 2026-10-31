# Molde compromisso

O gênero compromisso é o texto de um acordo entre quem chama e quem presta: o que quem
chama se obriga a fazer, e o que recebe em troca. É o gênero do contrato e de todas as
suas filhas: a interface (o acordo que vale a cada chamada), a integração (o acordo
continuado de nível e termos, que se parte em plano e pacto de serviço) e o contrato da
porta.

O que separa o compromisso dos outros gêneros é que ele pode ser descumprido. Uma
descrição só pode estar errada; um acordo pode ser quebrado por um dos lados, e mudá-lo
quebra quem contava com ele. Por isso cada frase do texto é algo que alguém de fora
consegue conferir, e que, se mudar, faz outro acordo.

Três leitores chegam ao texto. O primeiro é quem chama, e não pode abrir o código do
outro lado: outra cadeira, outro serviço, um agente. Ele precisa saber o que tem de fazer
e o que recebe, sem perguntar a ninguém. O segundo é quem presta, e vai mudar alguma coisa
do lado dele; precisa saber o que quebra quem chama e o que está livre para mudar. O
terceiro é o dono, que volta ao texto quando algo quebrou, para saber quem descumpriu o
quê.

## O que a ficha já mostra

O site abre o documento com a ficha, montada do banco. Nada dela se escreve no texto, nem
com outras palavras.

A ficha mostra a chave, o rótulo, a definição da classe e as ligações: o serviço que
presta, quem o consome, o componente que garante o acordo (o teste que o trava) e, na
integração, a vigência. O endereço e a zona de rede em que o acordo é servido ficam na
exposição; a versão em uso é medida. Nenhum dos três entra no texto.

O texto começa onde a ficha para. A ficha diz quem são as partes; o texto diz o que cada
uma dá.

## Objeto

Sobre o que é o acordo, dito pelo lado de quem chama.

- **O que se troca, em uma ou duas frases.** O que quem chama pede e que tipo de coisa
  recebe, sem precisar saber como se faz do outro lado.
- **A fronteira.** O que parece fazer parte e não faz, quando a confusão é real: as
  rotas que escrevem não fazem parte de um acordo de leitura. É a frase que impede quem
  chama de contar com o que ninguém prometeu.
- **Fica fora:** o mecanismo interno, como operar o serviço, onde ele responde e
  ponteiro para outro documento.

Exemplo de objeto:

- Ruim: «Este documento descreve a API de busca, que usa embeddings e um índice
  vetorial.»
- Bom: «O que a API de busca devolve a quem a chama, campo a campo, sem precisar abrir o
  código. As rotas que escrevem no motor não fazem parte deste acordo.»

## Obrigações

O que quem chama tem de fazer para ter direito à contrapartida.

- **Do lado de quem chama.** A credencial que apresenta, a forma da entrada, o limite
  que respeita, o aviso que dá. É o que ele faz antes de receber qualquer coisa.
- **No presente, e conferível.** «Apresenta o token no cabeçalho», «envia a consulta com
  até tantos termos». Quem presta consegue ver se a obrigação foi cumprida.
- **O que acontece com quem não cumpre.** A recusa e a forma dela. Sem isso, quem chama
  descobre a obrigação pelo erro.
- **Só o que se cobra.** Obrigação que ninguém confere e cujo descumprimento não muda a
  resposta não é obrigação, e sai.

Exemplo de obrigação:

- Ruim: «O cliente deve usar a API de forma adequada.»
- Bom: «Quem chama apresenta `Authorization: Bearer <token>` em toda rota, menos na de
  saúde. Sem o token, a chamada é recusada antes de chegar à busca.»

## Contrapartida

O que quem presta devolve a quem cumpriu. É o corpo do acordo, e todo acordo tem.

- **Promessa no presente, pelo lado de quem recebe.** «Devolve», «responde em», «traz o
  campo». «Procura», «tenta» e «sempre que possível» não prometem nada: ou a frase
  promete, ou sai.
- **Cada promessa conferível de fora.** Quem chama consegue ver se recebeu o prometido,
  sem abrir o código. Quando o próprio acordo dá o meio de conferir (um carimbo que duas
  respostas repetem, um campo que diz de onde veio o valor), diga isso: é o que
  transforma promessa em fato.
- **Só o que você trataria como quebra.** O que pode mudar sem aviso não se promete.
  Quando quem chama tenderia a contar com isso (uma ordem, um formato incidental), diga
  que não é prometido.
- **A resposta na falha também é contrapartida.** O que volta quando o erro é do lado de
  quem presta, e quando o serviço ainda não está pronto. É a parte que mais falta e a que
  mais se consulta.
- **O porquê da escolha que surpreende, numa oração.** «O carimbo não se repete na busca,
  porque é constante da sessão e gastaria contexto de quem chama.» Sem o porquê, quem
  presta desfaz a escolha achando que é descuido.
- **O que está em retirada se diz assim,** com o que o substitui e até quando vale, se
  há data prometida.
- **No plano, a contrapartida tem preço;** na interface, é a resposta. A régua é a mesma.

Exemplo de contrapartida:

- Ruim: «O serviço trata erros adequadamente e procura responder rápido.»
- Bom: «Falha interna devolve 502 só com o tipo do erro, sem trecho de consulta. Com o
  modelo ainda carregando, devolve 503 dizendo isso, e não 200 com resposta pior.»

## Seções de cada entidade

O gênero declara Objeto, Obrigações e Contrapartida. As seções que cada entidade
acrescenta têm a régua da dona dela; aqui vai só o nome:

- **interface:** Operações; Erros; O que trava o contrato.
- **integração:** Nível prometido; Termos.
- **plano:** Nível prometido; Termos; Autenticação.
- **pacto de serviço:** Nível prometido; Termos; Como se mede.
- **contrato da porta:** nenhuma.

## Como escrever

**Mudança que quebra é outro acordo.** Ao revisar, pergunte se a mudança quebra quem
chama. Se quebra, o texto não se reescreve no lugar: nasce outro documento. Se não
quebra (um campo novo opcional, uma rota a mais), reescreve-se este.

**Tabela para o que se enumera.** Rotas, campos e códigos de erro vão em tabela, uma linha
por item, com o que é e para que serve. A prosa fica com o que a tabela não diz: a
fronteira, a falha, o porquê. A tabela mora na seção a que pertence: os campos que voltam
são contrapartida e vão nela, e não numa seção nova.

**Cada fato num lugar só.** Quando a entidade tem seção própria para as rotas ou para os
erros, a tabela de lá é o único lugar do código e da rota. Obrigações e Contrapartida
dizem a regra em prosa («sem o token, a chamada é recusada») e não repetem a tabela. O
mesmo código escrito em três seções muda numa e fica velho nas outras duas.

**Nível com número e com a medida.** Promessa de nível sem número não se quebra, e por
isso não promete. O número vem com a janela em que vale e com o que se mede.

**Sem log.** Número de card, nome antigo, «depois da virada» e a história de como o acordo
chegou aqui ficam fora. Quem chama quer saber o que vale hoje.

## Antes de gravar

Confira, nesta ordem:

1. Quem chama, lendo só o Objeto, sabe o que pode pedir e o que não faz parte?
2. As Obrigações dizem o que quem chama faz, e o que acontece se não fizer?
3. Cada frase da Contrapartida é uma promessa no presente, que quem chama consegue ver se
   recebeu? Ela diz o que volta na falha?
4. Há alguma promessa que você não trataria como quebra se mudasse? Ela sai.
5. Esta revisão quebra quem já conta com o acordo? Se quebra, é outro documento.
6. Algum código, campo ou rota aparece em mais de uma seção, ou numa seção que o gênero e
   a entidade não declaram?
7. Alguma frase repete o que a ficha mostra, diz onde o serviço responde, aponta outro
   documento ou conta como era antes?
