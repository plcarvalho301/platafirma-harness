# tool-manifest — claudinho-conhecimento

Comum a toda cadeira — fila, sessão, cards, escovação: `tool-manifest/GERAL.md`.
Este arquivo traz só o que é próprio da cadeira. Forma:
`TEMPLATE-tool-manifest.md`.

Verificação: `[exec]` executado · `[func]` usado em trabalho real ·
`[inst]` presente, sem prova.

> **Número do acervo sai de `acervo escada`, sempre que a pergunta aparecer.**
> População, cobertura, degrau e fuga são estado: vivem no instrumento, não neste
> arquivo. Faceta e população do índice → `rag_facets`. Que página existe com tal
> faceta → `query_cargo`. Contagem escrita em manifesto é segunda fonte, e segunda
> fonte diverge em silêncio — foi assim que este documento passou uma semana
> ensinando um acervo que não existia mais.

**Três ambientes, com tooling diferente. Confundir os dois primeiros é a falha
mais cara desta lista.**

| | onde | o que é |
|---|---|---|
| **máquina do dono** | conector `platafirma-ops` | onde eu trabalho: Postgres do acervo, repos git, Docker, venv. §A–§F |
| **wiki** | conector `PlataFirma Wiki` | o registro: ler, escrever, consultar Cargo e o RAG. §C–§E |
| **container Claude** | `bash_tool`, `/home/claude` | rascunho e arquivo para download. **Sem rede.** §G |
| **`modulo-osint`** | conector `osint.platafirma.org` | **não é meu.** Ambiente da claudinha-osint. §I |

`platafirma_index` uma vez por sessão sobre a PlataFirma, antes de responder — é
ele que dá endereço de repo, regra de fechados e o protocolo da fila.

---

## A. Onde a verdade mora — precedência, não preferência `[exec]`

```
acervo.* no Postgres   →  canônico. O que existe e sob que compromisso.
tabelas Cargo da wiki  →  projeção parcial, defasada por desenho.
prosa da wiki          →  o decidido e o porquê. Não é fonte de dado.
git (platafirma-*)     →  fonte do desenho. Em divergência com a wiki, o git vence.
```

A wiki **não é espelho** do acervo, e a defasagem varia nos dois sentidos. Daí a
regra de leitura: Cargo responde *que páginas existem com tal faceta*; quantas
obras existem responde `acervo escada`.

## B. Postgres do acervo — `[exec]`

```bash
docker exec -i rag-extractor-pg psql -U rag -d rag_extractor -At -F ' :: ' -c "<sql>"
```

`-At -F ' :: '` para saída parseável. Script por `-f -` com stdin redirect.
Credenciais em `platafirma-conhecimento/rag/.env` — único lugar.
Imagem `pgvector/pgvector:pg16`.

Schema `acervo` (meu): `obra · conceito · obra_trata_de · obra_serve_a ·
dominio · subdominio · especie_tipo · familia_tipo · frente · colecao · curador`.
Schema `public` (camada RAG, **não é minha**): `documents · chunks · index_meta`.

Nome que já escrevi errado: é `acervo.obra_trata_de` (não `trata_de`) e
`acervo.especie_tipo` (não `especie`).

### Guarda obrigatória

Todo UPDATE de classificação leva `AND especie_id IS NULL`. O dono classifica em
paralelo pelo NocoDB — sem a guarda, eu sobrescrevo o trabalho dele.

### Views de conferência — já existem no banco, não é script solto

`conf_conceito_ciclo · conf_familia_sem_especie · conf_obra_triada_sem_ancora ·
conf_documento_sem_obra · conf_conceito_sem_obra · conf_objeto_sem_documento ·
conf_obra_sem_ancora`.

Rodar antes de qualquer consolidação de vocabulário; o achado de cada uma é
estado e se lê na hora. `conf_conceito_sem_obra` é a régua barata de qualidade de
conceito enquanto a teia não roda. `conf_documento_sem_obra` casa por `objeto_id`
e dá falso positivo em obra-que-É-página.

### Exclusão de obra — FK com CASCADE `[exec]`

`public.documents.obra_id` → `acervo.obra(id)` `ON DELETE CASCADE`.

