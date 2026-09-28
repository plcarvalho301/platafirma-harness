# Instalação e bancada

Como o harness entra num ambiente, onde o que ele roda guarda código e estado, e como quem vai
codar traz a família para a bancada. O README da raiz tem o caminho curto; aqui está o detalhe.

## As duas raízes de produção

Produção mora em duas raízes, e só nelas:

| raiz | caminho | o que guarda |
|---|---|---|
| release | `/opt/platafirma` | código imutável: por família, o espelho do forge, um checkout destacado por sha, `current` e `anterior`; os venvs construídos do lock; e os atalhos estáveis `/opt/platafirma/current/<curto>/` (`harness`, `core`, `conhecimento`, `motor`, `ui`, `rastreador`, `venv/<nome>`) |
| instância | `/srv/platafirma/casa` | `segredos/<stack>/<NOME>` (0700/0600, um arquivo por variável), `deploy/<stack>/` (sobreposição de compose e config da instância), `dados/` (corpus, acervo, backups, avaliação) e `var/` (log, run, tmp, fitas, abertura publicada, registro de promoções) |

Código referencia sempre `/opt/platafirma/current/<curto>/...`; estado, segredo e log, sempre
`/srv/platafirma/casa/...`. A bancada onde se escreve código pode ser apagada sem que o que está
no ar perceba.

## Instalar

```
# uma vez por host, com root (dono): /srv/platafirma/casa com dono claudinho,
# /etc/profile.d/platafirma.sh (PATH da release) e as units root
sudo bash platafirma-core/deploy/bootstrap-host.sh

# por família: espelha do forge, constrói o venv do lock, troca current/anterior
release promover platafirma-harness <sha>

# units --user do harness ligadas à release e gate de commit nos clones da bancada
/opt/platafirma/current/harness/deploy-harness/instalar
```

`/opt/platafirma/current/harness/bin` é o PATH. Ele chega por `Environment=PATH=` nas units, pelo
ambiente de subprocesso do `ops-mcp` e por `/etc/profile.d/platafirma.sh` para shell humano e cron;
não existe diretório de symlinks de verbos para assentar.

| a promoção faz | a promoção não faz |
|---|---|
| espelhar a família a partir da URL do forge declarada em `registro/familias.json` | ler clone de bancada |
| construir o venv do lock e trocar `current`/`anterior` de uma vez | instalar pacote de sistema ou binário de terceiro |
| agendar o restart da porta quando a família tem serviço | escrever credencial (isso é `seg segredo gravar`, na instância) |

`release estado` diz que sha está no ar e desde quando; `release reverter` volta para `anterior`.

`instalar` roda N vezes: corrige o que divergiu, relata o que não pode corrigir, e com `--check` só
mede. Unit `--user` cujo conteúdo muda numa promoção não recarrega sozinha: o systemd pede
`daemon-reload`, e `instalar` só o dá quando troca um link.

Depois de instalar:

```
release conferir procedencia    todo caminho de execução resolve para dentro da release (0 = sim)
release conferir verbo          cabeçalho de cada verbo contra o que ele serve
sinal                           estado de saúde dos serviços, um por linha
```

Pré-requisitos que a promoção não resolve: `git`, `python3`, `docker` e as ferramentas de terceiro
(`rg`, `fd`, `uv`, `jq`…). `instalar` mede cada uma e diz o que deixa de funcionar sem ela.

## Chamar verbo

Em qualquer conta, `platafirma <verbo> [args]`: `/usr/local/bin/platafirma`, posto pelo bootstrap
do host, chama o verbo da release pelo nome, de qualquer diretório, e o verbo roda como a conta dos
serviços; `platafirma` sem argumento lista os verbos. Na conta dos serviços, o nome direto
(`release estado`, `sinal`) basta.

Atalho `pf`, opcional: `puxar-bancada --alias` grava no `~/.bashrc` da conta o alias
`pf` → `platafirma`, entre os marcadores `# >>> platafirma alias >>>` e
`# <<< platafirma alias <<<`; vale no próximo shell. É ergonomia da conta, não nome de coisa da
plataforma (`acervo ler casa adr ont:0087`). Segunda execução relata `conforme`; alias ou função
`pf` com outro alvo, ou comando `pf` alheio no PATH, sai 4 sem editar; rc sem permissão de escrita
sai 3.

## Puxar a bancada

A bancada é da conta, não do ambiente: a raiz se declara em `~/.config/platafirma/bancada` (uma
linha) ou em `PLATAFIRMA_BANCADA`, sem default. Só verbo de bancada (`repo`, `teste`, `lint`,
tooling de avaliação) a lê; sem declaração ele sai 3 com «bancada nao declarada».

```
# primeira vez na conta (ou depois de a bancada ter sido apagada)
/opt/platafirma/current/harness/deploy-harness/puxar-bancada --declarar <dir>

# depois: todas as famílias com current, ou só as nomeadas; card abre ramo
puxar-bancada [<familia>...] [--cadeira <slug>] [--card <n> --slug <s>] [--ensaio]
```

`--declarar <dir>` grava a raiz (0600) só se a conta ainda não declarou; outra já declarada sai 4
sem sobrescrever, bancada em `/opt` ou `/srv` sai 4. Cada família vira
`<bancada>/wt/<familia>/<cadeira>` (cadeira: `--cadeira`, senão `PF_CADEIRA`, senão `fabrica`), pelo
`repo abrir <familia> --da-producao` da release. Saída, uma linha por família: família, sha em
produção, `criado`, `conforme` ou `impossivel: motivo`, caminho. Worktree já aberto em outro sha ou
sujo é relatado e não é tocado. `--ensaio` mostra o plano sem escrever.

## Testar verbo editado

Chame o verbo pelo caminho do worktree com as raízes num diretório temporário:

```
PLATAFIRMA_INSTANCIA=<tmp> PF_RELEASE_RAIZ=<tmp> <bancada>/wt/<familia>/<cadeira>/bin/<verbo>
```

Sem `PLATAFIRMA_INSTANCIA` de teste, o verbo da bancada executa contra a instância real
(`/srv/platafirma/casa`); o `puxar-bancada` avisa, não bloqueia. O que foi editado chega ao ar só
por `release promover`.
