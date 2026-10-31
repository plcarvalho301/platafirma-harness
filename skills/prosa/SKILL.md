---
name: prosa
description: Use SEMPRE que for escrever ou revisar texto da casa que uma pessoa vai ler: documento em qualquer pasta do repositório da casa, corpo de card ou comentário no rastreador, mesmo que ninguém peça revisão de texto. Siga as instruções ANTES de gravar, commitar ou enviar. NÃO dispare para resposta de chat, nem para dado, código ou frontmatter.
---

# Prosa

O texto da casa existe para quem chega depois ler e fazer o que ele descreve, sem
falar com quem o escreveu. Tudo de que você precisa para escrevê-lo está nesta pasta:
este passo a passo, os moldes em `moldes/`, os gabaritos em `gabaritos/` e as marcas de máquina em
`marcas-pt-br.md`. Nada se consulta fora dela.

## Passos

1. Ache a entidade do documento na tabela Gênero de cada entidade, no fim desta
   página, e abra `moldes/<gênero>.md`.
2. Escreva as seções do molde na ordem, junto com as que o molde diz que a sua
   entidade acrescenta. A seção opcional entra só se muda o que o leitor faz. A seção
   derivada não se escreve à mão: ela sai de outra fonte.
3. Seção que o molde não regula se escreve pelo núcleo e pela voz. Não invente régua
   por analogia.
4. Passe o texto pelo loop, nesta ordem:
   - tire o log: histórico, bibliografia, ponteiro e referência (terceiro modo de
     falha, abaixo);
   - tire o jargão e o estilo de IA que atrapalham entender, pelo catálogo de
     `marcas-pt-br.md`;
   - faça o leitor entender de verdade: seção que não muda nada sai, fato fica
     separado de palpite, termo da casa leva o nome comum ao lado na primeira vez;
   - ponha a voz da casa;
   - apare a marca cosmética que sobrou.
5. Se houver `gabaritos/<gênero>.md`, rode-o sobre o texto: o que não é do gênero sai
   para o destino que ele dá, e o que mudou de parte se reescreve pelo molde.
6. Releia antes de gravar e responda duas perguntas. O texto ainda soa gerado, ou
   soa explicado só para uma IA? Ele somou ou perdeu algum fato, nome, número, data
   ou juízo? Se alguma resposta for sim, corrija antes de gravar.
7. Dê nome ao arquivo pela seção Nome de arquivo.

## Os três modos de falha

O texto erra de três jeitos, e os três são fáceis:

1. Cortar demais e achar que explicou. O modelo se dá por satisfeito onde quem lê de
   fora ainda não entendeu. O teste é essa pessoa conseguir fazer o que o texto
   descreve.
2. Deixar marca de máquina: jargão, vitrine e enchimento, que denunciam quem escreveu
   e cansam quem lê.
3. Encher o texto de log. Prosa não é log. Histórico (o que mudou, quem decidiu,
   quando, por que antes era diferente), bibliografia, ponteiro para outro documento,
   número de card ou de registro de decisão e «ver também» ficam fora do texto. Eles
   entram porque parecem importantes, e por isso o erro passa sem ser visto: o texto
   cresce, e quem lê precisa garimpar o que vale agora. O texto diz o que é e como se
   faz hoje. O caminho até aqui já mora no git, no card e nas ligações da ficha, e
   não se copia para cá.

Toda passada mira o meio entre os dois primeiros e não cede no terceiro.

## A ordem que decide

Quando duas regras brigam, a de cima vence:

1. O leitor sai fazendo.
2. O leitor entende. O jargão de IA se resolve aqui, porque é o que mais atrapalha.
3. A voz da casa: direta, começando pela coisa.
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

- **Uma ideia por parágrafo**, de até quatro linhas na tela. Três itens ou mais viram
  lista, um por linha. Parede de texto é falta.
- **Sem log.** Nem histórico, nem bibliografia, nem ponteiro, nem referência. O único
  link que fica é o que o leitor precisa abrir para fazer o que o texto manda; ele
  leva o nome do alvo como texto, e entre documentos da casa é relativo ao arquivo.
- **Seção que não muda o que o leitor faz sai.**
- **Termo da casa com o nome comum ao lado** na primeira vez em que aparece.
- **Fato separado de inferência.** O que se sabe vai no presente ou no passado; o que
  se infere vai marcado («é provável que»); adjetivo de juízo sem evidência sai.
- **Sem citação no meio da frase.** Nem «segundo fulano», nem nota numerada.

## O que o site já mostra

Todo documento abre com a ficha dele, que o site monta do banco, com as ligações. O
texto não repete nada da ficha, nem com outras palavras: começa onde ela para. Cada
molde diz o que a ficha do gênero mostra.

## Fontes

Fontes é seção derivada, e quem escreve não escolhe o que entra nela. Ela tem duas
origens:

- as ligações da ficha do documento, que o site monta na leitura;
- a obra de cada trecho da biblioteca que o texto usou pelo motor. Ao usar um trecho,
  grave em Fontes a obra que a proveniência do trecho dá, como está lá.

Nada mais entra em Fontes, e nada de Fontes volta para o meio do texto.

## Formas de outro dono

- **Card e comentário tipado:** a forma sai de `tarefas modelo`. Daqui vem só a voz.

## Nome de arquivo

O arquivo mora em `<n>-<estrato>/<entidade>/<chave>.md`: a pasta numerada do estrato
da entidade, a pasta da entidade e a chave da instância.

O documento de chave numerada (registro de decisão, política interna) leva o número e
o trecho do título: `<número>-<trecho>.md`. O trecho é o título em slug: minúsculas,
sem acento, palavras ligadas por hífen, sem artigo no começo. Ele se fixa quando o
documento nasce e não muda quando o título é retocado.

## Gênero de cada entidade

| gênero | entidades |
|---|---|
| formal | conceito, página de entidade, página de vocabulário |
| comportamento | persona, chapéu, postura, cenário, circunstância, ritual |
| gatilho | gatilho, gabarito |
| compromisso | contrato, contrato da porta, integração, interface, plano, pacto de serviço |
| norma | padrão, cultura |
| processo | processo, ciclo, guia, procedimento, hábito, heurística |
| observacao | observação, parecer, levantamento, fichamento |
| construcao | serviço, stack, host, motor, verbo, automação, delegação, repositório, capacidade, conjunto de dados |

Peça sem documento próprio se escreve no documento do todo: componente, substrato,
lousa, memória e configuração vão no documento do serviço que os opera (ou da stack,
quando são parte direta dela); exposição vai no serviço, na seção do que ele expõe.

Card e seus níveis (épico, feature, story, incidente, task, débito técnico) e
comentário seguem `tarefas modelo`. Entidade fora desta tabela não tem prosa da casa.
