# caderno — dados / conhecimento

Método da cadeira. Não guarda estado (o instrumento mede), nem fato de negócio
(card, commit, wiki). Só o que continua verdadeiro depois que o assunto morre.

## Classificar vem ANTES de vetorizar, e a inversão não dá erro

O vetor de faceta é feito de um cabeçalho — `titulo · emitido_por · dominio ·
subdominio · tipo · trata_de · colecao`. Vetorizar antes de classificar grava
vetor pobre **sem erro nenhum**, e a busca por faceta passa a responder mal sem
nada acusar. Vale para `emitido_por` tanto quanto para `trata_de`: preencher
autoria depois de vetorizar exige re-rodar.

Corolário barato: `embed-meta --all` é idempotente e custa segundos. Na dúvida,
re-rode depois de qualquer mudança de classificação.

## Ao criar conceito, o tipo da aresta decide se a afirmação é verificável

Só `mais_amplo_tipo = generica` vira `rdfs:subClassOf` na projeção. As outras
(patologica, instrumental, condicional, tematica, partitiva…) não produzem
asserção lógica — o conceito entra como classe solta e o raciocinador não tem
o que checar.

Consequência prática: `generica` entre naturezas que o BFO declara disjuntas é
insatisfazível na hora. O mapa é `modelo` → ICE, `processo` e `fenomeno` →
process, `disposicao` → disposition. Antes de usar `generica`, conferir a
natureza dos dois lados. Toda a fila de reparo da `ont:0080` é esse mesmo erro
repetido — não são casos avulsos.

E o inverso é a armadilha: passar no reasoner com aresta não-genérica não é
mérito, é ausência de afirmação.

## Coerência de família manda sobre proposta isolada

Antes de fixar natureza/estatuto de um conceito novo, olhar os irmãos de
prefixo. A família `deriva-*` é toda `patologica/fenomeno/natural`; propor um
membro novo como `doutrinario` cria divergência que nada detecta depois.

## O reasoner não cobre o vocabulário inteiro

A projeção filtra `where c.mais_amplo_id is not null`: conceito **ilhado** —
sem pai e sem filho — nunca é projetado e nunca é verificado. "TBox
consistente" é afirmação sobre o subconjunto conectado, não sobre o
vocabulário. Ao reportar consistência, dizer a cobertura junto.

## Garantia literária é a régua para criar termo

Antes de aceitar termo novo (inclusive sugerido pelo dono), contar trechos no
acervo que o sustentam. Termo bonito com 2 trechos perde para termo feio com
12. A régua é nosso próprio conceito `garantia-literaria`, e aplicá-la a nós
mesmos é o teste de que ela vale.

## Título de normativo não é evidência

Ler o texto. Um decreto catalogado com a ementa de outro decreto sobreviveu ao
catálogo, à classificação e à vetorização sem ninguém notar — e fez o acervo
parecer ter uma norma que nunca teve. O número no título também não basta:
confere-se contra o corpo, que é barato quando a obra já está indexada.

Generaliza: para qualquer obra de título opaco, ler dois trechos custa segundos
e muda a resposta com frequência alta.

## Duplicata de obra: fundir, nunca deletar direto

Duplicatas raramente são cópias — cada entrada costuma carregar metade da
catalogação (uma com `id_canonico`, outra com espécie e conceitos). Deletar
direto joga fora juízo, não lixo.

Ordem: escolher sobrevivente → migrar para ela só o que está NULL, com guarda
que recusa subdomínio de domínio alheio → migrar âncoras com `ON CONFLICT DO
NOTHING` → só então apagar.

O índice vetorial mora em **outra instância** (`motor-pg`) e não há FK entre
elas: apagar obra aqui deixa vetor órfão lá. Apagar no motor **primeiro**.

## Ao gravar classificação em lote

Todo UPDATE leva `AND <campo> IS NULL` — o dono classifica em paralelo pelo
NocoDB e sobrescrever o trabalho dele é invisível. Backup em tabela `_backup_*`
antes. E rodar guardas que falham alto: padrão que não casou com obra nenhuma,
padrão ambíguo que casou com várias, termo inexistente no vocabulário. Foi uma
guarda de padrão ambíguo que revelou duplicata de obra.

