---
name: prosa
description: Use quando for ESCREVER ou REVISAR prosa da wiki (Inteligência de Base) antes de publicar — página nova, edição de página, ou passar um rascunho pela régua da casa. Orienta o agente que escreve. Implementa a spec do styleguide (platafirma-arquitetura/docs/spec_styleguide-da-wiki.md) e a wikipage explicativa (PlataFirma:Styleguide_da_wiki,_explicado) — não tem régua própria. NÃO dispare para o acervo (obra tem proveniência própria), nem para mural/fila (push, régua própria), nem para produto acabado (informe, apreciação, estimativa). O par `conferir prosa` é o lint que CONFERE o que já está escrito; esta skill ORIENTA quem escreve.
cadeiras: todas (matéria de escrita da wiki). Dono da régua é produto (§5 da spec); dono da skill, como implementadora, é o arquiteto.
compatibility: a régua servida está na spec + na wikipage; a amostra de voz padrão é a conduta do dono (abertura/dono.md, no harness). Roda antes de publicar página. O catálogo de marcas por extenso está em reference/marcas-pt-br.md.
---

# Prosa — escrever para a wiki pela régua do styleguide

A régua da wiki não é apagar marca de máquina. É fazer quem chega depois ler uma
página e fazer o que ela descreve sem falar com quem a escreveu. Marca de máquina é
o ÚLTIMO item da lista: um texto sem marca nenhuma que o leitor não consegue usar é
a mesma página ruim, agora bem passada a ferro.

Escopo: só a wiki — Inteligência de Base, o que se usa para trabalhar e repassar
conhecimento entre pares. Não é acervo, não é mural, não é fila, não é produto
acabado.

## A ordem que decide tudo

Duas regras boas às vezes brigam. Quando brigam, a de cima vence a de baixo, sempre:

1. **O leitor sai fazendo.** A página muda o que alguém consegue fazer.
2. **O leitor entende** — inclui saber o que na página é fato e o que é palpite.
3. **A voz da casa** — direta, começando pela coisa, sem cortesia de abertura.
4. **A ausência de marca de máquina** — texto que não denuncia ter saído de IA.

Corrigir marca (4) antes de compreensão (1–2) é lustrar o que ninguém vai usar. Por
isso o catálogo de marcas é capítulo subordinado, nunca o eixo.

## O loop — uma página por vez

Método forkado do blader/humanizer (MIT), mas ordenado pela precedência acima:

1. **Corta o que não muda nada.** Seção que não altera o que o leitor faz sai. A
   primeira passada não trata a estrutura do rascunho como fixa.
2. **Faz o leitor entender.** Fato no presente ou no passado; palpite marcado como
   inferência; jargão com o nome comum ao lado na 1ª vez; uma leitura basta.
3. **Bota a voz da casa.** Casa a amostra (padrão: a conduta do dono, abaixo).
4. **Tira as marcas de máquina.** Confere contra `reference/marcas-pt-br.md`.

Duas travas do método, em toda passada:

- **Não inventa fato.** Nome, número, data, citação ou qualquer detalhe factual vem
  da fonte ou de quem escreve — nunca do preenchimento. Falta detalhe? Pergunta, ou
  escreve a frase mais simples. Opinião e reação a voz pede; fato factual, não.
- **Só mexe na prosa.** Deixa intactos dado, código, frontmatter, a moldura derivada
  (banco → página), alvo de link e Cargo/predefinição. O rewrite é da prosa.

## A voz é a do dono

A amostra de voz padrão da wiki é a conduta do dono (`abertura/dono.md`, no harness):
direta, começa pela coisa, sem moldura de cortesia, frase de comprimento variável.
Leia a amostra antes de escrever e case o ritmo, a escolha de palavra e a pontuação
dela. Amostra vence regra de estilo genérica.

Consequência que separa esta skill do humanizer em inglês: **a amostra da casa usa
travessão (—) à vontade**, para aposto e parêntese, do jeito do pt-BR. Aqui o
travessão NÃO é banido — o §14 do humanizer não vale como proibição. Some só o
travessão usado como suspense fabricado; o de aposto fica.

## O núcleo — o que toda página cumpre (spec §3.1)

- **Voz da casa.** Direta, começando pela coisa.
- **Seção muda o que o leitor faz.** Senão, sai. É o teste mais barato contra a
  página de escritório que ninguém reabre.
- **Jargão com o nome comum ao lado.** Termo do vocabulário da casa sem a tradução
  na 1ª ocorrência é falta.
- **Fato vs inferência.** Sabido no presente ou passado; inferido marcado («é
  provável que», futuro do pretérito); possibilidade só em seção à parte, ou fora;
  adjetivo de juízo sem evidência sai; fonte que copia fonte conta como uma.
- **Sem citação inline.** Nem «segundo X», nem `[n]`, nem autor-data, nem nota
  ancorada. A obra entra como objeto (página de fichamento, ficha de referência) ou
  como lista de leitura ao fim, não amarrada a uma frase. É a régua mais mecânica.
- **Marcas de IA:** capítulo subordinado → `reference/marcas-pt-br.md`.

## O molde da página (estratos)

O molde é de dados (spec §3.2 e §5): a skill segue, não é dona. O único molde já
lavrado é o do **verbete de conceito**, em quatro estratos:

0. **Moldura derivada** — gerada do banco, datada, com o `sha` do export, nunca à
   mão. Traz no topo três campos que o leitor de uma leitura precisa ver primeiro:
   *valia em ‹data›*, *estado* (nota autoral | revisada | validada) e
   *classificação/difusão*.
1. **Abertura** — a 1ª frase define o conceito; um a três parágrafos que se bastam
   sozinhos e resumem o resto; jargão com o nome comum ao lado.
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

Antes de devolver, releia e pergunte: (a) o que ainda soa gerado por IA? (b) o
rewrite somou ou perdeu algum fato, nome, número, data, citação ou juízo? Adição sem
lastro, ou fato perdido, é erro.

## Falsos positivos

Pessoa também usa esses padrões — nenhum, sozinho, prova IA. A lista do que NÃO
acusar e os detalhes humanos a preservar estão em `reference/marcas-pt-br.md`. Na
dúvida, procure vários padrões juntos: um travessão não prova nada.

## Fonte e fronteira

- Método: fork do blader/humanizer (https://github.com/blader/humanizer, MIT), cujos
  padrões vêm de «Signs of AI writing» (Wikipedia, WikiProject AI Cleanup).
- Régua: a spec (`platafirma-arquitetura/docs/spec_styleguide-da-wiki.md`) + a
  wikipage explicativa. A régua é de **produto**; esta skill é **implementadora**
  (arquiteto). O par que confere o que já está escrito é o lint `conferir prosa`.
- 1º caso de teste: a própria wikipage explicativa
  (`PlataFirma:Styleguide_da_wiki,_explicado`).
- Trava: passe do dono, linha a linha, antes de qualquer promoção de anel. Esta skill
  não fecha sem isso.
