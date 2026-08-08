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
| estudos de caso de sistemas da APF | 10 | não recuperáveis — ver abaixo |
| manuais operacionais SIAPE / eSocial / SIASS | 10 | lastro principal |
| compliance e controle interno (COSO, ISO 31000) | 9 | provável colisão externa |
| normativos (LAI, 8.112, 8.159, 14.063, INs) | 8 | lastro de forma normativa |
| teoria (APW, Cohen & Levinthal, Scott, Coase, Walsh & Ungson) | 6 | lastro de mecanismo |
| demais | 11 | a triar |

### Obras não recuperáveis

Os 10 `Estudo de caso: <sistema>` — CadÚnico, Caixa Tem, CAR/SICAR, Estaleiro,
gov.br, Pix, RNDS, SIGEPE, SPED, Urna. Catalogados em `obras.csv`, ausentes do
índice: três consultas em ângulos distintos (arranjo de pagamentos; por que o
Pix funcionou; cadastro único) não retornaram nenhum deles, e trouxeram no lugar
o Manual de Padrões do Pix, o Decreto 10.046/2019 e o Manual do eSocial.

Não servem de âncora enquanto não forem ingeridos.

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
descobre é quem fica sabendo. O eSocial mostra a separação de pé — o leiaute
dos eventos e as regras de vínculo são dos órgãos que o compõem, e o Serpro
opera o ambiente que os recebe.

- obras-âncora: `0d146df8-af09-4c5b-8c41-f983b481b407` (Manual do eSocial),
  `2b4a31fd-447a-4a32-a417-33c3ce00cdb4` (Manual de Padrões para Iniciação do
  Pix v2.6.2)
- caso falseador: um órgão que entregue a regra exclusiva sob escopo fechado e,
  encerrado o contrato, saiba especificar e evoluir essa regra tão bem quanto
  quem a construiu.
- pai proposto: `armadilha-de-capacidade`
- substitui: `titularidade-do-core` (base)

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
