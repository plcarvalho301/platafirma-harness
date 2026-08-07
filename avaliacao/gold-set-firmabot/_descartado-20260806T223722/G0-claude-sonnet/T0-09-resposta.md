## O que é uma decisão arquitetural

Uma decisão arquitetural diz respeito, tipicamente, à estrutura da aplicação ou do sistema, podendo também envolver escolhas de tecnologia quando essas impactam características arquiteturais. Uma boa decisão arquitetural é a que orienta os times de desenvolvimento na escolha técnica certa.
*(Transcrito de: Richards & Ford, "Fundamentals of Software Architecture" — Capítulo 20: Architectural Patterns › Architectural Decisions.)*

Em uma leitura complementar, a decisão arquitetural é tratada como a **unidade primária de trabalho** das atividades de arquitetura: é ela que carrega os *tradeoffs* feitos em um contexto específico, e a arquitetura do sistema, vista como um todo, pode ser descrita como um conjunto (ou fluxo) dessas decisões.
*(Transcrito/derivado de: Erder & Pureur, "Continuous Architecture in Practice" — Capítulo 2: Architecture in Practice: Essential Activities, trechos "Drive architectural decisions..." e "Architecture as a Flow of Decisions".)*

Essa mesma ideia aparece como corrente de pensamento mais ampla na literatura: Bosch (2003) já defendia a decisão de design como "cidadã de primeira classe", e a arquitetura pode ser entendida como o **conjunto de decisões de design** tomadas ao longo do projeto.
*(Transcrito de: Babar, Dingsøyr, Lago & van Vliet, "Software Architecture Knowledge Management" — Seção 1.2.2.1: Architecture as a Set of Design Decisions.)*

### Estrutura de uma decisão registrada

Quando formalizada, uma decisão arquitetural costuma ter atributos mínimos:
- **Epitome** — o enunciado curto da decisão em si;
- **Rationale** — a justificativa, o "porquê", que não deve repetir o que já está em outros campos;
- **Scope** — o alcance da decisão, que pode ser limitado no tempo, na organização ou no design.
*(Transcrito de: mesmo livro — Seção 3.4.1: What Is an Architectural Design Decision?, citando o modelo de Kruchten.)*

Kruchten acrescenta ainda **estados de ciclo de vida** para a decisão: Decided, Approved, Challenged, Rejected, Obsolesced — úteis para consultar e filtrar decisões ao longo do tempo.
*(Transcrito de: Kruchten, "Architectural Blueprints" (2004) — seção sobre atributos de decisões arquiteturais.)*

## Quando se registra

Fazer a decisão envolve, segundo a Fundamentals: reunir informação relevante, justificar a decisão, **documentá-la** e comunicá-la aos stakeholders certos — a documentação é parte do próprio ato de decidir, não um passo posterior opcional.
*(Transcrito de: Richards & Ford — mesma seção acima.)*

O texto original de Nygard sobre ADRs (Architecture Decision Records) situa isso no contexto ágil: nem todas as decisões são tomadas de uma vez, nem todas no início do projeto — por isso o registro deve ser feito **em documentos pequenos e modulares**, atualizáveis, um por decisão, em vez de um documento monolítico que nunca se mantém atualizado nem é lido.
*(Transcrito de: Nygard, "Documenting Architecture Decisions" (2011).)*

A Continuous Architecture in Practice reforça uma prática de processo: além de documentar as decisões já tomadas, recomenda-se **identificar de antemão quais decisões precisarão ser tomadas** e suas dependências, tratando-as como itens de um fluxo (quadro Kanban com colunas Backlog → In Progress → Ready for Decision → Decision Made).
*(Transcrito de: Erder & Pureur — Capítulo 2, "Architecture as a Flow of Decisions".)*

Por fim, uma fonte chama atenção para o risco de **não registrar**: decisões de design costumam ficar sem documentação, seja porque são implícitas (o arquiteto nem percebe que decidiu — experiência prévia, política de empresa tácita), seja porque são explícitas mas a razão nunca é escrita (decisão consciente, mas o "porquê" evapora com o tempo). Isso é reconhecimento de conhecimento tácito perdido, não uma prescrição de quando registrar.
*(Transcrito de: Babar, Dingsøyr, Lago & van Vliet — Seção 1.2.2.1.)*

Nenhuma das fontes que chegaram propõe um gatilho único e objetivo ("registra-se quando X acontece"); o que elas convergem em dizer é que a decisão nasce arquitetural quando afeta estrutura ou características do sistema, e que o registro deve acontecer perto do momento da decisão, em formato pequeno e rastreável — não em documento monolítico produzido à parte do fluxo de trabalho.