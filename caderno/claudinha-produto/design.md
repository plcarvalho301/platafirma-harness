# caderno — claudinha-produto / design

## MediaWiki `SkinMustache` não expõe categorias por padrão

`SkinMustache::getTemplateData()` não inclui `html-catlinks`. Quem preenchia essa chave
era `SkinTemplate` (a classe-mãe mais antiga), e uma skin baseada em `SkinMustache` não
herda esse comportamento automaticamente. Se a página categoriza e o template não
referencia `{{{html-catlinks}}}`, o bloco de categorias não existe no HTML — não é
questão de CSS ou de estilo faltando, é ausência real na saída do parser.

Sintoma para reconhecer isto de novo, sem reabrir a investigação: buscar a string
`catlinks` no HTML servido de uma página categorizada e não achar nenhuma ocorrência.

Conserto: `$data['html-catlinks'] = $this->getCategories();` na subclasse da skin, mais
a referência no template mustache. Vale para qualquer skin PlataFirma futura que troque
de `SkinMustache` e herde este ponto cego de novo.

## O corpo do artigo, no HTML servido, é NETO da `.pfs-texto`, não filho

O parser do MediaWiki embrulha a saída renderizada numa `<div class="mw-parser-output">`
dentro do `#mw-content-text`, que por sua vez está dentro do que a skin nomear (aqui,
`.pfs-texto`). Qualquer seletor CSS que precise pegar "os blocos de topo do artigo" tem
de mirar `.pfs-texto .mw-parser-output > *`, e não `.pfs-texto > *` — o segundo pega o
wrapper inteiro como um bloco só, e nenhuma regra de irmão (`* + *`) dispara dentro dele.
Isso vale para qualquer skin PlataFirma sobre MediaWiki, não só para o ritmo de espaço do
#242: título de página, largura de coluna, qualquer coisa que precise mirar o conteúdo do
artigo e não o wrapper.

## Interface de skin não pode morar em conteúdo de wiki (`MediaWiki:Common.css`)

Qualquer conta com a permissão `editinterface` edita páginas do namespace `MediaWiki:`
sem gate, sem sign-off, sem passar pelo fluxo de merge da skin. Regra de decisão: CSS
que afeta a CASCA da skin (não o conteúdo do artigo) mora no repositório da skin
(`skin-platafirma/resources/`), nunca em `Common.css`. `Common.css` é para estilo que
o EDITOR de conteúdo precisa poder ajustar sem passar por deploy — classes que a prosa
usa (`.platafirma-chip`, `.platafirma-nota`), não elementos que a skin gera sozinha.
O selo de regime de leitura (`.pf-marca`) tinha ficado do lado errado dessa linha; motivo
descoberto em 17/08/2026 no #242, ao medir o aceite "selo não muda de degrau".
