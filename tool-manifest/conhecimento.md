# tool_manifest — claudinho-conhecimento

Verificado em 2026-08-03 executando cada item. Toda linha declara **como** foi
verificada: `[exec]` comando executado · `[func]` importado e testado em uso real
· `[inst]` presente, sem prova de funcionamento.

Espelha o padrão do manifesto da claudinha-osint. O recorte é outro: lá é
coleta e parsing de fonte hostil; aqui é **verdade canônica, vocabulário e
registro**.

**Três ambientes, com tooling diferente. Confundir os dois primeiros é a falha
mais cara desta lista.**

| | onde | o que é |
|---|---|---|
| **máquina do dono** | conector `platafirma-ops` | onde eu trabalho: Postgres do acervo, repos git, Docker, venv. §0–§F |
| **wiki** | conector `PlataFirma Wiki` | o registro: ler, escrever, consultar Cargo e o RAG. §C–§E |
| **container Claude** | `bash_tool`, `/home/claude` | rascunho e arquivo para download. **Sem rede.** §G |
| **`modulo-osint`** | conector `osint.platafirma.org` | **não é meu.** Ambiente da claudinha-osint. §I |

---

## 0. Abertura de sessão

`fila status claudinho-conhecimento` / `fila ler claudinho-conhecimento` -- comandos
e protocolo em `GERAL.md`. **`ls -1 fila/claudinho-conhecimento/` não funciona mais:**
a fila trocou de um diretório de arquivos por persona para um arquivo `.md` único
lido pelo binário `fila` -- confirmado nesta sessão (05/08), o caminho antigo dá
"No such file or directory".

`platafirma_index` uma vez por sessão sobre a PlataFirma, antes de responder —
é ele que dá endereço de repo, regra de fechados e o protocolo da fila. Uma
chamada; dentro da sessão o retorno não muda.

Linux Mint 22.3 · Python 3.12.3 · 1,5 TB livres · 30 G de RAM (15 em uso) ·
rede aberta (HTTP 200 em 0,21 s) · **sem sudo** (pede senha).

---

## A. Onde a verdade mora — precedência, não preferência `[exec]`

```
acervo.* no Postgres   →  canônico. O que existe e sob que compromisso.
tabelas Cargo da wiki  →  projeção parcial, defasada por desenho.
prosa da wiki          →  o decidido e o porquê. Não é fonte de dado.
git (platafirma-*)     →  fonte do desenho. Em divergência com a wiki, o git vence.
```

**Provado hoje, e é o fato mais importante deste documento:** a wiki **não é
espelho** do acervo.

| | Postgres | Cargo |
|---|---|---|
| obras / `Referencias` | 779 | 79 |
| conceitos / `Conceitos` | ver `acervo status` | 39 |

Divergem nos dois sentidos: `Referencias` cobre 10% do acervo (só obra com
página), e `Conceitos` tem 33 linhas **a mais** que o canônico. Consulta de
população, cobertura ou contagem se faz no Postgres. Cargo responde
"que páginas existem com tal faceta", nunca "quantas obras existem".

### População canônica em 2026-08-03

```
obra 779 · com espécie 287 · conceito 196 · obra_trata_de 456 · obra_serve_a 21
domínio 10 · subdomínio 32 · especie_tipo 25 · familia_tipo 6 · frente 7
coleção 2 · curador 3
```

Conceitos por obra (meta de curadoria: 3):

```
0 → 522    1 → 116    2 → 97    3 → 32    4 → 11    6 → 1
```

---

## B. Postgres do acervo — `[exec]`

```bash
docker exec -i rag-extractor-pg psql -U rag -d rag_extractor -At -F ' :: ' -c "<sql>"
```

`-At -F ' :: '` para saída parseável. Multi-statement por `-c` encadeado. Script
por `-f -` com stdin redirect. Credenciais em
`platafirma-conhecimento/rag/.env` — único lugar.

Imagem `pgvector/pgvector:pg16`; extensões `plpgsql 1.0` e `vector 0.8.5`.

### Nomes reais das tabelas — corrigidos hoje

| escrevi errado | é |
|---|---|
| `acervo.trata_de` | **`acervo.obra_trata_de`** |
| `acervo.especie` | **`acervo.especie_tipo`** |

