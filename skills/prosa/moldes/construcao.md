# Molde construção

O gênero construção é o texto de uma peça construída: o serviço, a stack, o host, o
motor, o verbo, a automação, a delegação, o repositório, a capacidade e o conjunto de
dados. A peça existe e se mede; o texto a situa no todo da casa, diz para que ela
serve, por que é como é e o que só quem a construiu sabia. Diferente do compromisso,
que promete e pode ser descumprido, a construção descreve: a frase só pode estar errada,
e se confere contra o que está declarado e o que está rodando.

A declaração da peça (o compose, a unit, o executável em `bin/`, o arquivo de agente) é
o golden, e o documento é referência sobre ela. Isso decide o que entra no texto: nada
do que a declaração diz se reescreve, e o que a declaração não consegue dizer é o que o
texto carrega. O teste é apagar a frase: se a declaração ou a medição a devolvem, ela
sobra.

Três leitores chegam ao texto. O primeiro chega de fora da técnica, o dono ou uma
cadeira de outra matéria, e precisa saber onde a peça está no todo, para que serve e o
que para se ela cair, sem abrir o código. O segundo vai mexer nela, operar, mudar ou
substituir, e precisa do que não está na declaração: a regra que não se vê, a alavanca,
o que não volta. O terceiro volta quando algo quebrou, para saber o que a peça deveria
ser e como se olha se ela está assim.

## O que a ficha já mostra

O site abre o documento com a ficha, montada do banco e da declaração. Nada dela se
escreve no texto, nem com outras palavras.

A ficha mostra a chave, o rótulo, a definição da classe, o estado e as ligações: a
stack de que a peça é parte, o host e o substrato em que aloca, os contratos que expõe
e consome, os componentes que a constituem, a capacidade que serve. Mostra também o que
a declaração já diz, montado na leitura, e o que é medido: a imagem corrente, a release,
o host em que roda, a memória que consome, o endereço em que atende. Medido não se copia
para o texto: o número envelhece calado.

O texto começa onde a ficha e a declaração param. Elas dizem o que a peça é e de que é
feita, em dado; o texto diz o que isso significa para quem a usa e para quem a opera.

## O que é

A peça no todo da casa, para quem chega de fora.

- **Primeira frase: o que a peça faz pela casa,** em palavras comuns, já situada.
  Não é a definição da classe, que a ficha mostra, nem o nome da tecnologia: é o
  trabalho que ela faz.
- **O lugar no todo.** De quem recebe e a quem serve, dito pelo que passa por ela, e não
  pelo nome das ligações, que a ficha lista. E o que para se ela cair, só o efeito que
  mais pesa, numa frase: é a medida mais rápida do peso da peça.
- **Por que é assim: a razão arquitetural.** A força que dá à peça a forma que ela
  tem: o problema que ela resolve, a restrição que a molda (do domínio, da escala, da
  segurança, do custo), a qualidade que ela privilegia e o que cede em troca, a
  alternativa que ela vence. A razão é verdadeira enquanto a peça for assim, e se a
  força some, a peça pode mudar. Quem mandou, quando e em que card não é razão: é log,
  e sai. O teste é a frase continuar valendo para quem nunca viu o card, a ata nem a
  conversa. Cabe em até três frases: a força principal, uma alternativa vencida (a que
  mais se confundiria com esta) e o que se cede em troca. Razão que discute cada
  alternativa descartada vira ensaio e esconde a força que importa. A posição da casa
  vai marcada como posição.
- **O que não faz de propósito.** A coisa que parecia caber e foi deixada de fora, com a
  razão em uma linha. É a decisão que não deixa rastro em lugar nenhum da peça, e por
  isso é a que o próximo operador «conserta» sem saber.
- **O vizinho que se confunde,** quando a confusão é real: o motor que parece serviço
  comum, a lousa que parece memória.
- **Fica fora:** a definição da classe, o endereço, a tecnologia pelo nome quando o
  trabalho se diz sem ela, e a crônica de como a peça chegou aqui.

Exemplo de primeira frase:

- Ruim: «O montador é um serviço Python da stack porta que roda em contêiner.»
- Bom: «O montador junta, a cada abertura de sessão, o pacote de contexto que a cadeira
  recebe antes de trabalhar: persona, conduta, rotinas e o que ficou na mesa.»

Exemplo de razão:

- Ruim: «A lousa usa Valkey porque o card de memória de trabalho decidiu assim.»
- Bom: «A lousa guarda o estado fora do processo do harness porque a sessão atravessa
  mais de um processo e mais de uma superfície; com o estado dentro do processo, a
  cadeira perderia o que estava ativo a cada troca.»

## De que é feito

As partes da peça que a declaração não explica.

