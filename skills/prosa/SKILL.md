---
name: prosa
description: Use quando for ESCREVER ou REVISAR prosa da wiki (Inteligência de Base) antes de publicar — página nova, edição de página, ou passar um rascunho pela régua da casa. Orienta o agente que escreve. Implementa a spec do styleguide (platafirma-arquitetura/docs/spec_styleguide-da-wiki.md) e a régua servida na wiki (Operar:styleguide) — não tem régua própria. NÃO dispare para o acervo (obra tem proveniência própria), nem para mural/fila (push, régua própria), nem para produto acabado (informe, apreciação, estimativa). O par `conferir prosa` é o lint que CONFERE o que já está escrito; esta skill ORIENTA quem escreve.
cadeiras: todas (matéria de escrita da wiki). Dono da régua é produto (§5 da spec); dono da skill, como implementadora, é o arquiteto.
compatibility: régua canônica na spec, servida em Operar:styleguide (wiki viva); a conduta do dono (abertura/dono.md, no harness) é referência de voz, não isenção de regra. Roda antes de publicar página. Catálogo de marcas por extenso em reference/marcas-pt-br.md.
---

# Prosa — escrever para a wiki pela régua do styleguide

A régua da wiki não é apagar marca de máquina. É fazer quem chega depois ler uma
página e fazer o que ela descreve sem falar com quem a escreveu.

Escopo: só a wiki — Inteligência de Base, o que se usa para trabalhar e repassar
conhecimento entre pares. Não é acervo, não é mural, não é fila, não é produto
acabado.

## Os dois modos de falha

A skill vive entre dois erros, e os dois são fáceis de cometer:

1. **Cortar demais** e achar que explicou sem ter explicado. A barra de uma IA para
   «isto está claro» não é a de um humano: o modelo se dá por satisfeito onde o
   leitor de fora ainda não entendeu. O teste não é o teu senso — é a pessoa de fora
   responder a pergunta de fato (spec §6).
2. **Vazar estilo de IA:** deixar o jargão, a vitrine e o enchimento que denunciam a
   máquina e cansam quem lê.

Toda passada mira o meio: explica de verdade, sem soar a máquina.

## A ordem que decide tudo

Quando duas regras brigam, a de cima vence a de baixo:

1. **O leitor sai fazendo.** A página muda o que alguém consegue fazer.
2. **O leitor entende** — fato vs palpite. **O jargão de IA mora aqui, não lá
   embaixo:** é o que mais quebra entendimento e mais cansa, então some primeiro.
3. **A voz da casa** — direta, começando pela coisa.
4. **A ausência de marca cosmética** — aspas, caixa de título, emoji, negrito solto,
   travessão fora de enumeração. Isso é acabamento; vem por último.

A marca que fica por último é só a cosmética. O jargão de IA não é cosmético.

## O loop — uma página por vez

Método forkado do blader/humanizer (MIT), reordenado pela precedência:

1. **Tira o jargão e o estilo de IA que quebram entendimento.** Palavra de vitrine,
   importância inflada, gerúndio raso, fonte vaga, enchimento, «não X, mas Y», trio
   forçado, ditado formulaico. É o que mais atrapalha o leitor e o que mais irrita
   com fadiga de IA — por isso vem primeiro. (Catálogo: `reference/marcas-pt-br.md`.)
2. **Faz o leitor entender de verdade.** Seção que não muda nada sai; fato no
   presente ou passado, palpite marcado como inferência; jargão de domínio com o
   nome comum ao lado na 1ª vez; uma leitura basta. Aqui mora a guarda contra o modo
   de falha 1: não corte até o ponto em que só uma IA acharia que ficou explicado.
3. **Bota a voz da casa.** Usa a conduta do dono como referência de voz (ritmo,
   direção, palavra) — não como isenção de regra (abaixo).
4. **Apara a marca cosmética que sobrou.** Aspas, caixa de título, emoji, negrito,
   travessão fora de enumeração.

Duas travas do método, em toda passada:

- **Não inventa fato.** Nome, número, data, citação ou qualquer detalhe factual vem
  da fonte ou de quem escreve — nunca do preenchimento. Falta detalhe? Pergunta, ou
  escreve a frase mais simples. Opinião e reação a voz pede; fato factual, não.
- **Só mexe na prosa.** Deixa intactos dado, código, frontmatter, a moldura derivada
  (banco → página), alvo de link e Cargo/predefinição. O rewrite é da prosa.

## A voz é a do dono

A referência de voz da wiki é a conduta do dono (`abertura/dono.md`, no harness):
direta, começa pela coisa, sem cortesia de abertura, frase de comprimento variável.
Leia antes de escrever e case o ritmo, a direção e a escolha de palavra.

