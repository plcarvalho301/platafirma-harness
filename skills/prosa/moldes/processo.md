# Molde processo

O gênero processo é o passo a passo: o texto que leva quem age de uma entrada a um
resultado que se confere. É o gênero do processo adotado, que se segue à risca, do ciclo,
que se repete cada vez que a mesma ocasião volta, do guia, que orienta um trabalho cujo
tipo ainda não se decidiu, e do procedimento, que detalha uma etapa só. É também o do
hábito e da heurística: o hábito guarda a rotina que um gatilho dispara, e a heurística
guarda o jeito de decidir quando ainda não se sabe o que fazer.

É texto instrutivo. Diz o que fazer, em que ordem quando a ordem importa, e como se sabe
que deu certo.

É o passo a passo de quem executa. O processo que contém outros processos, e que se lê
para saber em que estágio a coisa está e o que vem depois, não se escreve por este molde.

Três leitores chegam ao texto. O primeiro é quem executa, no meio do trabalho, com a
coisa na mão: ele chegou aqui porque um gatilho disparou, e lê o passo em que está, não o
texto inteiro. O segundo é quem recebe o resultado, a etapa seguinte ou outra cadeira, e
precisa saber o que vem pronto. O terceiro é o dono, que volta ao texto quando o processo
travou ou deu resultado errado, para achar o passo que faltou ou a passagem mal definida.

## O que a ficha já mostra

O site abre o documento com a ficha, montada do banco. Nada dela se escreve no texto, nem
com outras palavras.

A ficha mostra a chave, o rótulo, a definição da classe, o estado de adoção e as
ligações: o gatilho que dispara o processo, os procedimentos que detalham as etapas, o
padrão que diz a forma do resultado e o gabarito que o confere. No hábito, mostra também
de onde ele veio.

O texto começa onde a ficha para. A ficha diz o que dispara e o que cerca o processo; o
texto diz o que se faz.

## Quando serve

O que deveria disparar o processo, visto de dentro dele. O gatilho é escrito para quem
varre a lista de tools e decide se chama; esta seção é escrita para quem já está aqui e
precisa saber se este é o processo certo, e para o dono, que confere se o gatilho dispara
na hora certa.

- **A situação que o pede, e a entrada pronta.** O que aconteceu para o processo ser
  necessário, e o que precisa estar na mão para começar.
- **O vizinho que se confunde.** O processo parecido que não é este, e o que separa os
  dois.
- **Quando não serve.** A situação que parece pedir o processo e não pede.

## Passos

O corpo do gênero.

- **Um ato por passo, começando pelo verbo.** «Rode», «abra», «grave». Passo com dois
  atos é dois passos, e quem executa faz o primeiro e pula o segundo.
- **O passo acaba onde o trabalho poderia mudar de mão.** Se o resultado do passo pode
  ir a outra cadeira ou a outra fita, o passo termina ali. O que nunca muda de mão é um
  passo só, por mais atos de ferramenta que tenha.
- **A ordem só onde importa.** Quando dois passos podem vir em qualquer ordem, diga isso;
  numeração sugere uma sequência que talvez não exista.
- **Quem faz e o que passa adiante, quando muda.** Num processo que atravessa cadeiras,
  cada passo diz quem o faz e o que entrega ao seguinte.
- **A falha no passo em que acontece.** O que fazer quando o passo não dá certo, ou
  quando não deu para olhar, vem no próprio passo, e não num apêndice. «Não consegui
  olhar» não é «deu certo», e o passo diz o que cada um autoriza.
- **A escolha vira tabela.** Quando o passo depende de uma pergunta («qual classe
  olhar?»), uma tabela de pergunta e caminho decide mais rápido que um parágrafo.
- **O ato da ferramenta escrito como se chama.** Quando o passo é uma chamada, ela vai
  literal, pronta para copiar: o nome do ato é o caminho mais curto até ele.
- **Fica fora:** a regra que vale em qualquer passo, que é norma, e entra só no passo em
  que decide; o como de uma etapa que tem procedimento próprio; o porquê longo de o
  processo ser assim.

O procedimento segue as mesmas réguas, numa etapa só: os atos na ordem até a etapa estar
feita, de modo que quem os siga chegue ao mesmo resultado. Ele diz como; o porquê e o
quando são do processo que o contém.

Exemplo de passo:

- Ruim: «Verificar o estado do serviço e tomar as providências necessárias.»
- Bom: «Rode `release conferir servico <nome>`. Saída 0: siga. Saída 1: o serviço diverge
  do que o compose declara; abra o incidente. Saída 5: não deu para olhar, e isso não
  autoriza promover.»

## Como se confere

O resultado que fecha o processo e o sinal de que saiu certo.

- **O resultado pelo que se vê.** O arquivo no ar, o card no estado tal, a saída zero. É
  o marco que diz a quem executa que acabou, e a quem recebe que pode começar.
- **Os estados do resultado, quando são mais de dois.** Conforme, divergente e «não
  consegui olhar» são três resultados diferentes, e só o primeiro fecha.
- **Quando há gabarito, só o marco.** Os itens são do gabarito, e repetidos aqui ficam
  velhos lá.

## Seções de cada entidade

O gênero declara Quando serve, Passos e Como se confere. As seções que cada entidade
acrescenta têm a régua da dona dela; aqui vai só o nome:

- **hábito:** Recompensa esperada; Passos; Caso que o ensinou; Quando serve (derivada).
- **heurística:** Por onde procurar; Quando parar; O que fazer com o que se achou.
- **processo, ciclo, guia e procedimento:** nenhuma.

## Como escrever

**Para quem está no meio do trabalho.** Cada passo se entende sozinho, sem ler o texto
desde o começo; quem executa chega pelo meio.

**Termo da casa com o nome comum ao lado,** na primeira vez em que aparece, mesmo dentro
de um passo.

**Sem log.** O guia que este substituiu, o card que o criou, o mapa que aponta para ele e
como era antes ficam fora. O processo diz como se faz hoje.

## Antes de gravar

Confira, nesta ordem:

1. Quem nunca fez, seguindo só os passos, chega ao resultado sem perguntar a ninguém?
2. Cada passo tem um ato só, e acaba onde o trabalho poderia mudar de mão?
3. Onde um passo pode falhar, ou não deixar olhar, ele diz o que fazer ali mesmo?
4. A ordem está dita só onde importa?
5. O resultado que fecha tem um sinal que se confere, e «não consegui olhar» aparece
   diferente de «deu certo»?
6. Alguma regra virou passo, ou algum como de etapa que tem procedimento próprio está
   aqui?
7. Quem chegou aqui sabe, pelo Quando serve, se este é o processo certo?
8. Alguma frase repete o que a ficha mostra, ou conta como era antes?
