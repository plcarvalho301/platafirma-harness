# Reescrita de slug e definição — régua obrigatória

Vale para as propostas da rodada 2 **e** para os conceitos já existentes na base do seu domínio. Editar direto no consolidado.

## O que está errado

As definições foram escritas para decidir classificação de obra. Elas decidem — e não ensinam. Cada conceito tem um `endereco` que aponta para uma página que um ser humano vai abrir, e esse humano chegou ontem. Hoje ele abre, lê 45 palavras de abstração encadeada, e fecha.

Um leitor que dá aula do assunto precisou reler três das definições para entender. Se ele precisou, o novato não tem chance.

## O que muda e o que não muda

**Não muda:** o mecanismo, a decidibilidade, o falseador, a natureza, o estatuto, as âncoras. A régua continua tendo que decidir "esta obra trata disto?" a partir do próprio texto. Não afrouxe nada disso.

**Muda:** a mesma régua agora também tem que **ensinar**. Decidir e ensinar não são objetivos concorrentes — o texto que ensina decide igual, e o que só decide já provou que não ensina.

Se você acha que não dá para fazer os dois, o problema é que o mecanismo não está claro nem para você.

## As quatro regras

### 1. Primeira leitura, sem reler

O par slug + definição tem que ser enquadrável por alguém que nunca ouviu o termo, lendo uma vez só, sem consultar outra entrada e sem procurar nada fora. Enquadrar = saber o que é e por que importa. Não é dominar.

**Teste:** leia sua definição em voz alta uma vez. Se em qualquer ponto você precisou voltar, reescreva. Se ela tem mais de duas orações encadeadas antes do primeiro ponto final, reescreva.

### 2. Zero auto-referência ao corpus

O leitor não leu o acervo, não sabe o que é uma obra, não sabe que existe classificação, não vai ler outro conceito antes deste.

Banido da definição:

* "decide contra <outro conceito>"
* "a obra entra se..." / "classificar sob..." / "esta régua..."
* "distingue-se de <outro slug>" quando o outro slug não é termo corrente no mundo
* qualquer frase escrita para o curador em vez do leitor

O contraste entre conceitos é bom e não morre — vai para a **página**, onde há espaço para explicá-lo. Na definição, ele cobra do leitor um vocabulário que a entrada não forneceu.

**Contraste permitido:** contra coisa do mundo real que o leitor conhece sem o acervo. "Ao contrário do controle de ponto" passa. "Decide contra business capability" não passa.

### 3. Zero jargão não desempacotado

Toda palavra que só existe dentro de uma tradição específica ou sai, ou vem explicada na própria frase em que aparece.

Exemplos reais que reprovaram: stakeholder, objetivo de alinhamento, tipo sortal, anti-rígido, subsumir, proposição de valor, itens de valor, habilitado por capacidades, construtor, fragmento, termo de ciência e responsabilidade.

* **Se o termo técnico é indispensável:** use-o, e desempacote na mesma frase. "objetivo de alinhamento — a meta de TI que serve à meta do negócio — ..." custa oito palavras e salva o parágrafo.
* **Se o termo só está lá porque a fonte usava:** corte. Você está traduzindo, não transcrevendo.

**Teste do substantivo abstrato:** conte os substantivos abstratos seguidos. Três ou mais em sequência ("necessidade de stakeholder se traduz em objetivo corporativo, que se traduz em objetivo de alinhamento") = reprovado.

### 4. Slug que o novato chuta certo

O slug é a primeira coisa que aparece e a única que se clica.

**Reprova:**

* sigla de framework empilhada: `seis-dimensoes-ci-ddd`
* número ordinal de método: `cinco-forcas-porter`, `quatro-riscos-de-produto` (limítrofe — avalie)
* dois termos técnicos opostos por "vs" sem que nenhum dos dois seja conhecido: `expressividade-vs-tratabilidade`
* rótulo que não diz de que trata: `corte-por-capacidade`, `porta-para-fora-porta-para-dentro`, `hooks`, `tool`, `parametros`
* qualificador que ninguém digitaria: `gestao-por-resultado-pactuado`

**Aprova e fica como está:** sigla que **é** o nome da coisa no mundo, que o leitor vai encontrar assim no primeiro emprego e no primeiro edital — REST, OKR, RBAC, API, DDD, OCR, IAM, RAG. Não traduza essas. Mantenha o slug e desempacote a sigla na primeira frase da definição.

