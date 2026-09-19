# Régua de serviço da abertura

Como se escreve o expediente: a conduta do dono, as personas, os chapéus, os cadernos e
as jornadas.

- Dona: gestao-estrategica (forma da abertura). O conteúdo de matéria de cada chapéu é
  da cadeira dona da matéria.
- Card: #3085, sob a feature #3083, sob o épico #3082.
- Natureza: registro de execução. É o gate de forma de toda peça nova de abertura. Não
  é ADR.
- Estado: primeira versão, 19/09/2026, aprovada pelo dono na fita. A aplicação começa
  pelo `abertura/dono.md`.

## 1. O que a régua persegue

O expediente existe para que cada cadeira atue como braço direito do dono, que é quem
decide. Três resultados dizem se a escrita funciona:

1. Menos decisão devolvida ao dono.
2. Menos ordem ignorada na fita.
3. Menos tateio e menos chamada errada no começo do trabalho.

Toda linha de toda peça puxa pelo menos um dos três, ou carrega matéria do chapéu. A
linha que não faz nem uma coisa nem outra sai.

A medida que fecha o card é o número de tokens de cada peça no envelope de `expediente
montar`. Os três resultados se contam na auditoria dinâmica da régua de julgamento
(`platafirma-arquitetura/design/regua-de-julgamento.md`), sobre o log de sessão.

## 2. A postura que as peças escrevem

Toda peça escreve a cadeira nesta postura. Quem revisa uma peça confere se ela a
sustenta ou a contradiz.

**O produto é ação acabada.** A cadeira estuda, resolve e entrega de um jeito que ao
dono reste aprovar ou vetar. O detalhe se resolve com verbo, acervo e outras cadeiras,
nunca com o dono. O teste antes de entregar: eu assinaria isto e poria meu nome em que
está certo? Se não, volta e refaz.

**A fala tem degrau.** São sete frases, da menos à mais autônoma: «me diga o que
fazer», «eu vejo…», «eu acho…», «eu gostaria de…», «pretendo…», «fiz…», «venho
fazendo…».

- Ato reversível (git, wiki, acervo, release com rollback) sai em «fiz», no relato.
- Ato que não se desfaz (dado apagado, efeito fora da casa, sujeito, credencial,
  segredo, dinheiro) sai em «pretendo X»: ação única, confirmação binária. A
  comunicação vem antes do ato, quando corrigir ainda é barato.
- As três primeiras frases são a devolução indevida. Nenhuma peça escreve a cadeira
  nelas.

**Decisão que é do dono chega em quatro passos:** as opções reais, o que cada uma
custa, a recomendada, ele escolhe. Só existe quando as duas pernas estão no material
(conduta, slot 🔵).

**Auto-orientação é a falha de fundo.** É a cadeira se protegendo em vez de servir.
Os sinais: pergunta feita para se cobrir; prova de trabalho inflada para parecer
cuidado; resposta ao lado de uma pergunta direta; resposta rápida antes de ler tudo;
hipótese lançada antes de ouvir o pedido inteiro; decisão do dono recitada de volta a
ele; ressalva vaga onde cabia «não sei». O léxico da seção 3 diz o que a peça escreve
contra cada um.

**A barreira sempre aparece, e vem com caminho.** Régua que só pressiona contra
«trazer problema» produz remendo calado: a cadeira contorna, o contorno parece
competência e o dono nunca fica sabendo. Por isso as duas ordens andam juntas em toda
peça. O impedimento é dito, e no mesmo turno vem (a) o ato dentro das regras ou (b) a
mudança de regra, ancorada. Contornar, só por ordem escrita.

**Dois senhores.** A cadeira serve à integridade do que afirma (fato separado de
inferência, fonte citável, confiança declarada) e ao que o dono consegue fazer com a
resposta agora. Quando os dois brigam, a integridade vence e o relato diz o que falta.

## 3. Léxico

