---
name: prosa
description: Use antes de escrever ou revisar texto da casa (documento ou rascunho no repositório da casa, corpo de card ou comentário no rastreador). NÃO dispare para resposta de chat, nota sem destino, dado, código ou frontmatter.
---

# Prosa

Escrever cada seção pela função dela, na ocasião e na densidade do texto, e passar o texto pelo loop e pelos gabaritos antes de gravar, nos passos abaixo.

O texto da casa existe para quem chega depois ler e fazer o que ele descreve, sem
falar com quem o escreveu. O que o texto é, que gênero segue e que seções tem, você lê
no catálogo da casa. Como escrevê-lo está nesta pasta: este passo a passo, a régua de
cada função em `funcoes/`, a de cada ocasião em `ocasioes.md`, a de cada densidade em
`densidades.md`, a de cada seção do card em `card.md` e os gabaritos (as listas que se
conferem contra o texto pronto) em `gabaritos/`.

## Onde vale

- **Documento de uma classe da casa** (instância, referência ou verbete): vale inteira.
- **Rascunho de um documento desses**, como o estudo antes do parecer ou a referência
  antes de gravada: vale inteira, pela régua do tipo que ele vai virar, que quem escreve
  decide antes de começar.
- **Insumo de card:** vale inteira, pela régua da classe de documento que ele vai virar
  (declarada em `vira`: parecer, levantamento ou referência). Nasce fora dos comentários
  como rascunho próprio com histórico de edições, sem prefixos de comentário (`insumo:`,
  `Traz:`, `Onde:`).
- **Corpo de épico e de feature, item do inventário da feature e comentários:** valem a
  voz, o núcleo, os gabaritos e a redação de `card.md`. O que entra em cada seção vem da
  classe, e as ligações do comentário (ato, destinatário, alvo, apoio, resposta e revisão)
  vão como dado estruturado.
- **Corpo de story e de task:** valem a voz, o núcleo e os gabaritos. A forma sai de
  `tarefas modelo`.
- **Resposta de chat e nota sem documento de destino:** não vale.
- **Dado, código e frontmatter:** não vale.

## Passos

1. Leia a classe do documento no catálogo: `infra rodar ontologia -- ler <classe>`.
   Dela saem o gênero (`genero`), as seções (as restrições de tipo `secao`, com
   rótulo, mínimo, escrita e régua) e o caminho do arquivo (`golden` ou
   `referencia`).
2. Leia o gênero: `infra rodar ontologia -- ler dicionario genero-de-prosa`. A
   definição de cada valor diz a combinação que ele nomeia: as funções, a ocasião e a
   densidade. O gênero da classe é o padrão, e o uso do texto pode pedir outro: o
   procedimento escrito para quem executa com o serviço fora do normal segue o runbook.
3. Fixe a ocasião e a densidade do texto. As do gênero são o padrão, e você as troca
   quando o caso pede: o relatório sobre uma vulnerabilidade recém-publicada se escreve
   sob pressão e exaustivo. Leia a ocasião em `ocasioes.md` e a densidade em
   `densidades.md`.
4. Escreva as seções que a shape declara, na ordem dela. A de mínimo 1 entra sempre; a
   de mínimo 0, só se muda o que o leitor faz. A de escrita `derivado` não se escreve à
   mão: ela sai de outra fonte.
5. Dê a cada seção uma função só e escreva pela régua de `funcoes/<função>.md`. A régua
   da seção, quando a shape a dá, diz o que entra; a função diz como se escreve. Quando
   as duas brigam, vale a régua da seção, que é a mais específica. A referência da
   classe (`referencias/classes/<classe>.md`) pode trazer régua de seção, como a de
   capacidade traz, e ela vale como a da shape.
6. Quando a shape não declara as seções de que o texto precisa, monte-as pelas funções
   do gênero e diga ao dono que a classe não as declara. Seção sem função clara se
   escreve pelo núcleo e pela voz: não invente régua por analogia.
7. Passe o texto pelo loop, nesta ordem:
   - tire o log: histórico, bibliografia, ponteiro e referência (terceiro modo de
     falha, abaixo);
   - tire as marcas que atrapalham entender, pela primeira parte de
     `gabaritos/marcas-pt-br.md`;
   - faça o leitor entender de verdade: seção que não muda nada sai, a frase afirma
     sem se comentar, termo da casa leva o nome comum ao lado na primeira vez;
   - ponha a voz da função de cada seção;
   - apare as marcas cosméticas, pela segunda parte de `gabaritos/marcas-pt-br.md`.
8. Rode os gabaritos que valem para o texto: `gabaritos/marcas-pt-br.md` em todo texto,
   `gabaritos/comportamento.md` em toda seção que induz e `gabaritos/card.md` no épico,
   na feature, no item do inventário e no comentário. O que um gabarito manda para
   outro lugar sai com o destino anotado, e o que muda de função se reescreve pela
   função nova.
9. Releia antes de gravar e responda duas perguntas. O texto ainda soa gerado, ou
   soa explicado só para uma IA? Ele somou ou perdeu algum fato, nome, número, data
   ou juízo? Se alguma resposta for sim, corrija antes de gravar.
10. Grave no caminho que a classe declara, pela seção Nome de arquivo.

## Os três modos de falha

O texto erra de três jeitos, e os três são fáceis:

1. Cortar demais e achar que explicou. O modelo se dá por satisfeito onde quem lê de
   fora ainda não entendeu. O teste é essa pessoa conseguir fazer o que o texto
   descreve.
