1. Qual é o conjunto mínimo de práticas técnicas que o corpo DORA/Accelerate valida como preditoras de desempenho de entrega, e como cada uma é medida?
   tipo: simples
   esperada: Accelerate

2. Que perguntas o pilar de Excelência Operacional do AWS Well-Architected 2024 manda responder antes de aprovar uma mudança em produção?
   tipo: simples
   esperada: wellarchitected-framework-2024-06-27

3. Segundo Newman (Building Microservices 2nd), quais são os critérios para escolher entre deploy blue-green, canary e rolling, e o que cada um exige de infraestrutura?
   tipo: simples
   esperada: Building Microservices (2nd)

4. Como o Kafka: The Definitive Guide define a política de retenção de log por tamanho vs. por tempo, e qual o efeito de cada uma sobre consumidores atrasados?
   tipo: simples
   esperada: Kafka: The Definitive Guide

5. Quais métricas de fluxo o relatório DORA 2025 de desenvolvimento assistido por IA acrescenta ou reinterpreta em relação às quatro métricas clássicas?
   tipo: simples
   esperada: 2025_state_of_ai_assisted_software_development

6. Num host único sem orquestrador, que combinação de práticas de release (trunk-based, feature flag, rollback por imagem) reproduz o efeito de "deploy desacoplado de release" que a literatura de entrega contínua assume — e onde a reprodução quebra?
   tipo: complexa
   esperada: Building Microservices (2nd)   [casamento fraco — dono flagou: obra canônica é Continuous Delivery (Humble & Farley), ausente do acervo]

7. Como aplicar back pressure (Continuous Architecture in Practice) num pipeline de embedding batch onde o produtor é um extractor síncrono e o consumidor é uma GPU compartilhada com outra carga — e em que ponto isso deixa de ser problema de arquitetura e vira problema de dados (fronteira com o arquiteto)?
   tipo: complexa
   esperada: Continuous Architecture in Practice

8. Se a plataforma adotar comunicação por eventos entre personas em vez de fila de arquivos, que garantias de ordenação e idempotência a literatura de event-driven exige que o consumidor assuma, e o que disso a fila de arquivos atual já entrega de graça?
   tipo: complexa
   esperada: Building Event-Driven Microservices

9. Que controles do domínio de segurança (hardening de contêiner, verificação de assinatura, escaneamento de dependência) têm interseção com o pipeline de build a ponto de precisarem entrar no desenho da fábrica — e onde termina a minha decisão e começa a do claudinho-seguranca?
   tipo: complexa
   esperada: nist.sp.800-218

10. Como reconciliar a métrica de change failure rate com um ambiente onde o "deploy" é um `docker compose up` sem gate formal: o que a literatura de mudança controlada exige de mínimo para a métrica sequer ser mensurável?
   tipo: complexa
   esperada: Accelerate   [casamento parcial — dono flagou: cobre o núcleo (CAB/aprovação), mas ITSM formal (ITIL) segue ausente do acervo]

# nenhuma: 0 — dono declarou suspeito por conta própria, dois casamentos marcados fracos/parciais acima (6, 10)
# achado lateral (fora do gabarito): mapa de cobertura da instruction de TI está desatualizado — Release It!, Observability
# Engineering, DDIA, SRE Workbook e a série FitSM completa existem no manifesto sem faceta e não constam no "NÃO TEM" dele.
