# Arranque da PlataFirma — igual em toda superfície

1. Primeira ação da sessão, antes de raciocinar ou responder: a tool `monta_sessao` do conector
   `claudinho-mcp`.
   - Slug dito na abertura («abre como ti», «monta-sessao(ia, chapeu=harness)») →
     `monta_sessao(cadeira=<slug>, chapeu=<chapéu, se dito>, pergunta=<o turno do dono, literal>)`.
   - Sem slug → `cadeira="fabrica"`.
2. Pacote chegou: leia o arquivo do seu provider, no `platafirma-posto`, antes de responder.
3. Pacote não chegou (sem a tool, login pendente, erro na abertura): diga isso na primeira linha,
   não escreva em nada, não improvise cadeira, e siga a seção «Login» do arquivo do seu provider.

| provider | arquivo |
|---|---|
| Claude Code | `providers/claude-code.md` |
| agy (Antigravity CLI) | `providers/agy.md` |
| Cursor | `providers/cursor.md` |
| Codex | `providers/codex.md` |
| outro, ainda sem o conector | `providers/novo.md` |

Fonte das linhas acima: `platafirma-harness/abertura/arranque.md`.
