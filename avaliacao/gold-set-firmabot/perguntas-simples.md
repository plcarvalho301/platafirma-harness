# Perguntas simples — sondas single-hop

Vocabulário e alvo: `platafirma-conhecimento` (claudinho-conhecimento).
Sonda, protocolo e régua de admissão: este repo.
Protocolo de execução: `procedimento.md`

Numeração é estável e nunca se reaproveita: sonda que sai do núcleo mantém o número.

## Régua de alvo

- **Alvo é único.** Alvo com barra ou com `+` admite mais de um acerto e não mede nada.
- Havendo mais de uma obra ligada ao conceito, o alvo é a que **trata o conceito como
  matéria**. Citação de passagem não qualifica — entra como distrator conhecido, nomeado.
- Termo não carrega o nome da obra, do autor nem código de norma.

## Bloco A — 10 sondas conceituais

Intocáveis. Série de consolidação iniciada em 2026-08-04; reescrever qualquer uma
amputa a série.

| # | pergunta |
|---|---|
| 1 | o que é um conceito e qual seu critério de identidade? |
| 2 | o que distingue um tipo de um papel? |
| 3 | o que é arquitetura de software? |
| 4 | o que é arquitetura de dados? |
| 5 | o que é governança de dados? |
| 6 | o que é um domínio em gestão do conhecimento? |
| 7 | o que é inteligência? |
| 8 | o que é criptografia pós-quântica? |
| 9 | o que é uma decisão arquitetural e quando se registra? |
| 10 | o que é curadoria de acervo? |

## Bloco B — núcleo, 14 conceitos canônicos

Um termo por sonda, teste de dicionário estrito: termo → obra. Todo alvo tem obra única,
ou uma marcada como a certa com a razão escrita. `ᴱ` marca termo em inglês admitido.

| # | bloco | termo | alvo |
|---|---|---|---|
| 11 | arquitetura | DDD ᴱ | Evans, *Domain-Driven Design* |
| 12 | arquitetura | lei de Conway | *Architecture Modernization* (Tune/Perrin) — distrator conhecido: *Building State Capability*, que cita sem tratar |
| 13 | arquitetura | business-capability ᴱ | *BIZBOK Guide* |
| 17 | IA | fusão recíproca de rankings | Cormack, *Reciprocal Rank Fusion outperforms Condorcet…* |
| 18 | IA | degradação em contexto longo | *Lost in the Middle: How Language Models Use Long Contexts* |
| 19 | IA | quantização | *Quantize with Confidence?* — `llama.cpp — GGUF` segue ligado ao conceito e não é alvo: casa por nome de produto |
| 23 | TI (ITSM) | gestão de incidente de serviço (ITSM) | ITIL 4 §5.2.5 — conceito distinto de incidente de segurança |
| 24 | TI (ITSM) | habilitação de mudança (ITSM) | ITIL 4 |
| 25 | TI (ITSM) | observabilidade | *Observability Engineering* |
| 26 | fábrica (dev) | trunk-based development ᴱ | *Accelerate* |
| 27 | fábrica (dev) | feature toggle ᴱ | *Building Microservices* (2ª ed.) |
| 28 | fábrica (dev) | teste de contrato | *Building Microservices* (2ª ed.) |
| 30 | segurança | garantia de identidade | NIST SP 800-63B-4 |
| 31 | segurança | acesso privilegiado | *CIS Controls v8* — distrator conhecido: *NIST SP 800-53 Rev.5*, que cita em AC-6 dentro de um catálogo de ~20 famílias sem tratar como matéria |

## Bloco B — anel, 10 conceitos não medidos

Não existem em `acervo.conceito` com obra própria. Não entram em rodada de medição
enquanto não passarem pela régua de admissão — onda de admissão antes de onda de medição.
Ficam aqui para não serem reinventados com outro número.

| # | bloco | termo candidato |
|---|---|---|
| 14 | conhecimento | vocabulário controlado |
| 15 | conhecimento | continuant e occurrent |
| 16 | conhecimento | proveniência arquivística |
| 20 | produto | opportunity solution tree ᴱ |
| 21 | produto | posicionamento de produto |
| 22 | produto | avaliação heurística |
| 29 | segurança | cryptoperiod |
| 32 | gestão estratégica | cost of delay ᴱ |
| 33 | gestão estratégica | limite de WIP |
| 34 | gestão estratégica | role charter ᴱ |
