# ORDEM DE DEPLOY — economia-de-giro (fábrica, um turno)

> Efêmera. Canônico: `platafirma-arquitetura/docs/specs/spec_economia-de-giro.md`.
> Apagar no commit que fechar o deploy. Autor: ia (engenharia-de-harness), 06/09/2026, por ordem do dono (a feature é da ia ponta a ponta).

## Estado
Leva 1+2 já em `origin/main` (merge `daac764`). Falta pôr no ar. Dois fatos de ambiente que mandam na ordem:
- **O ops-mcp roda o `server.py` do CLONE de trabalho** (`WorkingDirectory=~/AI/platafirma-harness/ops-server`). O clone tem de estar no **main canônico** antes do restart, senão o restart carrega o branch de feature.
- **Restart do ops-mcp mata a conexão de quem chama.** Use `infra restart ops-mcp` — a casa já o **destaca** (systemd-run, `bin/infra:410-438`); a fita reconecta sozinha no giro seguinte. **NUNCA** `systemctl --user restart ops-mcp` direto de dentro da fita.

## Passos (em ordem)
1. **Clone canônico:** `cd ~/AI/platafirma-harness; git fetch -q origin; git checkout main; git pull --ff-only`. Conferir `git log --oneline -1` traz o merge (`daac764` ou à frente). A árvore de main está limpa pós-merge; se `teste`/`lint` reclamarem, é a árvore, não trabalho pendente.
2. **Env — drop-in `~/.config/systemd/user/ops-mcp.service.d/capsula.conf`:**
   - Renomear `PF_TOOLS_LOTE2` → `PF_TOOLS_LEVA2` (manter `=0`). É a onda de rollout da cápsula, que passou a chamar-se «leva» (D2). Sem renomear, a flag vira letra morta silenciosa (server.py agora lê `PF_TOOLS_LEVA2`).
   - Mesma renomeação na base `ops-mcp.service` linha 26 (higiene; o drop-in sobrepõe).
   - **Adicionar `Environment=PF_TOOLS_LOTE=1`** — decisão do dono (06/09): tudo junto, leva 1 e batch no mesmo restart.
   - `systemctl --user daemon-reload`.
3. **Publicar o texto novo do `oficio.md`:** `publicar-abertura` (default `origin/main`). Conferir `publicar-abertura estado` = current no head de origin/main.
4. **Restart:** `infra restart ops-mcp`. Espera ~10s antes de verificar (o restart é destacado; a fita reconecta no próximo giro).
5. **Verificar leva 1 no ar:**
   - `run_command("mesa ver")` volta com `aviso: "tem tool mesa …"` (gate roteou pela via de verbo).
   - `run_command("git status")` NÃO traz aviso (fallback legítimo, os 78%).
   - Uma linha de `run_command` no ops log de hoje (`~/AI/var/log/ops/ops-<hoje>.jsonl`) carrega `cadeira`/`sessao_id`/`ordem_id` (M1).
6. **Verificar batch (já ligado no passo 2):** `read_file(paths=["<a>","<b>"])` volta lote de 2 itens; `run_command(commands=["echo a","echo b"])` idem. (Voltar a duas fases um dia: `PF_TOOLS_LOTE=0` no drop-in, restart.)
7. Apagar esta ordem (`git rm docs/ordem-deploy-economia-de-giro.md`), commit + push no main.

## Rollback (qualquer perna, sem tocar banco nem git de conteúdo)
No drop-in: `Environment=PF_SOMBRA=0` e/ou `PF_GATE=0` e/ou `PF_TOOLS_LOTE=0`; `systemctl --user daemon-reload`; `infra restart ops-mcp`.

## Não fazer
- `systemctl --user restart ops-mcp` direto na fita (mata a conexão; use `infra restart`).
- Tocar `dono.md` ou o molde de resposta.
- Reiniciar mid-build de outra coisa (T1: invalida cache, queima teto).