Schema `acervo`: `obra · conceito · obra_trata_de · obra_serve_a · dominio ·
subdominio · especie_tipo · familia_tipo · frente · colecao · curador`.
Schema `public` (camada RAG, **não é minha**): `documents 371 · chunks 78.592 ·
index_meta`.

### Views de conferência — já existem no banco, não é script solto

`conferencia.sql` virou view. Estado hoje:

| view | achados |
|---|---|
| `conf_conceito_ciclo` | 0 |
| `conf_familia_sem_especie` | 0 |
| `conf_obra_triada_sem_ancora` | 0 |
| `conf_documento_sem_obra` | 6 — **redundante** desde a FK com CASCADE; casa por `objeto_id` e dará falso positivo quando obra-que-É-página entrar |
| `conf_conceito_sem_obra` | **46** — conceito declarado sem nenhuma obra |
| `conf_objeto_sem_documento` | 345 |
| `conf_obra_sem_ancora` | 491 |

Rodar as sete antes de qualquer consolidação de vocabulário. `conf_conceito_sem_obra`
é a régua barata de qualidade de conceito enquanto a teia não roda.

### Guarda obrigatória

Todo UPDATE de classificação leva `AND especie_id IS NULL`. O dono classifica em
paralelo pelo NocoDB (`127.0.0.1:8081`) — sem a guarda, eu sobrescrevo o trabalho dele.

### Exclusão de obra — FK com CASCADE `[exec]`

`public.documents.obra_id` → `acervo.obra(id)` `ON DELETE CASCADE` (conferido em
`pg_constraint`: `confdeltype='c'`, 626/626 preenchidos).

- `DELETE FROM acervo.obra` derruba `documents` e, por cascata, `chunks`. Não há
  mais exclusão em quatro lugares.
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
marker: o objeto some da listagem mas a versão fica, continua ocupando espaço e
continua contando nas estatísticas do console — que somam **todas** as versões.
Foi essa contagem que produziu, em 03/08, o falso achado de "117 objetos órfãos,
1,3 GB": 114 já estavam apagados por triagem, e o console mostrava o resíduo.

Expurgo real de objeto sem obra:

```bash
mc rm --versions --force pf/<bucket>/<sha256>
```

Conferência depois de qualquer expurgo — tem que dar zero:

```bash
# obras apontando para objeto inexistente
comm -23 <(psql ... -At -c "select distinct objeto from acervo.obra where objeto is not null" | sed 's#.*/##' | sort -u) \
        <((mc ls -r pf/acervo; mc ls -r pf/pessoal) | awk '{print $NF}' | sort -u)
```

---

## C. Wiki MCP — tools e pegadinhas `[exec]`

MediaWiki **1.43.9**, extensões `Cargo` e `CategoryTree`. URL humana:
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
| `repo_grep` | um padrão por chamada; volta vazio em silêncio se o SHA indexado rodou. Fallback: `grep -rnE` no clone local |
| `upload_file` | teto de 2 MB. Acima disso é `importImages.php` pelo ops. `[inst]` — não usei |

### Namespaces com página

```
principal 90 · Discussão 2 · PlataFirma 21 · Arquivo 3 · MediaWiki 3
Predefinição 5 · Ajuda 19 · Category 8 · Frente 103 · Arquitetura 6
```

`Frente` (3000) e `Arquitetura` (3002) são customizados. `Frente` roda com
`wgCapitalLinkOverrides = false`: o primeiro segmento do título é o **slug**, e
com capitalização default `Frente:mdm-rh` viraria `Frente:Mdm-rh` e quebraria o
link gerado pelo Cargo.

---

## D. Cargo — três tabelas, e o congelamento que morde `[exec]`

`cargo_pages 71 · cargo_backlinks 58 · cargo_tables 3`

| tabela | linhas | campos |
|---|---|---|
| `Referencias` | 79 | `titulo` `colecao` `dominio` `subdominio` `tipo` `trata_de`✱ `serve_a`✱ `emitido_por`✱ `id_canonico`✱ `publicacao` `anotacao` |
| `Conceitos` | 39 (o 229 anterior era `Conceitos__trata_de`) | `titulo` `slug` `dominio` `subdominio` `trata_de`✱ |
| `Frentes` | 85 | `nome` `estado` `dominios`✱ `abertura` |

✱ = `isList`, delimitador `,` → **só `HOLDS LIKE`**.

`estado` da frente: `ativa · dormente · encerrada`.
`colecao`: `firma · pessoal`.
`tipo` tem 24 valores permitidos; `dominio` 10; `subdominio` 32.