## Casar obra por título falha nos dois sentidos — a régua é o conceito

Conferir fila de aquisição, dedup ou "já temos isso?" por casamento de título produz as
duas falhas opostas, e nenhuma delas dá erro:

- **falso negativo em massa** — o acervo usa título hifenizado (`Vocabulary-Problem-Furnas-et-al`),
  e `ILIKE '%Vocabulary Problem%'`, com espaço, não casa. Uma fila de 70 pedidos sobreviveu
  inteira a uma passada dessas com 18 achados, quando os atendidos eram 52.
- **falso positivo** — homônimo e parente casam: FRAD casa com FRSAD, Knuth com *Art of UNIX
  Programming*, o *Guia* de Dados Abertos com o Decreto que institui a política.

Ordem que funciona: (1) normalizar dos dois lados — sem acento, hífen e sublinhado viram
espaço — e usar similaridade, nunca `LIKE`; (2) **perguntar ao acervo pelo conceito**, que é
o que de fato se quer saber; (3) abrir o primeiro trecho do candidato antes de decidir. Os
três passos custam segundos e mudam o veredito com frequência alta.

O corolário vale para a curadoria inteira: o que decide é o conceito estar carregado, não a
obra ser a mesma. Obra de outro autor que carrega o conceito fecha o pedido; obra homônima
que não o carrega, não.

## Estar no acervo não é estar recuperável

Obra pode ter objeto no store, impressão, classificação e vetor de faceta — e **zero trecho
elegível**. PDF sem camada de texto atravessa catálogo, classificação e `embed-meta` sem
acusar nada, e some da busca sem sumir da contagem.

Antes de afirmar que o acervo cobre um assunto por causa de uma obra, conferir:

```sql
SELECT count(*) FROM acervo.impressao i JOIN acervo.trecho t ON t.impressao_id = i.id
WHERE i.obra_id = '<uuid>' AND t.elegivel;
```

Zero aqui é pendência de **ingestão** (OCR), não de aquisição — e são estados diferentes,
que pedem atos diferentes de quem lê a fila.

## Entrega da fábrica se prova no ambiente que serve, nunca no host

Teste verde no host não diz nada sobre o serviço: o host tem `mc`, alias `pf`,
venv com tudo; a imagem `edm-rag-api` só tem o que `requirements-api.txt` instala
(o `Dockerfile.api` NÃO lê o `pyproject`). Uma entrega passou 9 testes no host
chamando `subprocess mc` — e o container não tem `mc`, nem `~/.mc`, nem cliente
S3. O relato "9 passed" era verdadeiro e irrelevante.

Antes de aprovar: `docker exec <api> which <binário>` / `python3 -c "import <dep>"`,
e o teste da rota rodando DENTRO do container. Dependência nova entra em
`requirements-api.txt` além do `pyproject`, ou a imagem quebra no import.
Build da imagem leva minutos: `longjob`, nunca inline no turno.

## Relato da fábrica é fonte não verificada — o que vale é o que se mede

O relato chega bem escrito e parcialmente falso, sem má-fé: numa mesma fita o commit
"empurrado" não estava no branch remoto (só como ancestral de outro branch), o clone de
trabalho ficou no branch dela com o verbo **vazio** no working tree (e o symlink do host
apontando pra ele), duas obras reais ficaram com conceito gravado pelo aceite de `--apply`,
e uma flag listada como entregue (`--situacao`) dava 404 em toda obra viva porque ninguém a
rodou. Nenhum desses fatos estava no relato, e todos custaram segundos para medir.

Antes de aprovar, na ordem: `git ls-remote` (o commit está onde o relato diz?) →
`git branch --show-current; git status --short` nos DOIS clones (a fábrica trabalha no
clone de trabalho e o deixa como estiver) → rodar cada flag que o relato lista, não só o
aceite do card → conferir o banco DEPOIS do aceite e exigir "desfeito" → build de produção
da release promovida de `main` (`/opt/platafirma/<familia>/<sha>`), nunca do clone que ela ocupa. Dois PRs
seguidos, dois consertos de dados por cima: o toque livre por cima da entrega é a regra,
não a exceção — e sobe no mesmo turno.

