---
name: diagrama
description: "Use SEMPRE que o dono, uma story ou você mesmo for desenhar ou refazer uma figura de arquitetura (camadas, módulos, o que roda e como conversa, onde roda, como algo anda passo a passo), mesmo que ache que consegue desenhar à mão. Siga ANTES de escrever qualquer fonte de figura ou de abrir um editor de desenho. NÃO dispare para gráfico de dado, para figura que se regenera de um dado, para ilustração de página nem para desenho de tela."
---

# Diagrama

## O que aciona

Use SEMPRE que o dono, uma story ou você mesmo for desenhar ou refazer uma figura de arquitetura, mesmo que ache que consegue desenhar à mão. Siga ANTES de escrever qualquer fonte de figura ou de abrir um editor de desenho. NÃO dispare para gráfico de dado (série, barra), para figura que sai de um dado e se regenera sozinha, para ilustração de página nem para desenho de tela. Quando o fluxo tem menos de três passos e nenhum ramo, escreva uma lista numerada.

## O que dispara

Desenhar a figura em cinco passos. Uma peça de código, a peça diagrama, faz a conferência e a renderização; você escreve o plano e a fonte e conta as voltas.

Toda chamada da peça vai pela porta, no verbo `infra`, ato `rodar`, com os argumentos `diagrama -- <ato> <caminhos>`. A peça roda no host e só acha arquivo por caminho absoluto. Grave o plano e a fonte com a escrita de arquivo da porta (`write_file`) no rascunho da fita, `/srv/platafirma/casa/var/tmp/<ordem_id>/`, com o `ordem_id` que a abertura da sessão devolveu. Os esquemas e os exemplos moram no repositório platafirma-harness, em `skills/diagrama/`, e se leem pelo verbo `repo`, ato `ler`.

1. **Planejar.** Escreva o plano em JSON, no esquema `plano.schema.json`: a pergunta que a figura responde, o pedido com as palavras de quem pediu, o leitor, o tipo de figura (`camada`, `modulo`, `componente-e-conector`, `alocacao` ou `fluxo`), o caminho de cada documento da fonte, as entidades e as relações. Entidade só entra com o documento que a sustenta, e relação só entra com nome. Cada tipo tem um plano de exemplo em `exemplo/`. Rode `infra rodar diagrama -- conferir-plano <plano>`: o lint recusa o que código mede, e só depois o auditor julga se o plano cobre o pedido. Saída 0 segue. Saída 1 traz a lista do que corrigir. O mesmo plano reprovado duas vezes encerra o passo.
2. **Produzir.** Escreva a fonte em JSON, no esquema `fonte.schema.json`, com as mesmas entidades e relações. A peça desenha pela grade, e quem diz onde cada caixa fica é você: declare as `faixas`, de cima para baixo, e dê a cada caixa a `faixa`, a `coluna` (contada da esquerda, a partir de 1) e a `ordem` (a posição dentro da célula, de cima para baixo); `colunas` estende a caixa por mais de uma coluna. Cada zona ganha a `faixa` que ocupa. A seta pode levar `sai` e `chega`, o lado da caixa por onde passa. A caixa sem faixa, coluna ou ordem, ou duas caixas na mesma célula, fazem a peça recusar a fonte e nomear a caixa. Rode `infra rodar diagrama -- renderizar <fonte> --saida <rascunho>`: saem o caminho do SVG e o do PNG, com 760 px de largura. Quando um rótulo não acha lugar, a peça diz qual: mude a coluna, a ordem ou o lado, ou encurte o rótulo.
3. **Ver e criticar.** Rode `infra rodar diagrama -- conferir-figura <plano> <svg> <png>`. A checagem estrutural vem primeiro e devolve cada defeito com o elemento; depois o crítico marca cada defeito como de conteúdo (volta ao passo 1) ou de forma (volta ao passo 2). O ciclo para quando passa de três voltas ou quando o crítico repete o mesmo defeito em duas voltas seguidas.
4. **Entregar ao dono.** Entregue o PNG, o plano, os defeitos que sobraram e a pergunta que a figura responde, só aqui, depois do último veredito ou, quando um juiz não rodou, da última chamada. Como o PNG chega à tela do dono depende da superfície: no **claude.ai**, `ler_arquivo` exibe a imagem apenas para a sessão — envie o PNG ao dono com `SendUserFile`; nas demais superfícies (como **agy** e **Claude Code**), abra-o uma vez com a leitura de arquivo da porta (`ler_arquivo`) e informe o caminho do PNG. A correção dele se escreve no plano, e o ciclo recomeça do passo 1.
5. **Gravar a figura.** Na pasta da figura entram três arquivos, e só eles: o texto (`<data>-<slug>.md`), o plano (`<data>-<slug>.plano.json`) e a fonte (`<data>-<slug>.fonte.json`). O SVG e o PNG ficam no rascunho e não entram no repositório da casa, porque o desenho sai da fonte sempre que alguém o pede (ordem do dono, 16/11/2026). Para refazer uma figura gravada, mude a fonte ao lado do texto e rode `renderizar` de novo; o ciclo recomeça do passo 1.

