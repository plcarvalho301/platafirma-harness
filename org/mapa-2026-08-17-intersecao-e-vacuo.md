# Mapa de interseção e vácuo — cruzamento das 7 respostas de escopo positivo

Data: 2026-08-17 · Autora: claudinha-gestao-estrategica (head, slug `estrategia`) · Ref: #189

Fecha o item que a rodada deixou em aberto desde 16/08: as sete cadeiras responderam o
escopo positivo por gerência olhando cada uma para si, e o cruzamento é meu. Isto **não
é decisão** — sobreposição se resolve com o dono da matéria, e as três decisões do fim
são do dono.

**Viés declarado.** Sou a demandante, a respondente e a cruzadora desta rodada. As outras
seis escreveram para um julgamento que não era delas. A mitigação é a régua aplicada
contra o meu próprio interesse: o item S-2 abaixo é uma sobreposição em que a parte que
opera sem régua sou eu, e ela foi escrita depois de eu ter cometido o ato.

## 1. Régua do cruzamento

`arq:0059` (17/08/2026): **uma capacidade existe uma única vez na organização inteira.**
É a régua de sobreposição, e ela chegou tarde de propósito — o arquiteto a registrou no
mesmo dia em que a rodada mediu que ela decidia em org chart e em compra sem estar
escrita em lugar nenhum.

Consequência para este mapa, e é o que separa achado de ruído:

- **Execução repartida não é sobreposição.** Duas cadeiras executando partes do mesmo ato
  são uma capacidade com execução declarada — já é o caso de `dados`, `integracao` e
  `resiliencia` em `org/fronteiras.md`.
- **Sobreposição é a mesma capacidade em duas unidades, ou sob dois nomes.**
- **Vácuo é capacidade sem unidade.** Não é tarefa sem executor: é pergunta que, feita
  hoje, não tem a quem ser feita.

## 2. O quadro que saiu da rodada

Sete respostas, todas validadas pelo dono entre 16 e 17/08. Vinte e um chapéus de matéria
e **seis modos de cadeira**.

| Cadeira | Chapéus | MODO da cadeira |
|---|---|---|
| arquiteto | negocio · plano-dados · stack · dominio (latente) | — |
| dados | ontologia · conhecimento · dados-como-produto | modelagem |
| IA | agente · contexto · harness | inferencia |
| TI | plataforma · release · construcao | observabilidade |
| segurança | iam · privacidade · blueteam · cripto | risco |
| produto | design · canais | produtizacao |
| gestão estratégica | portfolio · rh · secretaria (hipótese) | lente de carteira |

**O achado transversal da rodada** é este: cinco cadeiras, sem se falarem, acharam o mesmo
tipo de coisa — uma gerência de organograma cuja régua era a POSTURA da base palavra por
palavra. Nenhuma tinha ido derrubá-la antes porque nenhuma pergunta chegava endereçada a
ela. Já é regra: `org:0017`, em `platafirma-arquitetura@docs/org-regras.md`.

## 3. Sobreposições vivas

### S-1 · `arquiteto:dominio` × `dados:ontologia` — a mesma pergunta, dois donos

**O que colide.** `dominio` decide «onde o significado muda de dono»; `ontologia` decide
«entidades, relações, cardinalidade, identidade, glossário canônico». As duas respondem
"o que esta coisa é, e quem manda no nome dela".

**Corte proposto, e ele passa no teste de caso ocorrido.** A colisão
`gestao-de-incidentes` (raiz, ramo segurança) × `gestao-de-incidente` (filho de
`servico-de-ti`, ramo ITSM), achada por claudinho-TI em 17/08, foi resolvida por
claudinho-dados no mesmo dia (`platafirma-conhecimento` 3738912, decisão do dono). Nenhuma
linha do arquiteto foi necessária. Isso é o corte:

- **dados** — o critério de identidade da entidade e o nome canônico dela. Duas subárvores
  disputando o mesmo assunto é matéria de `ontologia`.
- **arquiteto** — qual **contexto** detém o significado quando dois contextos disputam a
  mesma entidade, e onde se põe a anticorrupção. É `arq:0012`, e é o caso que nenhuma
  cadeira sozinha decidia.

**Por que não é urgente.** `dominio` é chapéu **latente**: o gatilho é a internalização do
primeiro módulo, e nada de fora foi internalizado. O vazio é exógeno — não é medida da
função, é medida de que a ocasião não chegou. Enquanto não disparar, a matéria roda em
`ontologia` sem disputa.

### S-2 · `gestao-estrategica:rh` × `arq:0059` — quem autoriza a unidade a existir

**O que colide.** `rh` escreve e mantém persona, gerência e fronteira. `arq:0059` diz que
unidade organizacional nova — cadeira **ou gerência** — se justifica por capacidade do
mapa, e que capacidade já coberta é razão de **não** criar.

**Não é disputa de território, é uma régua que eu não estava aplicando.** Em 17/08 eu
dispensei três gerências e designei duas (`personas/eventos-org.jsonl`, cinco eventos
`ALTERACAO_FUNCAO`; harness a7bdb38) **sem passar nenhuma delas pelo mapa de
capacidades**. O resultado provavelmente está certo — as cadeiras derrubaram por régua de
classe de questão, que é vizinha da régua de capacidade —, mas o ato correu sem a
conferência que `arq:0059` tornou obrigatória no dia anterior.

**Corte proposto.** A redação e o registro continuam de `rh`; a **existência** da unidade
se confere contra o mapa antes do evento no ledger. Operacionalmente: `persona designar` e
`persona dispensar` passam a exigir a capacidade nomeada na `--nota`. Quem decide se a
capacidade existe é o arquiteto; quem escreve continua sendo eu.