## `outros_rotulos` é derivada; quem escreve é `conceito_rotulo` (ont:0086, 02/09/2026)

Apelido de conceito se grava em `acervo.conceito_rotulo` (rótulo, língua, papel); o array
`conceito.outros_rotulos` é reconstruído por trigger e continua sendo o que o motor lê.
Escrever no array direto é escrever em derivada: some na próxima sincronização. Mudou apelido
→ `embed-meta --all` (30 s). Aresta entre conceitos fora da coluna: `acervo.conceito_relacao`
(ont:0085), com `motivo` e `garantia`; leitura única pela view `conceito_aresta`.

## `frente` e gancho de organizacao; cobertura se mede em dominio e subdominio

`frente` serve para pendurar obra que nao achou casa em dominio/subdominio — e recorte
de trabalho, nao eixo tematico. Frente com ZERO obra e o estado normal: quer dizer que
tudo que passou por ali achou casa definitiva, que e o certo. Reportar isso como buraco
de corpus (feito uma vez, corrigido pelo dono em 01/09/2026) inventa lacuna onde ha
arrumacao. Ao ler `rag_facets`: dominio e subdominio sao a medida de cobertura — so ali
a ausencia significa "nao ha obra que responda"; `frente` e marcador de trabalho.

## `acervo ingerir casa <repo>` varre o SERVIDO inteiro; o que entra e o padrao_path

`acervo ingerir casa platafirma-arquitetura` varre `/opt/platafirma/current/<curto>` (o release, atalho para `<familia>/current`,
arq:0097 — nunca a raiz da morada, que e um dir por sha) e classifica cada `*.md` pelo
`padrao_path` de `acervo.especie_tipo`; sem glob que case, o arquivo sai `reprovado` com
motivo. Logo: doc em `main` que nao esta no release NAO entra — `release promover` vem
antes. Lista curada e `--adr` seguem aceitos como fonte de transicao. "Nenhum arquivo casa
com padrao_path" com o repo no ar e sinal de varredura na morada errada, nao de glob.

## Versao de doc de casa e do TEXTO, nao do ref (14/09/2026)

`casa_impressao.fonte_versao = sha256:<corpo normalizado>` (CRLF→LF, sem newline final),
a mesma forma de obra; `ja_ingerido` = mesmo texto servindo. O sha do ref e do repositorio
inteiro: por ele todo promover parecia edicao de tudo e re-embedava 155 docs por uma ADR.
O ref e proveniencia (`casa.sha`, `casa_fonte`), nao identidade da versao; item
`ja_ingerido` so avanca `casa.sha`. Uma unica funcao compoe a versao
(`escrita_casa.versao_do_corpo`), chamada no plano e na impressao — duas composicoes
divergem na primeira normalizacao. Antes de mudar a FORMA de uma coluna, ler a CHECK dela
(a 046 fixava `sha:<ref>`).

## Averbar verbo no golden record: migracao seed, nao `acervo registrar`

`bin/_acervo/registrar` existe, mas o dispatcher `acervo` nao o roteia; o trilho vivo e
migracao seed em `platafirma-conhecimento/rag/db/init/NNN_*.sql` (padrao 049), aplicada por
`migrar aplicar rag` — sem BEGIN/COMMIT, o verbo ja envolve. `ferramental_verbo.estado`
e o eixo de baixa (`deprecado` exige `sucessor`). Cabecalho com `# escreve:` em prosa (nao
`<ato>=<recurso>`) nao entra em `ferramental_acesso`: registrar SEM acesso e o certo; inventar
recurso e errado. A projecao `--tools` filtra pelo whitelist do oficio (ti), nao por estado:
averbar nao basta para a porta servir.

## Diario de bordo (cru, sem heuristica)

