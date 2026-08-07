## O que é uma decisão arquitetural

Uma decisão arquitetural é a decisão que estrutura a aplicação ou sistema — e pode incluir decisões de tecnologia quando elas afetam características arquiteturais (os "-ilities": performance, disponibilidade, etc.). Não é qualquer escolha técnica; é a que orienta os times de desenvolvimento nas escolhas técnicas certas.

> "Architectural decisions usually involve the structure of the application or system, but they may involve technology decisions as well, particularly when those technology decisions impact architectural characteristics. [...] a good architectural decision is one that helps guide development teams in making the right technical choices."

— transcrito de *Fundamentals of Software Architecture* (Richards & Ford), Chapter 20: Architectural Patterns › Architectural Decisions.

Duas fontes complementam esse conceito colocando a decisão como **unidade de trabalho da atividade arquitetural**, não como artefato acessório:

> "Drive architectural decisions, which are the primary unit of work of architectural activities."

— transcrito de *Continuous Architecture in Practice* (Erder & Pureur), Chapter 2 › Drive architectural decisions...

E na mesma obra, a ideia de que a arquitetura *é* esse fluxo de decisões:

> "the key unit of work of architecture is an architectural decision [...] architecture is just a flow of decisions."

— transcrito de *Continuous Architecture in Practice*, Chapter 2 › Architecture as a Flow of Decisions.

Um terceiro ângulo, mais estrutural, descreve a decisão pelos seus atributos mínimos — pelo menos um enunciado curto (epítome) e a justificativa (rationale):

> "Epitome (or the Decision itself). This is a short textual statement of the design decision [...] Rationale. This is a textual explanation of the 'why' of the decision, its justification."

— transcrito de *Software Architecture Knowledge Management* (Babar et al.), Chapter 3.4.1 What Is an Architectural Design Decision?, citando o framework de Kruchten.

## Quando se registra

Aqui as fontes não dão uma regra de "quando" no sentido de gatilho temporal explícito, mas dão dois elementos que, juntos, permitem responder por derivação:

**1. Registrar é parte constitutiva do ato de decidir, não uma etapa posterior facultativa.** Fundamentals of Software Architecture lista documentar e comunicar como parte do mesmo processo de "fazer" a decisão, junto com reunir informação e justificar — transcrito acima, mesmo trecho de [1].

**2. O registro deve ser modular e feito no momento em que a decisão é tomada, não como documentação monolítica ao final.** Michael Nygard argumenta que projetos ágeis não fazem todas as decisões de uma vez nem no início, e que documentos pequenos e modulares têm chance real de se manter atualizados — ao contrário de documentos grandes:

> "Not all decisions will be made at once, nor will all of them be done when the project begins. [...] Documents that assist the team itself can have value, but only if they are kept up to date. Large documents are never kept up to date. Small, modular documents have at least a chance at being updated."

— transcrito de adr2.pdf (Michael Nygard, "Documenting Architecture Decisions", 2011).

*Continuous Architecture in Practice* propõe operacionalizar isso com um quadro Kanban de decisões (Backlog → In Progress → Ready for Decision → Decision Made), recomendando identificar de antemão quais decisões serão necessárias e suas dependências, e tratar a documentação como parte do fluxo até o estado "Decision Made" — transcrito de [4], mesma seção citada acima.

**Derivado dessas duas fontes:** o registro acontece no momento em que a decisão é tomada (não antes, especulativamente, nem muito depois, de memória), e como artefato pequeno e específico daquela decisão — não como capítulo de um documento de especificação geral.

Como reforço do porquê disso importa, *Software Architecture Knowledge Management* descreve o custo de não registrar no momento certo — decisão implícita (o arquiteto nem percebe que decidiu) ou explícita mas não documentada (decidida por um motivo específico, mas a razão não é escrita e se perde com o tempo):

> "The design decision is explicit but undocumented: the architect takes a decision for a very specific reason [...] The reasoning is not documented, and thus is likely to vaporize over time."

— transcrito de [8], Chapter 1.2.2.1 Architecture as a Set of Design Decisions.

Nenhuma das fontes que chegaram detalha um gatilho formal (ex.: "toda decisão acima de X impacto" ou "em toda reunião de arquitetura") — se você precisa desse critério operacional específico, as fontes não cobrem esse nível.