**A pegadinha:** `allowedValues` é uma **cópia congelada** do vocabulário,
serializada dentro da declaração da tabela. Valor novo aprovado no Postgres não
aparece aqui — a tabela precisa ser redeclarada e recriada:

```bash
docker exec plataforma-wiki-mediawiki-1 \
  php /var/www/html/maintenance/run.php \
  /var/www/html/extensions/Cargo/maintenance/cargoRecreateData.php --table=Referencias
```

PHP 8.3.33 existe **dentro do container**, não no host. `php` no host: ausente.

**`Conceitos.dominio`/`subdominio` ainda existem como campo declarado.** Isso
contradiz ont:0062 (conceito não declara prateleira; a ocorrência é composta de
`obra_trata_de` + `obra.dominio_id`). Pendência de propagação, não decisão a rever.

---

## E. Camada RAG — o que eu leio, o que não é meu `[exec]`

Facetas com corpus vazio hoje (filtrar por elas devolve zero **legitimamente**):
os domínios `curadoria-acervo` e `platafirma`; os quatro subdomínios de
`inteligencia` — o domínio tem obra, nenhuma designada; `front-end`,
`avaliacao-e-governanca`, `produto-baseado-em-modelo`, `produto-publico-digital`,
`organizacao-do-conhecimento`, `cognicao-e-aprendizagem`, `estrategia-e-resultado`,
`estrutura-e-topologia`, `governanca-institucional`; e as frentes
`paper-capability-trap` e `wiki`. Lista derivada de `rag_facets` — conferir lá
antes de filtrar, não copiar daqui.

Índice: modelo `Qwen/Qwen3-Embedding-0.6B`, modo `hybrid`, RRF k=60. **Tamanho e
composição não se escrevem aqui** — rodar `acervo status`. Número copiado pra dentro
de manifesto vira segunda fonte que ninguém atualiza.

**Fronteira:** quais facetas existem e o que os valores significam é meu; quais
descem ao índice e com que peso é da claudinho-IA. Os pesos RRF acima são
leitura, não matéria minha.

---

## F. Ferramental na máquina do dono

### venv `~/AI/.venv` — instalado em 2026-08-03, `[func]`, todos provados por uso

| | uso | prova |
|---|---|---|
| `networkx` 3.6.1 | a teia: `bipartite.weighted_projected_graph`, `configuration_model` (null degree-preserving), `numeric_assortativity_coefficient` | projeção, grau preservado e coeficiente executados |
| `numpy` 2.5.1 · `scipy` 1.18.0 | **`networkx` não os declara como dependência** e a assortatividade quebra sem numpy | erro reproduzido e corrigido |
| `rdflib` 7.6.0 | SKOS: `ConceptScheme`, `prefLabel`, `broader`. Projeção publicável do vocabulário | Turtle com `@pt-BR` serializado |
| `rapidfuzz` 3.14.5 | rótulo quase-duplicado no canônico (`process.extract` sobre `acervo.conceito`) | 94,7 em par com/sem cedilha |
| `ftfy` 6.3.1 | mojibake em título vindo de PDF | `ConcepÃ§Ã£o` → `Concepção` |
| `langdetect` 1.0.9 | idioma da obra antes de citar | `pt` |
| `jsonschema` · `charset-normalizer` · `regex` | já no Python do sistema | importados |

**Sem driver de Postgres.** Leitura é `docker exec … psql -At -F ' :: '` e parse
da saída. Se a teia virar rotina, instalar `psycopg`.

### Binários do sistema `[exec]`

`git 2.x · docker · psql · jq · curl · wget · pandoc · sqlite3 · exiftool ·
pdftotext · tesseract · 7z · unzip · rsync · gh`. **`php` não** — só no container.

### `~/AI/bin` — binários próprios, fora do apt

`acervo` (despachante: status, get, pacote, extrato) `ops-log-prune` `longjob` ·
`age` `age-keygen` `sops` `minisign` `cosign` `gitleaks` · `grype` `dockle`
`hadolint` `osv-scanner` `lynis` `seg` · `ctop` `dive` `lnav` `restic` ·
`fd` `rg` `hurl` `jwt` `oauth2c` `opa`

Os três primeiros são de acervo e me interessam direto. `[inst]` — não executei
nenhum nesta verificação.

### Repos com clone de trabalho

