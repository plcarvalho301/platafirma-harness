# ops-server

`ops-server/` é o fonte do MCP de operação (`ops-mcp`): expõe, sob a conta `claudinho`,
`run_command`, `read_file`/`write_file` e as tools de verbo (`monta_sessao`, `mesa`, `fila`,
`tarefas`, `acervo`…). É a porta pela qual as três superfícies (claude.ai, fita do chat, Code)
tocam o host. Código: `ops-server/server.py`.

## Topologia

Tudo na conta `claudinho` (uid 1001):

- `ops-mcp.service`: uvicorn no venv `/opt/platafirma/current/venv/ops`, porta `127.0.0.1:8010`,
  com `WorkingDirectory=/opt/platafirma/current/harness/ops-server` e `uvicorn server:app`. Roda da
  release: o código novo chega por `release promover`, que troca `current` e reinicia a porta. A
  unit e o `setup-ops.sh` que a instala moram em platafirma-core.
- Raízes: código em `/opt/platafirma` (`PF_RELEASE_RAIZ`), estado e log em `/srv/platafirma/casa`
  (`PLATAFIRMA_INSTANCIA`). A porta sobe sem bancada declarada; caminho relativo em
  `run_command`/`read_file`/`write_file` é relativo à bancada (`PLATAFIRMA_BANCADA` ou
  `~/.config/platafirma/bancada`) e, sem ela, é recusado.
- `ops-tunnel.service`: túnel Cloudflare que publica `ops.platafirma.org/mcp` → `:8010`.
- `ops-healthcheck.service` + `.timer`: bate `/health` e reinicia o `ops-mcp` se ele parar de responder.

O venv `ops` se constrói de `ops-server/requirements.txt` (`registro/venvs.json`).

O processo é single-worker e single-thread (asyncio). `run_command` roda a parte bloqueante em
thread do anyio e em process group próprio (`start_new_session=True`); sem isso, um comando longo
travaria o servidor inteiro.

## Transporte sem estado

O FastMCP é instanciado com `stateless_http=True`: cada POST `/mcp` é autossuficiente e não há
sessão em memória.

No modo com estado (o default), a sessão vive no `StreamableHTTPSessionManager` chaveada por
`Mcp-Session-Id`. Numa fita ociosa, o túnel corta o stream SSE, o manager descarta a sessão, o
POST seguinte com a session id velha responde `400 Bad Request`, e o cliente larga o servidor
inteiro: todas as tools somem de uma vez, inclusive `monta_sessao`.

O custo: sem estado não há canal servidor→cliente persistente (notificação de progresso, sampling,
elicitation). O `ops-mcp` é request/resposta puro e não usa nada disso. Tool nova que precise mandar
dado de volta por streaming reabre a questão.

## Restart

Reiniciar o `ops-mcp` de dentro de um `run_command` mata o cgroup do próprio serviço no meio e pode
derrubar o comando antes do `systemctl` concluir. O restart vai num escopo transitório separado,
com um atraso curto para a chamada retornar antes da queda:

```
systemd-run --user --collect --unit=ops-mcp-restart \
  bash -c 'sleep 2; systemctl --user restart ops-mcp.service'
```

O `ops-healthcheck` cobre se algo sair torto. Conferir depois: `MainPID` novo,
`ExecMainStartTimestamp` novo, e `curl -s -o /dev/null -w '%{http_code}' 127.0.0.1:8010/health` = 200.

`systemctl --user` só enxerga a unit do próprio dono, e o docker rootless vive em `/run/user/1001`.
De outra conta, sem shell interativo:

```
sudo -u claudinho env XDG_RUNTIME_DIR=/run/user/1001 \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus <comando>
```

## Teste

```
teste rodar ops
```

Passou quando sai `suite VERDE` e exit 0. Os testes moram soltos em `ops-server/test_*.py`.

## Auditoria

Toda chamada grava uma linha JSONL em `/srv/platafirma/casa/var/log/ops/` (comando, cwd, exit,
duração, `mcp_session`, sujeito). O chamador não a silencia.
