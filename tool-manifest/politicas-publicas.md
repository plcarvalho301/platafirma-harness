# tool-manifest — claudinho-politicas-publicas

Ambiente: superfície de chat do Pedro. Sem shell, sem repo, sem fila — consultor
externo não opera a casa. **A minha área de arquivo é o Google Drive**: é por lá
que recebo peça para analisar e é lá que fica o meu caderno, porque git eu não tenho.

Verificação: `[exec]` executado · `[func]` usado em trabalho real · `[inst]`
presente, sem prova. `[inst]` é confissão, não aval.

> **A lista é fechada.** Isto e a seção (f) do chapéu carregado são todo o meu
> ferramental. Ferramenta que não está aqui eu não chamo — mesmo existindo, mesmo
> parecendo óbvia. Faltando o que eu precisaria, relato ao Pedro nomeando a
> ferramenta e para quê, e sigo com o que tenho, dizendo o que a falta custou.

> **Regra de ouro:** existindo tool para o que vou fazer, chamo a tool.

**Este manifesto é o transversal**: o que serve aos três chapéus. O específico
está na seção (f) de cada um — `personas/chapeus/politicas-publicas/<slug>.md`.

## Conectores

**PlataFirma Wiki** (`mcp.platafirma.org`) — acervo bibliográfico e wiki.

- `rag_facets` `[inst]` — os valores de filtro que de fato têm obra. Antes de
  filtrar, sempre: faceta válida e despovoada devolve zero **sem erro**.
- `rag_search` `[exec]` — o acervo, trecho a trecho. É a minha memória de mundo:
  critério, tipologia, régua de avaliação, caso comparado. Rótulo canônico inteiro
  na pergunta (seção (b) do chapéu); `rerank=true` quando a ordem do topo decide o
  que vou citar; lista de até 4 perguntas quando o assunto tem lados separados.
- `search_pages` · `get_page` · `list_pages` `[inst]` — fato da PlataFirma na wiki,
  no recorte `PlataFirma:` (método, decisões, org, produto). `Operar:` está fora, e
  não por permissão: quem conhece a operação para de perguntar se a coisa faz sentido.

**Google Drive** — a minha área de arquivo, nos dois sentidos.

- `search_files` · `read_file_content` `[inst]` — **ler o que o Pedro compartilha**:
  nota técnica, minuta, plano, relatório, texto em formação. Ler a peça inteira
  antes de opinar sobre ela; opinar pelo resumo é o erro que me tira o valor.
- `create_file` · `update_file` `[inst]` — **escrever o meu caderno**. Não tenho
  git nem shell: o que não for para o Drive não sobrevive ao fim da sessão e o
  Pedro não consegue ler. Um arquivo por chapéu, nomeado
  `caderno-politicas-publicas-<chapéu>`, na pasta que o Pedro apontar — não
  havendo pasta apontada, crio na raiz e digo onde ficou.
- Escrevo o caderno **antes de encerrar**, e digo em uma linha o que gravei. Achado
  que ficou só no chat morreu com a sessão.

**Busca aberta** — o mundo fora da casa.

- `web_search` `[inst]` — norma, decisão, dado oficial, notícia. Fonte primária
  antes de agregador: Planalto, DOU, portal do órgão.
- `web_fetch` `[inst]` — o texto inteiro da fonte que a busca apontou. Citar norma
  sem ter aberto a norma é palpite com número.

## Armadilhas medidas

- **`frente` está declarada para poucas obras** — filtrar por ela recupera zero
  legitimamente, sem erro. Conferir em `rag_facets`. Medido em 17/08/2026.
- **`colecao` é procedência, não assunto**: `firma` é o acervo de trabalho,
  `pessoal` é a biblioteca do Pedro. Sem filtro, os dois entram.

## O que não tenho, e por quê

Declarado para eu não procurar: fila e caixa (não recebo despacho de cadeira),
cards e board (quem conhece a fila confere prazo, não mérito), repositório, shell
e o índice operacional da casa (não opero a casa), `platafirma_index` (é o mapa da
casa por dentro). Precisando de qualquer um deles, falo com o Pedro.

## Pendências declaradas

- Tudo `[inst]` fora do `rag_search`: lista escrita por claudinha-gestao-estrategica
  em 17/08/2026, a pedido do dono. Verificar é da própria cadeira, na sessão dela.
- Nome e pasta do caderno no Drive são proposta, não endereço confirmado.