- **Só a responsabilidade e a morada.** Por parte, o que ela faz numa frase e onde o
  código ou o arquivo mora. O que a parte faz, não como: quem quiser o como abre o
  código, que a morada aponta.
- **O segredo dito pelo lado de fora.** Cada parte esconde um jeito de fazer. O texto
  diz o que quem usa a parte não precisa saber, e não o explica.
- **Tabela para enumerar.** Parte, responsabilidade e morada, uma linha por parte,
  quando são três ou mais. A prosa fica com o que a tabela não diz: como as partes se
  juntam.
- **A peça sem documento próprio mora aqui.** Componente, substrato, configuração, lousa
  e memória de um serviço se descrevem no documento dele; o que é parte direta da stack,
  sem serviço que o embarque, no documento dela. Biblioteca que constitui mais de uma
  peça se cita pelo nome e se descreve uma vez, no documento de quem a mantém.
- **Quando a entidade acrescenta seção para uma parte** (Componentes, Substratos,
  Configuração), esta seção diz num parágrafo como as partes se juntam e deixa a lista
  para a seção da entidade. Cada parte num lugar só.
- **Fica fora:** o nome da imagem, a porta, o volume e tudo o que o compose declara; a
  versão que roda, que é medida; o valor de configuração, que mora no arquivo; o segredo,
  que se cita pela referência e nunca pelo valor.

Exemplo de parte:

- Ruim: «Usa o Valkey 7.2 na porta 6379 como banco chave-valor para cache.»
- Bom: «A lousa guarda, fora da janela de contexto, o que a sessão precisa ter ativo e
  expira com ela; mora em `harness/lousa/`. Quem a usa não precisa saber onde o estado
  está nem como expira.»

## O que expõe

A face da peça para fora, por onde outros a usam.

- **Uma linha por face,** nomeada pelo que o outro lado faz com ela (ler o catálogo,
  tombar uma obra) e não pelo mecanismo, dizendo a quem serve e para quê. Os contratos a ficha liga, e
  operação, erro e nível prometido moram neles; aqui vai só o que cada face é para quem
  está do outro lado.
- **O que atravessa a fronteira sem contrato** entra aqui: o arquivo que a peça grava
  para outra ler, o evento que emite, a fila em que deposita. É o que mais surpreende
  quem muda a peça, porque ninguém o prometeu e alguém conta com ele.
- **O que a peça consome** de fora, pelo mesmo critério: de quem depende para funcionar
  e o que acontece se a fonte falta.
- **Fica fora:** endereço e zona, que são dado da exposição e medidos; a tabela de rotas
  e de erros, que é do contrato.

## Como roda

O que quem opera precisa saber, e que a declaração não diz.

- **Em que forma roda e em que ordem sobe,** só onde a ordem importa: o que precisa estar
  no ar antes, o que ela espera para começar.
- **O que só quem construiu sabe.** A regra que não está escrita em lugar nenhum da
  declaração: a ordem obrigatória entre dois atos, o invariante que o código assume, a
  armadilha em que o operador cai. O teste de cada frase: lendo só a declaração e a
  ficha, você não saberia disto.
- **As alavancas.** Por ajuste que a peça lê: o que ele decide, a faixa em que faz
  sentido e o que acontece para menos e para mais. O valor de hoje é medido e não se
  copia. Alavanca descrita só como «dá para subir» induz a levar ao máximo. Entra só a
  alavanca que a casa decide para esta peça; o parâmetro de fábrica da tecnologia, que
  todo operador dela conhece, fica fora.
- **O que não volta com o código.** O volume, a migração de esquema, o arquivo que outra
  peça já leu, o contrato que outra tela consome. É o que separa reverter de refazer.
- **Quando adoece.** O sinal de que não está bem e o primeiro lugar a olhar, em até um
  parágrafo. O passo a passo de voltar é do processo; aqui vai o que faz quem opera
  reconhecer que precisa dele.
- **Fica fora:** o passo a passo de subir e de voltar, que é processo; o valor de
  configuração e o segredo; o número medido.

Exemplo de regra:

- Ruim: «O serviço deve ser operado com cuidado para manter a consistência do índice.»
- Bom: «A geração nova do índice sobe em sombra e só vira depois de medida; virar sem
  medir apaga a geração que servia, e não há volta sem reindexar.»

## Como se confere

Como se olha se a peça está como o texto e a declaração dizem.

- **O ato que mede, escrito como se chama,** pronto para copiar. É o caminho mais curto
  até saber.
- **Três resultados, não dois.** Conforme, divergente e «não consegui olhar». O terceiro
  não é o primeiro, e o texto diz o que cada um autoriza.
