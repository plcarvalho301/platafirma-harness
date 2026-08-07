## Feature flag (feature toggle)

**Definição** — Mecanismo que esconde funcionalidade já implantada atrás de um controle (toggle) que liga ou desliga essa funcionalidade, ou alterna entre duas implementações diferentes de um mesmo comportamento, sem precisar de novo deploy. *(Transcrito/derivado de [1] e [2].)*

**De onde sai** — *Building Microservices: Designing Fine-Grained Systems*, 2ª ed., Sam Newman. A obra trata o conceito em dois lugares, cada um com um uso diferente:

- **Capítulo 8, Deployment › Progressive Delivery › Feature Toggles** [1]: aqui o foco é entrega progressiva. É o uso mais comum, associado a trunk-based development — funcionalidade incompleta é integrada e implantada, mas fica oculta do usuário final até estar pronta. Também serve para ligar uma feature em horário programado, desligar algo que está causando problema, ou dar tratamento granular por perfil de usuário (ex.: grupo beta vê a feature ligada, o resto vê desligada) — o que viabiliza canary rollout. O texto cita soluções gerenciadas (LaunchDarkly, Split), mas recomenda começar simples, até com um arquivo de configuração, e recomenda o artigo de Pete Hodgson, "Feature Toggles (aka Feature Flags)", para aprofundamento.

- **Capítulo 3, Splitting the Monolith › Useful Decompositional Patterns › Feature Toggle** [2]: aqui o uso é como padrão de decomposição durante migração para microsserviços. No contexto do strangler fig, o toggle permite alternar entre a funcionalidade que ainda vive no monolito e a nova implementação no microsserviço — por exemplo, implementado na camada de proxy HTTP do strangler fig.

**Observação sobre as demais fontes** — as fontes [3], [4], [5], [7] e [8] tratam de assuntos distintos (cultura organizacional, plataforma interna de desenvolvimento, campos de formulário em PDF, "database flag" do SQL Server no CIS Benchmark, e fundamentos de SRE) e não abordam feature flag/toggle como conceito — não as usei. A fonte [6] define "Feature" (não "feature flag") no glossário do *Lean Inception*, um conceito vizinho mas diferente, também deixada de fora por não nomear o conceito exato perguntado.