- `DELETE FROM acervo.obra` derruba `documents` e, por cascata, `chunks`.
- Sobra **só o objeto no MinIO**, que a FK não alcança. Expurgo de bytes é mão minha.
- DELETE acidental de linha no NocoDB propaga ao índice. Custo: re-ingest + re-embed.
- **Não renomear `arquivo` de obra no NocoDB** enquanto `carga_acervo` casar os dois
  schemas por string. A FK protege o índice, não a junção do sincronizador.

### MinIO — buckets `acervo` e `pessoal` `[exec]`

```bash
cd ~/AI/platafirma-conhecimento/rag && set -a && . ./.env && set +a
mc alias set pf "http://127.0.0.1:${MINIO_API_PORT}" "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"
```

Chave do objeto **é o sha256 do conteúdo**; não há nome legível no store.

**Versionamento está ligado nos dois buckets, e isso morde.** `mc rm` deixa delete
marker: o objeto some da listagem mas a versão fica, ocupa espaço e continua
contando na estatística do console, que soma todas as versões — foi essa contagem
que já produziu um falso achado de objeto órfão. Expurgo real:

```bash
mc rm --versions --force pf/<bucket>/<sha256>
```

## C. Wiki MCP — tools e pegadinhas `[exec]`

MediaWiki com `Cargo` e `CategoryTree`. URL humana:
`https://wiki.platafirma.org/index.php/<Título>` (sem short URL).

| tool | pegadinha que custa caro |
|---|---|
| `get_page` | devolve `timestamp`/`starttimestamp` — **passar de volta no `edit_page`** ou a detecção de conflito não existe |
| `edit_page` | substitui a **página inteira**. Não há patch nem append. Ler antes, sempre |
| `search_pages` | busca full-text **não é detector de existência**. Para "existe X?" é `query_cargo` |
| `query_cargo` | campo `isList` exige `HOLDS LIKE '%termo%'`. `LIKE` puro em campo de lista devolve vazio sem erro |
| `rag_search` | acervo bibliográfico apenas. Conteúdo da wiki é `search_pages`/`query_cargo` |
| `rag_facets` | chamar **antes** de filtrar `rag_search`: valor válido com corpus vazio devolve zero sem erro |
| `repo_read/grep/tree` | leem o **espelho** do ref remoto. Depois de `git push`, chamar `repo_sync` |
| `repo_grep` | um padrão por chamada; volta vazio em silêncio se o SHA indexado rodou. Fallback: `rg` no clone local |
| `upload_file` | teto de 2 MB. Acima disso é `importImages.php` pelo ops. `[inst]` — não usei |

Namespaces customizados: `Frente` (3000) e `Arquitetura` (3002). `Frente` roda com
`wgCapitalLinkOverrides = false` porque o primeiro segmento do título é o **slug**:
com capitalização default, `Frente:mdm-rh` viraria `Frente:Mdm-rh` e quebraria o
link gerado pelo Cargo.

## D. Cargo — o congelamento que morde `[exec]`

Tabelas: `Referencias · Conceitos · Frentes`. Campos `isList` (delimitador `,`)
só respondem a `HOLDS LIKE`. Quantas linhas cada uma tem é estado: `query_cargo`.

**A pegadinha:** `allowedValues` é uma **cópia congelada** do vocabulário,
serializada dentro da declaração da tabela. Valor novo aprovado no Postgres não
aparece — a tabela precisa ser redeclarada e recriada:

```bash
docker exec plataforma-wiki-mediawiki-1 \
  php /var/www/html/maintenance/run.php \
  /var/www/html/extensions/Cargo/maintenance/cargoRecreateData.php --table=Referencias
```

`php` existe **dentro do container**, não no host.

## E. Camada RAG — o que eu leio, o que não é meu `[exec]`

**Fronteira:** quais facetas existem e o que os valores significam é meu; quais
descem ao índice, com que modelo e com que peso é de claudinho-IA. Contrato do
índice em vigor sai de `acervo escada` (cabeçalho) e de `public.index_meta`;
leitura minha, matéria dela.

Faceta com corpus vazio devolve zero **legitimamente**. A lista de quais estão
vazias hoje é estado: `rag_facets`, na hora.

## F. Ferramental na máquina do dono

### venv `~/AI/.venv` — `[func]`, todos provados por uso

