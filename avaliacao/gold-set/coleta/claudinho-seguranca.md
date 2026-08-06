1. Qual é o procedimento completo de rotação de chaves de assinatura (realm keys) no Keycloak sem invalidar sessões ativas, e qual a ordem correta entre criar a chave nova, rebaixar a antiga e removê-la?
   tipo: simples
   esperada: nenhuma — seria Keycloak Server Administration Guide (documentação oficial, versão 26.x)

2. Quais são os requisitos exatos do NIST SP 800-63B para AAL2 em matéria de resistência a replay, prova de posse e intervalo de reautenticação?
   tipo: simples
   esperada: NIST SP 800-63B-4 — Authentication

3. Qual é a diferença normativa entre `aud`, `azp` e `resource` no RFC 8707 (Resource Indicators) e como o OIDC Core trata audience em ID token versus access token?
   tipo: simples
   esperada: Final_ OpenID Connect Core 1.0 incorporating errata set 2   [casamento parcial — dono flagou: só cobre metade OIDC Core; RFC 8707 não está no acervo]

4. Quais controles do CIS Controls v8 no IG1 cobrem gestão de contas e gestão de acesso (Controls 5 e 6), e quais safeguards exigem inventário de contas de serviço?
   tipo: simples
   esperada: CIS Controls v8

5. Qual é o ciclo de vida de chave recomendado pelo NIST SP 800-57 Part 1 — períodos de uso (originator-usage vs recipient-usage), estados da chave e cryptoperiods sugeridos por tipo de chave?
   tipo: simples
   esperada: nist.sp.800-57pt1r5

6. Num broker OIDC single-node como o nosso, a partir de que ponto a indisponibilidade do IdP federado (Google) deveria disparar um modo degradado local — e o que a literatura de resiliência diz sobre trade-off entre cache de sessão longa e janela de revogação, considerando que sessão longa é decisão de disponibilidade que corrói a garantia de revogação (AAL/FAL)?
   tipo: complexa
   esperada: Release it!_ design and deploy production-ready software -- Michael T_ Nygard -- The pragmatic programmers, Raleigh, N_C, North Carolina, -- Pragmatic -- isbn13 9780978739218 -- 93af097dc316b957068154ab9d210307 -- Anna's Archive   [dono flagou: casa a metade genérica (resiliência), não a topologia do nosso broker]

7. Se o token carrega `dominio:papel:escopo` como tupla plana e o downscoping recorta por frente, qual é o custo formal de expressividade em relação a um modelo ABAC completo do SP 800-162 — que classes de política se tornam inexpressáveis, e isso importa antes de existir um segundo sujeito no sistema?
   tipo: complexa
   esperada: nist.sp.800-162

8. Migração híbrida PQC no nosso TLS de borda (Cloudflare na frente, tunnel no meio, serviços atrás): onde exatamente x25519_mlkem768 protege contra harvest-now-decrypt-later e onde não protege nada, dado que o túnel termina TLS em pontos que não controlamos?
   tipo: complexa
   esperada: Relatório Executivo_ A Transição para a Criptografia Pós-Quântica (PQC) e a Proteção das Infraestruturas Críticas no Brasil   [dono flagou: tem gêmea próxima no acervo — "Ameaça da Computação Quântica..._ Relatório Executivo de Segurança"; não contar erro cheio se a busca devolver a gêmea]

9. O modelo de isolamento entre `megafone` e `claudinho` remove escalação por grupo, mas o MCP é um canal de execução arbitrária como `claudinho` — sob que modelo de ameaça (prompt injection na cadeia de contexto, comprometimento do cliente MCP) o isolamento de conta ainda vale alguma coisa, e o que a literatura de confused deputy diz sobre isso?
   tipo: complexa
   esperada: Security Engineering_ A Guide to Building Dependable -- Ross J_ Anderson [Anderson, Ross J_] -- 2010 -- Wiley -- 214b8251993da512c72cf9ba0da7837a -- Anna's Archive   [dono flagou: casa o núcleo conceitual, não a topologia megafone/claudinho — isso é wiki, não acervo]

10. Para um sistema single-user, qual é o ponto de inflexão mensurável em que logging de auditoria (CIS Control 8) deixa de ser teatro de conformidade e passa a ter valor forense real — e como dimensionar retenção quando o atacante plausível é o próprio operador da infraestrutura ou seu agente de IA?
   tipo: complexa
   esperada: nenhuma

# nenhuma: 2 (itens 1, 10) — item 1 alimenta a fila de aquisição (Keycloak Admin Guide, procedimento puro)
# fila de aquisição adicional sugerida pelo dono: RFC 8707 (Resource Indicators)