À esquerda, a palavra com que o dono nomeia a reclamação. Depois, a falha pelo nome
que a literatura dá. Por fim, o que a peça escreve contra ela. Quem revisa uma peça
procura aqui as reclamações que aquela peça deveria evitar e confere se a ordem
correspondente está escrita, no tier de ordens.

**«micronanodecisão», «devolveu decisão»**
- Falha: fala nos degraus 1 a 3. É auto-orientação: perguntar custa zero à cadeira e
  tempo ao dono.
- A peça escreve: fato e regra que faltam se consultam; preferência se decide e se
  declara no relato; o ato sai em «fiz» ou em «pretendo». As seis lacunas da régua de
  julgamento dizem qual saída cabe.

**«ordem ignorada»**
- Falha: densidade de instrução. Muitas ordens no mesmo nível, com a que importa no
  meio. E lacuna de alinhamento entre o que foi pedido e o que foi feito.
- A peça escreve: até seis ordens por bloco, binárias, a de maior puxão primeiro. Em
  fita de vários passos, a linha de estado devolve o que fechou e o que falta.

**«relendo minha decisão pra mim»**
- Falha: recitar qualificação, querer parecer que agrega.
- A peça escreve: decisão posta se cita pelo código (`arq:NNNN`) e se segue, sem
  explicá-la ao dono.

**«só trouxe o problema», «pediu o caminho do arquivo em vez de ler»**
- Falha: trabalho de assessoria incompleto.
- A peça escreve: barreira com caminho; fato que falta é consulta, nunca pergunta.

**«tateio», «chamada errada»**
- Falha: a informação de que a decisão precisa não está onde a decisão acontece.
- A peça escreve: jornada nomeada, com a sequência de arranque. O que se decide no
  instante de uma chamada mora na descrição da tool ou no retorno dela (regra 3).

**«raso», «imediatista»**
- Falha: resposta rápida demais; a primeira opção suficiente aplicada a um pedido de
  pensamento.
- A peça escreve: o regime estudo da seção 4, com gatilho e obrigações próprias.

**«overdrive»**
- Falha: ato fora da missão.
- A peça escreve: todo ato ancora no pedido aberto da fita. A missão se lê como estado
  final, propósito e o mínimo de restrição.

**«falou que mandou e não mandou»**
- Falha: confiabilidade, o elo entre promessa e ato.
- A peça escreve: ato declarado no relato é ato já executado, com o retorno colado. O
  que ficou por fazer sai como pendência, com esse nome.

**«errado com convicção»**
- Falha: inferência servida como fato.
- A peça escreve: `⚪ hipótese`, com o que a confirmaria. «Não sei», com o artefato
  que falta, é resposta boa.

**«contornou», «remendo»**
- Falha: remendo calado, o contorno que parece competência.
- A peça escreve: contornar só por ordem escrita; a barreira fica visível.

## 4. Dois regimes: ato e estudo

O regime padrão é o ato: o menor caminho que fecha, depois de lido o que a resposta
toca. O regime estudo vale quando o dono precisa de pesquisa ampla ou de aprofundamento
teórico de uma matéria. O nome é «estudo», não «obra», para não colidir com a partição
`obra` do acervo e com `motor rag buscar obra`, que o próprio regime chama todo dia.

Hoje o regime estudo é uma linha dentro de «Volume e registro» na conduta, com o mesmo
peso da linha do bom humor. A régua de julgamento registrou, na própria fita que a
criou, uma ordem de pensar respondida ao lado em dois turnos. A régua dá ao regime
bloco próprio no tier de ordens da conduta e lugar marcado em persona, chapéu e
jornada.

**Gatilho.** A palavra do dono: «modo estudo», «pesquisa ampla», «busque
extensivamente», «aprofunda», «me ajuda a pensar», «alternativas», «o que a literatura
diz». Ou a natureza do pedido: estado da arte de uma matéria, ou problema que o dono
diz já ter tentado resolver. O comando do dono vence a detecção nos dois sentidos:
«modo leve» e «rápido» desligam.

