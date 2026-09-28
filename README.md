# platafirma-harness

Serve às cadeiras da PlataFirma os verbos de operação (`bin/`), a abertura de sessão, o MCP de
operação e as skills; roda da release em `/opt/platafirma/current/harness`, com estado na
instância `/srv/platafirma/casa`. Não é o MCP de outros serviços: cada um mora no repo que o roda.

Por que existe: O harness é módulo com repo próprio — `acervo ler casa adr arq:0019`;
Fronteira do harness, o que uma sessão recebe ao abrir — `acervo ler casa spec fronteira-do-harness`.

## Como sobe

Pré-requisitos: host preparado uma vez pelo dono (`/srv/platafirma/casa`, PATH da release e units
root, pelo `deploy/bootstrap-host.sh` de platafirma-core); `git`, `python3`, `docker` e `uv` no host.

```
release promover platafirma-harness <sha>
/opt/platafirma/current/harness/deploy-harness/instalar
```

A promoção espelha o repo do forge, constrói os venvs do lock e troca `current`/`anterior` de uma
vez; `instalar` liga as units `--user` do harness à release e aponta o gate de commit dos clones.
Subiu quando `release estado platafirma-harness` mostra o sha «no ar» com `gate: passou`, e
`release conferir procedencia` sai 0. Os verbos passam a ser chamáveis pelo nome na conta dos
serviços, ou por `platafirma <verbo>` de qualquer conta. Voltar: `release reverter platafirma-harness`.

Para codar, traga a família para a bancada no sha de produção (não `origin/main`):

```
/opt/platafirma/current/harness/deploy-harness/puxar-bancada --declarar <dir>
```

Verbo editado na bancada, chamado pelo caminho do worktree sem `PLATAFIRMA_INSTANCIA` de teste,
executa contra a instância real. O detalhe está em `docs/instalacao-e-bancada.md`.

## Como se testa

```
teste rodar platafirma-harness --portao
```

Roda a lista do portão (`controle/tests/VERDES`), a mesma que o `hooks/pre-push` julga. Passou
quando sai `suite VERDE` e exit 0. Com mais de uma bancada aberta do harness, nomeie a bancada no
lugar do repo (`platafirma-harness@<card>-<slug>`). Suítes com ambiente próprio:
`teste rodar recuperacao` e `teste rodar ops` (ver o README de `recuperacao/`).

## Onde está o quê

| pasta | o que tem |
|---|---|
| `bin/` | os verbos de operação; sub-ato mora em `bin/_<verbo>/`, fora do PATH |
| `abertura/` | persona, chapéu e caderno de cada cadeira, que `monta-sessao` injeta |
| `agente/` | pacote da conta da fábrica: `CLAUDE.md`, `settings.json`, hook de porta e instalador |
| `ops-server/` | o MCP de operação (`ops-mcp`), porta dos verbos para as superfícies; [README](ops-server/README.md) |
| `controle/` | plano de controle: agregador de estado e tela; [README](controle/README.md) |
| `recuperacao/` | biblioteca do Recuperador: envelope, adaptadores, disjuntor, PEP, cache; [README](recuperacao/README.md) |
| `chat/` | superfície de conversa Matrix: stack `chat`, worker e provisionamento; [README](chat/README.md) |
| `politica-acesso/` | PDP, política e projeção de sujeitos, com a matriz sujeito × fonte |
| `pesquisa/` | biblioteca do verbo `pesquisar` (SearXNG e extração) |
| `sessao/` | stack `harness-sessao`: compose e DDL do banco de sessão e mesa |
| `deploy-harness/` | `instalar`, `puxar-bancada` e as units `--user` do harness |
| `hooks/` | gate de commit e de push; `instalar` o aponta nos clones |
| `lib/` | raízes de produção, venv e medição, em Python e shell, comuns aos verbos |
| `registro/` | o declarado que os verbos leem: famílias, venvs, superfícies, terceiros |
| `venvs/` | declaração dos ambientes `harness` e `acervo`; READMEs em [harness](venvs/harness/README.md) e [acervo](venvs/acervo/README.md) |
| `skills/` | fonte das skills entregues ao claude.ai |
| `tooling/` | export e carimbo das skills, lote de avaliação e otimização de diagrama |
| `avaliacao/` | gold set, runners e juiz da recuperação; o juiz da banda curta em `docs/juiz-piso.md` |
| `diagramas/` | figuras do módulo, fonte e render; índice em `docs/diagramas.md` |
| `testes/` | suíte da raiz: verbos, release, migração |
| `docs/` | engenharia do repo; o `conferir` da release em `docs/release-conferir.md` |
