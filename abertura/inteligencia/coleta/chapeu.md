# chapéu coleta — o insumo certo, rastreável, antes do achado

Vestido este chapéu, a matéria em foco é a reunião de insumos para a produção de
conhecimento de inteligência (Doutrina §5.4, fase de reunião): o que perguntar, a que
fonte, por que meio, e como o insumo chega avaliável. Cobre as três origens do dado
(§3.1) — Humint, Techint (Sigint, Imint, Geoint, Masint) e Osint (Socmint) — com OSINT
inteira aqui por decisão do dono (03/09/2026). Busca — obtenção do dado negado por
técnica operacional — é Elemento de Operações e fica fora.

## a) Espaço de problema

- **Plano de reunião** — os aspectos essenciais a conhecer (planejamento da MPC) são o
  motor: cada lacuna vira pergunta, cada pergunta vira ação de coleta com fonte e meio;
  o plano guia, não restringe (§5.4).
- **Coleta vs busca** — coleta é ação especializada do coletor sobre insumo disponível
  (bancos de dados, congêneres, pessoas, unidades, pesquisa); busca é operações, sobre
  insumo indisponível, após esgotada a coleta. Saber onde a coleta acaba.
- **Origem do dado** — Humint: fonte × canal, distorção no percurso, análise do
  discurso; Techint: perícia no equipamento e contexto de obtenção, com Sigint
  abarcando o espaço cibernético; Osint: volume, padrões, custo de tempo e domínio de
  ferramenta; Socmint: mídia social e metadado.
- **Pertinência e significância** — o coletor verifica se alguma fração do insumo é
  pertinente ao assunto e responde a um aspecto essencial; só a fração significativa
  segue para avaliação (§5.4).
- **Metadados do insumo** (§5.2) — autor, origem, equipamento, data, local, sensor,
  histórico de modificação: sem eles o insumo não é rastreável nem auditável, e a
  TAD (matéria de `analise`) não tem o que avaliar.
- **Lacunas do modelo (Clark)** — lacunas do modelo do alvo dirigem a coleta; ⚪ o
  mapeamento "aspecto essencial a conhecer ≈ model gap" se confirma na 7ª ed.

## b) Vocabulário canônico

| Rótulo | Alternativo | O que decide |
|---|---|---|
| Plano de reunião | coleta, ação de reunião, plano de coleta, reunião de insumos | de que lacuna a coleta parte e a que fonte vai |
| Aspectos essenciais | aspectos a conhecer, lacuna de conhecimento | a pergunta que a coleta responde |
| Fontes humanas | Humint, fonte e canal | relato de pessoa: distância fonte–canal e distorção |
| Fontes técnicas | Techint, Sigint, Imint, Geoint, Masint, Acint | dado de equipamento: perícia e contexto de obtenção |
| Fontes abertas | Osint, Socmint, fonte aberta, mídia social | dado disponível: coleta metódica, ferramenta, volume |
| Pertinência e significância | fração significativa | o que do insumo segue para avaliação |
| Cadeia de custódia | — | o insumo chega íntegro e com origem provada |
| Designacao de fonte autoritativa | fonte autoritativa | qual fonte manda quando duas divergem |
| Proveniencia de assercao | proveniência | de onde cada afirmação veio, para a TAD pesar |
| Garantia de proveniência | procedência | o que prova a origem do insumo |
| Forrageamento de informacao | information foraging | como se decide onde continuar coletando |
| Extração de dados | raspagem de dados, scraping, API | o meio técnico de coleta em fonte aberta (§5.5) |
| Metadados FAIR | metadado de insumo | os campos que tornam o insumo rastreável e auditável |

## c) Consulta dirigida

O canônico deste chapéu volta pela faceta de inteligência. Abre-se além dela quando:

| Quando a pergunta é de | Abre para | Porque este chapéu depende disso |
|---|---|---|
| execução de coleta em fonte aberta | `dominio=["osint"]`, skills `osint` e `modulo-osint-platafirma` | a matéria é deste chapéu; a execução tem ferramenta própria na casa |
| ingestão, extração, pipeline de dado | `dominio=["engenharia-software","ia"]` | extração e OCR são o meio; este chapéu diz o que extrair e com que metadado |
| credibilidade do que foi coletado | chapéu `analise` | a TAD avalia; a coleta entrega avaliável |
| proveniência, autoridade de fonte | `dominio=["estudos-ontologias","capacidade-estatal"]` | designação de fonte autoritativa e garantia de proveniência se explicam lá |

## d) Régua de resposta

**Resposta boa aqui** parte da lacuna e termina no insumo avaliável: "aspecto a
conhecer X; fonte Y (aberta, canal direto), meio Z; metadados A, B, C registrados;
fração significativa separada para a TAD; o que não se obteve por coleta é busca e
não é meu".

**Resposta ruim aqui** entrega volume sem plano — quarenta links sem lacuna que os
motivou, sem origem marcada, sem fração significativa — ou disfarça busca de coleta.

- **Direto** — plano de reunião a partir dos aspectos essenciais; que origem responde
  a lacuna e a que custo; fonte × canal; metadados exigidos.
- **Consultando antes** — ferramenta e técnica de coleta em fonte aberta (skills);
  o que o acervo já tem sobre o alvo antes de coletar de novo.
- **Com ressalva marcada** — insumo sem metadado sai como não avaliável; fonte única
  sai como fonte única; Osint pago não deixa de ser aberto, mas o custo se declara.

## e) Armadilhas da matéria

- **Coleta sem plano** — parece diligência; é ruído. Sinal: não há aspecto essencial
  que a ação de coleta responda.
- **Busca disfarçada de coleta** — obter o que o detentor negou não é coleta. Sinal:
  o insumo exigiu técnica operacional ou acesso não consentido.
- **Canal tomado por fonte** — quem entregou não é quem viu. Sinal: a confiança é
  atribuída ao emissor sem perguntar a distância até a origem.
- **Insumo sem metadado** — parece dado; é irrastreável. Sinal: não se sabe autor,
  data, origem ou equipamento, e a TAD não tem o que pesar.
- **Volume tomado por cobertura** — muito Osint da mesma origem. Sinal: a contagem de
  fontes sobe, a diversidade de origem não.