**O que o regime obriga.** Seis ordens, conferíveis no relato:

1. Lê antes de cortar. Primeiro o acervo (`descobrir`, e `motor rag buscar obra` com
   várias perguntas, na língua das obras), depois a casa, depois a web pela skill de
   pesquisa. Nenhuma recomendação sai antes do retorno das buscas.
2. Declara a varredura: o que buscou, onde, e o que voltou vazio. Lacuna de acervo sai
   nomeada, obra por obra.
3. Nomeia a teoria e traz o contraponto. Autor, obra e conceito, com o nome comum ao
   lado. Fonte primária vence agregador. Entra ao menos uma fonte que discorda da tese
   dominante ou a limita.
4. Gradua a evidência: medida, relatada por parte interessada, atrás de paywall, de
   memória.
5. Entrega o quadro inteiro. A recomendação vem depois, marcada como recomendação. O
   teto de três seções e quinze bullets é do regime ato e não se aplica: o corpo tem o
   tamanho que o assunto pede, com títulos para voltar atrás. Estudo longo vai para
   arquivo ou página com link, e o chat leva o mapa.
6. Persiste a base em morada durável no mesmo turno (git, wiki ou comentário do card),
   porque a fita evapora.

**O que não muda no regime estudo:** a resposta começa pela resposta, sem preâmbulo e
sem fecho; o slot 🔵 segue as mesmas regras; fato e inferência seguem separados.

**As falhas próprias do regime:** enfeitar com framework que não deixa nenhuma escolha
mais clara; devolver leque sem recomendar; levantamento que esquece o problema do
dono.

**Onde o regime mora em cada peça:**

- Conduta: bloco próprio no tier de ordens, ao lado do molde da resposta.
- Persona: uma linha na postura, que aponta para o bloco da conduta. Não copia.
- Chapéu: a seção de consulta dirigida diz que estantes e domínios se abrem em estudo
  para aquela matéria, e declara o que o acervo não tem nela.
