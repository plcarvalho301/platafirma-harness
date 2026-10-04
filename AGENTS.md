# platafirma-harness — roteiro para agente

Arranque de sessão: `CLAUDE.md` (primeira ação, de onde sai a cadeira, o que não
fazer). Charter do módulo e o que entra/não entra: `README.md`.

Clone é cliente: execução e escrita só por `claudinho-mcp`, na máquina do dono.

Verbo se chama por `platafirma <verbo>` (qualquer conta) ou pelo nome (conta dos serviços); `puxar-bancada --alias` grava na conta o atalho de shell `pf` (opcional, ergonomia; a plataforma não nomeia nada `pf`, ont:0087); para codar, `deploy-harness/puxar-bancada --declarar <dir>` na primeira vez traz cada família para a bancada no sha de produção (`docs/instalacao-e-bancada.md`).

## Não fazer

- Não carimbar à mão a cópia de skill entregue ao claude.ai: o carimbo sai de `tooling/export/carimbar.py`, e carimbo à mão mente por construção.
- Não reiniciar o `ops-mcp` direto de dentro de um `malote`: o restart vai em escopo transitório separado (`docs/ops-server.md`, "Restart").
- Não produzir retrato de ator para `chat/avatares/`: é identidade visual, e vem de quem cuida dela, não da fábrica.
- Não pôr diagrama em `diagramas/` sem a linha dele no índice de `docs/diagramas.md`, no mesmo commit; nem instrumento de diagrama em `diagramas/` (mora em `tooling/diagramas/`).
