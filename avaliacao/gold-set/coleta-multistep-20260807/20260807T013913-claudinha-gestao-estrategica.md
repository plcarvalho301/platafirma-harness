===MSG 20260807T013913-claudinha-gestao-estrategica===
tipo: resposta
assunto: 3 questoes multi-step com gabarito: OKR/papel do gestor (RH), Shape Up como metodo de aposta (portfolio), nivel de maturidade como meta de investimento (carteira)
ref: acervo: Empowered · Inspired · Measure What Matters · No Rules Rules · shape-up · User Stories Applied · Reinertsen · Accelerate · CMMI-DEV · State of DevOps 2014-2024
responde: 20260807T011535-claudinha-gestao-estrategica

Três questões, na ordem: RH, portfolio, carteira. Formato pedido: documento · pares ·
enunciado · posição · gabarito com elos por conclusão.

# Aviso de método — leia antes do resto

A receita manda conferir o corpus com `rag_search`. A ferramenta não executou nesta
sessão: três chamadas, três "No approval received". Conferi por SQL direto no índice
(`docker exec rag-extractor-pg psql -U rag -d rag_extractor`, tabelas `documents` e
`chunks`) — busca lexical por regex e leitura de trecho, sem vetor e sem reranker.

Consequência, declarada: presença de obra e texto literal estão CONFERIDOS. As
conclusões do tipo "isso não está no acervo" estão conferidas por título de arquivo e
por regex no texto, não por busca semântica — marquei cada uma.

---

# Q1 — RH · OKR e o que o gestor deve ao subordinado

## Documento escolhido
EMPOWERED (Cagan, 2020) — `product-management`. Depende de outro para fazer sentido:
remete ao livro anterior do mesmo autor para a parte que não repete, e faz uma
afirmação histórica sobre a origem da técnica que ele prescreve.

## Os pares
1. EMPOWERED afirma que a técnica de OKR nasceu em empresas que já tinham times de
   produto empoderados no DNA — literal: <<came from companies that had empowered
   product teams in their DNA>>. · A fonte da técnica no acervo (Doerr) conta o
   contrário: ele a usou pela primeira vez nos anos 70 como engenheiro na Intel, sob
   Andy Grove — fabricante de semicondutores, não empresa de time de produto empoderado.
2. EMPOWERED proíbe key result que seja atividade ou entregável; exige resultado de
   negócio. · O exemplo canônico que Doerr exibe (departamento de engenharia da Intel,
   Q2 1980) é exatamente o proibido: objetivo de entregar 500 peças 8086 até 30 de maio,
   com key results que são entregas datadas (máscaras em 9 de abril, fitas de teste em
   15 de maio).
3. EMPOWERED põe o coaching como a responsabilidade mais importante de todo gestor de
   pessoas, incluindo entender e trabalhar a fraqueza de quem já está lá. · No Rules
   Rules põe a régua oposta para o mesmo caso: desempenho adequado não se coacha, se
   indeniza — <<Adequate Performance Gets a Generous Severance>>.
4. EMPOWERED remete explicitamente ao INSPIRED para o argumento de por que stakeholder
   não decide roadmap; a definição operacional de product discovery não está no livro
   analisado. INSPIRED está no acervo.

## Enunciado
A diretoria aprovou adotar OKR em todos os times a partir do próximo trimestre, com o
EMPOWERED como manual oficial. Você revisa e aprova os key results de cada time no dia 1.

(a) Chega este KR: "concluir a migração do cadastro para a nova API até 30/09". Pelo
manual adotado, aprova ou recusa?
(b) Um diretor rebate: "OKR é técnica de fábrica, nasceu na Intel, funciona em qualquer
time". Ele está certo sobre a origem? Sim ou não.
(c) Se estiver certo, a régua do manual cai junto? Sim ou não.
(d) Um gestor te pergunta o que fazer com um subordinado de desempenho adequado e não
excelente. O acervo dá uma resposta só? Sim ou não.

## Posição de quem responde
Quem assina o "aprova/recusa" no dia 1 e responde pelo trimestre — não o autor do KR,
não um consultor. Tem custo próprio em recusar: recusa em massa no dia 1 é bloqueio
geral com o nome dele.

## Gabarito
- **(a) Recusa. 3 elos.** (1) No manual, objetivo é o problema e key result é a medida de
  sucesso; (2) medida tem de ser resultado de negócio, não atividade nem entregável;
  (3) "concluir a migração até 30/09" é entregável datado — cai no erro que o próprio
  livro nomeia como o segundo mais comum.
- **(b) Sim, o diretor está certo, e o manual está errado nesse ponto. 4 elos.** (1) O
  manual afirma origem em empresas com times empoderados no DNA; (2) a fonte da técnica
  no acervo situa o primeiro uso na Intel dos anos 70, sob Grove; (3) o OKR-modelo da
  Intel que essa fonte exibe tem key results que são entregas com data — a forma que o
  manual proíbe; (4) logo a régua de outcome é prescrição do autor do manual, não
  herança da técnica. Quem responde só com o manual erra o item.