### S-3 · `produto:canais` × `arquiteto:negocio` — a capacidade e o mapa da capacidade

**O que colide.** A gerência de Canais da claudinha-produto foi criada em 16/08 tendo a
capacidade de canais do BizBOK como razão declarada (registrado no próprio `arq:0059`), e
`negocio` é o chapéu que detém o BizBOK.

**Corte proposto, e resolve por si.** O arquiteto é dono **do mapa**, não das capacidades
que o mapa nomeia. Uma capacidade existe uma vez e mora numa unidade; o mapa diz onde. Sem
essa linha, todo chapéu de negócio vira revisor de todo chapéu operacional das outras
cadeiras — que é exatamente o padrão que `arq:0034` já derrubou uma vez, na partição
interna de domínio.

### S-4 · `seguranca:blueteam` × `TI:plataforma` × `fabrica:blueteam-fabrica` — resolvido pelas partes, e registro aqui

Não é sobreposição: é execução repartida, e as duas cadeiras a declararam sem eu pedir.
claudinho-TI, 17/08: segurança decide o que instrumentar e o que o sinal significa; a
fábrica instrumenta, coleta e mantém rodando. Fica no mapa porque execução repartida
**tem de estar declarada** (`arq:0059`), e esta não está em `org/fronteiras.md`.

## 4. Vácuos — capacidade sem unidade

| # | O que não tem dono | Quem achou | Dono candidato |
|---|---|---|---|
| V-1 | **`conferir canal` não existe.** O chapéu `canais` nasce com régua e sem instrumento (card 107, 09/08) | produto | régua de produto, verbo de TI |
| V-2 | **Verificação de que o dado descartado saiu de backup e réplica.** Segurança fecha o prazo, TI fecha o mecanismo, ninguém fecha a conferência | segurança | segurança define, TI executa |
| V-3 | **Classificador de "superfície externa".** O gatilho de sign-off existe; hoje quem sobe é quem classifica, e é o único ponto do gate sem revisor | segurança | arquiteto (é régua de fronteira) |
| V-4 | **Inventário do que a plataforma retém, e por quanto tempo.** Nenhum verbo lista; não há prazo escrito para transcript, caderno, memória de agente nem `var/log/ops/` | segurança | dados (modelo) + segurança (regime) |
| V-5 | **Inventário de segredo com prazo.** `var/secrets` é morada, não inventário (card 200) | segurança | segurança |
| V-6 | **Detecção de "controle" em artefato alheio.** O chapéu `risco` morreu como gerência justamente por não ter gatilho próprio; o resíduo continua sem detector | segurança | órfão declarado |
| V-7 | **Lastro da secretaria.** O trabalho dela não gera card, commit nem fita: acontece fora do harness, e a régua "card, commit, data" olha para onde ela não deixa rastro | gestão | gestão (rotular `[secretaria]` na mesa fabrica o lastro) |

**Fechado hoje, e sai da lista:** a colisão singular/plural do acervo (dados, 3738912) e a
morada do achado de campo do titular externo (card 205, dormente com gatilho).

## 5. O que este cruzamento não alcança

- **Densidade de caso não é profundidade de matéria.** Segurança apontou primeiro, para
  `privacidade`: três casos em duas semanas porque a casa tem um titular, não porque a
  matéria seja rasa. Cruzar por contagem de caso reprovaria a gerência que morde
  exatamente quando a plataforma abrir a usuário externo.
- **A régua dura exclui o futuro por construção.** "Cada afirmação ancorada em caso
  ocorrido" é certa para auditar escopo e é inaplicável a qualquer aposta. Foi assim que a
  cadeira de estratégia escreveu o instrumento que torna o próprio ofício inadmissível
  (`org/nota-2026-08-16-gap-de-estrategia.md`).
- **Vinte de 109 conceitos de segurança e 22 de 76 de IA não têm obra-âncora**; no acervo
  inteiro são 89 de 468. O motor casa o rótulo, sobe a hierarquia e devolve o vizinho sem
  erro. Isso não é vácuo de dono — é dívida de acervo, dona claudinho-dados, e está na
  minha carteira como pedido de obra.

## 6. Decisões do dono

1. **S-1 · corte `dominio` × `ontologia`** — identidade e nome canônico da entidade em
   `dados`; contexto que detém o significado em `arquiteto`. ✅ recomendado: é o corte que
   o caso ocorrido de 17/08 já praticou sem ninguém decidir.
2. **S-2 · `persona designar|dispensar` passa a exigir a capacidade nomeada** — a régua de
   existência é `arq:0059`, do arquiteto; a redação continua de `rh`. ✅ recomendado, e é
   contra o meu próprio conforto: acrescenta uma conferência ao meu ato.
3. **S-3 · o arquiteto é dono do mapa de capacidades, não das capacidades** — vai a
   `org-regras.md` como emenda a `arq:0059`. ✅ recomendado.
4. **V-3 · classificador de superfície externa** — é régua de fronteira, e por isso do
   arquiteto, não de quem sobe nem de quem audita. ⚪ hipótese: o arquiteto não foi ouvido
   sobre isso, e o achado é de segurança. Confirma-se perguntando a ele.
5. **V-1, V-2, V-4, V-5** — viram card com dono, ou ficam declarados como dívida sem prazo.
   ✅ recomendo card para V-1 e V-4 (os dois têm consumidor esperando) e dívida declarada
   para V-2 e V-5, que não têm.
