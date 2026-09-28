# ops-server

Pasta de `platafirma-harness` com o MCP de operação (`ops-mcp`): a porta pela qual claude.ai, a fita
do chat e o Code chamam os verbos da casa e leem e escrevem arquivo no host, sob a conta `claudinho`.
Roda como a unit `ops-mcp.service` em `127.0.0.1:8010`, publicada em `ops.platafirma.org/mcp`.

## Como sobe

Chega pela release, que constrói o ambiente `ops` de `requirements.txt` e reinicia a porta:

```
release promover platafirma-harness <sha>
```

Subiu quando `infra estado` lista `ops-mcp.service` `running` e a saúde responde:

```
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8010/health
```

devolve `200`. A unit e o instalador dela moram em platafirma-core.

Reiniciar o `ops-mcp` de dentro de uma chamada da própria porta derruba a chamada no meio: o
restart vai em escopo separado, com atraso. O comando está em `docs/ops-server.md`.

## Como se testa

```
teste rodar ops
```

Roda no ambiente `ops`, que tem o pacote `mcp`. Passou quando a primeira linha diz `suite VERDE` e
sai com exit 0. Apontar a bancada e a pasta (`teste rodar platafirma-harness@<bancada> ops-server`)
roda no ambiente `harness` e a coleta falha com `No module named 'mcp'`.

Topologia, transporte sem estado e auditoria: `docs/ops-server.md` na raiz do repositório.