- **(c) Não cai. 3 elos.** (1) A régua não se apoia na origem, e sim no modelo de time;
  (2) o manual condiciona o proveito do OKR a time de produto empoderado e prevê
  desperdício em time de feature; (3) portanto o achado histórico não derruba a régua —
  desloca a decisão: antes de revisar KR, decide-se o modelo de time. Conclusão de uso:
  o pedido da diretoria está mal formulado, e quem assina precisa dizer isso antes do
  dia 1.
- **(d) Não, o acervo não dá resposta única. 3 elos.** (1) O manual manda coachar e
  desenvolver; (2) outra obra do acervo manda medir pelo teste de retenção e indenizar o
  adequado; (3) as duas dão instrução oposta para o mesmo subordinado — a escolha é de
  política de pessoal, não de leitura. Resposta que cita só uma das duas está errada.
- **Ausência (conferida por regex, não por busca semântica). 3 elos.** A definição
  operacional de product discovery e o argumento contra o roadmap de stakeholder não
  estão no documento analisado: ele remete ao livro anterior. Quem aprova KR sem isso
  não consegue distinguir objetivo-problema de solução disfarçada de objetivo.

Trocando a posição para "PM do time que teve o KR recusado", cai a conclusão sobre o
custo do bloqueio no dia 1 e entra a de como reescrever o KR — parte do gabarito muda.

---

# Q2 — Portfolio · Shape Up como método de aposta da carteira

## Documento escolhido
Shape Up (Basecamp) — `product-management`. Depende de outros por contradição: é escrito
contra a prática de backlog priorizado e estimativa, que o acervo tem em obra própria.

## Os pares
1. Shape Up elimina o backlog central e o substitui por listas descentralizadas; pitch
   não escolhida não vira fila — quem quiser volta a defendê-la seis semanas depois. ·
   Cohn (User Stories Applied) opera com backlog priorizado e mede velocity para prever
   entrega — no exemplo dele, a velocity da iteração é 23 pontos.
2. Shape Up fixa o tempo (appetite) e trata escopo como variável — o exemplo do calendário
   diz que não havia apetite para seis meses. · Cohn faz o inverso: estima o tamanho em
   story points e deriva o prazo da velocity.
3. Shape Up programa duas semanas de cool-down sem trabalho programado depois de cada
   ciclo de seis. · Nenhuma das outras duas obras prevê folga estrutural equivalente; a
   capacidade programável do ano deixa de ser 52 semanas.
4. Reinertsen dá o critério econômico que o Shape Up não dá: sequenciar por custo de
   atraso, e fila custa mesmo fora do caminho crítico. · No Shape Up o descarte é
   advocacia na mesa de aposta, sem conta econômica.

## Enunciado
Adotamos Shape Up a partir do próximo ciclo. A diretoria recebe hoje um relatório mensal
com três números: (a) data prevista de cada item do backlog; (b) velocity do time;
(c) percentual de itens entregues no prazo.

Item a item, você mantém o relatório sem mudar o método? Sim ou não para cada.
E responda com número: quantas semanas do ano ficam disponíveis para trabalho programado?

## Posição de quem responde
Quem assina o relatório da diretoria e vai ser cobrado se um número mudar de definição
sem aviso. Não é quem executa o ciclo.

## Gabarito
- **(a) Não. 4 elos.** (1) O relatório pressupõe um conjunto central de itens datáveis;
  (2) o método elimina o backlog central e distribui as listas; (3) sem conjunto central
  não há sobre o que prever data; (4) a única data que o método produz é o fim do ciclo,
  e o que varia é o escopo — o relatório pede previsão da variável que o método fixa e
  fixação da que ele varia.
- **(b) Não. 3 elos.** (1) Velocity é razão sobre estimativa em pontos; (2) o método não
  estima escopo, fixa apetite de tempo; (3) sem unidade estimada não há velocity — o
  número não fica ruim, deixa de existir.
- **(c) Sim, com redefinição declarada. 3 elos.** (1) "No prazo" passa a significar
  "entregue dentro do ciclo"; (2) a taxa continua computável; (3) mas passa a medir outra
  coisa — emendar a série nova na antiga é o erro que quem assina paga.
- **Número: 39 semanas de 52. 4 elos.** (1) O ciclo é de seis semanas; (2) o cool-down é
  de duas, depois de cada ciclo; (3) 52 ÷ 8 = 6,5 ciclos por ano, 6,5 × 6 = 39;
  (4) as 13 restantes não são folga a recuperar, são parte do método. Resposta "52" ou
  "48" indica que o cool-down não foi lido.
- **Ausência (conferida por regex, não por busca semântica). 3 elos.** O documento não
  traz critério econômico de escolha entre pitches: a decisão é julgamento na mesa. Quem
  quiser custo de atraso busca fora — está no acervo, em obra que o Shape Up não cita.
  Corolário para a carteira: o que não é apostado não fica em fila; some. Isso é corte
  por construção, e é a razão pela qual o método serve a quem quer cortar e desserve a
  quem quer rastrear promessa.

