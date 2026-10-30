---
name: prosa
description: "Use quando for ESCREVER ou REVISAR texto que uma pessoa vai ler em git, na wiki ou no rastreador, antes de publicar: página de wiki, corpo de card e comentário tipado (antes de `tarefas criar`, `tarefas editar` com corpo ou `tarefas comentar`; a forma é a de `tarefas modelo`, e a skill só dá a voz), lista de verificação, benchmark, parecer, runbook, e a voz (não a forma) de adr, spec e ato normativo. Em ato normativo e política interna, a forma é da skill redacao-normativa, que roda antes; esta faz a passada de voz nos dispositivos e escreve a nota e o material de apoio. Um motor comum a todo tipo (tira jargão de IA, faz entender, voz da casa) e a forma do tipo pela leitura acervo ler casa forma (a shape da classe), com molde em reference/moldes/ só para forma canônica e espécie ainda sem classe. Régua: acervo ler casa padrao styleguide-da-wiki. NÃO dispare para acervo cru, mural ou fila, produto de outra cadeira com régua própria (informe, apreciação, estimativa) nem resposta de chat."
cadeiras: todas (matéria de escrita legível por humano em git/wiki). Dona da régua é produto (spec §5 + anexo styleguide-moldes-por-tipo.md); dono da skill, como implementadora, é o arquiteto. A estrutura dos tipos é de dados (a shape da classe; na espécie ainda sem classe, acervo.especie_tipo).
compatibility: régua canônica na spec e no anexo de moldes; servida em Operar:styleguide (wiki viva). Motor agnóstico de superfície; molde por tipo em reference/moldes/. A conduta do dono (abertura/dono.md) é referência de voz, não isenção de regra. Catálogo de marcas por extenso em reference/marcas-pt-br.md.
---

# Prosa — escrever para git e wiki pela régua do styleguide

A régua não é apagar marca de máquina. É fazer quem chega depois ler um artefato e
fazer o que ele descreve sem falar com quem o escreveu.

Escopo: prosa que um humano lê em git, na wiki ou no rastreador — página de wiki
(conhecimento em geral: toda a parte conceitual do acervo), corpo de card e comentário
tipado, lista de verificação, benchmark, parecer, runbook, e a voz (não a forma) de
adr, spec e atos normativos.
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

## O núcleo — o que todo artefato cumpre (styleguide §3.1)

- **Quebra de linha e lista.** Uma ideia por parágrafo, parágrafo de até quatro linhas
  na tela. Três itens ou mais viram lista, um por linha. Campo com rótulo começa em
  linha própria, com linha em branco antes do seguinte. Para quem escreve, a quebra é
  um caractere; a falta dela custa a leitura inteira. Parede de texto é falta.
- **Referência resolvida.** Código de ADR, número de card e seção de spec vêm com o
  nome do que apontam, no ponto de leitura; onde a forma comporta rodapé, o código
  desce ao rodapé (ADR 0098, ponteiro nu). Parênteses empilhados com códigos no meio
  da frase são falta. Quando o alvo tem endereço, a referência é link, e o texto do
  link é o nome do que aponta. Entre documentos da casa, o link é relativo ao arquivo
  (`../guia/discovery.md`); ADR citada pela chave entre crases (`arq:0075`) o site da
  casa já liga sozinho. Fora da casa, o endereço inteiro.
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

## Roteador de tipo — de onde vem a forma

O primeiro passo de toda escrita e reescrita é pedir a forma ao acervo, numa chamada:

- documento novo: `acervo ler casa forma <classe>`;
- reescrita: `acervo ler casa forma --suporte <repo>@<caminho>`, que acha a classe pelo
  documento.

A forma é atributo da classe e mora na shape dela; o gerador a resolve pelos andares (a
raiz prosa, o andar comum com Fontes, o gênero, a mãe e a própria classe) e o catálogo a
serve. A lista de tipos e os nomes dos gêneros não se escrevem aqui: vêm da chamada.
O que fazer com a saída:

1. **Saída 0, gênero.** Escreve as seções na ordem que a chamada dá. A obrigatória
   entra sempre; a opcional, só se muda o que o leitor faz. A seção `derivado` não se
   escreve à mão: sai de outra fonte por ato. A régua de cada seção diz o que ela
   contém; seção sem régua segue só o núcleo e a voz, e não se inventa régua por
   analogia (a do gênero é de produto, a da seção da classe é da dona dela).
2. **Saída 3, canônica.** A forma mora fora da shape, no ponteiro que a chamada dá (ADR,
   modelo do rastreador, outra skill). Segue o ponteiro para a forma e rege só a voz.
3. **Saída 3, coberta por.** A peça não tem arquivo próprio: escreve-se na seção do
   documento do todo que a chamada nomeia (a de componentes do serviço, por exemplo).
4. **Saída 3, sem forma.** Não é prosa da casa; o motivo vem na saída.
5. **Saída 2.** A classe não existe no catálogo: é espécie ainda sem classe (spec,
   nota-tecnica, runbook, benchmark, lista-de-verificacao e as outras da F3973). Vale o
   molde transitório de `reference/moldes/<tipo>.md`, quando há; sem molde, só o motor e
   o núcleo, e sinaliza que a forma falta. A lista de verificação tem contrato com a
   máquina (nomes de coluna que o `lint` lê): o molde traz o contrato e o esqueleto, e
   nome de coluna não se improvisa.

