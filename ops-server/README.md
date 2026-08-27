# ops-server — o MCP de operação da PlataFirma (`ops-mcp`)

Servidor MCP que expõe os verbos de operação sob o usuário `claudinho`:
`run_command`, `read_file`/`write_file`, e os verbos de cadeira (`monta_sessao`,
`mesa`, `fila`, `tarefas`, `acervo`…). É a porta pela qual as três superfícies
(claude.ai, fita do chat, Code) tocam o host. Código: `server.py`.

## Topologia (tudo na conta `claudinho`, uid 1001)

- `ops-mcp.service` — uvicorn (`.venv-ops`, porta 127.0.0.1:8010). **Roda DIRETO do
  repo** (`WorkingDirectory=.../platafirma-harness/ops-server`, `uvicorn server:app`):
  `restart` já pega o código novo, sem etapa de build/deploy.
- `ops-tunnel.service` — túnel Cloudflare que publica `ops.platafirma.org/mcp` → :8010.
- `ops-healthcheck.service` + `.timer` — bate `/health` periodicamente e reinicia o
  `ops-mcp` se ele parar de responder. É a rede de segurança de qualquer restart.

O processo é **single-worker, single-thread** (asyncio cooperativo). Por isso
`run_command` roda a parte bloqueante em thread do anyio e em process group próprio
(`start_new_session=True`): sem isso, um comando longo travaria TODO o servidor.

## Transporte: `stateless_http=True` (decisão do incidente #2890, 27/08/2026)

O FastMCP é instanciado com **`stateless_http=True`** (`server.py`, no `FastMCP(...)`).
Cada POST `/mcp` é autossuficiente; **não existe sessão em memória**.

**Por quê.** No modo *stateful* (default), as sessões vivem no
`StreamableHTTPSessionManager` chaveadas por `Mcp-Session-Id`. Numa fita **ociosa**, o
túnel Cloudflare corta o stream SSE idle → o manager descarta a sessão → o próximo POST
com a session id velha responde **`400 Bad Request`** → o cliente Claude larga o servidor
inteiro da lista, e **todos os verbos somem de uma vez** (inclusive `monta_sessao`). O
servidor nunca cai; quem morre é a sessão daquela fita. Fitas movimentadas nunca caem —
renovam o stream antes do idle. Raio de dano medido: 1 fita ociosa por vez.

**O custo (e quando revisitar).** Stateless remove o canal server→client persistente
(notificação/streaming de progresso, sampling, elicitation). O ops-mcp é request/resposta
puro e não usa nada disso, então hoje é de graça. **Se algum verbo novo precisar mandar
dado de volta por streaming, o stateless passa a atrapalhar — aí revisitar esta decisão.**

Laudo completo, evidências e commit: card **#2890** (comentários #501/#502). Fix em
commit `24c9842`.

## Restart seguro

O `ops-mcp` **não se reinicia de dentro de si** — é ato de terminal. E cuidado: reiniciar
de dentro de um `run_command` mata o cgroup do próprio serviço no meio, podendo derrubar o
comando antes do `systemctl` concluir. Despache o restart num **escopo transitório
separado**, com um atraso curto para o `run_command` retornar antes da queda:

    systemd-run --user --collect --unit=ops-mcp-restart \
      bash -c 'sleep 2; systemctl --user restart ops-mcp.service'

O `ops-healthcheck` cobre se algo sair torto. Verificar depois: `MainPID` novo,
`ExecMainStartTimestamp` novo, e `curl -s -o /dev/null -w '%{http_code}' :8010/health` = 200.

> **Rodar como `claudinho`, nunca como `megafone`.** `systemctl --user` só enxerga o unit
> do próprio dono e o docker rootless vive em `/run/user/1001`. Sem shell interativo:
>
>     sudo -u claudinho env XDG_RUNTIME_DIR=/run/user/1001 \
>       DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus <comando>
>
> Use sempre caminho ABSOLUTO `/home/claudinho/AI` — `~/AI` como megafone vira `/home/megafone/AI`.

## Auditoria

Toda chamada grava linha JSONL em `~/AI/var/log/ops/` (comando, cwd, exit, duração,
`mcp_session`, sujeito). Não é silenciável pelo chamador.
