# b2 — propostas de conceito · capacidade-estatal

Domínio `capacidade-estatal`. Propõe: `claudinho-politicas-publicas`. Slug e
inclusão decididos pelo dono.

Formato conforme `distribuicao/rodada-2/PROMPT-rodada-2.md` (passo 6); definição
conforme `distribuicao/rodada-2/PROMPT-reescrita-slug-definicao.md`.

## Lote

54 obras com `dominio_atual = capacidade-estatal` em
`distribuicao/rodada-1/obras.csv`. O domínio não foi reivindicado na rodada 1:
nenhuma obra do lote aparece em `reivindicacoes/` ou em `conflitos.csv`. Sem
derrota de arbitragem, logo sem réplica.

| bloco | obras | uso |
|---|---|---|
| estudos de caso de sistemas da APF | 10 | lastro principal — lidos na wiki |
| manuais operacionais SIAPE / eSocial / SIASS | 10 | lastro de modelo publicado |
| compliance e controle interno (COSO, ISO 31000) | 9 | provável colisão externa |
| normativos (LAI, 8.112, 8.159, 14.063, INs) | 8 | lastro de forma normativa |
| teoria (APW, Cohen & Levinthal, Scott, Coase, Walsh & Ungson) | 6 | lastro de mecanismo |
| demais | 11 | a triar |

### Instrumento de leitura dos estudos de caso

Os 10 `Estudo de caso: <sistema>` não estão no índice vetorial: três consultas
em ângulos distintos não retornaram nenhum deles. Eles moram na wiki, em
`Frente:paper-capability-trap/case-<sistema>`, e são lidos por `get_page`. As
âncoras marcadas **[wiki]** abaixo foram lidas ali, não no RAG.

A frente tem 14 páginas — as 10 catalogadas mais `case-petrvs`,
`case-reforma-administrativa`, `case-sei` e `referencias`, que não constam de
`obras.csv`.

## Conceitos

### armadilha-de-capacidade

```
rotulo: Armadilha de capacidade
natureza: fenomeno
estatuto: doutrinario
```

**definição.** Um órgão só consegue comprar bem aquilo que já saberia fazer.
Para contratar um sistema, julgar a proposta e cobrar o resultado é preciso
entender do assunto — e é justamente esse entendimento que falta em quem
terceirizou tudo. A saída aparente é contratar mais, e cada contrato afasta o
dia em que o órgão saberia fazer.

O que fecha a armadilha é a competência ausente ser a mesma nos dois lados:
quem não sabe especificar também não sabe reconhecer que especificou mal, então
o órgão não percebe o que está perdendo. Sai-se dela trazendo para dentro quem
já tem a competência, nunca comprando a solução.

- obras-âncora: `84ee87ce-3cb8-4807-8c6e-33171aa8ed6e` (Building State
  Capability), `aa5d0cda-3a60-4f2c-b28f-0a17f2d450c7` (Fichamento: Andrews,
  Pritchett & Woolcock)
- caso falseador: um órgão sem competência técnica interna que, de tanto
  contratar, passe a especificar e avaliar bem — a competência entraria pela
  compra e não haveria fecho.
- pai proposto: —
- substitui: `armadilha-de-capacidade` (base)

Filhos que já declaram este pai na base e continuam válidos sob a régua nova:
`carga-prematura`, `retencao-estrutural`, `titularidade-do-core`.

### titularidade-do-core

```
rotulo: Titularidade do core
natureza: modelo
estatuto: doutrinario
```

**definição.** Todo órgão faz uma coisa que mais ninguém faz — reconhecer um
vínculo de trabalho, lançar um tributo, liquidar um pagamento — e faz muita
coisa que todo mundo faz: folha, protocolo, login. A titularidade do core é a
decisão de qual dessas partes o órgão continua entendendo por dentro, mesmo
quando outro a executa.