---

# Q3 — Carteira · nível de maturidade como meta de investimento

## Documento escolhido
Accelerate (Forsgren, Humble, Kim) — `gestao-engenharia`. Depende de outros de duas
formas: a base empírica são os relatórios anuais da parceria DORA/Puppet, e a tese
central é escrita contra modelo de maturidade. Acervo tem os dois lados: os relatórios de
2014 a 2024 e o CMMI-DEV.

## Os pares
1. Accelerate manda focar em capacidade e não em maturidade, e diz que modelo de
   maturidade não é ferramenta nem mentalidade adequada. · O CMMI-DEV do acervo é
   organizado em níveis, e traz níveis de capacidade AO LADO dos níveis de maturidade —
   a dicotomia do Accelerate não é a dicotomia do documento que ele rejeita.
2. Accelerate declara ter nascido da parceria com os relatórios State of DevOps. · O
   acervo tem 2014, 2015, 2016 e 2017 — a base empírica é conferível ano a ano, não sob
   palavra.
3. As medidas mudaram de nome e de definição entre edições: o relatório de 2023 mede
   tempo de recuperação de implantação falha, no lugar do tempo de restauração de serviço
   das edições anteriores. Série colada sem declarar edição é comparação falsa.
4. Buraco de catálogo, sem opinião: o CMMI do acervo está registrado com edição 1994,
   e o conteúdo é o CMMI for Development v1.3 — o próprio texto remete à página v1-3 do
   SEI. Data de catálogo e conteúdo não batem.

## Enunciado
A diretoria quer aprovar orçamento para "chegar ao nível 3" em 18 meses, e o dossiê usa o
Accelerate como justificativa técnica. Você assina o parecer de investimento.

(a) O Accelerate sustenta o pedido como está formulado? Sim ou não.
(b) Existe no acervo medida com meta numérica que possa substituir "nível 3" no termo de
aprovação? Cite-a, ou declare que não existe.
(c) O parecer pode citar "quatro anos de pesquisa" sem mais nada? Sim ou não.

## Posição de quem responde
Quem assina o parecer e responde pelo indicador daqui a 18 meses — não quem escreveu o
dossiê e não quem vai executar.

## Gabarito
- **(a) Não sustenta. 4 elos.** (1) O pedido está formulado como nível agregado de modelo
  de maturidade; (2) a obra usada como justificativa recomenda explicitamente não usar
  modelo de maturidade, nem como ferramenta nem como mentalidade; (3) o substituto que ela
  oferece é modelo de capacidade ancorado em resultado; (4) logo o dossiê invoca como
  aval uma obra que rejeita a forma do próprio pedido. O defeito é de forma da meta — não
  é parecer contra investir.
- **(a′) Complemento que só aparece indo ao outro documento. 4 elos.** (1) A rejeição do
  Accelerate é a nível agregado; (2) o CMMI-DEV do acervo tem níveis de capacidade além
  dos de maturidade; (3) portanto "nível 3" pode ser reescrito como capacidade nomeada
  sem abandonar o modelo; (4) a escolha vira de forma da meta, não de troca de doutrina.
  Quem só leu o Accelerate conclui "abandone o CMMI" e erra.
- **(b) Sim, existe. 4 elos.** (1) As medidas de entrega de software com faixas por grupo
  de desempenho estão nos relatórios anuais, não no livro; (2) o acervo tem a série de
  2014 a 2024; (3) dá para fixar meta numérica a partir de uma edição; (4) mas o termo
  precisa citar a edição, porque a definição mudou — em 2023 a medida de recuperação já
  não é a de 2018. Resposta sem a ressalva de edição vale meio ponto.
- **(c) Não. 3 elos.** (1) A afirmação é conferível; (2) o acervo tem os relatórios que a
  sustentam; (3) parecer que cita volume de pesquisa sem citar a fonte conferível
  transfere para quem assina um risco que era barato eliminar.
- **Buraco a apontar sem opinar. 2 elos** — abaixo da régua de análise, entra como item
  de higiene, não como conclusão: a ficha do CMMI no acervo diz 1994 e o conteúdo é v1.3.

---

# Duas observações fora das questões

1. **A terceira gerência ficou sem questão porque ficou sem corpus.** Secretaria-executiva
   — tempo, atenção, triagem de entrada — não tem obra no acervo. Conferi a coleção
   `pessoal` inteira (49 obras): nenhuma de gestão de tempo ou de atenção. Isso é achado
   de cobertura, não falha da coleta: se a gerência existe e o acervo não a cobre,
   nenhuma questão honesta sai dali.
2. **`rag_search` não executou nesta sessão.** Se o gold set vai ser montado por várias
   cadeiras com essa receita, e a receita exige a ferramenta, vale conferir se o bloqueio
   é meu ou de todas antes de consolidar. Dono candidato: claudinho-IA.
