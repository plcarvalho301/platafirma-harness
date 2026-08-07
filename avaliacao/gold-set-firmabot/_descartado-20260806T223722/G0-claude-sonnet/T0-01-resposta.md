Respondendo por partes, porque as fontes que chegaram cobrem os dois pedaços da pergunta de forma desigual.

## Conceito

A fonte que trata do assunto por definição formal é **D18 (WonderWeb Deliverable D18) › KIF version of DOLCE-Lite+ (PL dialect)** [5]. Nela, `CONCEPT` é introduzido como especialização de `UNIVERSAL`:

> `(DEFCONCEPT UNIVERSAL (?SELF) :=> (CONCEPT ?SELF))`
> `(DEFCONCEPT ENTITY (?SELF) :AXIOMS (UNIVERSAL ENTITY))`

Isso é **transcrito** da fonte — é código KIF, uma definição operacional dentro da ontologia DOLCE-Lite+, não uma definição em prosa do termo "conceito". Lida como axioma: todo `UNIVERSAL` é um `CONCEPT`, e `ENTITY` é declarado como `UNIVERSAL`. Não há, no trecho que chegou, explicação em linguagem natural do que caracteriza um conceito além dessa hierarquia formal.

A fonte **503124-503150 › Evaluating Ontological Decisions with OntoClean** [3] é adjacente — trata de metaproperties usadas para "caracterizar aspectos relevantes do significado pretendido das propriedades, classes e relações que compõem uma ontologia" (**transcrito**) — mas o trecho que chegou introduz apenas a primeira noção formal, "Essence and Rigidity", e é cortado antes de qualquer definição de "concept" propriamente dita.

## Critério de identidade

Nenhuma das fontes que chegaram trata explicitamente de **critério de identidade** (identity criteria). O trecho de [3] chega a anunciar que vai tratar de "Essence and Rigidity" como primeira noção formal da metodologia OntoClean, mas o texto é cortado exatamente aí — não avança até identidade. A fonte [6] (NC20 IN01_DSIC_GSIPR) traz só o título de seção "3 Conceitos e Definições", sem conteúdo — trecho sem matéria, não sustenta afirmação nenhuma. As demais fontes (Tractatus, Alexy, Doutrina da Atividade de Inteligência, Dewey) não tratam do conceito exato perguntado: são índice/sumário ou tratam de outros assuntos (jurisprudência dos conceitos em Alexy é vizinho semântico, não o mesmo objeto).

**Diante disso: as fontes não cobrem "critério de identidade".**

Como leitura minha, sem fonte no que chegou: em metodologias de ontologia formal como o OntoClean (do qual [3] é justamente o texto de referência, mas cujo trecho não chegou completo), "critério de identidade" costuma ser tratado como uma das metaproperties centrais — a condição que permite decidir se duas instâncias, em momentos ou descrições diferentes, são a mesma entidade. Isso normalmente aparece ao lado de rigidez, unidade e dependência como as quatro metaproperties da metodologia. Mas isso é conhecimento meu, não algo que as fontes fornecidas sustentam — se a resposta precisa se apoiar no acervo, valeria buscar o restante do texto de [3], que claramente continua além do ponto em que o trecho foi cortado.