Substitui: tool-manifest-geral (arq:0071/0073); mora em abertura/oficio.md

# tool-manifest — núcleo

Regras comuns a toda cadeira. **Os verbos do núcleo chegam como tools** (nome = slug
do verbo; descrição = golden record, na forma `<o que> · use para: … · atos: …`;
`tools/list` é o índice — spec cápsula de verbos, 02/09/2026). Contrato, dito aqui e
só aqui:

- `<verbo>(ato, args, stdin, sessao_id, timeout)` executa `bin/<verbo> <ato> <args>`.
  Sem `ato` o verbo lista os atos; `deploy`, `descobrir`, `situacao` e `motor <inst>`
  levam o alvo no `ato` — a descrição diz.
- `sessao_id` é o do `monta_sessao`. Sem ele, a porta resolve por sessão-sombra só
  quando é inequívoca (uma sessão viva sua); ambíguo → roda sem cadeira, e
  `mesa`/`fila`/`tarefas` não sabem de quem é o ato.
- `run_command` é lote entre verbos DISTINTOS numa chamada só, sem shell e sem
  fallback: programa que não é verbo não roda — a recusa diz qual verbo usar, e
  `sugestao: null` é card de verbo novo (spec_porta-so-verbo).

## Abertura: `monta_sessao` é a PRIMEIRA ação, em toda cadeira

Não é cortesia nem passo opcional — é impedimento: sem ela a cadeira não tem persona,
ofício nem mesa, e o estado fica como está. Monta antes de raciocinar ou responder,
mesmo que o prompt não repita a ordem; recusar porque "a tarefa não pede" é o desvio.

- `monta_sessao(cadeira, pergunta=<turno literal do dono>)`: o roteador escolhe o
  chapéu (`roteador.via`). `chapeu=` só quando o dono o disse.
- `roteador.slug: null` (fallback) → a cadeira infere a gerência do prompt e DECLARA o
  slug na primeira linha da resposta, sem segunda chamada. Prompt sem alvo: declara
  "sem chapéu".
- Fora da abertura, a troca de chapéu é só por ordem do dono — a cadeira não troca
  sozinha.

- Norma de card, execução inteira e teste de admissão da fila:
  `platafirma-arquitetura/docs/administrativo.md`, por ato.

> **Entrega vai a git ou wiki no mesmo turno.** O dono não tem shell no host: arquivo
> parado em `~/AI` é rascunho. Publica, e só então relata, com link inteiro e colável.

Necessidade → verbo: ver/editar mesa, fila, tarefas, acervo, motor, deploy… → a tool de
mesmo nome. O que era fallback tem dono: git → `repo` · `conferir` · `situacao`; cat/rg/fd
→ `read_file(paths)` · `descobrir`; docker/systemctl/journalctl → `infra`; docker exec
rag-* → `motor`; curl → `pesquisar`; pytest/ruff → `teste` · `lint`. Arquivo: `read_file`
e `write_file` (tipo × morada; `trecho={antes, depois}` edita sem reescrever).

## Um giro carrega o independente — agrupe, nao encadeie

Cada chamada de tool e um giro, e giro custa token. O que mais infla giro/turno e
disparar comandos em cadeia — roda um, le, roda outro — quando eles nao dependiam
um do outro.

- `run_command(commands=[...])`: varios shells num giro so; cada item roda em seu
  proprio `bash -c`, erro num nao derruba os outros, resultado por item.
- `read_file(paths=[...])`: varias leituras num giro so.

A regua e a DEPENDENCIA, nao o gosto: so encadeia (um giro por vez) quando o
proximo comando PRECISA do resultado do anterior. Antes de disparar o segundo
`run_command`, pergunte se ele ja nao cabia no primeiro.

E antes de sondar o host, leia a memoria que ja veio na abertura — mesa e caderno
(`mesa caderno <chapeu>`). Sondar com `run_command` o que a mesa ja diz e giro
gasto a toa.

## Cinco armadilhas que mordem toda cadeira

- **Espelho de repo serve o SHA velho depois do push** — `repo_sync`, ou ler o clone
  local por `run_command`.
- **`&&` no `run_command` some com o erro** — usar `;` ou chamadas separadas.
- **Faceta válida e despovoada devolve zero sem erro** — `rag_facets` antes de filtrar.
- **`longjob` não herda o ambiente da sessão** — `bash -lc 'export VAR=x PATH=...; <verbo>'`.
- **`edit_page` substitui a página inteira** — `get_page` antes, sempre.

## Três regras que não são de ferramenta

- **Escovação de bit só no miolo do loop**: o que sobe no contexto a cada giro. Fora
  dele, clareza vence contração.
- **O comportamento é o mesmo nas três superfícies** (claude.ai, fita do chat, Code):
  a equalização é pelo MEIO — as três servem `claudinho-mcp` e `platafirma-wiki`.
  Texto de cadeira não se reescreve para caber em superfície mais pobre.
- **Todo verbo declara `capacidade:` e `dono:`** no cabeçalho, e a conta é um verbo
  por capacidade (`arq:0037`). `conferir verbo` mede.

Clones de trabalho: `platafirma-{core,conhecimento,arquitetura,harness,motor,posto}`
e `modulo-osint`, todos em `~/AI`.
