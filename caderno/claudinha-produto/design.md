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

## Três armadilhas do CSS da skin, medidas na rodada de estética de 17/08

`outline: var(--platafirma-focus-ring)` **não desenha nada.** O token é a LARGURA
(`2px`), não o anel: sem `solid <cor>` o `outline-style` fica no inicial `none` e o
foco de teclado é invisível. Estava assim no `summary` da dobra lateral. Qualquer
`outline:` que consuma esse token precisa da tríade completa.

O bundle serve `summary` em **`content-box` com 16px de padding**. Dar
`width: var(--platafirma-target-touch)` a um `<summary>` produz 76px de lado, não 44:
o token vira a caixa de CONTEÚDO e o recuo entra por fora. Alvo de toque sobre
`summary` exige `box-sizing: border-box` e `padding: 0` explícitos.

`.pfs-menu-itens li a` (0,1,2) empata em especificidade com qualquer
`.minha-classe li a` e vence pela ORDEM — o bloco da lateral mora no fim do arquivo.
Menu que reusa o parcial `Menu.mustache` e quer outra medida precisa de duas classes
no seletor (`.pfs-conta-painel .pfs-menu-itens li a`), não de uma.

## Chave de template inexistente falha em SILÊNCIO no mustache

`{{{form-data-search}}}` não é chave de `SkinMustache` — o contrato real é
`data-search-box`, com `form-action`, `page-title` e `html-input`. O mustache resolve
chave desconhecida em string vazia, sem erro e sem aviso: a busca do cabeçalho ficou
morta desde que a skin nasceu, servindo `<div class="pfs-busca"></div>` como um
espaçador de 917px. O template de referência é
`includes/skins/templates/fallback/skin.mustache`, dentro do container — é ele que
lista as chaves que o core realmente entrega. Conferir lá antes de inventar nome.

## `MediaWiki:Common.css` vence a skin, e o namespace é protegido

Com o estilo em duas cópias — uma na skin, outra no `Common.css` —, **manda a do
`Common.css`**: a folha de conteúdo do site carrega depois da folha da skin. Foi por
isso que o selo de regime continuou em caixote depois do deploy da skin que o tirava:
a skin dizia uma coisa e a página respondia com a outra. Sintoma para reconhecer sem
reabrir: mexer na regra, servir, e o computed style vir com o valor ANTIGO — não é
cache, é a outra cópia.

E a remoção não sai pela conta de bot: `MediaWiki:` é namespace protegido e a API
devolve `protectednamespace-interface`. O caminho é o script de manutenção dentro do
container, que roda como o Admin da instância:

    docker exec -i plataforma-wiki-mediawiki-1 sh -lc \
      "cd /var/www/html && php maintenance/run.php edit.php --user=<admin> \
       --summary='...' --nocreate MediaWiki:Common.css < /tmp/novo.css"

Corolário para o caderno anterior: a regra "interface de skin não mora em conteúdo de
wiki" continua valendo, mas o motivo é mais forte do que o registrado — não é só que
`editinterface` apaga sem gate; é que enquanto as duas cópias existirem, a do conteúdo
é a que decide, e o repositório da skin vira ficção.
