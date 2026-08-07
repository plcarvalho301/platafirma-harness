## Feature flag (feature toggle)

**Definição:** mecanismo que esconde funcionalidade já implantada atrás de um controle que liga ou desliga essa funcionalidade — ou permite alternar entre duas implementações diferentes de algo. *(Transcrito/derivado das fontes [1] e [2].)*

**De onde sai:**

- *Building Microservices, 2nd ed.* (Sam Newman) — Capítulo 8, "Deployment › Progressive Delivery › Feature Toggles" [1]: aqui o conceito aparece no contexto de entrega progressiva. O uso mais comum é junto de trunk-based development, permitindo que código ainda incompleto seja integrado e implantado, mas mantido oculto do usuário final. Também pode ter granularidade mais fina — estado diferente conforme quem faz a requisição (ex.: grupo beta vs. resto dos usuários), o que serve de base para canary rollout. O trecho cita soluções gerenciadas (LaunchDarkly, Split) mas recomenda começar simples, com um arquivo de configuração, e aponta o artigo de Pete Hodgson, "Feature Toggles (aka Feature Flags)", para aprofundamento.

- *Building Microservices, 2nd ed.* — Capítulo 3, "Splitting the Monolith › Useful Decompositional Patterns › Feature Toggle" [2]: aqui o mesmo mecanismo aparece como padrão útil na migração para microsserviços. No contexto do strangler fig, o toggle permite alternar entre a funcionalidade que ainda vive no monólito e a nova implementação no microsserviço — por exemplo, implementado na camada de proxy HTTP usada no strangler fig.

**Fora do escopo desta resposta:** as fontes [3]–[8] não tratam do conceito de feature flag/toggle de software. [7] usa "flag" no sentido de *database trace flag* do SQL Server (Cloud SQL), que é homônimo mas não o mesmo conceito. [6] define "feature" isoladamente (glossário de produto), não "feature flag". [3], [4], [5], [8] não tocam no termo. Nenhuma delas foi usada para sustentar a definição acima.