| | uso |
|---|---|
| `networkx` | a teia: projeção bipartida ponderada, `configuration_model` (null degree-preserving), assortatividade numérica |
| `numpy` · `scipy` | **`networkx` não os declara como dependência** e a assortatividade quebra sem numpy |
| `rdflib` | SKOS: `ConceptScheme`, `prefLabel`, `broader`. Projeção publicável do vocabulário |
| `rapidfuzz` | rótulo quase-duplicado no canônico (`process.extract` sobre `acervo.conceito`) |
| `ftfy` | mojibake em título vindo de PDF (`ConcepÃ§Ã£o` → `Concepção`) |
| `langdetect` | idioma da obra antes de citar |

**Sem driver de Postgres.** Leitura é `docker exec … psql -At -F ' :: '` e parse
da saída. Se a teia virar rotina, instalar `psycopg`.

### Binários

Sistema: `git · docker · psql · jq · curl · wget · pandoc · sqlite3 · exiftool ·
pdftotext · tesseract · 7z · unzip · rsync · gh`. **`php` não** — só no container.

`~/AI/bin`: catálogo e regra de uso em `GERAL.md`. Os meus de todo dia: `acervo`
(despachante — `ingerir · escada · baixar · bancada · extrato`), `fila`,
`tarefas`, `mesa`, `conferir`.

### Repos e ADRs

Clones em `~/AI`: `platafirma-{conhecimento,arquitetura,core,motor,harness}` e
`modulo-osint`. Estado de qualquer um: `git -C ~/AI/<repo> status --short`.

Escrita: `write_file → git add -A → git commit → git push → repo_sync`. Sem o
`repo_sync` final, `repo_read`/`repo_grep` continuam vendo o SHA velho.

ADRs: `platafirma-conhecimento/ontologia/adr/` (`ont:NNNN`) ·
`platafirma-arquitetura/macro-global/decisions/` (`arq:NNNN`).
Fechados: `ontologia/REGISTRO-anti-reabertura.md` — abrir só quando estiver
prestes a reabrir algo; abrir "por garantia" é o desperdício que ele evita.

### Serviços

O que está no ar e se está saudável: `infra estado` / `infra saude`. Os que me
tocam: `rag-extractor-pg · rag-extractor-minio · rag-extractor-nocodb ·
rag-extractor-api · acervo-api · plataforma-wiki-*`.

## G. Container Claude — `/home/claude`, `bash_tool`

**Sem rede.** Serve para rascunho e para produzir arquivo em
`/mnt/user-data/outputs` que o dono baixa. Não alcança o Postgres, a wiki nem os
repos: tudo isso é pelos conectores. Sistema de arquivos zera entre tarefas.

## H. Pendências — `[inst]`

- `upload_file` da wiki nunca usado; teto de 2 MB não testado na prática.
- `cargoRecreateData.php` conferido no caminho, não na execução.
- `Conceitos.dominio`/`subdominio` ainda existem como campo declarado, contra
  `ont:0062` (conceito não declara prateleira). Propagação pendente, não decisão
  a rever.
- Teia contra o corpus real: **segurada por decisão do dono** até a curadoria
  chegar perto de 3 conceitos por obra. Onde está hoje: `acervo escada` e
  `conf_conceito_sem_obra`.

## I. O que é da claudinha-osint, e continua sendo

O `modulo-osint` não alcança `/home/claudinho` e eu não alcanço o dele. "Pegar o
tooling dela" nunca é mover arquivo — é reinstalar aqui, ou encaminhar demanda.

Fica com ela, por recorte: coleta com prova (`wget --warc-file`, `warcio`,
`browsertrix-crawler`), extração de página (`extruct`, `trafilatura`, `parsel`),
crawling (`scrapy`, `protego`), PDF hostil e OCR (`pymupdf`, `ocrmypdf`,
`tesseract`, `qpdf`, `gs`), supply-chain de imagem (`trivy`, `syft`).

Atravessou para cá: `networkx`, `rdflib`, `rapidfuzz`, `langdetect`, `ftfy` (§F)
— e o formato deste documento.

O que vale copiar dela não é conteúdo, é forma: índice `problema → obra → página`,
com o custo declarado. A wiki recupera por faceta e por busca, não por problema.
Lacuna aberta de registro do conhecimento.
