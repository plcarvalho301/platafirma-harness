# tool-manifest — claudinha-fabrica

Substitui: a delegação a `TODA-CADEIRA.md` (2026-08-17). Fora do quadro não se
recebe a peça do núcleo — decisão do dono, 17/08 —, então o que a fábrica usa
está aqui, inteiro. Ponteiro para peça que não chega é falta que não aparece.

Ambiente: sessão do Claude Code na conta que roda a fábrica, em **máquina
qualquer**. Dois sistemas de arquivos na mesma sessão, e confundi-los é o erro
mais caro daqui:

- **local** — o clone do repositório do card, na máquina onde o Code abriu.
  `Bash`, `Write` e `Edit` nativos valem aqui e só aqui.
- **host da plataforma** — `~/AI`, uid `claudinho`. Não é alcançável por Bash
  nativo em máquina nenhuma. Chega-se nele **só** pelo connector
  `platafirma-ops`, e é onde vivem contêineres, units, banco e os verbos.

> **Regra de ouro:** existindo verbo para o que vou fazer, chamo o verbo. Montar
> `docker exec` na mão, reimplementar cliente REST ou repetir credencial em
> script de sessão é o erro que este manifesto existe para cortar.
> **A lista abaixo é fechada:** verbo que não está aqui não é meu, e o que falta
> se pede a claudinho-TI em vez de se improvisar.

## Conectores

**platafirma-ops** (`ops.platafirma.org`) — a caixa do `claudinho` no host. É a
única porta para o host, em qualquer máquina.

- `run_command` — shell (`bash -c`, não-login) sob `~/AI`. Teto de 600 s, e mata
  o process group no timeout. Grava trilha em `~/AI/var/log/ops/`: é por ela que
  a entrega de fornecedor se audita.
- `read_file` · `write_file` — arquivos sob `~/AI`. `Edit` e `str_replace`
  nativos **não** alcançam arquivo do host; escrita no host é `write_file`.
- `monta_sessao(cadeira="fabrica")` — persona, este manifesto e a mesa numa
  chamada. Sob demanda, não gate de entrada.

**PlataFirma Wiki** (`mcp.platafirma.org`) — leitura de repo e acervo.

- `repo_read` · `repo_tree` · `repo_grep` — leem o **espelho do ref remoto**, não
  a árvore local. Úteis para ler repo que não está clonado na máquina.
- `rag_search` · `rag_facets` — só nos recortes que o card declarar. Card sem
  recorte é card sem acervo.

Conector de outra cadeira que apareça na sessão não é meu: não chamo.

## Verbos — o índice inteiro desta cadeira

Opção de um verbo: chamá-lo **sem argumento**. Flag, contrato e armadilha de cada
um: `tool-manifest/nucleo-detalhe.md`, por ato — leitura, não peça de abertura.

```
tarefas ler|comentar|fechar|sub   o card: ler antes de começar, comentar o andamento
mesa ver|item|fez|fita            memória de trabalho: item TEM ato e alvo
mesa caderno [chapeu]             índice na abertura; corpo só por ato
encerrar fita|varredura           fecha por marco fechado, não por hora do dia
fila status|ler|enviar            caixa: só no encerrar fita, ou por ordem do dono
minuta ler|escrever|circular      deliberação entre cadeiras; nunca leitura automática
conferir repo|commit|verbo        antes de entregar; `conferir` sem argumento lista as classes
longjob run <nome> <cmd...>       todo comando acima de 2 min — run_command corta em 600 s
git -C <clone> …                  branch, commit e push da fabrica/<card>-<slug>
uv venv|pip|uvx                   venv reprodutível; nunca pip de sistema
python3 · rg · fd · jq · yq       busca e leitura de config — regex em YAML não
pytest · ruff                     quando o repo os declarar (presentes, sem prova daqui)
```

Fora da lista, e por isso não meus: `deploy`, `infra`, `acervo`, `motor`,
`acesso`, `chat`. O que sobe, quando e com que rollback é decisão de
claudinho-TI, escrita no card — acesso remoto não é autoridade. Card que manda
operar sem dizer o rollback volta como pergunta fechada, não vira execução com
critério meu.

## Branch e worktree

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

Duas regras que caem disto:

- **Commit por caminho explícito.** `git add <caminho> [...]`, nunca `git add -A`
  nem `git add .`. Arquivo que você não escreveu não entra no seu commit.
- **Fatia irmã não se conserta.** Achou defeito em arquivo de outra fatia, é
  pergunta fechada a claudinho-TI, não edição.

Fechado o card e mergeada a branch, o worktree se remove com
`git worktree remove ~/AI/wt-<card>-<slug>`.

## Onde abrir a sessão — decide o card, não o hábito

Procedimento completo: `docs/instanciacao-fabrica.md`.

- **Card de um repositório só**: clone do repo do card, com `Bash`, `Write` e
  `Edit` nativos; o push da branch sai do próprio clone.
- **Card que toque mais de um repositório, ou o `platafirma-harness`**: estação
  emprestada — o clone do harness, onde `.claude/settings.json` nega `Bash`,
  `Write`, `Edit` e `NotebookEdit`, e toda escrita passa por `platafirma-ops`
  contra as árvores em `~/AI/`. Dois repositórios viram dois caminhos na mesma sessão.
- **No modo estação**: commit sai com a identidade de quem o `ops` executa
  (`claudinho`), e o push é `run_command` com `git -C ~/AI/<repo> push`.
- **Roteiro do repo tocado**: `AGENTS.md` na raiz — vale para qualquer agente.

Card sem repo declarado não começa: volta para claudinho-TI.

## Armadilhas medidas

- **Espelho de repo serve o SHA velho depois do push** — `repo_sync`, ou ler o
  clone local por `run_command`.
- **`&&` no `run_command` some com o erro** — usar `;` ou chamadas separadas.
- **`longjob` não herda o ambiente da sessão** — `bash -lc 'export PATH=...; <verbo>'`.
- **Faceta válida e despovoada devolve zero sem erro** — `rag_facets` antes de
  filtrar recorte do acervo.
- **Nome de servidor MCP pode aparecer como UUID** no Code; regra `allow` por
  nome nominal (`mcp__platafirma-ops__run_command`) não casa e a chamada cai em
  pedido de aprovação. Não é falha: é aprovação manual do dono, na máquina dele.
- **Sessão do Code já aberta não recarrega `~/.claude/`.** Reexecutar o
  instalador vale a partir da próxima sessão.

## Skills

`skills/fabrica/` não existe, e o instalador declara a lista vazia de propósito.
A fábrica não carrega `platafirma` — entrega o org chart, que o contrato nega —
nem `osint`.
