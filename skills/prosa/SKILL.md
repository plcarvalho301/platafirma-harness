---
name: prosa
description: Use quando for ESCREVER ou REVISAR prosa que um humano vai ler em git ou na wiki, antes de publicar — página de wiki, benchmark, parecer, runbook, e a voz (não a forma) de adr/spec/atos normativos. Orienta o agente que escreve. O MOTOR (tira jargão de IA, faz entender, voz da casa, apara cosmético) é o mesmo pra todo tipo; o MOLDE vem do tipo (reference/moldes/<tipo>.md); a lista de tipos é a taxonomia de acervo.especie_tipo, a skill não a hardcoda. Régua fina de cada molde na fonte de produto (docs/styleguide-moldes-por-tipo.md). NÃO dispare para: acervo cru (obra tem proveniência própria), mural/fila (régua própria), produtos de negócio de outra cadeira com régua própria (informe, apreciação, estimativa), nem resposta de chat (a régua do chat é a conduta do dono, abertura/dono.md). O par `conferir prosa` é o lint que CONFERE o que já está escrito; esta skill ORIENTA quem escreve.
cadeiras: todas (matéria de escrita legível por humano em git/wiki). Dona da régua é produto (spec §5 + anexo styleguide-moldes-por-tipo.md); dono da skill, como implementadora, é o arquiteto. A estrutura dos tipos é de dados (acervo.especie_tipo).
compatibility: régua canônica na spec e no anexo de moldes; servida em Operar:styleguide (wiki viva). Motor agnóstico de superfície; molde por tipo em reference/moldes/. A conduta do dono (abertura/dono.md) é referência de voz, não isenção de regra. Catálogo de marcas por extenso em reference/marcas-pt-br.md.
---

# Prosa — escrever para git e wiki pela régua do styleguide

A régua não é apagar marca de máquina. É fazer quem chega depois ler um artefato e
fazer o que ele descreve sem falar com quem o escreveu.

Escopo: prosa que um humano lê em git ou na wiki — página de Inteligência de Base,
benchmark, parecer, runbook, e a voz (não a forma) de adr, spec e atos normativos.
Não é acervo cru, não é mural, não é fila, não é produto de negócio de outra cadeira
com régua própria.

Nota de leitura: onde este texto diz «página», vale para todo artefato de texto
corrido no escopo, salvo onde o tipo mandar diferente — o molde do tipo diz.

Duas camadas: o MOTOR abaixo é o mesmo para todo tipo; o MOLDE vem do tipo do
artefato (Roteador de tipo, adiante). A régua fina de escrita de cada molde é de
produto e mora no anexo `docs/styleguide-moldes-por-tipo.md`; a skill implementa,
não reescreve (spec §1 proíbe segunda fonte).

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

1. **O leitor sai fazendo.** O artefato muda o que alguém consegue fazer.
2. **O leitor entende** — fato vs palpite. **O jargão de IA mora aqui, não lá
   embaixo:** é o que mais quebra entendimento e mais cansa, então some primeiro.
3. **A voz da casa** — direta, começando pela coisa.
4. **A ausência de marca cosmética** — aspas, caixa de título, emoji, negrito solto,
   travessão fora de enumeração. Isso é acabamento; vem por último.

A marca que fica por último é só a cosmética. O jargão de IA não é cosmético.

## O loop — um artefato por vez

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

A referência de voz é a conduta do dono (`abertura/dono.md`, no harness):
direta, começa pela coisa, sem cortesia de abertura, frase de comprimento variável.
Leia antes de escrever e case o ritmo, a direção e a escolha de palavra.

O que a amostra NÃO faz: **ela dá voz, não isenta de regra.** A conduta em si passa
pelo lint como qualquer página — não é gabarito imune.

**Travessão:** não é banido, mas o uso é **principalmente em enumerações** —
introduzir ou emoldurar uma lista de itens. Fora disso, apare: travessão de aposto
espalhado e travessão de suspense fabricado (o que corta a frase pra criar drama).
Não confunda com o hífen de palavra composta. (Sim, a conduta abusa de travessão; a
régua vale pra ela também.)