A pergunta que separa os dois casos: **se o leitor procurar isso no mundo, ele vai achar por este nome?** Sim, mantém. Não, troca.

## Forma

* Primeira frase: o que é, em português, sem oração subordinada.
* Segunda frase em diante: o mecanismo — o que ele decide, o que quebra sem ele.
* Dois parágrafos são permitidos quando o conceito é denso. Use o segundo para o caso concreto, não para mais abstração.
* Exemplo concreto vale mais que precisão adicional. Um conceito entendido com 90% de exatidão vence um conceito exato e fechado.
* Não abra com o próprio rótulo ("Algo é X quando...") — articule o mecanismo direto.

## Antes e depois — calibragem

### contexto-delimitado

**Antes:** "Fronteira explícita dentro da qual cada termo tem significado único e o modelo vale com exatidão; fora dela, o mesmo rótulo pode denotar outra régua sem que isso seja erro. A fronteira é declarada, não descoberta, e decide quando duas definições divergentes exigem reconciliação (mesmo contexto) e quando exigem apenas mapeamento entre contextos."

**Depois:** "A mesma palavra significa coisas diferentes em partes diferentes de uma organização, e isso não é confusão a ser corrigida: para o time de vendas, 'cliente' é quem pode comprar; para o financeiro, é quem tem contrato ativo. O contexto delimitado é a fronteira declarada dentro da qual cada palavra tem um significado só.

Declarar a fronteira decide o que fazer quando duas definições divergem. Dentro da mesma fronteira, divergência é defeito e alguém tem que ceder. Entre fronteiras diferentes, não há defeito nenhum — o que se constrói é a tradução de um lado para o outro, e tentar unificar destrói informação dos dois lados."

Por que passa: o exemplo chega antes da abstração; o mecanismo continua inteiro; nada foi afrouxado; um novato entende e um sênior não se sente insultado.

### cascata-de-objetivos

**Antes:** "Necessidade de stakeholder se traduz em objetivo corporativo, que se traduz em objetivo de alinhamento, que seleciona e prioriza processos e recursos; a decisão local se justifica pelo rastro até o topo, e objetivo sem rastro não tem lastro. Decide contra OKR: lá o mecanismo é pactuação colaborativa de metas por ciclo, aqui é derivação rastreável entre níveis."

**Depois:** "Cada meta de uma equipe tem que poder ser rastreada, degrau por degrau, até uma meta da organização inteira — e essa, até alguém de fora que espera algo dela: quem paga, quem fiscaliza, quem usa o serviço. Uma equipe que não consegue mostrar esse caminho está trabalhando em algo que ninguém pediu, por mais bem-feito que seja.

O que caracteriza a cascata é a direção: a meta desce de cima, já decidida, e o de baixo justifica o que faz mostrando a ligação. Não é o único jeito de definir metas — há métodos em que a equipe propõe e a chefia referenda —, e o que muda entre eles é quem formula primeiro, não se há acordo."

Por que passa: "stakeholder" virou "quem paga, quem fiscaliza, quem usa"; a rima saiu; o contraste com OKR ficou sem citar OKR — e mais correto, porque cascata **também** é pactuada, o que muda é a direção.

### corte-por-capacidade — só o slug

O rótulo não diz de que trata. Candidatos: `teto-de-compromisso`, `limite-do-que-se-promete`. A régua atual abre com tese ("A priorização só decide quando...") em vez de definição — reescreva começando pelo que é.

### expressividade-vs-tratabilidade

Slug ilegível e definição com o núcleo no fim. O núcleo é: quanto mais coisas uma linguagem formal permite afirmar, mais caro fica calcular o que ela implica — e existe um ponto em que o computador deixa de dar resposta em tempo útil. Comece por aí. O slug precisa dizer isso; o "vs" não diz.

### seis-dimensoes-ci-ddd — base pré-existente

Sigla de framework dentro de número ordinal. Não é nome de nada no mundo. Renomeie pelo que o conceito faz.

## Como entregar

Edite direto no consolidado. Não abra arquivo novo, não faça anexo, não mande lista de sugestões — a edição **é** a entrega.

Escopo: **todos** os conceitos do seu domínio. As propostas da rodada 2 e os que já estavam na base. Conceito antigo não tem passe livre por ser antigo.

Não mexa em: falseador, natureza, estatuto, âncoras, pai proposto.

Antes de fechar, releia cada definição uma vez, em voz alta, fingindo que nunca ouviu o termo. Voltou uma vez que seja, não terminou.
