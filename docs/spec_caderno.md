# Caderno — memória durável de ofício, por cadeira e chapéu

Baseline decidido pelo dono em 14/08/2026. Ajuste com o uso vem depois de v0 do
chat.

## O que é

Arquivo versionado em `caderno/<cadeira>/<chapeu>.md`, lido por
`mesa caderno <chapeu>`. Durável, sem TTL. A abertura de sessão entrega só o
**índice** (nome, idade, bytes); o corpo entra na fita que o pediu.

Par do slot efêmero: mesa (`mem:<cadeira>:<slot>`, TTL 14 dias, sobrescrita)
guarda o que a fita de hoje entrega à de amanhã; caderno guarda o que aquele
chapéu aprendeu do próprio ofício. Mesmo eixo — o chapéu declarado na persona.

## Admissão — os dois testes, juntos

1. Continua verdadeiro depois que o assunto da fita morrer?
2. A próxima fita pagaria custo real para re-derivar — medição refeita,
   armadilha repisada, régua de leitura reconstruída?

Falhando um, não entra.

### Não entra, e para onde vai

| o que é | casa certa |
|---|---|
| fato de negócio, decisão registrada | card, commit, wiki |
| estado de runtime (número, SHA, card aberto) | o instrumento que mede |
| decisão de remit, fronteira, propriedade | canônico (org, ADR, persona) |
| o que vale para toda cadeira | o ofício (`abertura/oficio.md`) ou o chapéu |
| conhecimento com validade ("X está aposentado", "por ora, carta") | mesa — expira junto |

O último é o corte menos óbvio e o mais caro de errar: conhecimento verdadeiro
hoje e falso em três semanas apodrece no durável e passa a mentir com cara de
canônico. Referência aposentada tem prazo; mesa tem TTL.

## Ciclo de vida

- **Nascimento** — no primeiro delta real. Não se preenche caderno de memória
  nem retroativamente: seria fabricar exatamente o fóssil que a revisão existe
  para matar.
- **Escrita** — etapa obrigatória de `encerrar fita`, por chapéu tocado na fita.
  "Sem delta" é resposta válida e **declarada**; silêncio não é.
- **Forma** — só estado atual, como todo documento da casa. Entrada nova
  **substitui** a que contradiz; não convivem. Histórico é o git.
- **Poda** — teto de **100 linhas por chapéu**. Acima disso, a próxima escrita
  poda antes de acrescentar. `encerrar fita` mede e marca.
- **Revisão** — `conferir caderno [cadeira]`: confere nome de cadeira contra o
  org, verbo contra o catálogo, stack e host contra o registro do `deploy`, e
  reprova referência a coisa que não existe mais. Roda na varredura diária, não
  no gate de commit — reprovar no meio do ritual de encerramento trava a
  escrita que o verbo acabou de exigir. Redação do subcomando é de claudinho-TI
  (`conferir` é verbo dele).

## Por que a régua é magra

Testada em 14/08 contra quatro memórias de Project de cadeiras distintas, quase
nada foi para o caderno: o grosso era estado (já servido em runtime), armadilha
compartilhada (TODA-CADEIRA), conduta do dono (RH) ou conhecimento com validade
(mesa). O resíduo por cadeira é pequeno **por desenho** — caderno gordo é
Project Memory reconstruída com outro nome, fóssil incluído.

Prova do mesmo teste: o único caderno existente carregava uma cadeira
renomeada dois dias antes e uma decisão de remit superada pelo org. As duas
saíram; a segunda por escopo, não por idade.
