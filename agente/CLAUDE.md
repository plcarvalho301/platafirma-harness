# Arranque da PlataFirma — igual em toda superfície

1. Primeira ação da sessão, antes de raciocinar, ler arquivo ou responder: chamar a tool
   `monta_sessao` do conector `claudinho-mcp`, do jeito que a coluna «como chamar» da tabela
   abaixo diz para o seu provider. Não abra o arquivo do provider antes: a chamada vem primeiro.
   - Slug dito na abertura → `monta_sessao(cadeira=<slug>, chapeu=<chapéu, se dito>,
     pergunta=<o turno do dono, literal>)`. Formas: a primeira linha da mensagem, sozinha, como
     `(ia, harness)` ou `(ia)` — cadeira, depois chapéu; «abre como ti»; «monta-sessao(ia, chapeu=harness)».
   - Sem slug → `cadeira="fabrica"`.
2. Pacote chegou: leia o arquivo do seu provider, no `platafirma-posto`, antes de responder.
3. Pacote não chegou só se prova com o erro de uma chamada feita. Não ver a tool na lista de
   funções, no bloco de servidores MCP ou numa busca não prova nada: chame assim mesmo, e o erro
   que o cliente devolver é a prova. Com erro, espere alguns segundos e chame de novo, uma vez,
   porque o conector pode estar montando. Com o segundo erro, a primeira linha da resposta cita o
   erro literal; sem erro para citar, não se diz que o pacote não chegou. Então não escreva em
   nada, não improvise cadeira, e siga a seção «Login» do arquivo do seu provider.

| provider | como chamar | arquivo |
|---|---|---|
| Claude Code | `ToolSearch` com `select:mcp__claudinho-mcp__monta_sessao`, depois a tool | `providers/claude-code.md` |
| agy (Antigravity CLI) | `call_mcp_tool(ServerName="claudinho-mcp", ToolName="monta_sessao", Arguments={...})` | `providers/agy.md` |
| Cursor | a tool `monta_sessao` do servidor `claudinho-mcp`, achada na descoberta de MCP do Cursor | `providers/cursor.md` |
| Codex | `tool_search` com `monta_sessao`, depois a tool | `providers/codex.md` |
| outro, ainda sem o conector | não há o que chamar | `providers/novo.md` |

Fonte das linhas acima: `platafirma-harness/abertura/arranque.md`.
