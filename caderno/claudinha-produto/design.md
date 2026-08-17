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

## O que fica e o que sai do `MediaWiki:Common.css` — critério e resultado da varredura

Critério, do #242: `Common.css` é para o estilo que o **editor de conteúdo** precisa
ajustar sem deploy, ou seja, as classes que a prosa escreve no wikitexto. O que a skin
gera sozinha mora no repositório dela, onde passa por merge.

Varredura de 17/08/2026, 292 linhas. **Saíram** (110 linhas):

- ponte do vocabulário Codex (`--color-*`, `--background-color-*`, `--border-color-*`) —
  estava em duas cópias; a da skin (`html.platafirma-tema-*`, 0-1-1) já vencia a daqui
  (`:root`, 0-1-0), então a cópia só dava a impressão de que este arquivo mandava
- `margin-top` fixo em `h2`/`h3`/`h4` — segunda fonte para o ritmo que o #242 tinha
  passado a calcular por relação entre irmãos, na skin. O `font-size` ficou: escala
  tipográfica da prosa é conteúdo
- `.subpages` — gerada pela skin dentro do `html-subtitle`, nunca escrita por wikitexto

**Ficaram:** prosa dentro de `.mw-parser-output` (corpo, `dl`, `pre`), tabela
(`.wikitable` e variantes) e os componentes `platafirma-chip`, `-cartao`, `-linha`,
`-nota`, `-grade`. Todos são classe que o editor escreve.

Prova de que o corte foi mesmo redundância, e não mudança disfarçada: computed
`margin-top` e `font-size` de `h2/h3/h4/p/ul/dl/pre/table` medidos em cinco páginas
antes e depois, **zero diferença**; e `--color-base`, `--background-color-base`,
`--border-color-base`, `--color-progressive` continuam resolvendo em `action=edit`,
`Especial:` e artigo. Esse par de medidas é o teste de regressão para a próxima
varredura.

## Três valores CRUS do SkinModule desenham a escada do corpo por cima da nossa

A ponte de token no topo do `tela.css` cobre o vocabulário Codex (`--color-*`), e por
isso é fácil supor que ela cobre tudo. Não cobre o corpo do artigo. As *features* do
`SkinModule` ligadas no `skin.json` compilam LESS em valor fixo, e três desses valores
mandavam na hierarquia da prosa sem passar por token nenhum. Medidos em 17/08/2026 com
`platafirma-arquitetura/design/wireframes/medir-wiki.mjs`:

- `elements` dá `border-bottom: 1px solid #aaa` ao `<h1>` **e** ao `<h2>`. Cinza morto
  fora da paleta, e o MESMO marcador gráfico em dois níveis: título de página e seção
  de artigo empatavam na única régua da tela. A mesma feature dá ao `<h1>` um recuo
  assimétrico — 16px em cima, 5,44 embaixo.
- `content-links` compila o wikilink em `#0645ad`, o azul do MediaWiki. Contra a
  superfície branca mede **8,5:1** — o ponto mais saturado da página inteira, e ele
  pertence ao nível MAIS BAIXO da hierarquia. O olho ia ao link antes do título da
  seção. `--color-link` da ponte não alcança: quem pinta o link do corpo é a feature.
- O bundle serve lista em `0.95em`, então `<li>` saía com 14,25px contra os 15px do
  parágrafo — o rés-do-chão da escada invertido.

Sintoma para reconhecer sem reabrir: computed style com cor ou medida que não bate com
nenhum `--platafirma-*`, e nenhuma regra nossa casando com o seletor. Antes de culpar
cascata, procurar a feature no `skin.json`.

## O piso de percepção do fio, e o degrau que falta no design system

`--platafirma-border-default` mede **1,30:1** contra a superfície branca, e
`bg-sunken` contra `bg-page` mede **1,045:1** — os dois abaixo do limiar. É a causa
mecânica do "a página inteira parece lavada": o fio que deveria dizer onde o cartão
começa não existe, e a lateral flutua sobre uma página do mesmo cinza.

Régua para não rediscutir: limite gráfico que transmite informação — e agrupar é
informação — pede **3:1** (WCAG 1.4.11). O degrau seguinte, `border-strong`, mede 5:1
e é traço duro demais para contornar cartão inteiro. **Não existe degrau entre os
dois**, e é essa a lacuna do design system.

Correção medida em detalhe importante do aceite 7 do #242: aquele aceite dizia que
fundo recuado separava a lateral do conteúdo, e contra a SURFACE branca ele separa
mesmo. O que não foi medido na época é que a lateral não flutua sobre a surface — ela
flutua sobre a PÁGINA, e ali não separa nada. A régua §d manda parar no primeiro
mecanismo que separa; quando o mecanismo escolhido não separa, ele não é o mecanismo.

## Reproduzir defeito de skin: apagar a regra em runtime, não adivinhar a causa

Quando o dono relata uma tela que a máquina não reproduz, `deleteRule` no puppeteer
diz se a hipótese "falta a regra X" fecha, sem tocar em arquivo nem em deploy:

    for (const f of document.styleSheets) { let rs; try { rs = f.cssRules } catch { continue }
      for (let i = rs.length - 1; i >= 0; i--)
        if (rs[i].type === 1 && /minha-classe/.test(rs[i].selectorText || '')) f.deleteRule(i) }

Foi assim que o "ícone virou caixa branca" fechou em 17/08: sem as regras
`.pfs-conta-botao`, o `<summary>` cai em 68x52 com `list-style-type: disclosure-open`
— e é esse marcador nativo o "chevron" que aparecia no lugar da cabecinha. Como o CSS
servido TINHA a regra e o `.pfs-conta-painel` da captura já era o novo, a conclusão é
HTML antigo com CSS novo: cache de borda de página anônima, não a skin.

## Upload por Action API falha em `WrongToken` quando o curl fala HTTP

O manifesto manda subir imagem por `curl` + Action API da própria máquina, e a razão
continua válida (os bytes não atravessam a saída do modelo). Mas com `$wgServer` em
`https://` os cookies de sessão saem `Secure`, e o curl contra `http://127.0.0.1:8080`
com header `Host:` não os reenvia — o login responde `WrongToken` e o upload responde
`mustbeloggedin`. Rota que funciona sem sessão nenhuma:

    docker cp /tmp/pfimg plataforma-wiki-mediawiki-1:/tmp/pfimg
    docker exec plataforma-wiki-mediawiki-1 sh -lc "cd /var/www/html && \
      php maintenance/run.php importImages.php --user='<admin>' --comment='...' --overwrite /tmp/pfimg"

Continua valendo conferir a MINIATURA depois (`prop=imageinfo&iiurlwidth=900`), e não
o resultado do upload: `Added: 2` não prova que a página renderiza.
