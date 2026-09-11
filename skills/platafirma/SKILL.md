---
name: platafirma
description: Use sempre que a conversa tocar a PlataFirma — cadeiras e personas claudinho/claudinha, harness, repos platafirma-*, wiki, fila, card, mesa, caderno, PEP, abertura de sessão — ou quando a palavra "platafirma" aparecer. Esta skill é CASCA - ela não carrega regra nenhuma, só manda abrir a sessão pela porta, de onde vem tudo. NÃO se aplica ao Jaiminho nem ao ambiente isolado modulo-osint (skill `osint`).
cadeiras: todas
fonte: platafirma-harness/skills/platafirma/SKILL.md
---

# PlataFirma — casca

Esta skill é ponteiro, não fonte (`abertura/arranque.md`: todo texto de arranque em
superfície é PONTEIRO para a abertura, nunca cópia). Cópia congela no dia do upload e
passa a contradizer a régua viva sem que ninguém veja — foi o que aconteceu com a versão
anterior desta skill (reescrita em 11/09/2026, ordem do dono).

O desenho da casa é fungível: a mesma abertura serve claude.ai, fita do chat, Code e agy.
Skill é específica do claude.ai; por isso ela não sabe nada — quem sabe é a porta.

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
