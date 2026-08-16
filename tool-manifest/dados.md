# tool-manifest — claudinho-dados

Ambiente: **três**, com tooling diferente. Confundir os dois primeiros é a falha mais
cara desta lista.

| | onde | o que é |
|---|---|---|
| **máquina do dono** | conector `platafirma-ops` | onde eu trabalho: Postgres do acervo, MinIO, repos git, Docker, venv |
| **wiki** | conector `PlataFirma Wiki` | o registro: ler, escrever, consultar Cargo e o RAG |
| **container Claude** | `bash_tool`, `/home/claude` | rascunho e arquivo para download. **Sem rede**, e o FS zera entre tarefas |

`modulo-osint` (`osint.platafirma.org`) **não é meu** — ambiente externo isolado, sem
canal comigo. "Pegar o tooling de lá" nunca é mover arquivo: é reinstalar aqui.

Verificação: `[exec]` binário executado · `[func]` usado em trabalho real ·
`[inst]` presente, sem prova. `[inst]` é confissão, não aval.

> **Regra de ouro:** existindo tool para o que vou fazer, chamo a tool. Responder de
> memória o que uma busca recupera é o erro que este manifesto existe para cortar.

> **Nenhum número mora aqui.** População, cobertura, degrau, contagem de tabela e sha
> de índice são estado: saem de `acervo escada`, `rag_facets`, `query_cargo` e do
> banco, na hora. Contagem escrita em manifesto é segunda fonte, e segunda fonte
> diverge em silêncio — foi assim que este documento passou uma semana ensinando um
> acervo que não existia mais.

Comum a toda cadeira — fila, sessão, cards, escovação: `tool-manifest/TODA-CADEIRA.md`.
Armadilha que morde toda cadeira mora lá e não se repete aqui.

## Onde a verdade mora — precedência, não preferência `[exec]`

```
acervo.* no Postgres   →  canônico. O que existe e sob que compromisso.
tabelas Cargo da wiki  →  projeção parcial, defasada por desenho.
prosa da wiki          →  o decidido e o porquê. Não é fonte de dado.
git (platafirma-*)     →  fonte do desenho. Em divergência com a wiki, o git vence.
```

A wiki **não é espelho** do acervo, e a defasagem varia nos dois sentidos. Daí a régua:
Cargo responde *que páginas existem com tal faceta*; *quantas obras existem* é
`acervo escada`.

## Conectores

**platafirma-ops** (`ops.platafirma.org`) — a máquina do dono.
- `monta_sessao` — abertura da cadeira numa chamada: persona, este manifesto, org e
  fila. Chamar em vez de encadear leitura. Sob demanda, não gate de entrada.
- `run_command` — verbo único: git, docker, psql, venv, os binários de `~/AI/bin`.
- `read_file` · `write_file` — arquivo sob `~/AI`. Escrita segue para git no mesmo turno.

**PlataFirma Wiki** (`mcp.platafirma.org`) — o registro.
- `platafirma_index` — uma vez por sessão sobre a PlataFirma, antes de responder.
- `get_page` · `edit_page` · `search_pages` · `query_cargo` · `rag_search` · `rag_facets`
  · `repo_read` · `repo_grep` · `repo_tree` · `upload_file`.

## ontologia — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| `psql` no schema `acervo` | canônico do vocabulário: `conceito · dominio · subdominio · especie_tipo · familia_tipo` | `[exec]` |
| views `conf_*` | antes de qualquer consolidação: `conf_conceito_ciclo · conf_familia_sem_especie · conf_conceito_sem_obra · conf_obra_sem_ancora` — já existem no banco, não é script solto | `[exec]` |
| `query_cargo` | "existe página com tal faceta?" — é isto, nunca `search_pages` | `[exec]` |
| `rapidfuzz` (`~/AI/.venv`) | rótulo quase-duplicado: `process.extract` sobre `acervo.conceito` | `[func]` |
| `rdflib` | projeção SKOS publicável: `ConceptScheme`, `prefLabel`, `broader` | `[func]` |
| `networkx` + `numpy`/`scipy` | a teia: projeção bipartida, `configuration_model`, assortatividade | `[func]` |
| ADRs `ont:NNNN` | `platafirma-conhecimento/ontologia/adr/`. Fechados: `ontologia/REGISTRO-anti-reabertura.md` | `[exec]` |

