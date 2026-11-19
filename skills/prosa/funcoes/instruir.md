# Instruir

A seção que instrui leva quem executa de uma entrada a um resultado que se confere, ou a
um achado. Vale só na vez de cada passo, e acaba no resultado. É a função do
procedimento, da missão, da exploração e da instrução, e a regra de conduta só no
procedimento adotado, em que desviar da ordem escrita é falta.

Três leitores chegam ao texto. O primeiro é quem executa, no meio do trabalho, com a
coisa na mão: chegou porque um gatilho disparou, e lê o passo em que está. O segundo é
quem recebe o resultado e precisa saber o que vem pronto. O terceiro é o dono, que volta
quando o processo travou, para achar o passo que faltou ou a passagem mal definida.

## O que o texto de um processo cobre

A shape diz as seções. Quando ela não as declara, o texto cobre estes pontos.

### Quando serve

- **A situação que pede o processo, e a entrada pronta.** O que aconteceu e o que
  precisa estar na mão para começar.
- **O vizinho que se confunde,** e o que separa os dois.
- **Quando não serve.** A situação que parece pedir o processo e não pede.

### Passos

- **Um ato por passo, começando pelo verbo.** «Rode», «abra», «grave».
- **O passo acaba onde o trabalho poderia mudar de mão.** O que nunca muda de mão é um
  passo só, por mais atos de ferramenta que tenha.
- **A ordem só onde importa.** Quando dois passos podem vir em qualquer ordem, diga.
- **Quem faz e o que passa adiante, quando muda.**
- **A falha no passo em que acontece.** «Não consegui olhar» não é «deu certo», e o
  passo diz o que cada um autoriza.
- **A escolha vira opções com letra.** Quando o passo depende de uma pergunta, cada
  resposta vira um item, (a), (b), (c), com o sinal que a reconhece e o caminho que ela
  abre. Diga se a primeira que casa decide.
- **O ato da ferramenta escrito como se chama,** literal, pronto para copiar.

### Os dois ganchos de cada passo

Todo passo que toca algo da casa tem dois ganchos em volta do comando. É por eles que o
texto fica curto sem deixar quem executa às cegas: o conteúdo chega na hora, e o texto
só diz quando ir buscá-lo.

- **O gancho de busca, antes do comando.** A chamada que acha o estado vivo do que o
  passo vai tocar, ou a regra que decide o passo. O termo da busca é o nome da classe
  que o passo toca (componente, teste, mudança), porque o nome casa direto com a ficha;
  a frase livre fica para o que só aquele passo pede. O passo diz o que fazer quando a
  busca volta vazia.
- **O gancho de conferência, depois de todo comando que escreve.** A chamada que
  confere o resultado contra o que está no ar, e o que cada saída autoriza. O que o
  processo não conferiu no ar não está feito.

A recusa do verbo já traz a próxima chamada. O passo manda segui-la, e não lista as
recusas nem as curas.

### O que fica no texto

O padrão de uma classe, a cura de cada recusa e a regra de outro documento chegam pela
busca e pelo verbo, e não se copiam. Fica só o que é deste processo e de nenhum outro:

- o critério que fecha cada passo ou etapa;
- a ordem, onde ela importa;
- quando parar de buscar, e qual apoio vale quando dois divergem;
- o que não se faz, como contornar o verbo;
- a passagem ao processo seguinte, pelo nome. O processo cujo resultado só serve no ar
  termina passando a vez a quem o põe no ar.

O teste de cada linha: se ela vale para qualquer processo que toque aquela classe, mora
na classe e chega pela busca. Se vale só para este, fica.

Na missão, as etapas seguem a régua dos passos, menos a ordem, que fica com quem
executa, e cada etapa leva o critério que a fecha. Na exploração, o texto diz por onde
procurar, quando parar e o que fazer com o que se achou. A instrução é uma etapa só: o
que ler antes do comando, e o comando, de modo que quem a siga chegue ao mesmo
resultado.

O marco que fecha o processo é da função conferir.

Exemplo:

- Ruim: «Verificar o estado do serviço e tomar as providências necessárias.»
- Bom: «Rode `release conferir servico <nome>`. Saída 0: siga. Saída 1: o serviço
  diverge do que o compose declara; abra o incidente. Saída 5: não deu para olhar, e
  isso não autoriza promover.»

## Como escrever

- **Fica fora:** a regra que vale em qualquer passo, que é de obrigar e entra só no
  passo em que decide; o como de uma etapa que tem instrução própria; o porquê longo de
  o processo ser assim.

## Antes de gravar

1. Quem nunca fez, seguindo só os passos, chega ao resultado sem perguntar a ninguém?
2. Cada passo tem um ato só, e acaba onde o trabalho poderia mudar de mão?
3. Onde um passo pode falhar, ou não deixar olhar, ele diz o que fazer ali mesmo?
4. A ordem está dita só onde importa?
5. Quem chegou aqui sabe, pelo Quando serve, se este é o processo certo?
6. Cada passo que toca algo da casa tem o gancho de busca antes do comando, e cada
   comando que escreve tem o de conferência depois?
7. Alguma linha repete o que a busca ou a recusa do verbo já devolvem? Se repete, sai.
