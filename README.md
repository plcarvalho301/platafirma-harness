# platafirma-harness

Módulo do harness (`arq:0019`): a superfície de contato entre as personas
(claudinhos/claudinhas) e a plataforma. Dono: claudinho-IA.

## Entra

- **Fontes das skills** entregues ao claude.ai (a cópia entregue é classe B —
  copiada-pra-fora — e carrega carimbo de frescor).
- **Tooling de export e carimbo** — script que gera o artefato de upload com
  `origem: <repo>@<blob_sha>`, `fonte: <path>`, `sincronizado_em: <ISO 8601>`.
  Carimbo à mão é proibido pela spec: mente por construção.
- **MCP do harness** — predicado do mapa de entrypoints e `identity_check(persona)`.
- **Verbos de operação** (`bin/`) — o que toda cadeira chama por `run_command`:
  `fila`, `monta-sessao`, `tarefas` (rastreador), `infra` (contêiner, unit,
  timer), `acervo escada`, `longjob`, `seg`. Fonte única: o PATH de produção é
  `/opt/platafirma/current/harness/bin`, a release deste repo, e `conferir
  procedencia` reprova quando deixa de ser verdade.
- **Identidade e plano de controle** (`agente/`, `ops-server/`) — o pacote de
  conta da fábrica e o fonte do MCP de operação, trazidos do `platafirma-core`
  no #396: quem serve a plataforma às personas mora no módulo do harness.

## Instalar num ambiente

