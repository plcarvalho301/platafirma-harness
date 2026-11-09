# Arranque da PlataFirma — igual em toda superfície

1. Primeira ação da sessão, antes de raciocinar, ler arquivo ou responder: chamar a tool
   `monta_sessao` do conector `claudinho-mcp`, do jeito que a coluna «como chamar» da tabela
   abaixo diz para o seu provider. Não abra o arquivo do provider antes: a chamada vem primeiro.
   - Slug dito na abertura → `monta_sessao(cadeira=<slug>, chapeu=<chapéu, se dito>,
     pergunta=<o turno do dono, literal>)`. Formas: a primeira linha da mensagem, sozinha, como
     `(ia, harness)` ou `(ia)` — cadeira, depois chapéu; «abre como ti»; «monta-sessao(ia, chapeu=harness)».
   - Sem slug → `cadeira="fabrica"`.
2. Pacote chegou: leia o arquivo do seu provider, no `platafirma-posto`, antes de responder.
3. Pacote não chegou só se prova com o retorno de uma chamada feita, do jeito da tabela, repetida
   depois de alguns segundos (o cliente pode carregar os servidores MCP depois do primeiro turno) e
   citada literal na primeira linha da resposta. Vale como prova:
   - erro devolvido pelo conector: autenticação (401, `Unauthorized`, login pendente) ou servidor
     desconectado;
   - o cliente dizer que a própria ferramenta da coluna «como chamar» não existe: ele não carregou
     os servidores MCP.
   Não vale: não ver a tool antes de chamar, nem erro de argumento ou de nome que você mesmo errou
   fora da receita da tabela; esse se corrige e se chama de novo. Sem prova citada, não se diz que o
   pacote não chegou. Com a prova: não escreva em nada, não improvise cadeira, e siga a seção
   «Login» do arquivo do seu provider, que diz qual login falta para cada erro.

| provider | como chamar | arquivo |
|---|---|---|
| Claude Code | `ToolSearch` com `select:mcp__claudinho-mcp__monta_sessao`, depois a tool | `providers/claude-code.md` |
| agy (Antigravity CLI) | `call_mcp_tool(ServerName="claudinho-mcp", ToolName="monta_sessao", Arguments={...})` (medido em 07/11/2026) | `providers/agy.md` |
| Cursor | a tool `monta_sessao` do servidor `claudinho-mcp`, achada na descoberta de MCP do Cursor | `providers/cursor.md` |
| Codex | `tool_search` com `monta_sessao`, depois a tool | `providers/codex.md` |
| outro, ainda sem o conector | não há o que chamar | `providers/novo.md` |

Fonte das linhas acima: `platafirma-harness/abertura/arranque.md`.