Nome que já escrevi errado: é `acervo.obra_trata_de` (não `trata_de`) e
`acervo.especie_tipo` (não `especie`).

`networkx` **não declara** numpy/scipy como dependência — assortatividade quebra sem numpy.

## conhecimento — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| `acervo escada` | ÚNICA fonte de número do acervo. `--json`, `--detalhe` | `[exec]` |
| `acervo` (despachante) | `ingerir · escada · baixar · bancada · extrato` — sem argumento, lista os atos | `[exec]` |
| `psql` no schema `acervo` | classificação. **Todo UPDATE leva `AND especie_id IS NULL`**: o dono classifica em paralelo pelo NocoDB | `[exec]` |
| `mc` (MinIO) | buckets `acervo` e `pessoal`; alias por `rag/.env`. Chave do objeto **é o sha256 do conteúdo** | `[exec]` |
| `cargoRecreateData.php` | depois de aprovar valor novo de vocabulário — `allowedValues` é cópia congelada | `[inst]` |
| `edit_page` + `get_page` | publicar o decidido. Edição grande: `docker cp` + `maintenance/run.php edit` | `[exec]` |
| `ftfy` · `langdetect` | mojibake de título vindo de PDF; idioma da obra antes de citar | `[func]` |
| `pdftotext` · `exiftool` · `pandoc` · `tesseract` | triagem de obra antes de ingerir | `[exec]` |

Conexão ao banco:

```bash
docker exec -i rag-extractor-pg psql -U rag -d rag_extractor -At -F ' :: ' -c "<sql>"
```

Credenciais em `platafirma-conhecimento/rag/.env`, único lugar. Sem driver de Postgres
no venv: leitura é parse da saída. Virando rotina, instalar `psycopg`.

Recriação de tabela Cargo (`php` só existe **dentro** do container):

```bash
docker exec plataforma-wiki-mediawiki-1 php /var/www/html/maintenance/run.php \
  /var/www/html/extensions/Cargo/maintenance/cargoRecreateData.php --table=Referencias
```

## modelagem — ferramental próprio

Gerência nova (dono, 12/08/2026). Ferramental herdado do TI, **artefato meu ainda não
escrito** — ver pendências.

| ferramenta | quando chamar | verif. |
|---|---|---|
| `bin/fila_streams.py` (leitura) | fonte do envelope em vigor: `de · tipo · assunto · ref · responde` + corpo; tipos `decisao\|resposta\|pedido\|minuta\|demanda\|handoff` | `[exec]` |
| `platafirma-motor/docs/msg-implantado.md` | estado implantado da malha — **defasado**, ver armadilhas | `[exec]` |
| ADRs `arq:0018 · 0024 · 0036` | malha, retenção e assinatura. `arq:0045`/`0046`: cadeia obra→impressão→trecho→índice→vetor | `[exec]` |
| `psql` (DDL de leitura) | conferir schema servido contra o modelo declarado: `\d+ acervo.*` | `[exec]` |

Fronteira, que é onde esta gerência mais confunde: conceitual, lógico, schema e contrato
são meus; **tipo concreto, índice, partição, DDL, migração e o transporte da malha são de
claudinho-TI**. Eu modelo, ele implementa.

## produtos — ferramental próprio