Delegar a execução do que é comum não custa nada. O que quebra é entregar a
parte exclusiva sob contrato de escopo fechado: as regras dela ninguém de fora
conhece de antemão, elas se descobrem enquanto o sistema é construído, e quem
descobre é quem fica sabendo. No Pix a separação está de pé — o Banco Central
opera ele mesmo o diretório de chaves e a liquidação, e terceiriza transporte e
execução periférica.

- obras-âncora: `0d146df8-af09-4c5b-8c41-f983b481b407` (Manual do eSocial),
  `2b4a31fd-447a-4a32-a417-33c3ce00cdb4` (Manual de Padrões para Iniciação do
  Pix v2.6.2), `ef1f162c-5ad3-4235-a12a-cf81ae9f2ef4` (Estudo de caso: Pix)
  **[wiki]**
- caso falseador: um órgão que entregue a regra exclusiva sob escopo fechado e,
  encerrado o contrato, saiba especificar e evoluir essa regra tão bem quanto
  quem a construiu.
- pai proposto: `armadilha-de-capacidade`
- substitui: `titularidade-do-core` (base)

### legibilidade-do-sistema

```
rotulo: Legibilidade do sistema
natureza: disposicao
estatuto: doutrinario
```

**definição.** Documentar tudo não é o mesmo que deixar navegável. Um sistema é
legível quando a própria superfície mostra onde uma parte termina e a outra
começa: qual porta dá no mesmo dado que qual outra, o que é tela e o que é base
por baixo. Sem isso, a resposta está lá e ninguém acha — e quem procura conclui
que o problema é ele.

Quem consome um sistema ilegível não extrai o modelo dele por mais que leia.
SIAPE, Sigepe e SouGov são três nomes de camadas de acesso sobre a mesma base
de dados, e nem servidor nem integrador consegue dizer com segurança se são um
ou três: a informação existe e está escrita, o que falta é a superfície
sinalizar a fronteira.

- obras-âncora: `60b18ee3-b1e9-400f-8119-98dbe14560b4` (Estudo de caso: SIGEPE)
  **[wiki]**, `ef1f162c-5ad3-4235-a12a-cf81ae9f2ef4` (Estudo de caso: Pix)
  **[wiki]**
- caso falseador: consumidores que reconstroem o modelo de um sistema cuja
  superfície não sinaliza fronteira nenhuma, na mesma taxa e no mesmo tempo em
  que reconstroem o de um sistema que sinaliza.
- pai proposto: —
- substitui: `legibilidade-do-sistema` (base)

### carga-prematura

```
rotulo: Carga prematura
natureza: fenomeno
estatuto: doutrinario
```

**definição.** A obrigação chega antes do meio de cumpri-la. Liga-se o prazo, a
sanção ou a escala enquanto o instrumento que tornaria o cumprimento possível
ainda está sendo inventado — e quem tem que cumprir descobre isso sozinho. O
estrago não é só a regra descumprida: a estrutura que já funcionava é posta a
carregar peso que não aguenta, e cede.

O sinal costuma estar legível no próprio papel, num instante só: a norma que
obriga e, no mesmo texto, remete a ato futuro o que faria a obrigação
funcionar. Na Rede Nacional de Dados em Saúde o envio virou obrigatório antes
de existir a regulamentação da consequência do descumprimento, e o modelo de
dados seguia sendo corrigido a partir dos erros que apareciam em produção.

- obras-âncora: `84ee87ce-3cb8-4807-8c6e-33171aa8ed6e` (Building State
  Capability), `c66f85c1-d731-4c61-b17b-0f3bf590563e` (Estudo de caso: RNDS)
  **[wiki]**
- caso falseador: uma obrigação ligada antes do instrumento cujo cumprimento se
  dê na mesma taxa e no mesmo prazo que o de obrigação ligada depois — a
  antecipação não faria diferença.
- pai proposto: `armadilha-de-capacidade`
- substitui: `carga-prematura` (base)

