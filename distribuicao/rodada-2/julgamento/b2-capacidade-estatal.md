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

## Candidatos com uma âncora só

Não propostos — a cota do passo 5 exige duas.

- **`congelamento-por-criticidade`** — o sistema que não pode parar também não
  pode ser reorganizado, então a desordem deixa de ser corrigível e passa a ser
  apenas documentada; documentação abundante vira sintoma da imobilidade, não
  sinal de ordem. Âncora: Estudo de caso: SIGEPE **[wiki]**. Segunda âncora a
  procurar em SPED, Urna ou Estaleiro.

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
