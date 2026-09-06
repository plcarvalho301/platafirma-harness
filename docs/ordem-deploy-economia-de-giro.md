# ORDEM DE DEPLOY — economia-de-giro §3 + métrica (fábrica, UM turno)

> Efêmera. Canônico: `platafirma-arquitetura/docs/specs/spec_economia-de-giro.md`.
> Apagar no commit que fechar o deploy (passo 5). Autor: ia (engenharia-de-harness),
> 06/09/2026, por ordem do dono. A feature é da ia ponta a ponta.

## Estado — o código JÁ está em prod (git); falta só pôr no ar
- `origin/main` = `44c580d`. O clone que o `ops-mcp` roda
  (`WorkingDirectory=~/AI/platafirma-harness/ops-server`) está no mesmo `44c580d`.
  **Nada a pushar.** Restart só faz sentido depois do código em main — e já está.
- O processo vivo (uvicorn, desde 12:02) está ATRÁS de `44c580d`: carrega o
  `server.py` velho até o restart. É isso que o passo 3 corrige.

Dois fatos de ambiente que mandam na ordem:
- **O ops-mcp roda o `server.py` do CLONE de trabalho.** O clone tem de estar no
  main canônico antes do restart (passo 1 é a guarda), senão o restart sobe o
  `server.py` de um branch de feature.
- **Restart mata a conexão de quem chama.** Use `infra restart ops-mcp` — a casa o
  destaca (systemd-run, `bin/infra`), e a fita reconecta no giro seguinte. **NUNCA**
  `systemctl --user restart ops-mcp` direto de dentro da fita.

## O que sobe em `44c580d` (vs. o processo de 12:02)
- `server.py`: sessão-sombra inequívoca ON por padrão (§3); `lote_id`/`lote_n`
  carimbados em cada linha do lote de `run_command`/`read_file` (separa giro de item).
- `bin/descansar`: colapsa lote por `lote_id` e estima turno por gap (`_turnos_por_gap`,
  estimativa declarada, §7). É verbo — **já vale sem restart**; entra junto por higiene.
- `abertura/oficio.md`: régua nova de sessão-sombra. **Precisa `publicar-abertura`**.

## Env — JÁ está certo, NÃO mexer
Env vivo do unit: `PF_TOOLS_VERBOS=1  PF_TOOLS_LEVA2=0  PF_TOOLS_LOTE=1`, sem `PF_SOMBRA`.
- `PF_TOOLS_LOTE=1` já setado (leva 2). Mantém.
- Sem `PF_SOMBRA` no env → manda o default do código, que agora é ON (§3). É o estado
  desejado. **NÃO** adicionar `PF_SOMBRA`.
- `PF_TOOLS_LEVA2` já renomeado (era `PF_TOOLS_LOTE2`). Nada a fazer.

## Passos (em ordem, um turno)
1. **Guarda — clone no main canônico:**
   `cd ~/AI/platafirma-harness; git fetch -q origin; git checkout main; git pull --ff-only`
   Conferir: `git rev-parse --short HEAD` = `44c580d` (ou à frente). Árvore limpa; se
   `teste`/`lint` reclamarem, é dívida de baseline declarada (#2468), não trabalho pendente.
2. **Servir o `oficio.md` novo:** `publicar-abertura` (default `origin/main`).
   Conferir: `publicar-abertura estado` → `current` no head de `origin/main` (`44c580d`).
3. **Restart (último passo, código já em prod):** `infra restart ops-mcp`.
   Esperar ~10s antes de verificar (o restart é destacado; a fita reconecta no giro seguinte).
4. **Verificar no ar:**
   - Gate vivo: `run_command("mesa ver")` volta com aviso de roteamento por verbo;
     `run_command("git status")` NÃO traz aviso (fallback legítimo).
   - Lote carimbado: `read_file(paths=["abertura/oficio.md","abertura/persona.md"])`
     volta 2 itens; em `~/AI/var/log/ops/ops-<hoje>.jsonl` as 2 linhas de `read_file`
     carregam o MESMO `lote_id` e `lote_n` 0 e 1.
   - Sombra §3 (⚪ conferir no log): chamada de verbo sem `sessao_id`, com uma só sessão
     viva, resolve a cadeira em vez de cair em `-`.
5. **Fechar:** `git rm docs/ordem-deploy-economia-de-giro.md`; commit
   `ordem-deploy: fecha economia-de-giro §3 — deploy verificado no ar`; push no main.

## Rollback (qualquer perna, sem tocar git de conteúdo)
Drop-in `~/.config/systemd/user/ops-mcp.service.d/rollback.conf`:
`Environment=PF_SOMBRA=0` (volta sombra OFF) e/ou `PF_GATE=0` e/ou `PF_TOOLS_LOTE=0`;
`systemctl --user daemon-reload`; `infra restart ops-mcp`.

## Não fazer
- `systemctl --user restart ops-mcp` direto na fita (mata a conexão; use `infra restart`).
- Tocar `dono.md` ou o molde de resposta.
- Adicionar `PF_SOMBRA` ao env (o default do código já é o certo).
- Reiniciar no meio de outro build.