- **A divergência esperada separada da que é alarme.** O que diverge por desenho (a
  cópia que se regenera, o apelido que aponta outro digest) não é defeito; o texto diz
  qual divergência manda abrir incidente.
- **Quando há gabarito, só o marco.** Os itens são do gabarito, e repetidos aqui ficam
  velhos lá.
- **Fica fora:** o número medido, que envelhece; o resultado da última conferência, que é
  observação.

## Seções de cada entidade

O gênero declara O que é, De que é feito, O que expõe, Como roda e Como se confere. As
seções que cada entidade acrescenta têm a régua da dona dela; aqui vai só o nome, e
onde ela entra:

- **serviço:** Interface (derivada), em O que expõe; Substratos, Componentes e
  Configuração, em De que é feito.
- **stack:** O que aloca (derivada), em De que é feito; Componentes, em De que é feito;
  Como se promove e reverte, em Como roda.
- **host:** Eixos e tetos (derivada) e O que hospeda (derivada), em De que é feito;
  Acesso e recuperação, em Como roda.
- **verbo:** Capacidade servida, Atos com entrada e saída, e Códigos de saída (derivadas),
  em O que expõe; O que trava, em Como roda.
- **delegação:** O que não faz, em O que é; Teto, em Como roda.
- **motor, automação, repositório, capacidade e conjunto de dados:** nenhuma.

A seção da entidade entra depois da seção do gênero que ela detalha, e o gênero não
repete o que ela traz.

## Como escrever

**A declaração é o golden; o texto é referência.** Nada que o compose, a unit, o
executável ou o arquivo de agente dizem se reescreve. O que eles não dizem é o que o
texto carrega. Quando a peça muda, o documento se reescreve no lugar: ele diz o que a
peça é hoje, e o que ela foi está no git.

**O que, não o como.** O texto dá a abstração: o que a peça e cada parte fazem, para
quem olha de fora. O como mora no código, e a morada o aponta. A exceção é a regra que
o código assume e não mostra, que vai em Como roda.

**Para quem não é técnico, sem perder o técnico.** Termo da casa com o nome comum ao
lado na primeira vez, mesmo em seção que só o operador vai ler; a stack é lida também
por quem decide o que construir.

**O nome comum não colide com o da casa.** Quando a palavra comum para a tecnologia é
também o nome de uma entidade da casa (motor, componente, contrato, substrato), escolha
outra: «o banco relacional», e não «o motor relacional», que na casa é outra coisa.

**A palavra do molde é régua, não texto.** «O segredo que a peça esconde», «atravessa a
fronteira sem contrato» e «o que só quem construiu sabe» dizem o que procurar; no
texto, diga a coisa achada, com as palavras dela.

**Medido não se copia.** Imagem, release, host, memória, endereço e número de qualquer
coisa são servidos e a ficha mostra. O número copiado envelhece calado e vira a frase
em que ninguém mais confia.

**Tabela para enumerar.** Partes, faces e alavancas vão em tabela quando são três ou
mais, uma linha por item. A prosa fica com o que a tabela não diz.

**Sem log.** O card que criou a peça, o nome antigo, «depois da virada» e como se
chegou a este desenho ficam fora. A razão arquitetural entra; a crônica não, nem
quando vem disfarçada de porquê («porque o dono decidiu em tal data»).

## Antes de gravar

Confira, nesta ordem:

1. Quem não é técnico, lendo só O que é, sabe onde a peça está, para que serve e o que
   para sem ela?
2. Cada frase diz algo que a declaração, a ficha ou a medição não dizem? Apague a que a
   declaração devolve.
3. O porquê é razão arquitetural (problema, restrição, qualidade privilegiada,
   alternativa vencida) e continua valendo para quem nunca viu o card nem a conversa?
   Algum «porque fulano decidiu» ou «porque o card mandou» ficou? Cabe em até três
   frases, com uma alternativa só, e o efeito de cair em uma?
4. O que a peça não faz de propósito está dito, com a razão?
5. Cada parte tem responsabilidade e morada, e aparece num lugar só?
6. Quem vai operar acha em Como roda o que só quem construiu sabia, e cada frase dali
   passa no teste de não estar na declaração?
7. Cada alavanca diz o que decide e o que acontece para menos e para mais, e é uma que a
   casa decide para esta peça, não parâmetro de fábrica da tecnologia?
8. Como se confere dá o ato pronto para copiar e separa conforme, divergente e «não
   consegui olhar»?
9. Algum número medido, endereço, nome de imagem, valor de configuração ou segredo
   está no texto? Alguma frase conta como era antes?
10. Algum nome comum colide com o de uma entidade da casa, ou alguma expressão do
    molde («o segredo que esconde», «sem contrato») virou frase do texto?
