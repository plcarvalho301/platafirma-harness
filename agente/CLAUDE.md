# Arranque da PlataFirma — igual em toda superfície

1. Primeira ação da sessão, antes de raciocinar ou responder: chamar a tool `monta_sessao` do
   conector `claudinho-mcp`, onde quer que o cliente a ponha — na lista de funções, num bloco de
   servidores MCP, atrás de uma busca de tool ou de um despachante genérico de MCP. Muito cliente
   carrega MCP sob demanda: não estar na lista de funções à vista não é não existir.
   - Slug dito na abertura → `monta_sessao(cadeira=<slug>, chapeu=<chapéu, se dito>,
     pergunta=<o turno do dono, literal>)`. Formas: a primeira linha da mensagem, sozinha, como
     `(ia, harness)` ou `(ia)` — cadeira, depois chapéu; «abre como ti»; «monta-sessao(ia, chapeu=harness)».
   - Sem slug → `cadeira="fabrica"`.
2. Pacote chegou: leia o arquivo do seu provider, no `platafirma-posto`, antes de responder.
3. Pacote não chegou se prova com uma tentativa, nunca com a lista à vista: o conector não consta
   em catálogo nenhum do cliente, ou a chamada voltou erro (login pendente, erro na abertura). Só
   então diga isso na primeira linha, com o erro, não escreva em nada, não improvise cadeira, e
   siga a seção «Login» do arquivo do seu provider.

| provider | arquivo |
|---|---|
| Claude Code | `providers/claude-code.md` |
| agy (Antigravity CLI) | `providers/agy.md` |
| Cursor | `providers/cursor.md` |
| Codex | `providers/codex.md` |
| outro, ainda sem o conector | `providers/novo.md` |

Fonte das linhas acima: `platafirma-harness/abertura/arranque.md`.