## O núcleo — o que todo artefato cumpre (spec §3.1)

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

## Roteador de tipo — qual molde carregar

Antes de escrever, identifica o tipo do artefato e resolve o molde por eixo. A lista
de tipos não se hardcoda aqui: as espécies são a taxonomia de `acervo.especie_tipo`
(id, slug, família). Os estratos de cada molde vêm de `reference/moldes/` — a régua
fina no anexo de produto —, não de `especie_tipo`.

1. **Espécie de obra de git com molde próprio** (benchmark, parecer, runbook, e os
   que forem lavrados) → carrega `reference/moldes/<tipo>.md`. Tipo ainda sem molde
   (nota-tecnica, levantamento, rito, fichamento, nota-de-pesquisa, estudo-de-caso,
   entre outros): aplica o motor e o núcleo, e sinaliza que o molde falta — não
   fabrica molde por analogia; pede a régua a produto e a estrutura a dados. A casa
   lavra por tipo, sem tocar este arquivo.
2. **Tipo de forma canônica própria** (adr, spec, ato-normativo: lei, decreto,
   portaria, resolução, instrução-normativa) → a skill NÃO tem molde de estratos.
   Aponta para o canônico do dono do formato (arquiteto, para adr e spec) e aplica só
   a voz — o motor roda, a especialização por estrato não. Regra geral: onde o tipo
   tem forma canônica própria, herda a forma e rege só a voz. Estes moram no git, não
   na wiki; a skill topa com eles só se colados lá.
3. **Ciclo-de-vida** (minuta, roadmap, rascunho — NÃO é `especie_tipo`) → molde de
   prosa próprio; o roteador não os resolve como espécie do acervo. A minuta é
   deliberação em trânsito e vira adr ou spec ao formalizar.
4. **Página de wiki** (verbete-de-conceito) → `reference/moldes/verbete-de-conceito.md`.

## O molde vem do tipo — a régua fina mora no anexo

Cada `reference/moldes/<tipo>.md` traz a ESTRUTURA — os estratos, na ordem (matéria
de dados, `especie_tipo`) — e o distintivo operacional de cada estrato. A RÉGUA FINA
de escrita — o que cada estrato contém, em que voz, o que o distingue — é de produto
e mora em `docs/styleguide-moldes-por-tipo.md`; o molde da skill aponta para a seção
do anexo. Divergiu, a fonte é o anexo.

Todo molde cumpre primeiro o núcleo (seção acima, spec §3.1); a régua por tipo só
acrescenta o que o tipo exige além dele. A precedência da «ordem que decide tudo»
resolve todo conflito.

A morada do artefato — peça entregue vai ao acervo com proveniência, a de trabalho
fica na wiki — é decisão da tipologia e do acervo, não desta skill. O mesmo molde
vale para o artefato entregue e para o de trabalho.

## Como devolver, e quando roda

Roda **antes de publicar** o artefato. Três modos:

- **Artefato ou rascunho colado:** devolve o rascunho, uma lista curta do que ainda
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
  **servida** na wiki viva, em `Operar:styleguide` (o «como»). A régua fina dos
  moldes por tipo mora no anexo `docs/styleguide-moldes-por-tipo.md`. A régua é de
  **produto** (§5); a **estrutura** dos tipos é de **dados** (`acervo.especie_tipo`);
  esta skill é **implementadora** (arquiteto). O par que confere o que já está escrito
  é o lint `conferir prosa`.
- Ponto para produto: a spec põe toda «marca de máquina» por último (§1/§3.1). Esta
  skill trata o jargão de IA como quebra-entendimento (nível 2, cortado primeiro) e
  só o cosmético como nível 4. Se produto concordar, a spec e o servido refletem isso.
- Trava: passe do dono, linha a linha, antes de qualquer promoção de anel. Esta skill
  não fecha sem isso.