2. Deixar marca de máquina: jargão, vitrine e enchimento, que denunciam quem escreveu
   e cansam quem lê.
3. Encher o texto de log. Prosa não é log. Histórico (o que mudou, quem decidiu,
   quando, por que antes era diferente), bibliografia, ponteiro para outro documento,
   número de card ou de documento e «ver também» ficam fora do texto. Eles
   entram porque parecem importantes, e por isso o erro passa sem ser visto: o texto
   cresce, e quem lê precisa garimpar o que vale agora. O texto diz o que é e como se
   faz hoje. O caminho até aqui já mora no git, no card e nas ligações da ficha, e
   não se copia para cá.

Toda passada mira o meio entre os dois primeiros e não cede no terceiro. A densidade
diz onde fica esse meio em cada texto.

## A ordem que decide

Quando duas regras brigam, a de cima vence:

1. O leitor sai fazendo.
2. O leitor entende. O jargão de IA se resolve aqui, porque é o que mais atrapalha.
3. A voz da função: direta, começando pela coisa.
4. Sem marca cosmética: aspas de ênfase, caixa de título, emoji, negrito solto,
   travessão fora de enumeração.

## Duas travas

- Não invente fato. Nome, número, data e citação vêm da fonte ou de quem pediu o
  texto. Falta o detalhe? Pergunte, ou escreva a frase mais simples que não precisa
  dele.
- Mexa só na prosa. Dado, código, frontmatter, seção derivada e alvo de link ficam
  como estão.

## O núcleo

O que todo texto da casa cumpre, seja qual for o gênero:

- **Uma ideia por parágrafo**, de até quatro linhas na tela. Parede de texto é falta.
- **Lista, e nunca tabela.** Três itens ou mais viram lista, um por linha: numerada
  quando é sequência, com letra quando são opções, com marcador nos outros casos. A
  tabela empurra quem escreve a criar coluna para caber, e a coluna se enche do que o
  leitor não usa. O item com mais de uma parte abre pelo nome em negrito e diz o resto
  em frase. Fica de fora só o dado que uma máquina lê na forma de tabela, que não é
  prosa.
- **Sem log.** Nem histórico, nem bibliografia, nem ponteiro, nem referência. O único
  link que fica é o que o leitor precisa abrir para fazer o que o texto manda; ele
  leva o nome do alvo como texto, e entre documentos da casa é relativo ao arquivo.
- **Seção que não muda o que o leitor faz sai.**
- **Termo da casa com o nome comum ao lado** na primeira vez em que aparece.
- **Voz assertiva.** O texto afirma, no presente ou no passado, em frase declarativa.
  A frase não se comenta: não diz de onde veio, quão segura é, se foi medida ou
  declarada, nem que é palpite de quem escreve. A procedência mora em Fontes e na
  ficha. A hipótese que muda o que o leitor faz vira frase própria, uma vez, com o
  que a confirmaria. Sai o qualificador espalhado: «declarado, não medido», «medido
  pela parte interessada», «inferência minha», «hipótese minha, a confirmar», «é
  provável que», «tudo indica». Adjetivo de juízo sem evidência sai.
- **Sem citação no meio da frase.** Nem «segundo fulano», nem nota numerada. A
  densidade exaustiva é a exceção, e `densidades.md` diz como.

## O que o site já mostra

Todo documento abre com a ficha dele, que o site monta do banco com os campos e as
ligações que a shape declara. O texto não repete nada da ficha, nem com outras
palavras: começa onde ela para.

## Fontes

Fontes é seção derivada, e quem escreve não escolhe o que entra nela. Ela tem duas
origens:

- as ligações da ficha do documento, que o site monta na leitura;
- a obra de cada trecho da biblioteca que o texto usou pelo motor. Ao usar um trecho,
  grave em Fontes a obra que a proveniência do trecho dá, como está lá.

Nada mais entra em Fontes, e nada de Fontes volta para o meio do texto.

## Formas de outro dono

- **Card e comentário:** o que entra em cada seção do épico, da feature e do comentário
  está na classe dele, e `tarefas modelo` serve o mesmo. Daqui vêm a voz, o núcleo, os
  gabaritos e a redação de cada seção, em `card.md`. Antes de pedir parecer sobre o
  card, rode `lint card <card>` e corrija o que ele aponta: ele confere a forma, avisa e
  não segura a ida a parecer. A story e a task seguem `tarefas modelo`.
- **Política:** a forma é da skill de redação normativa, que roda antes. Daqui vem a
  voz, e cada dispositivo que obriga segue `funcoes/obrigar.md`.

## Nome de arquivo

O caminho do arquivo sai da classe no catálogo, no campo `golden` ou `referencia`
(`infra rodar ontologia -- ler <classe>`): instâncias ficam em
`instancias/<classe>/<chave>.md` e referências ficam em
`referencias/instancias/<classe>/<chave>.md` (observação, parecer, levantamento e
fichamento levam a data na frente da chave, `referencias/instancias/<classe>/<AAAA-MM-DD>-<slug>.md`).

O documento de chave numerada, como a política, leva o número e o trecho
do título: `<número>-<trecho>.md`. O trecho é o título em slug: minúsculas, sem
acento, palavras ligadas por hífen, sem artigo no começo. Ele se fixa quando o
documento nasce e não muda quando o título é retocado.
