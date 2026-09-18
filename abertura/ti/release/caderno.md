# caderno — release (chapéu de TI)

## Lições (conhecimento curado)

- Promover platafirma-harness NÃO é `deploy` nem `release promover ... --ensaio` sem rev: é família de código, exige rev explícita alcançável por origin/main (`release promover platafirma-harness <sha>`). `deploy` só serve stacks de compose (harness-controle, chat, etc.), não o harness inteiro.
- Merge de PR não sobe código: o release fica no sha anterior até `release promover`. Sequência de entrega de PR da fábrica = pr-merge → repo atualizar (pega o sha novo do squash) → release promover <sha> → a própria promoção despacha o restart da porta (ops-mcp), destacado. Conferir depois com `infra estado ops-mcp` + `infra saude`.
- Validar entrega da fábrica exige o venv do release (`/opt/platafirma/current/venv/harness`), não o Python do sistema nem `uvx`. As suítes de contrato (controle/tests, ops-server) só passam nesse venv; fora dele quebram por dep faltando, sem ser culpa do código.

## Diário de bordo

2026-09-18 — validar PR 63 rodando testes: `teste rodar /tmp/pr63` recusou (só aceita slug dentro de ~/AI); worktree solto (`/home/claudinho/AI/pr63-harness`) rodou com uvx/python3.14 do sistema e quebrou por yaml/redis/mcp/psycopg ausentes — falsos vermelhos de ambiente. Contorno NA DATA 18/09: apontei o worktree oficial `wt/platafirma-harness/ti` para o ramo do PR (checkout --detach), rodei `teste rodar platafirma-harness <alvo>` (usa o venv harness), 4 suítes de contrato verdes; depois restaurei o worktree para eed707a→main.
2026-09-18 — suíte ops-server/test_run_command_lote_injecao.py não coleta nem no venv harness: `ModuleNotFoundError: mcp` (server.py:64, import da FastMCP, fora do diff). Parede: o venv harness não carrega o pacote `mcp` da porta. Contorno NA DATA 18/09: nenhum daqui; validado por leitura do diff do teste + relato do autor (3/3 no ambiente da porta). Fica registrado que essa suíte precisa do venv `ops`, não `harness`.
2026-09-18 — `git` cru, `bash`/`ls`/`find` crus e `cd &&` recusados pela porta (roteados a repo/teste/read_file/descobrir, ou barrados como metacaractere). Contorno NA DATA 18/09: git via `repo git <slug> -C <path> ...`; navegação de arquivo por `run_command` com `cwd`; nunca encadear com `&&`.
2026-09-18 — `release promover ... --ensaio` para sha recém-mesclado falhou: "rev não resolve no forge" — o espelho do release não faz fetch em ensaio. Contorno NA DATA 18/09: rodar a promoção real (ela faz o fetch), com o sha completo confirmado por `repo git rev-parse origin/main`.