### responsabilidade-de-traduzir

```
rotulo: Responsabilidade de traduzir
natureza: modelo
estatuto: doutrinario
```

**definição.** Quando dois sistemas com vocabulários diferentes precisam
conversar, alguém tem que traduzir — e o que decide o resultado é de quem é
esse trabalho. No destino, um time só o faz uma vez, confere o que entra e
devolve erro dizendo o que faltou. Na origem, cada um dos muitos remetentes
traduz por conta própria, e o mais fraco deles define a qualidade do conjunto.

Não se trata de culpa, e sim de onde o trabalho fica — e ele quase sempre é
atribuído por omissão: o centro publica o vocabulário canônico, obriga seu uso
e não diz quem converte. Na Rede Nacional de Dados em Saúde a integração ficou
escrita como responsabilidade do gestor de cada ente, e o indicador da falha se
chama taxa de rejeição, nome que localiza o erro em quem enviou. No Pix e no
login gov.br o trabalho está do outro lado: o centro recebe, confere e responde
com erro nomeado.

- obras-âncora: `c66f85c1-d731-4c61-b17b-0f3bf590563e` (Estudo de caso: RNDS)
  **[wiki]**, `49b89d8c-a8d0-478b-b803-b3819aad0ed1` (Estudo de caso: gov.br)
  **[wiki]**, `ef1f162c-5ad3-4235-a12a-cf81ae9f2ef4` (Estudo de caso: Pix)
  **[wiki]**
- caso falseador: um arranjo em que cada remetente traduz por conta própria e a
  qualidade do dado recebido seja igual à de um arranjo em que o destino traduz
  e valida.
- pai proposto: —
- substitui: `direcao-da-autoridade-semantica` (base)

Slug proposto no lugar do da base: o rótulo antigo não diz de que trata e o
novato não o chuta. A entrada é linkada na wiki sob
`Ontologias/`, e a fronteira com `estudos-ontologias` também é dele.

## Candidatos com uma âncora só

Não propostos — a cota do passo 5 exige duas.

- **`congelamento-por-criticidade`** — o sistema que não pode parar também não
  pode ser reorganizado, então a desordem deixa de ser corrigível e passa a ser
  apenas documentada; documentação abundante vira sintoma da imobilidade, não
  sinal de ordem. Âncora: Estudo de caso: SIGEPE **[wiki]**. Sem segunda
  âncora no corpus da frente.

- **`fronteira-de-versionamento`** — quem muda o contrato de interface e quem
  arca com o custo de acompanhar a mudança é decisão separada de quem executa a
  tradução: o login gov.br acerta a execução e transfere por escrito o
  acompanhamento às pontas. Âncora: Estudo de caso: gov.br **[wiki]**. O próprio
  case rebaixa o eixo a higiene de API; entra como candidato, não como proposta.

## Homônimo fora do acervo

`armadilha-de-competencias` — o *capability trap* de Repenning e Sterman (ASQ
47, 2002): a pressão por resultado de curto prazo consome o esforço que iria
para melhoria e manutenção, a capacidade erode, e a queda de desempenho
aumenta a pressão. Mecanismo distinto do de Andrews, Pritchett e Woolcock, sob
o mesmo nome em inglês. Traduzido na literatura brasileira de gestão de
operações como *armadilha de competências*.

Sem obra no acervo: não cumpre a cota de duas âncoras do passo 5. Slug
reservado, entrada não proposta. Aquisição de Repenning & Sterman (2002)
resolve.

## Colisões vigiadas

Conceitos que ocorrem em `capacidade-estatal` com régua lavrada por outra
cadeira. Não são propostos nem editados aqui:

`governanca-dados` · `lei-de-conway` · `sistemas-distribuidos` ·
`gestao-de-risco` · `gestao-pessoas` · `escalabilidade-sistemas` ·
`extracao-dados`