- 13/09 — pedido: ingerir ultimas ADR + spec_verbologia_onda1.md em
  acervo.casa. `acervo ingerir casa platafirma-arquitetura/docs/spec_verbologia_onda1.md`
  deu "nenhum item na lista <path>" (path tratado como lista curada, nao
  como alvo). Contorno na mesma fita: lista ad-hoc de 1 item em
  `var/tmp/<ordem_id>/lista-verbologia.md`, ingerida por ela. Sem
  encaminhamento.
- 13/09 — `run_command "repo"` sem args: ~250 linhas de "repo: falta o
  nome do repo" + "fork: retry: Resource temporarily unavailable" antes
  do exit 2. Formas com ato (`repo estado <repo>`, `repo git <repo> ...`)
  funcionaram normal; nao usei "repo" bare de novo. Sem encaminhamento.

## Escrita no acervo passa pela API; migracao nao semeia dado; teste mede a rev

Tres regras de dado que a fabrica violou na mesma fita (13/09) e que valem para todo
verbo que toca o acervo:
- O cliente do verbo nunca escreve no Postgres para gravar conteudo: manda o lote para a
  rota do servidor, que grava casa, impressao, trechos, indices e o ponteiro
  (`acervo.casa_fonte`). INSERT direto produz linha cega — esta na tabela, o motor nao ve,
  o `ja_ingerido` nao reconhece. `curar casa alias` ainda escreve por psql (declarado);
  e a excecao a fechar, nao o modelo.
- Migracao e DDL e regra de dado. Linha de fato (sha ingerido, alias de conceito) nasce do
  ato que a prova; semeada por migracao, ela afirma o que nunca aconteceu, e `varrido:`
  passa a mentir com ancora.
