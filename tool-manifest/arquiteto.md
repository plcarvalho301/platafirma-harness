# tool-manifest — claudinho-arquiteto

Ambiente: host do harness, conta `claudinho`, clones em `~/AI`. O dono não tem
shell aqui — arquivo parado em `~/AI` não é entrega; git ou wiki, no mesmo turno.

Verificação: cada linha declara **como** — `[exec]` binário executado ·
`[func]` usado em trabalho real · `[inst]` presente, sem prova de funcionamento.
`[inst]` é confissão, não aval.

> **Regra de ouro:** existindo tool para o que vou fazer, chamo a tool.
> Responder de memória o que uma busca recupera, ou navegar na mão o que um
> filtro resolve, é o erro que este manifesto existe para cortar.

Comum a toda cadeira — fila, sessão, cards, git, acervo, infra, deploy,
`conferir`: `tool-manifest/TODA-CADEIRA.md`. Aqui só o que é próprio de arquitetura.

## Conectores

**platafirma-ops** (`ops.platafirma.org/mcp`) — shell e arquivo do host, como
`claudinho`. É por onde passa todo verbo de `~/AI/bin`.
- `monta_sessao` — contexto de abertura numa chamada: persona, este manifesto,
  org canônico, mesa e fila. Chamar em vez de encadear leitura. `[exec]`
- `run_command` — único caminho para git, docker, systemd e verbo de `bin/`.
  Toda chamada grava auditoria em `var/log/ops/`. `[exec]`
- `read_file` / `write_file` — arquivo sob `~/AI`, caminho relativo à raiz.
  `write_file` grava o arquivo INTEIRO. `[exec]`

**PlataFirma Wiki** (`mcp.platafirma.org/mcp`) — wiki, espelho de leitura dos
repos e acervo bibliográfico. Escrita em repo NÃO passa por aqui.
- `platafirma_index` — mapa de entrada: que repos existem e o que cada um é.
  Uma chamada por sessão, antes de afirmar endereço. `[func]`
- `repo_tree` / `repo_read` / `repo_grep` — a resposta traz o SHA lido, logo é
  citável. `repo_grep` é regex ERE. `[func]`
- `get_page` / `edit_page` — wikitext. `edit_page` substitui a página inteira;
  passar `basetimestamp` do `get_page` para detectar conflito. `[inst]`
- `search_pages` — prosa livre. `query_cargo` — faceta declarada (`dominio`,
  `tipo`, `tema`). Critério de escolha é esse, não preferência. `[inst]`

Fronteira: `Figma`, `Canva` e `Google Drive` aparecem na sessão e não são desta
cadeira.

## sistemas (head) — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| `npx -y @mermaid-js/mermaid-cli -i <n>.mmd -o <n>.svg -b transparent` | render de diagrama; fonte `.mmd` versionada junto (`arq:0042`) | `[exec]` 11.16.0 |
| `d2` (`~/.local/bin/d2`) | fonte alternativa quando o layout do Mermaid não fecha | `[inst]` |
| `python3 -c "import xml.dom.minidom; xml.dom.minidom.parse('f.svg')"` | well-formedness de SVG escrito à mão | `[func]` |

## negocio — arquitetura de negócio

| ferramenta | quando chamar | verif. |
|---|---|---|
| mermaid-cli / `d2` | mapa de capacidades, cadeia de valor, BPMN | `[exec]` |

## dados — arquitetura de dados

| ferramenta | quando chamar | verif. |
|---|---|---|
| `docker exec <container> psql` | estado real do schema antes de reportar; nenhum verbo expõe detalhe de tabela | `[func]` |

## dominio — design de domínios

| ferramenta | quando chamar | verif. |
|---|---|---|
| `query_cargo` | contexto delimitado e classificação declarada; predicado determinístico sobre faceta | `[inst]` |
| `rag_search` / `motor rag buscar` | o que a literatura diz de um padrão, antes de fixá-lo como nosso | `[inst]` |

## Armadilhas medidas

- `conferir verbo` sai 1 hoje por dois verbos órfãos de outra cadeira
  (`longjob`, `ops-log-prune`): exit 1 não significa divergência minha.
- `conferir repo` mede o topo declarado no README, não o par fonte/render de
  `arq:0042` — a régua do par não tem instrumento; a conferência é manual.
- `ragq` não existe mais em `~/AI/bin`. O equivalente de linha é
  `motor rag buscar`; o de tool, `rag_search`.
- Nome de arquivo não diz função: ler o cabeçalho antes de inferir para que
  serve (caso medido: `ssg-deriva`, `rag.py`).

## Pendências declaradas

- Instrumento para o par fonte/render de `arq:0042`. Serviria para o gate de
  pre-commit acusar SVG sem fonte versionada; falta o verbo — dono é
  claudinho-TI, não abri card.
- `tooling/diagramas/` não existe em `platafirma-arquitetura`. Os `.mmd` vivem
  em `diagramas/` e o render é chamado na mão, sem script versionado.

## Minuta — deliberação entre cadeiras

`minuta ler` · `escrever` · `circular` · `formalizar`, no manifesto comum
(`tool-manifest/TODA-CADEIRA.md`). Verbo de toda cadeira; dona da matéria:
claudinha-gestao-estrategica. **Nunca é leitura automática** — só roda chamada,
por ping `tipo: minuta` na caixa ou ordem do dono. Protocolo:
`platafirma-arquitetura/minutas/PROTOCOLO.md`.