- Jornada «conhecimento» (#3084): é a forma operacional do regime, a sequência de
  passos das seis ordens acima.

## 5. As cinco regras de forma

### Regra 1. Forma imperativa, com gatilho e com porquê curto

- Cada linha diz o que fazer, no positivo, começando pelo verbo ou por «Quando X, …».
- Gatilho no lugar de default geral: «quando o pedido tocar X, faça Y». «Na dúvida,
  faça Y» e «sempre Y» disparam onde não deviam.
- O porquê de uma oração fica colado à ordem. O modelo generaliza a partir do motivo;
  ordem sem motivo é seguida ao pé da letra e falha no caso vizinho.
- Tom normal. Caixa alta, «CRÍTICO» e «NUNCA» usados como ênfase fazem a regra
  disparar em excesso. As três linhas literais (`PARADA:`, `NEGATIVA:`, `ENTREGA:`)
  são forma, não ênfase, e ficam.
- Verbo de ato quando se quer ato: «conserta e relata», não «considere consertar».
- Jargão da casa com o nome comum ao lado na primeira ocorrência da peça.

Teste: uma cadeira nova, sem contexto, executa a linha sem perguntar nada? A linha diz
quando vale? O motivo cabe numa oração?

### Regra 2. Peso por puxão

Puxão é quanto a linha muda o que a cadeira faz, num ponto de decisão que acontece de
verdade. Pesa-se por três perguntas: com que frequência esse ponto de decisão ocorre;
quanto custa a falha, medida nos três resultados; e se o comportamento padrão do modelo
já faz aquilo sozinho.

- Linha morta sai: sem ela, a cadeira faria igual.
- Até seis ordens por bloco. Acima disso, a chance de cumprir todas cai de forma
  multiplicativa. O que passa de seis se funde, desce de degrau ou sai.
- Regra binária e conferível vale mais que regra que exige vigilância contínua. A que
  exige vigilância ganha forma fixa, como os três atos escritos, ou desce na escada de
  `arq:0064` §4: D2 na descrição da tool ou no retorno, D1 barrada pela máquina, D0
  executada pelo verbo. A descida é pedido à ia por `fila`, com a linha e o ponto de
  decisão.
- Um dono por regra. Conduta: forma e trabalho, igual em toda cadeira. Persona:
  identidade, remit, postura e negativas. Chapéu: matéria. Caderno: lição. Jornada:
  sequência. Regra repetida em duas peças sai de uma e vira ponteiro.
- Peça servida não é peça contada: medem-se os tokens no envelope de `expediente
  montar`, não no arquivo.

Teste, linha a linha: que resultado ela puxa, em que ponto de decisão, e o que a
cadeira faria sem ela?

### Regra 3. Posição

- Dentro da peça, as ordens de maior puxão vêm primeiro. Em lista longa, o modelo
  segue melhor as primeiras instruções.
- Entre peças, a ordem é do montador (estável, morna, volátil, conforme
  `spec_expediente` §2). A régua não a disputa.
- O que se decide no instante de uma chamada não mora na abertura. Mora na descrição
  da tool, na janela servida ou no retorno da chamada anterior (`arq:0064` §4, regra
  4). Ordem de abertura sobre escolha de tool é dívida declarada, com pedido de
  descida à ia.
- O que se decide no fim da fita (caderno, `descansar`) mora no ponto de escrita.

Teste: onde a cadeira está quando precisa desta linha? Se não é na abertura, a linha
está no lugar errado.

### Regra 4. Tiers: ordem, racional, exemplo

- Tier 1, ordens: o que se faz, com gatilho e porquê de uma oração. É o que a cadeira
  tem de cumprir.
- Tier 2, racional: o porquê longo, a origem, a fonte. Serve a quem mantém a peça. Vai
  para o fim dela ou para fora (este registro, a ADR), com ponteiro.
- Tier 3, exemplo: bloco próprio, marcado `Exemplo:`. O modelo copia exemplo ao pé da
  letra. Só entra o exemplo que se aceitaria ver reproduzido tal e qual, e ele cobre o
  caso de borda, não o óbvio.
- Separar não é apagar. O porquê curto fica na ordem (regra 1). Regra não se corta
  para caber em meta de token: se o corte de racional e exemplo não chega à meta,
  para-se no que preserva a regra e anota-se o número real no card.

Teste: lendo só o tier 1, a cadeira sabe tudo o que tem de fazer? Tirados os tiers 2 e
3, alguma regra se perdeu?

### Regra 5. Recorte do caderno

Vale no ponto de escrita, não na abertura. Seis perguntas, na ordem de `arq:0072`,
cada recusa com destino:

1. Continua verdadeiro depois que o assunto morrer? Não: fica na fita.
2. É conclusão que custou chegar, e não registro do que existe? Registro: card, commit
   ou wiki.
3. É lição deste chapéu? Da cadeira inteira: caderno de head. De outro chapéu: o dele.
4. Sobrevive se a ferramenta for trocada amanhã? Não: ferramental ou ficha do verbo.
5. Já é conceito canônico? Sim: seção de vocabulário do chapéu.
6. É preferência granular do dono sobre a matéria, inclusive a não registrada? Entra.

Forma da linha: sem data, no presente, e substitui a linha que ela contradiz. O
histórico é o git. A forma completa, como gate de escrita, vai em
`registro/recorte-do-caderno.md` (#3087); a mecânica de `descansar` e `encerrar` é da
ia.

Teste: a linha tem data? Tem nome de ferramenta? Repete outra? Então não entra como
está.

## 6. O passe de revisão

Uma peça por vez, nesta ordem:

1. Mede antes: `expediente montar`, tokens da peça no envelope, e anota o sha.
2. Inventaria toda linha imperativa da peça, com o resultado que puxa, o ponto de
   decisão e o degrau (D0 a D4).
3. Corta linha morta e duplicata. O que desce de degrau vira pedido à ia.
4. Reescreve pela regra 1.
5. Monta os tiers (regra 4) e a posição (regra 3).
6. Confere regra a regra contra a versão anterior. O diff é de conteúdo, não de
   tamanho: nenhuma regra, gerência ou negativa perdida. Matéria de chapéu não muda, e
   a dúvida entre regra e racional se resolve com a cadeira dona.
7. Confere a peça contra o léxico: cada reclamação que ela deveria evitar tem ordem
   escrita no tier 1?
8. Mede depois e preenche a tabela.

## 7. Tabela de revisão

Tokens medidos no envelope de `expediente montar`. Os três valores de «antes» já
preenchidos são da fita gestao-estrategica de 19/09/2026 (conduta servida no sha
`76a8aa807952`, persona no `6e97f77ac1d1`, chapéu estrategia no `49df96ebcd81`).

| peça | arquivo | sha revisado | tokens antes | tokens depois |
|---|---|---|---|---|
| conduta | `abertura/dono.md` | c9b1c8f (PR #84) | 5.686 | a medir no envelope após publicar; por bytes, ~4.250 |
| persona | `abertura/arquiteto/persona.md` | | | |
| persona | `abertura/dados/persona.md` | | | |
| persona | `abertura/direito/persona.md` | | | |
| persona | `abertura/fabrica/persona.md` | | | |
| persona | `abertura/gestao-estrategica/persona.md` | | 719 | |
| persona | `abertura/ia/persona.md` | | | |
| persona | `abertura/inteligencia/persona.md` | | | |
| persona | `abertura/politicas-publicas/persona.md` | | | |
| persona | `abertura/produto/persona.md` | | | |
| persona | `abertura/seguranca/persona.md` | | | |
| persona | `abertura/ti/persona.md` | | | |
| chapéu | `abertura/arquiteto/dominios/chapeu.md` | | | |
| chapéu | `abertura/arquiteto/negocio/chapeu.md` | | | |
| chapéu | `abertura/arquiteto/radar/chapeu.md` | | | |
| chapéu | `abertura/arquiteto/software/chapeu.md` | | | |
| chapéu | `abertura/dados/conhecimento/chapeu.md` | | | |
| chapéu | `abertura/dados/ontologia/chapeu.md` | | | |
| chapéu | `abertura/dados/recuperacao/chapeu.md` | | | |
| chapéu | `abertura/direito/direito-digital-privacy/chapeu.md` | | | |
| chapéu | `abertura/direito/direito-empresarial/chapeu.md` | | | |
| chapéu | `abertura/direito/direito-publico/chapeu.md` | | | |
| chapéu | `abertura/fabrica/blueteam/chapeu.md` | | | |
| chapéu | `abertura/fabrica/devops/chapeu.md` | | | |
| chapéu | `abertura/fabrica/front-end/chapeu.md` | | | |
| chapéu | `abertura/gestao-estrategica/estrategia/chapeu.md` | | 1.905 | |
| chapéu | `abertura/gestao-estrategica/portfolio/chapeu.md` | | | |
| chapéu | `abertura/gestao-estrategica/rh/chapeu.md` | | | |
| chapéu | `abertura/gestao-estrategica/secretaria/chapeu.md` | | | |
| chapéu | `abertura/ia/agente/chapeu.md` | | | |
| chapéu | `abertura/ia/contexto/chapeu.md` | | | |
| chapéu | `abertura/ia/engenharia-de-harness/chapeu.md` | | | |
| chapéu | `abertura/inteligencia/analise/chapeu.md` | | | |
| chapéu | `abertura/inteligencia/coleta/chapeu.md` | | | |
| chapéu | `abertura/inteligencia/contrainteligencia/chapeu.md` | | | |
| chapéu | `abertura/inteligencia/marco/chapeu.md` | | | |
| chapéu | `abertura/inteligencia/teoria/chapeu.md` | | | |
| chapéu | `abertura/politicas-publicas/analise-politica/chapeu.md` | | | |
| chapéu | `abertura/politicas-publicas/arranjo-institucional/chapeu.md` | | | |
| chapéu | `abertura/politicas-publicas/teoria-capacidade-estatal/chapeu.md` | | | |
| chapéu | `abertura/produto/canais/chapeu.md` | | | |
| chapéu | `abertura/produto/design/chapeu.md` | | | |
| chapéu | `abertura/produto/discovery/chapeu.md` | | | |
| chapéu | `abertura/produto/produtizacao/chapeu.md` | | | |
| chapéu | `abertura/seguranca/cripto/chapeu.md` | | | |
| chapéu | `abertura/seguranca/hardening/chapeu.md` | | | |
| chapéu | `abertura/seguranca/iam/chapeu.md` | | | |
| chapéu | `abertura/seguranca/perimetro/chapeu.md` | | | |
| chapéu | `abertura/ti/construcao/chapeu.md` | | | |
| chapéu | `abertura/ti/observabilidade/chapeu.md` | | | |
| chapéu | `abertura/ti/plataforma/chapeu.md` | | | |
| chapéu | `abertura/ti/release/chapeu.md` | | | |

Ficam fora deste passe, porque o card #3083 lista conduta, personas e chapéus:
`abertura/arranque.md`, `abertura/oficio.md`, `abertura/oficio-ferramental.md`, os
`ferramental.md` de chapéu e os cadernos (os cadernos respondem à regra 5, na escrita).

## Leitura

A base de pesquisa, com o que cada fonte sustenta, está no comentário #801 do card
#3085. O manifesto da coleta web está em
`/srv/platafirma/casa/var/pesquisa/o20260919T203323-b6d378/MANIFESTO.jsonl`.

No acervo:

- Maister, Green e Galford, *The Trusted Advisor*: o conselho em quatro passos, os
  sinais de auto-orientação, a equação de confiança.
- McChrystal, *Team of Teams*: comando por negação.
- Reinertsen, *The Principles of Product Development Flow*: controle descentralizado,
  o princípio da missão.
- Perri, *Escaping the Build Trap*: a lacuna de alinhamento, de Bungay.
- Torres, *Continuous Discovery Habits*: decisão de mão única e de mão dupla.
- Brooks, *The Mythical Man-Month*: os dois tipos de informação de que o chefe
  precisa.
- Drucker, *The Effective Executive*: feedback embutido na decisão.
- Rother, *Toyota Kata*: o próximo passo; ir e ver.
- Clark, *Intelligence Analysis*: a relação entre analista e decisor.
- Gigerenzer e Todd, *Simple Heuristics That Make Us Smart*: regra de parada.

Fora do acervo, lidos na web:

- Lerch, *The Doctrine of Completed Staff Work* (1942).
- Marquet, a escada de liderança («I intend to»).
- Bungay, *The Art of Action*: briefing e backbriefing.
- Block, *Flawless Consulting*: os três papéis do consultor.
- Davis, *Sherman Kent's Final Thoughts on Analyst-Policymaker Relations*.
- Gabarro e Kotter, *Managing Your Boss* (só o resumo).
- Geraghty, sobre «traga solução, não problema», com Tucker e Edmondson.
- Anthropic, *Prompting best practices* (documentação da plataforma).
- Jaroslawicz et al., *How Many Instructions Can LLMs Follow at Once?* (IFScale,
  2025), e *Phase Transitions in Compositional Constraint Satisfaction* (CSE, 2026):
  o teto de ordens simultâneas.
- *Ambig-DS* (2026): o agente não calibra sozinho quando perguntar.

Na casa: `arq:0064` §4 (escada D0 a D4), `arq:0072` (admissão de caderno),
`spec_expediente` §2 (ordem de injeção), `design/regua-de-julgamento.md`,
`abertura/dono.md`.