| ferramenta | quando chamar | verif. |
|---|---|---|
| `rag_facets` | ANTES de filtrar `rag_search`: diz faceta válida e população real | `[exec]` |
| `rag_search` | acervo bibliográfico apenas — FORMALISMO, nunca fato da PlataFirma | `[exec]` |
| `motor rag buscar` | mesma consulta pela linha de comando, mesmo contrato | `[exec]` |
| `motor rag ajuste` | ver os ajustes do motor e o trade-off de cada — **ver é meu, mexer é de claudinho-IA** | `[exec]` |
| `public.index_meta` | contrato do índice em vigor. Leitura minha, matéria dela | `[exec]` |
| `avaliacao/gabarito.jsonl` (harness) | gabarito canônico único, 228 itens. Autor: claudinho-IA | `[exec]` |
| scripts de bench (`platafirma-conhecimento`) | `eval_retrieval · estratifica_gold · _teste_continuo_z · calibra_cobertura`; leem o gabarito por `PF_GABARITO` | `[exec]` |

Contrato com o consumidor: claudinho-IA tuna assertividade (embedder, chunking, pesos,
rerank, avaliação). Defeito que o tuning não conserta — obra ausente, classificação errada,
faceta despovoada, chunk mal recortado na origem — volta para mim com a medição junto.

## Armadilhas medidas

- **FK com CASCADE derruba o índice.** `public.documents.obra_id → acervo.obra(id)`
  `ON DELETE CASCADE`: `DELETE FROM acervo.obra` leva `documents` e, por cascata,
  `chunks`. DELETE acidental de linha no NocoDB propaga. Custo: re-ingest + re-embed.
- **A FK não alcança o MinIO.** Sobra o objeto no store; expurgo de bytes é mão minha.
- **Versionamento ligado nos dois buckets.** `mc rm` deixa delete marker: o objeto some
  da listagem, a versão fica e continua contando na estatística do console — já produziu
  falso achado de objeto órfão. Expurgo real é `mc rm --versions --force pf/<bucket>/<sha>`.
- **Não renomear `arquivo` de obra no NocoDB** enquanto `carga_acervo` casar os dois
  schemas por string. A FK protege o índice, não a junção do sincronizador.
- **`query_cargo` em campo `isList` exige `HOLDS LIKE '%termo%'`.** `LIKE` puro devolve
  vazio sem erro.
- **`search_pages` não é detector de existência.** É full-text. Para "existe X?" é `query_cargo`.
- **`Cargo.allowedValues` é cópia congelada** do vocabulário, serializada na declaração da
  tabela: valor aprovado no Postgres não aparece até recriar a tabela.
- **`conf_documento_sem_obra` casa por `objeto_id`** e dá falso positivo em obra-que-É-página.
- **`msg-implantado.md` afirma que a caixa ainda roda em arquivo.** É falso: já roda na
  malha. Doc de outra cadeira (TI/motor), nomeado aqui para não me enganar de novo.
- **`repo_grep` da wiki aceita um padrão por chamada** e volta vazio em silêncio se o SHA
  indexado rodou. Fallback: `rg` no clone local.

## Pendências declaradas

- **Contrato do envelope `msg` não existe como documento meu** — só no código do cliente.
  Enquanto for assim, compatibilidade é o que o parser aceita, não o que a plataforma
  promete. Falta: ADR ou página de wiki com campo, tipo, obrigatoriedade e regra de evolução.
- **`bin/fila_streams.py` declara `dono: claudinho-IA`** no cabeçalho, e o contrato do
  envelope migrou para mim em 12/08. Cabeçalho de verbo alheio: nomeio, não conserto.
- `upload_file` da wiki nunca usado; teto de 2 MB não testado. Acima disso é
  `importImages.php` pelo ops.
- `cargoRecreateData.php` conferido no caminho, não na execução.
- `Conceitos.dominio`/`subdominio` ainda existem como campo declarado, contra `ont:0062`.
  Propagação pendente, não decisão a rever.
- Sem driver de Postgres no venv (`psycopg`), o que torna todo trabalho de grafo um
  parse de texto.
- Índice `problema → obra → página`, com custo declarado: a wiki recupera por faceta e por
  busca, não por problema. Lacuna de registro conhecida — a superfície é de claudinha-produto.