Os casos abaixo dizem o que muda em cada ponteiro canônico.

1. **Tipo de forma canônica própria** (adr, spec, ato-normativo: lei, decreto,
   portaria, resolução, instrução-normativa) → a skill NÃO tem molde de estratos.
   Aponta para o canônico do dono do formato (arquiteto, para adr e spec; direito, pela
   skill `redacao-normativa`, para ato normativo e política interna) e aplica só
   a voz — o motor roda, a especialização por estrato não. Regra geral: onde o tipo
   tem forma canônica própria, herda a forma e rege só a voz. A forma da spec é a da
   ADR 0126 (spec é referência técnica de peça viva); a voz das seções Em uma tela e
   Comportamento está no anexo de moldes, §5. Estes moram no git, não na wiki; a skill
   topa com eles só se colados lá. Todo documento derivado termina com a seção Fontes,
   de linha única (anexo de moldes, §9).
2. **Ciclo-de-vida** (minuta, roadmap, rascunho — NÃO é `especie_tipo`) → molde de
   prosa próprio; o roteador não os resolve como espécie do acervo. A minuta é
   deliberação em trânsito e vira adr ou spec ao formalizar. A minuta foi absorvida
   pelo card (épico #3365) e sai depois da F3; até lá, vale só para as que já existem.
3. **Página de wiki** (verbete de conceito) → `acervo ler casa forma conceito` (gênero
   verbete; a régua da definição vem como régua de campo).
4. **Card e comentário tipado** (saída 3, canônica) → a skill NÃO tem molde. A forma e
   a régua de cada rótulo moram num lugar só, o molde do rastreador, e se leem com
   `tarefas modelo <épico|feature|story|task>`, `tarefas modelo story derivada`,
   `tarefas modelo story refinada` ou `tarefas modelo comentario <tipo>`. Rode o modelo do
   caso antes de escrever, siga os rótulos e a régua que ele imprime, e aplique aqui só o
   motor e o núcleo. Documento que repita esses rótulos está velho: vale o `tarefas
   modelo`.

## Ato normativo — a ponte com a `redacao-normativa`

Portaria, resolução, instrução normativa, política interna, regimento: a forma é da skill
`redacao-normativa` (direito). As duas se completam, nesta ordem (anexo de moldes §5):

1. **`redacao-normativa` primeiro.** Gate antes de redigir, matriz de densidade, texto
   dos dispositivos, aceite da minuta. Se ela não estiver disponível, diga isso e não
   redija dispositivo por esta skill.
2. **`prosa` nos dispositivos, só voz.** Tira marca de máquina e enchimento. Não troca
   termo definido por sinônimo, não funde dispositivo, não simplifica o que a outra
   skill fixou como precisão. Onde o dispositivo restringe direito, sanciona ou decide
   sobre pessoa, precisão vence simplicidade.
3. **`prosa` inteira no que cerca a norma.** A nota da minuta (problema, alternativas,
   motivação) e o material de apoio que explica a norma a quem ela obriga: é ali que a
   compreensão do sujeito se resolve.

Falso positivo dentro de ato normativo: repetir o mesmo termo, e abrir dispositivos
seguidos com o mesmo sujeito, é exigência da redação normativa. A parte da marca 11 do
catálogo que acusa abertura repetida não vale em dispositivo; variar o termo, ali, é o
erro.

## A forma vem da classe — a régua mora na shape

A ESTRUTURA — as seções, na ordem — e a RÉGUA de cada uma moram na planilha da ontologia e
na shape da classe, e chegam pela chamada `acervo ler casa forma`. A régua da raiz e dos
gêneros é de produto; a das seções que a classe acrescenta, da dona da classe. Os
`reference/moldes/<tipo>.md` que ficam são transitórios, de espécie ainda sem classe (o
card e o comentário tipado não têm molde aqui: vêm de `tarefas modelo`), e saem quando a F3973 der a
classe; o anexo de moldes (`acervo ler casa padrao styleguide-moldes-por-tipo`) guarda a
régua delas até lá. Divergiu, vale a shape.

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
- Régua: **canônica** no styleguide do acervo da casa (`acervo ler casa padrao
  styleguide-da-wiki`); **servida** na wiki viva, em `Operar:styleguide` (o «como»). A
  régua fina dos moldes por tipo mora no anexo (`acervo ler casa padrao
  styleguide-moldes-por-tipo`). A cópia antiga em `platafirma-arquitetura/docs/` não
  é fonte. A régua é de
  **produto** (§5); a **estrutura** dos tipos é de **dados** (a shape da classe; na espécie ainda sem
  classe, `acervo.especie_tipo`);
  esta skill é **implementadora** (arquiteto). O par que confere o que já está escrito
  é o lint de prosa.
- Ponto para produto: a spec põe toda «marca de máquina» por último (§1/§3.1). Esta
  skill trata o jargão de IA como quebra-entendimento (nível 2, cortado primeiro) e
  só o cosmético como nível 4. Se produto concordar, a spec e o servido refletem isso.
- Trava: passe do dono, linha a linha, antes de qualquer promoção de anel. Esta skill
  não fecha sem isso.
