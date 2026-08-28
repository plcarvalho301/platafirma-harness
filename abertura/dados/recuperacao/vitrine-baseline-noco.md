# Vitrine do baseline (NocoDB) — régua de dados

A vitrine de avaliação — o NocoDB que expõe o baseline do RAG pra leitura humana — é
matéria de **dados**, não de TI. O dado, o source e o schema que a vitrine serve são de
dados e se fecham na mão; só a operação de container (rede, túnel) é de TI.

## Topologia

- **NocoDB** `rag-extractor-nocodb`, `127.0.0.1:8081`. Metadb SQLite no volume
  `edm_nocodb` (`/usr/app/data/noco.db`). Binário empacotado: `/usr/app` só tem `data`,
  sem node_modules — módulos do noco NÃO são resolvíveis por `node -e` avulso.
- Base `platafirma` = `poc0n5jbphxnomd`.
- Source antigo `biggs_darklighter` → integração `rag` → `rag-extractor-pg` /
  `rag_extractor`, searchPath `acervo`. É o acervo vivo; válido pro que serve, não lixo.
- Baseline vive em **motor-pg** (rede `motor_malha`), db `motor`, schema `avaliacao`:
  `run`, `resultado`, `julgamento`, `gabarito_versao`. Baseline atual: run
  `671ed1a4-d4e4-4432-9194-e795d2618578`, 89 resultados, stack `e1d30f6-provisorio`,
  p50 73.8ms / p95 204.7ms.
- Redes disjuntas por padrão: noco em `edm_default`, motor-pg em `motor_malha`.

## Religar (verbo de dados + 1 op de rede TI)

1. Rede: `docker network connect motor_malha rag-extractor-nocodb`. Confere:
   noco resolve `motor-pg` → `:5432`. Prova de rota (cliente efêmero na malha):
   `docker run --rm --network motor_malha -e PGPASSWORD=<senha> postgres:16 psql -h motor-pg -U motor -d motor -tc "select count(*) from avaliacao.resultado;"`
2. Source pela **API oficial**, nunca por INSERT no metadb: source injetado à mão não
   entra no cache de sources e não aparece em `/sources`.
   - Login: o noco valida senha como `bcrypt.hash(senha, salt)` com o `salt` guardado à
     parte em `nc_users_v2` — o hash tem que usar ESSE salt, não `gensalt` novo. JWT do
     `POST /api/v1/auth/user/signin`, header `xc-auth`.
   - `POST /api/v2/meta/bases/<base>/sources` com o config pg.

## Armadilha que custa a fita

`source-create` da API **não copia o `searchPath`** da integração pro source — fica
`{"client":"pg"}`, a introspecção varre `public` (vazio), o meta-diff volta `[]` e a
vitrine fica vazia SEM erro. Correção: pôr `{"client":"pg","searchPath":["<schema>"]}`
no config do source e redisparar
`POST /api/v1/db/meta/projects/<base>/meta-diff/<source>`.

**Régua:** conferir sempre o config do SOURCE (searchPath), não só o da integração.

## Pendência de fronteira (TI, transporte)

Não há rota de túnel pro noco (8081 só interno) — o dono não acessa a vitrine de fora
até TI expor. Isso sim é operação de rede, não de dados.
