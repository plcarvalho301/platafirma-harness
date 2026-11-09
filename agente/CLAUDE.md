# Arranque da PlataFirma — igual em toda superfície

1. Primeira ação da sessão, antes de raciocinar, ler arquivo ou responder: chamar a tool
   `monta_sessao` do conector `claudinho-mcp`, do jeito que a coluna «como chamar» da tabela
   abaixo diz para o seu provider. Não abra o arquivo do provider antes: a chamada vem primeiro.
   - Slug dito na abertura → `monta_sessao(cadeira=<slug>, chapeu=<chapéu, se dito>,
     pergunta=<o turno do dono, literal>)`. Formas: a primeira linha da mensagem, sozinha, como
     `(ia, harness)` ou `(ia)` — cadeira, depois chapéu; «abre como ti»; «monta-sessao(ia, chapeu=harness)».
   - Sem slug → `cadeira="fabrica"`.
2. Pacote chegou: leia o arquivo do seu provider, no `platafirma-posto`, antes de responder.
3. Pacote não chegou só se prova com o erro que o conector devolveu a uma chamada feita: erro de
   autenticação (401, `Unauthorized`, login pendente) ou servidor desconectado, repetido depois de
   alguns segundos e citado literal na primeira linha da resposta.
   - Erro do próprio cliente sobre a forma da chamada (tool desconhecida, nome errado, argumento
     inválido) não prova nada: a chamada é que está errada. Chame a `monta_sessao` pelo nome com
     que o cliente lista o servidor `claudinho-mcp` e tente de novo. Só quando o servidor não aparece
     em lugar nenhum do cliente e a chamada por esse nome também é recusada, cite os dois como prova
     de conector não montado.
   - Não ver a tool antes de chamar não prova nada. Sem prova citada, não se diz que o pacote não
     chegou.
   - Com a prova: não escreva em nada, não improvise cadeira, e siga a seção «Login» do arquivo do
     seu provider.

| provider | como chamar | arquivo |
|---|---|---|
| Claude Code | `ToolSearch` com `select:mcp__claudinho-mcp__monta_sessao`, depois a tool | `providers/claude-code.md` |
| agy (Antigravity CLI) | a tool `monta_sessao` do servidor `claudinho-mcp`, pelo nome com que o agy a expõe; `call_mcp_tool` não existe no agy do posto | `providers/agy.md` |
| Cursor | a tool `monta_sessao` do servidor `claudinho-mcp`, achada na descoberta de MCP do Cursor | `providers/cursor.md` |
| Codex | `tool_search` com `monta_sessao`, depois a tool | `providers/codex.md` |
| outro, ainda sem o conector | não há o que chamar | `providers/novo.md` |

Fonte das linhas acima: `platafirma-harness/abertura/arranque.md`.
