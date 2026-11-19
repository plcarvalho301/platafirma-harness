# Descrever

A seção que descreve diz como uma coisa é hoje: para que serve, de que é feita e por que
é assim. É a função do texto de uma peça construída (serviço, stack, host, motor, verbo,
automação, delegação, repositório, conjunto de dados), da referência de capacidade e de
qualquer instância que existe e se confere.

Descrever não promete: a frase só pode estar errada, e se confere contra a coisa, no
que está declarado e no que está rodando. A declaração da coisa (o compose, a unit, o
executável, a shape) é o golden, e o texto é referência sobre ela. Nada que a
declaração diz se reescreve; o que ela não consegue dizer é o que o texto carrega. O
teste é apagar a frase: se a declaração ou a medição a devolvem, ela sobra.

Três leitores chegam ao texto. O primeiro chega de fora da técnica, o dono ou uma
cadeira de outra matéria, e precisa saber onde a coisa está no todo, para que serve e o
que para se ela cair. O segundo vai mexer nela e precisa do que não está na declaração:
a regra que não se vê, a alavanca, o que não volta. O terceiro volta quando algo
quebrou, para saber o que a coisa deveria ser.

## O que a descrição de uma peça cobre

A shape diz as seções. Quando ela não as declara, a descrição de uma peça cobre estes
pontos, nesta ordem. Cada ponto mora num lugar só.

### O lugar no todo

- **Primeira frase: o que a peça faz pela casa,** em palavras comuns, já situada. Não é
  a definição da classe nem o nome da tecnologia: é o trabalho que ela faz.
- **De quem recebe e a quem serve,** dito pelo que passa por ela, e não pelo nome das
  ligações, que a ficha lista. E o que para se ela cair, só o efeito que mais pesa.
- **Por que é assim,** em até três frases: a força que dá à peça a forma que ela tem
  (o problema, a restrição de domínio, escala, segurança ou custo, a qualidade que ela
  privilegia), uma alternativa vencida e o que se cede em troca. Quem mandou e em que
  card não é razão: é log.
- **O que não faz de propósito,** com a razão em uma linha. É a decisão que não deixa
  rastro na peça, e por isso a que o próximo operador «conserta» sem saber.
- **O vizinho que se confunde,** quando a confusão é real.

Exemplos:

- Ruim: «O montador é um serviço Python da stack porta que roda em contêiner.»
- Bom: «O montador junta, a cada abertura de sessão, o pacote de contexto que a cadeira
  recebe antes de trabalhar: persona, conduta, rotinas e o que ficou na mesa.»
- Ruim: «A lousa usa Valkey porque o card de memória de trabalho decidiu assim.»
- Bom: «A lousa guarda o estado fora do processo do harness porque a sessão atravessa
  mais de um processo e mais de uma superfície; com o estado dentro do processo, a
  cadeira perderia o que estava ativo a cada troca.»

### As partes

- **Por parte, a responsabilidade e a morada.** O que ela faz numa frase e onde o
  código ou o arquivo mora. O que, não como: quem quiser o como abre o código.
- **O que quem usa a parte não precisa saber,** dito pelo lado de fora, sem explicar.
- **Lista quando são três ou mais,** um item por parte, aberto pelo nome dela, com a
  responsabilidade e a morada. A prosa fica com como as partes se juntam.
- **A peça sem documento próprio mora aqui.** Componente, substrato, configuração,
  lousa e memória de um serviço se descrevem no documento dele; o que é parte direta da
  stack, no documento dela. Biblioteca que constitui mais de uma peça se cita pelo nome
  e se descreve uma vez, no documento de quem a mantém.

### As faces

- **Uma linha por face,** nomeada pelo que o outro lado faz com ela («ler o catálogo»,
  «tombar uma obra»), e não pelo mecanismo. Operação, erro e nível prometido moram no
  contrato.
- **O que atravessa a fronteira sem contrato:** o arquivo que a peça grava para outra
  ler, o evento que emite, a fila em que deposita. Ninguém o prometeu, e alguém conta
  com ele.
- **O que a peça consome,** e o que acontece se a fonte falta.

### Como roda

- **A ordem de subir, só onde importa.**
- **O que só quem construiu sabe.** A ordem obrigatória entre dois atos, o invariante
  que o código assume, a armadilha em que o operador cai. Lendo só a declaração e a
  ficha, você não saberia disto.
- **As alavancas que a casa decide para esta peça:** o que cada uma decide, a faixa em
  que faz sentido e o que acontece para menos e para mais. Parâmetro de fábrica da
  tecnologia fica fora.
- **O que não volta com o código:** o volume, a migração de esquema, o arquivo que outra
  peça já leu.
- **Quando adoece:** o sinal de que não está bem e o primeiro lugar a olhar. O passo a
  passo de voltar é de instruir.

Exemplo:

- Ruim: «O serviço deve ser operado com cuidado para manter a consistência do índice.»
- Bom: «A geração nova do índice sobe em sombra e só vira depois de medida; virar sem
  medir apaga a geração que servia, e não há volta sem reindexar.»

Como se olha se a peça está como o texto diz é da função conferir.

## Como escrever

- **Medido não se copia.** Imagem, release, host, memória, endereço e número de
  qualquer coisa a ficha mostra. O número copiado envelhece calado.
- **O nome comum não colide com o da casa.** Quando a palavra comum é também nome de
  uma entidade da casa (motor, componente, contrato, substrato), escolha outra: «o
  banco relacional», e não «o motor relacional».
- **A palavra da régua não vira texto.** «O que só quem construiu sabe» diz o que
  procurar; no texto, diga a coisa achada, com as palavras dela.
- **Quando a peça muda, o texto se reescreve no lugar.** Ele diz o que a peça é hoje.

## Antes de gravar

1. Quem não é técnico, lendo só o lugar no todo, sabe onde a peça está, para que serve
   e o que para sem ela?
2. Cada frase diz algo que a declaração, a ficha ou a medição não dizem?
3. O porquê é razão que continua valendo para quem nunca viu o card, em até três
   frases, com uma alternativa só?
4. O que a peça não faz de propósito está dito, com a razão?
5. Cada parte tem responsabilidade e morada, e aparece num lugar só?
6. Algum número medido, endereço, imagem, valor de configuração ou segredo está no
   texto?