Saída 3 ou 5 em qualquer chamada quer dizer que não deu para olhar: rode de novo, e isso não vale como veredito. Se a mesma chamada sair 3 ou 5 duas vezes seguidas, registre o defeito da peça e siga sem aquele juiz até a entrega, dizendo ao dono qual juiz faltou: a figura sem veredito não se chama de conferida, mas se entrega.

## O que você não faz

- **Não abra o PNG antes da entrega.** Quem desenha não julga o próprio desenho, e cada imagem lida fica na janela até o fim da fita. O crítico abre o PNG; você recebe a lista de defeitos em texto.
- **Não abra figura da galeria.** Exemplo no contexto ancora o desenho. Quem escolhe e baixa a galeria é `conferir-figura`.
- **Não escreva código que a peça execute.** A fonte é dado no esquema, e a peça a traduz; rodar no host código escrito pelo modelo abre execução arbitrária.
- **Não chame os juízes direto.** `conferir-plano` e `conferir-figura` garantem a ordem: o lint antes do auditor, a checagem antes do crítico.

## Os tipos de figura

| Tipo | Responde |
|---|---|
| `camada` | quem usa o quê, na ordem de baixo para cima |
| `modulo` | como o código se divide |
| `componente-e-conector` | o que roda e como conversa |
| `alocacao` | onde cada coisa roda, ou quem responde por cada parte |
| `fluxo` | como algo anda, passo a passo, com ramo e volta |

Uma figura responde uma pergunta só. Duas perguntas são dois planos. O desenho que põe um fluxo em cima e, em faixas embaixo, o que o sustenta responde duas: faça o plano do fluxo e outro do tipo que responde a segunda, em geral `alocacao` ou `camada`.

O plano usa até quatro categorias técnicas por figura, e a caixa de cadeira (ator) leva a cor de cadeira, em outra dimensão. Categoria é só de componente técnico: a caixa de negócio, como capacidade ou processo, vai sem categoria e sai neutra.

No fluxo, o `tipo` de cada entidade é a forma, e cada forma tem um sentido só:

| `tipo` | forma | regra que o lint cobra |
|---|---|---|
| `inicio`, `fim` | elipse | só na ponta: o início não recebe seta e o fim não solta |
| `passo` | retângulo arredondado | tem saída |
| `decisao` | losango | o nome é pergunta, com duas saídas ou mais, cada uma com rótulo próprio |
| `coisa` | retângulo | nenhuma |

As zonas do fluxo são raias. Todo tipo de figura sai pela grade, sem PlantUML nem Graphviz.

O tracejado diz camada: use `"tracejada": true` na seta, na caixa ou na zona só quando a ligação ou o grupo é de outra camada e isso diz algo ao leitor. A seta tracejada pode ir sem rótulo; a cheia, não. A seta pode sair de uma zona inteira, quando qualquer caixa dela faz a mesma ligação. Nenhuma caixa leva ícone ou glifo: o tipo vai escrito no rótulo.