- `teste <verbo>` roda contra o bin do repo (a rev), nao contra o PATH servido
  (`/opt/platafirma/current/harness/bin`), e apaga o vocabulario que cria. Ate 13/09 o
  PATH da casa resolvia para o proprio clone do harness (arq:0097 violada; cura #3014 e
  #3010); hoje o servido e a release, e o que esta em main so chega la por `release promover`.

## Golden record do verbo: (verbo, ato) e a chave, nao o verbo

Desde a onda 1 (verbo = canonico, ato = folha): `ferramental_ato (verbo, ato, capacidade,
acao, tipo)` e o mapeamento para a folha; `ferramental_acesso (verbo, ato, recurso_id,
modo)` e o que o ato le e escreve, com `nada` como linha explicita (ato sem linha =
nao declarado, reprova); `ferramental_recurso` e o enum de arq:0102 D1. A tabela de
capacidades volta a ser so o mapa de folhas — colunas verbo/ato nela colapsam folha com
mapeamento. O cabecalho declara `# le: <ato>=<recurso>,...` e `# escreve: <ato>=...`,
uma linha por ato; `registrar` acumula chave repetida.

## write_file devolvendo `substituiu: true` e sinal de parar e ler

Escrevi um parecer por cima de um que ja existia sem ter lido. O `substituiu: true` do
retorno e o unico aviso; a cura foi `git checkout --` antes de qualquer commit. Regra: em
docs/ de repo compartilhado, `read_file` antes de `write_file` sem trecho, sempre.

## Diario de bordo (cru, sem heuristica) — 13/09, fita do verbo acervo

- 13/09 — `repo pr-ver platafirma-harness 22` saiu 3: `gh pr view` quebra em
  "GraphQL: Projects (classic) is being deprecated". Contorno: `repo git <repo> log
  origin/main..origin/<ramo>` + `diff --stat`. Sem encaminhamento.
- 13/09 — `repo git <repo> branch -r --format=%(refname:short)` recusado pela porta
  (metacaractere `(`). Contorno: `branch -r --sort=-committerdate` sem --format.
- 13/09 — tentei aplicar migracao com `acervo psql` e stdin `\i /dev/stdin`: exit 0 e
  nada rodou. Contorno: colar o SQL inteiro no stdin.
- 13/09 — `acervo ingerir casa platafirma-arquitetura --apply` (versao da fabrica) cuspiu
  390 KB: varria node_modules e listava 2.366 reprovados um a um; a porta cortou em 50 KB
  e omitiu o item seguinte do lote. Contorno: so `*.md`, pula node_modules/.git, resumo
  com 10 exemplos (5eb2490).
- 13/09 — `deploy rag promover` saiu 1: worktree de deploy com 6 arquivos editados e 6
  untracked travava o checkout; a rag estava 16 commits atras de main. Contorno: `deploy
  promover` passou a guardar a sujeira em `git stash push -u` nomeado e seguir (5eb2490).
- 13/09 — `infra instalar acervo` devolve "nada a assentar": o diretorio de verbos da pasta de trabalho da conta era o clone. Nao e
  erro; e o estado (arq:0097 violada, #3014).

## Diario de bordo (cru, sem heuristica) — 14/09, fita da caixa (golden, ingestao, idempotencia)

- 14/09 — `acervo ingerir casa platafirma-arquitetura` deu "nenhum arquivo casa com
  padrao_path" com o repo no ar; varre_repo lia a raiz por sha do repo (na data, sob a pasta de trabalho
  da conta; hoje `/opt/platafirma/<familia>/<sha>`), nao `/current` — contorno na data 14/09: corrigir casa-ingerir (harness PR #27) e promover
  8c961e4.
- 14/09 — `repo commitar platafirma-harness` recusou por sujeira de terceiro
  (agente/settings.json) — contorno na data 14/09: commitar por caminho nomeado.
- 14/09 — `repo git platafirma-harness switch main` falhou (main preso no worktree
  platafirma-harness-caderno); `repo pr-merge` falhou pelo mesmo motivo, o merge remoto
  aconteceu — contorno na data 14/09: branch de origin/main + pr-abrir + fetch +
  `release promover <sha explicito>`.
- 14/09 — `migrar aplicar rag` com BEGIN no corpo: WARNING "transaction in progress"; e
  `ON CONFLICT (slug)` em ferramental_capacidade falhou por falta de UNIQUE — contorno na
  data 14/09: sem BEGIN/COMMIT e a UNIQUE criada na propria 049.
- 14/09 — migracao 050: UPDATE violou `casa_impressao_fonte_versao_check` (046 fixava
  `sha:<ref>`) — contorno na data 14/09: DROP/ADD da check aceitando `sha256:` na mesma
  migracao.
- 14/09 — `fila enviar` com tipo/assunto posicionais: "--tipo e --assunto sao
  obrigatorios" — contorno na data 14/09: `--de --tipo --assunto --responde`.
- 14/09 — `mesa anota --chapeu X`: unrecognized arguments — contorno na data 14/09: o slot
  e posicional, `mesa anota X`. `mesa caderno X` so LE (stdin ignorado): escrever e editar o
  .md em `abertura/<cadeira>/<chapeu>/caderno.md` no clone e subir.
- 14/09 — `write_file` recusou `platafirma-harness-caderno/...` (fora de morada) —
  contorno na data 14/09: branch no clone platafirma-harness (que estava no ramo da
  fabrica), escrever la, PR.
- 14/09 — `teste rodar platafirma-conhecimento` morre na coleta de mcp/test_server.py
  (ModuleNotFoundError: mcp) — contorno na data 14/09: `teste rodar platafirma-conhecimento
  rag/tests`; as 7 falhas restantes (fosseis, fora de casa) viraram dt #3058.
- 14/09 — `acervo psql "<sql>"` como string: recusa por metacaractere — contorno na data
  14/09: item estruturado `{verbo: acervo, ato: psql, args: [rag], stdin: <sql>}`.
- 14/09 — `release ler <repo> <path> --linhas`: opcao desconhecida; `repo procurar` sem
  `--termo` recusa — contorno na data 14/09: `read_file` com offset/max_bytes no caminho
  servido; `repo procurar <repo> --termo <t> [prefixo]`.
- 14/09 — depois do restart do ops-mcp pelo ti (whitelist #28), a porta passou a servir 22
  verbos SEM `release` e com `repo` sem ler/listar/procurar — nenhum contorno; encaminhado a
  ti na resposta da caixa.
