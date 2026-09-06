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

## Execução sob a conta de SO do sujeito (`conta_so`, story #3007)

Por default toda tool de execução roda sob o uid do processo do `ops-mcp`
(`claudinho`, 1001). Para uma cadeira isso é o desenho — a porta **é** a conta. Para a
conta de **provider** não é: a `seg:0013` promete isolamento por uid, e uid
compartilhado não isola nada no disco (arquivo do provider sai `owner 1001`, legível e
regravável por toda cadeira).

**Como se liga:** campo `conta_so:` na entrada do sujeito em
`politica-acesso/sujeitos.yaml`. Ausente — que é o caso de **todos** os sujeitos hoje —
nada muda: sem wrapper, sem fork, mesmo caminho de código de sempre. Presente, o
comando atravessa para aquela conta de SO e o `write_file` escreve por lá, para o
arquivo nascer com o owner certo.

    jaiminho-fabrica:
      natureza: servico
      papeis: [fornecedor]
      dominios: [plataforma]
      conta_so: jaiminho          # <- uid 1003

**Não degrada.** Wrapper ausente, negado ou mal configurado devolve erro nomeado;
nunca cai de volta para o uid da porta. Cair calado para 1001 é exatamente o vazamento
que a story fecha, e um fallback silencioso o reintroduziria com cara de correção.

A auditoria ganha `conta_exec` em toda linha — `claudinho` no caminho de hoje, a conta
projetada no outro. É por esse campo que se mede a virada no log, não pelo `ps`.

### Os dois atos de root que isto exige — do dono, não desta conta

O `ops-mcp` roda sem privilégio (`sudo -l` de `claudinho` = 4 comandos do Mint). Nada
abaixo tem contorno em user-space; é ato de root, e é cobrança, não workaround.

1. **Regra de sudoers**, em `/etc/sudoers.d/pf-conta-provider` (`visudo -f`):

       claudinho ALL=(jaiminho) NOPASSWD: ALL

   Isto **não é escalação**: dá a `claudinho` (1001) o poder de virar `jaiminho`
   (1003), que é descida de privilégio. O isolamento resultante é de mão única, e é
   essa a propriedade que se quer — a plataforma alcança o provider, o provider nunca
   alcança a plataforma. Restringir por lista de comandos não cabe: a superfície é
   `run_command`, cujo conteúdo é arbitrário por definição.

2. **Um lugar onde o uid 1003 possa escrever.** `/home/claudinho/AI` é
   `claudinho:claudinho drwxrwsr-x` e `id jaiminho` = `groups=1003(jaiminho)` apenas —
   hoje todo write do provider sob a raiz falharia em `EACCES`. Escolha do dono entre
   `usermod -aG` num grupo compartilhado e uma raiz própria (`OPS_ROOT`) para a
   instância do provider. **Sem este ato o aceite da #3007 não passa nem com a regra de
   sudoers no lugar** — o comando troca de uid e o arquivo não nasce.

`PF_EXEC_WRAPPER` troca o mecanismo (default `sudo -n -u {conta} --`); numa instância
que rode como root, `runuser -u {conta} --` dispensa a regra 1.

### Medir o aceite

    # 1. comando do provider sai sob 1003 (e não 1001)
    <tool run_command do sujeito com conta_so>  ->  id -u   ==  1003
    # 2. write do provider nasce com o owner certo
    stat -c '%u %n' <arquivo escrito pela tool>  ->  1003
    # 3. a troca de uid NÃO mexeu na chave do sujeito no PEP
    grep -c 'pep_negou.*"regra": "projecao"' ~/AI/var/log/ops/<hoje>.jsonl  ->  0

O item 3 já está fechado por leitura de código: `identidade.py:67-71` deriva o sujeito
de `claims["sub"]` do JWT, e não há `uid`, `pwd` nem `getlogin` em `identidade.py`,
`pep.py` ou `pdp.py`. A chave do sujeito é do realm; o uid do host não entra nela. O
modo de falha de 31/08 (133 negativas `regra=projecao`) veio de entrada ausente no
`sujeitos.yaml`, não de troca de uid — acrescentar `conta_so` a uma entrada existente
não o reproduz. Medir mesmo assim, porque leitura de código não é medição.

## Auditoria

Toda chamada grava linha JSONL em `~/AI/var/log/ops/` (comando, cwd, exit, duração,
`mcp_session`, sujeito, `conta_exec`). Não é silenciável pelo chamador.
