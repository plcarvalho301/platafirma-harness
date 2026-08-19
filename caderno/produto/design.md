# caderno de design — cadeira produto

O que continua verdadeiro depois que o assunto morrer, e que a proxima fita pagaria para
re-derivar. Fato de negocio vive em card, commit e wiki; estado de runtime, no instrumento.

## A quebra em largura estreita e do CONTEUDO, nunca de um numero na folha

`@media (max-width: ...)` escreve na folha um ponto de quebra que a varredura de valor cru
recusa — e recusa com razao: e um palpite sobre o aparelho de alguem. A saida ja provada
nesta casa e deixar o layout quebrar por `flex-wrap`, amarrar largura com `100%`/`max-content`
e, para painel sobreposto, usar `anchor-name`/`position-area` com `position-try-fallbacks`
dentro de `@supports` — o motor sabe a largura da janela e vira o painel sozinho.

Custa duas iteracoes descobrir isso do zero: a primeira tentativa erra por media query, a
segunda por ancorar o painel no contentor errado. Ancorar na barra em vez de no gatilho
FUNCIONA e nunca estoura, mas abre o painel debaixo do controle errado — foi visto na tela e
descartado. Nao reabrir.

## `<details>` nativo e o disclosure da casa; `pf-dropdown` nao serve a selecao multipla

`pf-dropdown` espelha `pf-item-menu` e FECHA ao escolher — certo para menu de acao, errado
para selecao multipla, onde marcar quatro opcoes custaria quatro aberturas. `pf-select` tem
`value` escalar e `pf-combobox` e heranca nua do fornecedor.

`<details>`/`<summary>` entrega foco, Enter/Espaco e estado expandido pelo navegador, sem uma
linha de script, e degrada sem JavaScript para lista aberta — nunca para conteudo
inalcancavel. E o mesmo padrao que a lateral da wiki adotou. Duas armadilhas medidas: filho
`position: absolute` ESCAPA do contenimento do `<details>` fechado e precisa de
`:not([open]) > ... { display: none }`; e o `<details>` vem vestido pelo bundle (borda, fundo,
recuo) por cima do que a folha desenha no `summary`.

## A camada `wa-native` do bundle decide espaco que a tela nao pediu

Ela aplica `margin-block-end` a TODO bloco que tenha irmao depois. Um valor so, entre tudo:
titulo e paragrafo separam igual a paragrafo e paragrafo. Foi a causa mecanica do flat do
canal wiki, e reapareceu no rastreador desalinhando em 24px dois controles iguais lado a
lado — o primeiro tinha irmao depois, o ultimo nao. `align-items: end` nao corrige, porque a
margem entra DEPOIS do alinhamento.

Nenhum token de espaco alcanca isso: e regra de terceiro, e se desfaz declarando. Ao ver
espaco vertical que nenhuma folha da tela explica, ou dois irmaos identicos desalinhados,
procurar aqui antes de procurar na propria folha.

## Esconder implicito nao e esconder

`[hidden]` do user-agent e so `display: none`, e qualquer regra de autor com `display` o
derrota. Classe com `display: flex` mais atributo `hidden` = elemento visivel, sem erro em
lugar nenhum. Vale para toda classe que ganhe `display`; a que escapa, escapa por acaso.
Mesma familia do `<details>` acima: os dois sao um esconder que a folha desfez sem dizer.

## O painel sobreposto e o unico degrau de elevacao que uma tela de trabalho gasta

Layer-2 para o que sai do fluxo; controle que permanece no fluxo NAO ganha fundo nem sombra,
senao passa a competir com o conteudo — numa tela de cartoes, o cartao e o conteudo. Barra de
controle separa do quadro por espaco e um fio, e so.

## `pf-select` reconstroi o listbox por `MutationObserver`; mutar sem necessidade demole o
## combobox no instante em que ele fecha

O componente espelha o light DOM para dentro do shadow, e o espelhamento faz
`interno.replaceChildren()` do listbox inteiro a cada mutacao — nao um patch. Redesenhar as
`<pf-opcao>` a cada projecao (rotulo com contagem, por exemplo) sem checar se o CONTEUDO
mudou faz o combobox nascer de novo bem no momento em que a escolha deveria fecha-lo: o
sintoma na tela e "o seletor agarra, nao fecha nunca" — e nao e o `<details>` que agarra, e
sim um elemento novo nascendo aberto a cada clique. Guardar uma assinatura do conteudo
(`dataset.assinatura`) e so mutar quando ela muda resolve sem tocar no fornecedor.

Vale para qualquer primitivo desta biblioteca que espelhe filhos por observer: o mesmo
padrao pode repetir em `pf-combobox` e em qualquer outro que reuse `_composicao.js`.

## `pf-dialogo` expõe `close-button` como `part`; escondê-lo é CSS, não prop nova

Nao ha atributo para tirar so o X mantendo o titulo (`without-header` esconde os dois
juntos). Como o embrulho e por HERANCA (nao composicao), a parte do fornecedor atravessa
direto: `#meu-dialogo::part(close-button) { display: none; }` funciona sem escrever
componente novo. Serve para todo dialogo cujo cancelamento tem consequencia e nao deve
oferecer uma saida muda no canto.

## `pf-dialogo` reabrir logo apos fechar entrega caixa de altura zero

O fornecimento tem animacao de fecho (`Dialogo`, herdado do fornecedor): `dialog.open = false`
nao e instantaneo. Reabrir o MESMO `pf-dialogo` — ou disparar o gesto que o reabre — antes de o
fecho terminar faz o campo interno nascer com `getBoundingClientRect()` de altura zero; qualquer
automacao que clique nele (Puppeteer inclusive) recusa com "Node is either not clickable".
Esperar `pf-dialogo-fechou` nao bastou sozinho: o corpo do dialogo ainda reconstroi depois do
evento. Contornado esperando o evento E um atraso fixo depois dele, ou — mais robusto — usando
uma pagina/instancia nova por abertura em vez de reabrir a mesma. Vale para qualquer script que
dispare aberturas em sequencia rapida do mesmo `pf-dialogo`, nao so em prova.
