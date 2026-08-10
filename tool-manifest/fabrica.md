# tool-manifest — claudinha-fabrica

Ambiente: sessão do Claude Code na conta que roda a fábrica, em **máquina
qualquer**. Dois sistemas de arquivos na mesma sessão, e confundi-los é o erro
mais caro daqui:

- **local** — o clone do repositório do card, na máquina onde o Code abriu.
  `Bash`, `Write` e `Edit` nativos valem aqui e só aqui.
- **host da plataforma** — `~/AI`, uid `claudinho`. Não é alcançável por Bash
  nativo em máquina nenhuma. Chega-se nele **só** pelo connector
  `platafirma-ops`, e é onde vivem contêineres, units, banco e os verbos.

Preenchimento inicial por claudinho-TI (o cliente), porque esta é a única
cadeira sem sessão de manutenção própria. A verificação declarada abaixo é a do
ambiente da plataforma, não a de uma sessão da fábrica: o que a fábrica medir em
sessão, ela reclassifica aqui.

Verificação: cada linha declara **como** — `[exec]` binário executado ·
`[func]` importado e usado em trabalho real · `[inst]` presente, sem prova de
funcionamento. `[inst]` é confissão, não aval.

> **Regra de ouro:** existindo verbo para o que vou fazer, chamo o verbo.
> Montar `docker exec` na mão, reimplementar cliente REST ou repetir credencial
> em script de sessão é o erro que este manifesto existe para cortar.

Comum a toda cadeira — fila, sessão, cards: `tool-manifest/GERAL.md`. O que está
lá não se repete aqui.

## Conectores

**platafirma-ops** (`ops.platafirma.org`) — a caixa do `claudinho` no host. É a
única porta para o host, em qualquer máquina.
- `run_command` — shell (`bash -c`, não-login) sob `~/AI`. Teto de 600 s, e mata
  o process group no timeout. Grava trilha em `~/AI/var/log/ops/`: é por ela que
  a entrega de fornecedor se audita.
- `read_file` · `write_file` — arquivos sob `~/AI`. `Edit` e `str_replace`
  nativos **não** alcançam arquivo do host; escrita no host é `write_file`.
- `monta_sessao(cadeira="fabrica")` — persona canônica, este manifesto e estado
  da fila numa chamada. Serve de conferência: diferença contra o instalado em
  `~/.claude/CLAUDE.md` é deriva de build. Sob demanda, não gate de entrada.

**PlataFirma Wiki** (`mcp.platafirma.org`) — leitura de repo e acervo.
- `repo_read` · `repo_tree` · `repo_grep` — leem o **espelho do ref remoto**, não
  a árvore local. Úteis para ler repo que não está clonado na máquina.
- `rag_search` · `rag_facets` — só nos recortes que o card declarar. Card sem
  recorte é card sem acervo.

Fronteira: conectores de outras cadeiras que apareçam na sessão não são meus —
não chamo.

## dev — construção de software

| ferramenta | quando chamar | verif. |
|---|---|---|
| `Bash`/`Write`/`Edit` nativos | tudo dentro do clone local do card | [exec] |
| `git -C <clone> …` | branch, commit e push da `fabrica/<card>-<slug>` | [exec] |
| `uv venv` · `uv pip` · `uvx` | venv reprodutível; nunca `pip` de sistema | [exec] |
| `python3` | 3.12.3 no host; na máquina local, o que houver | [exec] |
| `rg` · `fd` · `jq` · `yq` | busca e leitura de config — regex em YAML não | [exec] |
| `pytest` · `ruff` | teste e lint quando o repo os declarar | [inst] |
| `tarefas ler <id>` | ler o card antes de começar; comentar o andamento | [exec] |

Branch por item de trabalho, a partir de `main`. Push da branch e para aí: merge
e push em `main` são de claudinho-TI.

## ops — operação no host

Toda esta linha passa por `platafirma-ops` → `run_command`. Bash nativo não
alcança o host, e o que não passa por `run_command` não deixa trilha. As
negativas de `docker`, `systemctl`, `psql` e `mc` no `settings.json` são disso:
não barram a linha `ops`, barram `ops` sem auditoria.

| ferramenta | quando chamar | verif. |
|---|---|---|
| `infra estado [alvo]` · `infra saude` | o que está no ar, antes de mexer | [exec] |
| `infra logs <alvo> [n]` | log de contêiner ou unit; descobre qual dos dois | [exec] |
| `infra restart <alvo>` | reiniciar destacado; alvo explícito obrigatório | [exec] |
| `infra exclusivo -- <cmd>` | carga de GPU: espera a vez e a cota | [exec] |
| `deploy <stack> up -d` | promover release; stack obrigatória, sem default | [exec] |
| `deploy <stack>` | ver o declarado, sem tocar em nada | [exec] |
| `conferir servico [nome]` | declarado x servido; exit 1 = há divergência | [exec] |
| `longjob run <nome> <cmd…>` | qualquer coisa acima de 2 min: build, migração | [exec] |
| `acervo ingerir/escada/…` | degrau do acervo, quando o card declarar | [exec] |
| `docker exec -i rag-extractor-pg psql -U rag -d rag_extractor -At -c "<sql>"` | SQL no acervo | [exec] |

O que sobe, quando e com que rollback **não é meu**: é decisão de claudinho-TI,
escrita no card. Acesso remoto não é autoridade. Card que manda operar sem dizer
o rollback volta como pergunta fechada, não vira execução com critério meu.

## Armadilhas medidas

- **Bind mount de arquivo único não acompanha `git checkout`.** O checkout troca
  o inode; o mount fica preso ao velho. `nginx -t` passa, `reload` não acusa, e a
  mudança não aparece. Só `up -d --force-recreate <serviço>` refaz o mount.
- **`repo_read`/`repo_grep`/`repo_tree` servem o SHA velho depois de um push**,
  em silêncio — são espelho do remoto. Chamar `repo_sync` antes.
- **`&&` encadeado no `run_command`**: passo intermediário não-zero derruba o
  resto sem erro visível. Usar `;` ou chamadas separadas.
- **`~/AI/deploy/*` são worktrees detached**: `git pull` ali falha com "You are
  not currently on a branch". O caminho é `git fetch origin main` +
  `git checkout --detach <sha>` — ou o verbo `deploy`.
- **Nome de servidor MCP pode aparecer como UUID** no Code; regra `allow` por
  nome nominal (`mcp__platafirma-ops__run_command`) não casa e a chamada cai em
  pedido de aprovação. Não é falha: é aprovação manual do dono, na máquina dele.
- **Sessão do Code já aberta não recarrega `~/.claude/`.** Reexecutar o
  instalador vale a partir da próxima sessão.

## Pendências declaradas

- **`shellcheck`, `shfmt`** ausentes no host; instaláveis sem privilégio.
- **Skills**: `skills/fabrica/` não existe, e o instalador declara a lista vazia
  de propósito. A fábrica não carrega `platafirma` (entrega org chart, que o
  contrato nega) nem `osint`.
