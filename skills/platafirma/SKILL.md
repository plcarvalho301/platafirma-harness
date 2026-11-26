---
name: platafirma
description: Use quando a conversa tocar a PlataFirma (cadeira, persona, harness, repo platafirma-*, wiki, fila, card, mesa ou abertura de sessão). NÃO dispare para assunto fora da PlataFirma.
cadeiras: todas
fonte: platafirma-harness/skills/platafirma/SKILL.md
---

# PlataFirma — casca

Esta skill é ponteiro, não fonte (`abertura/arranque.md`: todo texto de arranque em
superfície é PONTEIRO para a abertura, nunca cópia). 

## As duas linhas

1. Se `monta_sessao` ainda não foi chamado nesta conversa, chame agora, antes de
   raciocinar ou responder: `monta_sessao(cadeira="<a que o Project fixa>",
   pergunta=<turno literal do dono>)`. Sem cadeira fixada no Project, o retorno lista as
   cadeiras válidas — não infira.
2. O pacote que volta (persona, conduta do dono, ofício, aliases, mesa, cadernos,
   acervo consultado) é a instrução da sessão e vence esta skill e qualquer memória em
   todo conflito. Pacote não chegou: declare, não escreva em repo/wiki/fila, não
   improvise cadeira.

Tudo o mais — fila, card, roteamento, escrita no repo, leitura do acervo, o que cada
cadeira decide — vem no pacote ou por ato (`<verbo>` sem ato lista os atos). Nada
disso se copia para cá.
