## conhecimento curado
- Sub-agente não responde ao dono: não carrega conduta nem tem dono. Recebe o recorte de cadeira e chapéu que a tarefa pede, medido, e age na sessão do orquestrador (preferência do dono, 27/09).
- Sub-agente e bot são planos distintos que compõem: o arquivo do especialista diz quem faz (instrução, tools, modelo); o bot diz quando roda, dono e vivo/caído. Fundir põe agenda num especialista que a sessão comum não usa.
- Modelo do sub-agente se escolhe por papel, não pela sessão: orquestrador caro planeja e confere, fan-out barato executa; a conferência do achado fica com modelo diferente do que gerou (juiz-modelo).
- Vocabulário: turno = um prompt, uma saída (`claude -p`); giro = cada chamada de tool dentro do turno. O `--max-turns` do Claude Code conta giros (dono, 28/09).
- Guia de estudo de multiagente (perguntas 1-8 da aula #3155) na wiki: IA/agentes/multiagente-guia-de-estudo (28/09).

## diario de bordo
- 27/09 — tarefas editar devolveu "[igual ao giro 12 — 136 bytes não reenviados]" na segunda e terceira edição do mesmo card: a poda deduplica a confirmação, idêntica, e o retorno não distingue "editou de novo" de "não rodou" — contorno encontrado NA DATA 27/09 foi nenhum; confiei no exit 0. Encaminhar a ti.
- 27/09 — mesa item com texto posicional e --ref: erro de uso; a forma é mesa item <chapeu> --ato --alvo — contorno encontrado NA DATA 27/09 foi ler mesa item --help.
- 27/09 — mesa caderno <chapeu> com stdin só lê; escrita do caderno é mesa escrever <chapeu> — contorno encontrado NA DATA 27/09 foi ler mesa escrever --help.
- 27/09 — motor buscar casa "posto" voltou cobertura fraca (0.453), só o runbook estacao-emprestada; não há documento de casa sobre o posto em si — contorno encontrado NA DATA 27/09 foi ler o runbook inteiro.
- 28/09 — sem conector de wiki no chat, a wiki cai no login; com o dono logado no navegador do app, a API da wiki aceita edição (sai como IP interno, não como bot) — contorno encontrado NA DATA 28/09 foi editar pela API via navegador; o conserto é o conector PlataFirma Wiki no projeto.
- 28/09 — tarefas comentar via lote com --stdin gravou o literal «--stdin» (#1136, #1143 no #3155); texto posicional funciona — contorno encontrado NA DATA 28/09 foi comentar com o texto como argumento.