Produção mora em duas raízes, e só nelas (card #3010, `arq:0102` D6):

| raiz | caminho | o que guarda |
|---|---|---|
| release | `/opt/platafirma` | código imutável: por família, o espelho do forge, um checkout destacado por sha, `current` e `anterior`; os venvs construídos do lock; e o diretório de atalhos estáveis `/opt/platafirma/current/<curto>/` (`harness`, `core`, `conhecimento`, `motor`, `ui`, `rastreador`, `arquitetura`, `venv/<nome>`) |
| instância | `/srv/platafirma/casa` | `segredos/<stack>/<NOME>` (0700/0600, um arquivo por variável), `deploy/<stack>/` (sobreposição de compose e config da instância), `dados/` (corpus, acervo, backups, avaliação) e `var/` (log, run, tmp, fitas, abertura publicada, registro de promoções) |

Código referencia sempre `/opt/platafirma/current/<curto>/...`; estado, segredo e
log, sempre `/srv/platafirma/casa/...`. Nada de produção lê ou grava fora das
duas: a bancada onde se escreve código pode ser apagada sem que o que está no ar
perceba.

```
# uma vez por host, com root (dono): /srv/platafirma/casa com dono claudinho,
# /etc/profile.d/platafirma.sh (PATH da release) e as units root
sudo bash platafirma-core/deploy/bootstrap-host.sh

# por família: espelha do forge, constrói o venv do lock, troca current/anterior
# atômico e reassenta /opt/platafirma/current/<curto>
release promover platafirma-harness <rev>
```

Pronto: `/opt/platafirma/current/harness/bin` é o PATH, e os verbos (`fila`,
`tarefas`, `infra`, `deploy`, `sinal`, `conferir`…) passam a ser chamáveis pelo
nome. Ele chega por `Environment=PATH=` nas units, pelo ambiente de subprocesso
do `ops-server` e por `/etc/profile.d/platafirma.sh` para shell humano e cron —
não existe diretório de symlinks de verbos para assentar. O que a promoção faz e
o que ela deliberadamente não faz:

| Faz | Não faz |
|---|---|
| espelhar a família a partir da URL do forge declarada na release (`registro/familias.json`) | ler clone de bancada |
| construir o venv do lock e trocar `current`/`anterior` de uma vez | instalar pacote de sistema ou binário de terceiro |
| agendar o restart da porta quando a família tem serviço | escrever credencial (isso é `seg segredo gravar`, na instância) |

`release estado` diz que sha está no ar e desde quando; `release reverter` volta
para `anterior`.

A bancada (onde se escreve código) é da conta, não do ambiente: a raiz é
declarada em `~/.config/platafirma/bancada` (uma linha) ou em `PF_BANCADA`, sem
default. Só verbo de bancada (`repo`, `teste`, `lint`, tooling de avaliação) a
lê; sem declaração ele sai 3 com "bancada nao declarada".

**Depois de instalar**, três verificações valem a pena:

```
conferir procedencia    todo caminho de execução resolve para dentro deste repo (0 = sim)
conferir verbo          cabeçalho de cada verbo e a conta de arq:0037
sinal                   estado de saúde dos serviços, um por linha
```

Pré-requisitos que a promoção não resolve: `git`, `python3`, `docker` e as
ferramentas de terceiro (`rg`, `fd`, `uv`, `jq`…). Faltando alguma, ela diz qual
e o que deixa de funcionar — a instalação segue, degradada e declarada.

Estação emprestada e conta da fábrica têm guia próprio: `docs/estacao-emprestada.md`
e `docs/instanciacao-fabrica.md`.

## Não entra

- MCP de outro serviço — mora no repo que roda o serviço. O `ops-server` não é
  exceção a isso e sim aplicação: o serviço que ele serve é o próprio harness,
  a superfície de contato. Quem o **sobe** segue no core (`deploy/setup-ops.sh`).
- `CLAUDE.md`/`AGENTS.md` de outros repos — voz de cada repo.
- Fila v0 (`fila/`) — runtime, sem repo por design.

## Relação com o motor

O harness é **cliente** da malha de mensageria (`platafirma-motor`, `arq:0017`/`arq:0018`).

## Diretórios de topo

Declarados por `arq:0042`; `conferir repo platafirma-harness` mede contra esta lista.

| Diretório | O que é |
|---|---|
| `bin/` | verbos de operação chamados por toda cadeira; fonte única, servidos pela release em `/opt/platafirma/current/harness/bin` |
| `hooks/` | gate de commit da `arq:0042` (`pre-commit`); instala-se com `git config core.hooksPath` |
| `personas/` | texto canônico de cada cadeira, mais template e higiene de redação |
| `abertura/<cadeira>/<slug>/ferramental.md` | ferramental por chapéu (L2); o comum é `abertura/oficio.md` |
| `skills/` | fontes das skills entregues ao claude.ai |
| `tooling/` | script de export e carimbo, e o preparo de lote de avaliação |
| `avaliacao/` | instrumentos e conjunto rotulado de avaliação do harness |
| `distribuicao/` | deliberação que reparte o acervo entre as cadeiras, por rodada |
| `experimentos/` | experimento com hipótese declarada e resultado, um diretório cada |
| `registro/` | o declarado que os verbos leem — `stacks.json` (fonte do `deploy`). O catálogo da montagem de sessão é a árvore `abertura/` + `PECAS_VERBO` no `bin/monta-sessao` |
| `docs/` | documentação do módulo |
| `diagramas/` | figuras do módulo: fonte `.mmd`/`.d2` e render `<fonte>.svg` |
| `mcp/` | MCP do harness, previsto por `arq:0019`, ainda sem implementação |
| `controle/` | plano de controle do harness: agregador de estado e tela de leitura |
| `caderno/` | caderno durável por cadeira, particionado por chapéu |
| `deploy-harness/` | o que instala o próprio harness num ambiente: units do `sinal` e o instalador |
| `agente/` | pacote de conta da fábrica: `CLAUDE.md`, `settings.json` e o instalador; `~/.claude/CLAUDE.md` é symlink para a release (`/opt/platafirma/current/harness/agente/CLAUDE.md`) e `settings.json` é cópia gerida |
| `ops-server/` | fonte do MCP de operação (`claudinho-mcp`); sobe por `platafirma-core:deploy/setup-ops.sh`, fora do compose |
| `.claude/` | configuração do Claude Code na estação emprestada |

Spec de referência: [PlataFirma:Produto/harness/spec](https://wiki.platafirma.org/index.php/PlataFirma:Produto/harness/spec).

- Abrir a PlataFirma de uma estação emprestada: `docs/estacao-emprestada.md`
- Instanciar a fábrica no Claude Code: `docs/instanciacao-fabrica.md`
