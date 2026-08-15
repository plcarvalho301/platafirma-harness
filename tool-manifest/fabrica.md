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

Comum a toda cadeira — fila, sessão, cards: `tool-manifest/TODA-CADEIRA.md`. O que está
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
| `python3` | o do host; na máquina local, o que houver | [exec] |
| `rg` · `fd` · `jq` · `yq` | busca e leitura de config — regex em YAML não | [exec] |
| `pytest` · `ruff` | teste e lint quando o repo os declarar | [inst] |
| `tarefas ler <id>` | ler o card antes de começar; comentar o andamento | [exec] |

Branch por item de trabalho, a partir de `main`, **em worktree próprio**. Push da
branch e para aí: merge e push em `main` são de claudinho-TI.

Abertura, antes de escrever a primeira linha:

```
cd ~/AI/<repo>
git fetch origin main
git worktree add -b fabrica/<card>-<slug> ~/AI/wt-<card>-<slug> origin/main
cd ~/AI/wt-<card>-<slug>
```

Daí em diante, todo `Bash`/`Write`/`Edit` acontece dentro de `~/AI/wt-<card>-<slug>`,
e nunca em `~/AI/<repo>`. O clone principal é do dono do repo: `git checkout` ali
troca a branch **debaixo de quem mais estiver trabalhando**, e trabalho não
commitado de outra fatia passa a aparecer no seu `git status`.

Duas regras que caem disto, e valem mesmo em worktree:

- **Commit por caminho explícito.** `git add <caminho> [...]`, nunca `git add -A`
  nem `git add .`. Arquivo que você não escreveu não entra no seu commit.
- **Fatia irmã não se conserta.** Achou defeito em arquivo de outra fatia, é
  pergunta fechada a claudinho-TI, não edição.

Fechado o card e mergeada a branch, o worktree se remove com
`git worktree remove ~/AI/wt-<card>-<slug>`.

## ops — operação no host

Toda esta linha passa por `platafirma-ops` → `run_command`. Bash nativo não
alcança o host, e o que não passa por `run_command` não deixa trilha. As
negativas de `docker`, `systemctl`, `psql` e `mc` no `settings.json` são disso:
não barram a linha `ops`, barram `ops` sem auditoria.

`infra`, `deploy`, `conferir`, `longjob`, `acervo` e o `psql` do acervo estão em
`TODA-CADEIRA.md`, com a mesma glosa. O que é próprio daqui é o parágrafo abaixo.

O que sobe, quando e com que rollback **não é meu**: é decisão de claudinho-TI,
escrita no card. Acesso remoto não é autoridade. Card que manda operar sem dizer
o rollback volta como pergunta fechada, não vira execução com critério meu.

## Armadilhas medidas

- **Bind mount de arquivo único não acompanha `git checkout`.** O checkout troca
  o inode; o mount fica preso ao velho. `nginx -t` passa, `reload` não acusa, e a
  mudança não aparece. Só `up -d --force-recreate <serviço>` refaz o mount.
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

## Minuta — deliberação entre cadeiras

`minuta ler` · `escrever` · `circular` · `formalizar`, no manifesto comum
(`tool-manifest/TODA-CADEIRA.md`). Verbo de toda cadeira; dona da matéria:
claudinha-gestao-estrategica. **Nunca é leitura automática** — só roda chamada,
por ping `tipo: minuta` na caixa ou ordem do dono. Protocolo:
`platafirma-arquitetura/minutas/PROTOCOLO.md`.