```
platafirma-conhecimento  main 4d5f002    ontologia/, wiki, mcp/
platafirma-arquitetura   main 06caf91    macro-global/decisions/, docs/
platafirma-core          main d2f5345    eixo transversal, .env do Vikunja
platafirma-motor         main cc015c1
platafirma-harness       main 412904e
modulo-osint             master 3e45ea0  o ambiente dela, versionado aqui
```

Escrita: `write_file → git add -A → git commit → git push → repo_sync`.
Sem o `repo_sync` final, `repo_read`/`repo_grep` continuam vendo o SHA velho.

ADRs: `platafirma-conhecimento/ontologia/adr/` (`ont:NNNN`) ·
`platafirma-arquitetura/macro-global/decisions/` (`arq:NNNN`).
Fechados: `ontologia/REGISTRO-anti-reabertura.md` (só abrir quando estiver
prestes a reabrir algo — abrir "por garantia" é o desperdício que ele evita).

### Docker — 15 containers, `[exec]`

`rag-extractor-pg` (pgvector) · `rag-extractor-minio` (9000/9001) ·
`rag-extractor-nocodb` (**8081**) · `rag-extractor-api` · `acervo-api` ·
`plataforma-wiki-mediawiki-1` · `plataforma-wiki-db-1` (mariadb 11) ·
`plataforma-wiki-mcp-1` · Keycloak · Vikunja + proxy + db · oauth2-proxy ·
cloudflared

### Rastreador de tarefas: **Vikunja**, não Todoist `[inst]`

`tarefas.platafirma.org`, REST puro — não há tool. Token em
`platafirma-core/.env` chave `VIKUNJA_API_TOKEN`; padrão de chamada em
`tmp-dor/criar_cards.py`. Não exercitei nesta sessão.

---

## G. Container Claude — `/home/claude`, `bash_tool`

**Sem rede.** Serve para rascunho e para produzir arquivo em
`/mnt/user-data/outputs` que o dono baixa. Não alcança o Postgres, a wiki nem os
repos: tudo isso é pelos conectores. Sistema de arquivos zera entre tarefas.

---

## H. Pendências — `[inst]`

- `upload_file` da wiki nunca usado; teto de 2 MB não testado na prática.
- `cargoRecreateData.php` não rodado nesta sessão — o comando está conferido no
  caminho, não na execução.
- API do Vikunja não exercitada por mim.
- Os três binários de acervo em `~/AI/bin` não executados.
- Teia contra o corpus real: **segurada por decisão do dono** até a curadoria
  chegar perto de 3 conceitos por obra. Hoje 522 obras de 779 têm zero.

---

## I. O que é da claudinha-osint, e continua sendo

O `modulo-osint` não alcança `/home/claudinho` e eu não alcanço o dele. "Pegar o
tooling dela" nunca é mover arquivo — é reinstalar aqui, ou encaminhar demanda.

Fica com ela, por recorte: coleta com prova (`wget --warc-file`, `warcio`,
`browsertrix-crawler` em Docker rootless), extração de página (`extruct`,
`trafilatura`, `parsel`), crawling (`scrapy`, `protego`), PDF hostil e OCR
(`pymupdf`, `ocrmypdf`, `tesseract` com 161 idiomas, `qpdf`, `gs`), supply-chain
de imagem (`trivy`, `syft`).

Atravessou para cá: `networkx`, `rdflib`, `rapidfuzz`, `langdetect`, `ftfy` (§F)
— e o formato deste documento.

O corpus de ontologia dela em boa parte já está no meu acervo: `BFO2-Reference`,
`Building Ontologies with BFO`, `e-ARQ Brasil`, `SKOS`, `VCGE`, `Ontological
Foundations for Structural Conceptual Models`. **Correção 05/08, conferida no
Postgres:** `Ontology Matching` (Euzenat & Shvaiko) e `Ontological Anti-Patterns`
(Sales & Guizzardi) NÃO estão -- a linha anterior dizia o contrário e estava errada.
São exatamente 2 das 3 obras que claudinho-IA reportou ausentes no rechaveamento
do gold-set T2 (20260805T213646); a lacuna é real, não falso-negativo do matching dela.

O que vale copiar do §G dela não é conteúdo, é forma: índice `problema → obra →
página`, com o custo declarado. A wiki recupera por faceta e por busca, não por
problema. Lacuna aberta de registro do conhecimento.