O que a amostra NÃO faz: **ela dá voz, não isenta de regra.** A conduta em si passa
pelo lint como qualquer página — não é gabarito imune.

**Travessão:** não é banido, mas o uso é **principalmente em enumerações** —
introduzir ou emoldurar uma lista de itens. Fora disso, apare: travessão de aposto
espalhado e travessão de suspense fabricado (o que corta a frase pra criar drama).
Não confunda com o hífen de palavra composta. (Sim, a conduta abusa de travessão; a
régua vale pra ela também.)

## O núcleo — o que toda página cumpre (spec §3.1)

- **Voz da casa.** Direta, começando pela coisa.
- **Seção muda o que o leitor faz.** Senão, sai. É o teste mais barato contra a
  página de escritório que ninguém reabre.
- **Jargão de domínio com o nome comum ao lado.** Termo do vocabulário da casa sem a
  tradução na 1ª ocorrência é falta. (Diferente do jargão de IA, que sai, não se
  traduz.)
- **Fato vs inferência.** Sabido no presente ou passado; inferido marcado («é
  provável que», futuro do pretérito); possibilidade só em seção à parte, ou fora;
  adjetivo de juízo sem evidência sai; fonte que copia fonte conta como uma.
- **Sem citação inline.** Nem «segundo X», nem `[n]`, nem autor-data, nem nota
  ancorada. A obra entra como objeto (página de fichamento, ficha de referência) ou
  como lista de leitura ao fim, não amarrada a uma frase.
- **Marcas de IA:** catálogo em `reference/marcas-pt-br.md`, aplicado em dois tempos
  — o que quebra entendimento sai no passo 1 do loop; o cosmético, no passo 4.

## O molde da página (estratos)

O molde é de dados (spec §3.2 e §5): a skill segue, não é dona. O único molde já
lavrado é o do **verbete de conceito**, em quatro estratos:

0. **Moldura derivada** — gerada do banco, datada, com o `sha` do export, nunca à
   mão. Traz no topo três campos que o leitor de uma leitura precisa ver primeiro:
   *valia em ‹data›*, *estado* (nota autoral | revisada | validada) e
   *classificação/difusão*.
1. **Abertura** — a 1ª frase define o conceito; um a três parágrafos que se bastam
   sozinhos e resumem o resto; jargão de domínio com o nome comum ao lado.
2. **Corpo** — seções planas, um nível só, na ordem em que a pessoa usa ou em que a
   coisa funciona. Exemplo é seção, não nota de rodapé.
3. **Apêndices** — leitura relacionada não ancorada; «veja também» só com conceitos
   já lavrados; proveniência.

O molde dos outros tipos de página entra à medida que a tipologia é lavrada (dados).

## Como devolver, e quando roda

Roda **antes de publicar** a página. Três modos:

- **Página ou rascunho colado:** devolve o rascunho, uma lista curta do que ainda
  soa a máquina, e a versão final.
- **Arquivo ou página nomeada:** roda o processo inteiro e grava só a versão final;
  muda só a prosa; depois, um resumo curto.
- **Embutido** (a favor de outra tarefa): devolve só a versão final.

Antes de devolver, releia e pergunte: (a) ainda soa gerado por IA, ou soa explicado
só pra uma IA? (b) o rewrite somou ou perdeu algum fato, nome, número, data, citação
ou juízo? Adição sem lastro, ou fato perdido, é erro.

## Falsos positivos

Pessoa também usa esses padrões — nenhum, sozinho, prova IA. A lista do que NÃO
acusar e os detalhes humanos a preservar estão em `reference/marcas-pt-br.md`. Na
dúvida, procure vários padrões juntos.

## Fonte e fronteira

- Método: fork do blader/humanizer (https://github.com/blader/humanizer, MIT), cujos
  padrões vêm de «Signs of AI writing» (Wikipedia, WikiProject AI Cleanup).
- Régua: **canônica** na spec (`platafirma-arquitetura/docs/spec_styleguide-da-wiki.md`);
  **servida** na wiki viva, em `Operar:styleguide` (o «como»). A wikipage
  `PlataFirma:Styleguide_da_wiki,_explicado` é o «porquê» e o 1º caso de teste. A
  régua é de **produto** (§5); esta skill é **implementadora** (arquiteto). O par que
  confere o que já está escrito é o lint `conferir prosa`.
- Ponto para produto: a spec põe toda «marca de máquina» por último (§1/§3.1). Esta
  skill trata o jargão de IA como quebra-entendimento (nível 2, cortado primeiro) e
  só o cosmético como nível 4. Se produto concordar, a spec e o servido refletem isso.
- Trava: passe do dono, linha a linha, antes de qualquer promoção de anel. Esta skill
  não fecha sem isso.
