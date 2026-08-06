# Estado de formalização — G0-rag-base, 34 sondas

Levantado em 2026-08-06, contra `acervo_sha 24ed2cbf607e`. Wiki: `search_pages`
(prosa livre, termo exato e sem acento — o buscador não normaliza acento).
Git: `platafirma-conhecimento/ontologia/adr/*` e `platafirma-arquitetura/macro-global/*`
por padrão de conteúdo; demais repos (`mdm-rh`, `platafirma-motor`,
`platafirma-ollama-orchestrator`, `platafirma-osint`, `platafirma-posto`, `platafirma-core`,
`platafirma-harness`) por grep amplo de termo.

Ausência é dado — nenhuma linha omitida.

## Bloco A — 10 sondas fixas

Nenhum termo tem página wiki homônima. O que existe são páginas-índice/ajuda
adjacentes, listadas abaixo com data de criação e última edição (via Action API).

| # | termo | página adjacente existente | criada | última edição |
|---|---|---|---|---|
| 01 | conceito | Estudos-ontologias/teia-de-conceitos | 2026-07-31 | 2026-07-31 |
| 01 | conceito | Ajuda:Glossário | 2026-08-02 | 2026-08-04 |
| 01 | conceito | Estudos-ontologias | 2026-07-15 | 2026-08-06 |
| 02 | tipo vs papel | Ajuda:Método/taxonomia | 2026-07-18 | 2026-07-25 |
| 03 | arquitetura de software | Arquiteturas | 2026-07-15 | 2026-08-05 |
| 03 | arquitetura de software | Engenharia-software | 2026-07-15 | 2026-08-05 |
| 03 | arquitetura de software | Arquitetura:Índice | 2026-08-01 | 2026-08-03 |
| 03 | arquitetura de software | Arquitetura:Topologia | 2026-07-29 | 2026-08-03 |
| 04 | arquitetura de dados | Engenharia-dados | 2026-07-28 | 2026-07-28 |
| 05 | governança de dados | Governo-digital (nome não bate) | 2026-07-15 | 2026-07-28 |
| 06 | domínio | Ajuda:Criar um domínio | 2026-07-15 | 2026-08-04 |
| 06 | domínio | Ajuda:Explorar por faceta | 2026-07-16 | 2026-07-28 |
| 07 | inteligência | IA (nome não bate) | 2026-07-15 | 2026-07-26 |
| 08 | criptografia pós-quântica | Seguranca-privacidade | 2026-07-15 | 2026-08-01 |
| 08 | criptografia pós-quântica | Frente:modulo-firma/backlog-canalseguroPQC-draft | 2026-07-14 | 2026-08-01 |
| 09 | decisão arquitetural | Arquitetura:ADRs | 2026-08-03 | 2026-08-03 |
| 09 | decisão arquitetural | Arquitetura:Registro-de-decisoes | 2026-08-03 | 2026-08-03 |
| 09 | decisão arquitetural | PlataFirma:Decisões/adrs | 2026-07-29 | 2026-08-03 |
| 10 | curadoria de acervo | Ajuda:Operar o acervo | 2026-08-03 | 2026-08-03 |
| 10 | curadoria de acervo | Ajuda:Sincronizar o acervo | 2026-08-03 | 2026-08-03 |
| 10 | curadoria de acervo | PlataFirma:Ops/operar-o-acervo | 2026-08-01 | 2026-08-05 |

**ADR/git** (`t0_adr_estado.sh`, grep por termo em `platafirma-conhecimento/ontologia/adr`
e `platafirma-arquitetura/macro-global`): zero ocorrência para
`arquitetura de software`, `arquitetura de dados`, `governança de dados`,
`criptografia pós-quântica`. `inteligência` aparece em 3 arquivos, `curadoria` em 8 —
menção lateral, não ADR dedicado ao conceito.

SHA no momento da varredura: `platafirma-arquitetura 2d1db226`,
`platafirma-conhecimento fc4e5f26`.

## Bloco B — 24 conceitos canônicos

**Wiki: 0/24 tem página de conceito.** Confirmado sem página em `search_pages`,
testado com e sem acento. Exceção parcial: nenhuma.

**ADR/git:** zero ADR dedicado a qualquer um dos 24, em nenhum dos 9 repos
verificados. Três achados de menção lateral (não formalização do conceito):

- `#25 observabilidade` — README estrutural de capability em
  `platafirma-arquitetura/macro-global/capabilities/observabilidade/README.md`,
  e nome de gerência no org chart (`macro-global/organizacao/README.md`).
- `#13 arquitetura de negócios`, `#23/#24 gestão de incidente/mudança` — só como
  nome de gerência/head no org chart, mesmo README.
- `#31 gestão de acesso privilegiado` — citado 9x em `mdm-rh/docs/1_adr.md`
  (ADR de projeto), como decisão de escopo ("fora dos 4 painéis, acesso
  privilegiado documentado"). É o único dos 24 com peso de decisão registrada
  em algum lugar — mas em ADR de projeto (mdm-rh), não em ADR de domínio/macro.

| # | termo | wiki | ADR dedicado | menção lateral |
|---|---|---|---|---|
| 11 | DDD | não | não | ADR 0067 (conhecimento), como exemplo de termo doutrinário |
| 12 | convergência sociotécnica | não | não | — |
| 13 | arquitetura de negócios | não | não | nome de gerência (org chart) |
| 14 | vocabulário controlado | não | não | — |
| 15 | continuant e occurrent | não | não | — |
| 16 | proveniência arquivística | não | não | — |
| 17 | fusão recíproca de rankings | não | não | — |
| 18 | estratégia de chunking | não | não | — |
| 19 | quantização de modelo | não* | não | — |
| 20 | opportunity solution tree | não | não | — |
| 21 | posicionamento de produto | não | não | — |
| 22 | avaliação heurística | não | não | — |
| 23 | gestão de incidente | não | não | nome de gerência (org chart, ITSM) |
| 24 | gestão de mudança | não | não | nome de gerência (org chart, ITSM) |
| 25 | observabilidade | não | não | README de capability + nome de gerência |
| 26 | trunk-based development | não | não | — |
| 27 | feature flag | não | não | — |
| 28 | teste de contrato | não | não | — |
| 29 | cryptoperiod | não | não | — |
| 30 | nível de garantia de autenticação | não | não | — |
| 31 | gestão de acesso privilegiado | não | não | ADR de projeto (mdm-rh/docs/1_adr.md, 9 menções) |
| 32 | cost of delay | não | não | — |
| 33 | limite de WIP | não | não | — |
| 34 | role charter | não | não | — |

`*` `#19 quantização de modelo` não tem página **conceito** homônima, mas existe
conteúdo adjacente em `IA/infra/quantizacao` (estrato de infra, não conceito
individual) — mesma distinção wiki-de-conceitos vs. wiki-de-estrato do Bloco A.
Achado à parte: `search_pages` não normaliza acento (`quantização` → 0 resultados,
`quantizacao` → acha a página); todos os 24 termos foram testados nas duas formas.

## Leitura

Zero conceito do Bloco B tem página própria ou ADR dedicado — o gold set está
testando recuperação bibliográfica (o RAG busca nas obras) contra um vocabulário
que a wiki ainda não formalizou. Isso não é falha do RAG nem do teste: é o estado
real do acervo de conceitos em 06/08/2026, e é exatamente o gap que justifica a
existência do próprio gold set.
