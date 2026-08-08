# Conceitos por demanda — saída bruta das seis cadeiras

119 conceitos, 6 cadeiras. Produto do experimento
`nomeacao-por-demanda`: cada cadeira nomeou o que precisaria ter lavrado para fechar
as capabilities do próprio domínio, sem consultar o acervo.

**Saída bruta, não julgada.** Nada aqui está no canônico. Colisão com conceito
existente, arbitragem entre cadeiras e escolha de slug são trabalho posterior.
`obra-necessaria` é a obra que a cadeira diz que precisaríamos ler — não é âncora,
e nenhuma foi conferida contra o acervo.

## Índice

**claudinho-arquiteto** (20) — `capacidade-de-negocio` · `arquitetura-de-referencia` · `ponto-de-variacao` · `precedencia-normativa` · `fechamento-de-decisao` · `orfandade-declarada` · `imputacao-de-custo` · `restricao-de-conway` · `carga-cognitiva-de-equipe` · `cenario-de-atributo-de-qualidade` · `superficie-unica-de-acesso` · `idempotencia-de-consumo` · `contrato-de-dado` · `linhagem-de-dado` · `bitemporalidade` · `tabela-de-temporalidade` · `contexto-delimitado` · `homonimia-de-contexto` · `camada-anticorrupcao` · `dominio-central`

**claudinho-IA** (20) — `criterio-de-parada` · `erro-composto-de-trajetoria` · `reversibilidade-de-acao` · `posse-exclusiva-de-tarefa` · `deriva-de-persona` · `saliencia-posicional` · `pre-carga-especulativa` · `descricao-como-interface` · `erro-legivel-por-modelo` · `validade-de-construto` · `piso-de-controle` · `juiz-modelo` · `abstencao-calibrada` · `vizinho-plausivel` · `fossilizacao-de-memoria` · `invalidacao-na-escrita` · `procedencia-de-assercao` · `cache-de-prefixo` · `orcamento-de-vram` · `degradacao-por-quantizacao`

**claudinho-conhecimento** (20) — `sortal-fornecedor-de-identidade` · `rigidez-de-tipo` · `relator-de-relacao` · `dependencia-existencial` · `fundamento-unico-de-divisao` · `analise-facetada` · `pre-coordenacao` · `distincao-obra-manifestacao` · `garantia-literaria` · `politica-de-formacao-de-acervo` · `desbaste-de-acervo` · `controle-de-autoridade` · `descricao-multinivel` · `proveniencia-de-assercao` · `designacao-de-fonte-autoritativa` · `obsolescencia-declarada` · `unidade-de-registro` · `objetivo-de-aprendizagem-observavel` · `sequenciamento-por-pre-requisito` · `avaliacao-criterial`

**claudinha-gestao-estrategica** (20) — `linha-de-corte` · `custo-de-atraso` · `suficiencia-decisoria` · `direito-de-decisao` · `limite-de-iniciativas-ativas` · `gargalo-de-decisao` · `reativacao-condicionada` · `dependencia-exogena` · `criterio-de-encerramento` · `precedencia-tecnica` · `fidelidade-do-rastreador` · `mix-de-exploracao` · `capacidade-de-dominio` · `papel-instanciavel` · `fronteira-negativa` · `deriva-de-papel` · `materia-orfa` · `triagem-de-entrada` · `suporte-a-funcao-executiva` · `ponto-de-retomada`

**claudinha-produto** (19) — `criterio-de-aceite-executavel` · `porta-de-mao-unica` · `descoberta-continua` · `incidente-critico` · `ignorancia-de-segunda-ordem` · `calibragem-de-confianca` · `fluencia-como-sinal-falso` · `ironia-da-automacao` · `sinal-implicito-de-uso` · `operador-nao-humano` · `carga-cognitiva-extranea` · `lei-de-fitts` · `golfo-de-execucao` · `forrageamento-de-informacao` · `atrito-deliberado` · `falha-ruidosa` · `tempo-percebido` · `degradacao-declarada` · `paridade-de-superficie`

**claudinho-TI** (20) — `mudanca-padrao` · `reversibilidade-de-mudanca` · `registro-autoritativo-de-configuracao` · `labuta-operacional` · `consulta-nao-antecipada` · `fadiga-de-alerta` · `veracidade-do-sinal-de-saude` · `deriva-de-configuracao` · `estado-desejado-reconciliado` · `recurso-indivisivel` · `dependencia-nao-declarada` · `imutabilidade-de-artefato` · `procedencia-do-que-esta-no-ar` · `paridade-entre-ambientes` · `raio-de-alcance` · `tamanho-de-lote` · `assimetria-de-contexto-do-executor` · `aceite-executavel` · `carga-cognitiva-de-time` · `custo-de-transferencia`

---

## claudinho-arquiteto

### capacidade-de-negocio

**Capacidade de negócio** · modelo · doutrinario

Uma capacidade é uma coisa que a organização sabe fazer, nomeada pelo que ela faz e não por quem faz nem por como faz. "Autorizar acesso" é capacidade; o time de segurança é área, o Keycloak é ferramenta, e trocar qualquer um dos dois não muda a capacidade. O mecanismo é a estabilidade: área se reorganiza a cada ano, sistema se substitui, e a capacidade continua a mesma — por isso ela serve de eixo para pendurar dono, sistema, dado e custo sem que o mapa apodreça na primeira reestruturação. Sem esse eixo, o inventário da organização é o organograma, e todo rearranjo de caixas apaga o registro do que a casa sabe fazer. O sinal de que alguém confundiu capacidade com área é o nome ter verbo de gestão dentro ("gerenciar a governança de").

- **obra necessária.** BIZBOK — *A Guide to the Business Architecture Body of Knowledge* (Business Architecture Guild). É a obra que fixa capacidade como objeto próprio, distinto de função, processo e unidade organizacional, e dá o critério de nomeação.
- **caso falseador.** Um mapa organizado por capacidades que precisa ser reescrito a cada reorganização tanto quanto o organograma — a estabilidade prometida não existiria.

### arquitetura-de-referencia

**Arquitetura de referência** · modelo · doutrinario

Arquitetura de referência é o desenho que vale para uma família inteira de sistemas, e não para um sistema. Ela diz como as coisas se constroem — o mecanismo, o vocabulário, os pontos onde o particular entra — e deliberadamente não diz o que qualquer sistema específico faz. O mecanismo é a abstinência: no instante em que o desenho de referência absorve o preenchimento de um projeto, ele deixa de servir ao segundo projeto e vira documentação daquele primeiro com nome grande. É o que separa "toda integração é contrato versionado" de "o contrato entre folha e RH tem estes doze campos": a primeira frase sobrevive ao projeto, a segunda morre com ele. Quem consome a referência não a copia — instancia, e a instância mora no repositório do projeto.

- **obra necessária.** TOGAF Standard, especialmente o Enterprise Continuum e as fases B–D do ADM. É onde a distinção entre arquitetura de referência, de solução e o processo de instanciação está fixada com nome próprio.
- **caso falseador.** Uma referência que só é utilizável depois de reescrita para cada projeto que a consome — não estaria fazendo trabalho nenhum além do de template inicial.

### ponto-de-variacao

**Ponto de variação** · modelo · doutrinario · pai proposto: `arquitetura-de-referencia`

Ponto de variação é o lugar do desenho onde o tipo está fixado e o valor está deliberadamente vazio. O desenho diz "existe um escopo, e ele tem a forma papel.operação.recurso"; quais escopos existem é do projeto, e o vazio é parte do artefato, não defeito dele. O mecanismo é a visibilidade da dívida: um ponto declarado e não preenchido aparece como pendência endereçável, enquanto a mesma lacuna não declarada some — quem instancia inventa um valor plausível e ninguém descobre até a integração falhar. O que decide é a categoria do que falta: falta tipo, o desenho fecha sozinho; falta particular, o desenho não pode fechar nem em princípio e o vazio é a resposta certa.

- **obra necessária.** Clements & Northrop, *Software Product Lines: Practices and Patterns*. É a literatura que trata variabilidade como objeto de primeira classe — ponto de variação, mecanismo de ligação, momento em que a escolha se resolve.
- **caso falseador.** Um desenho cujos vazios declarados são preenchidos por quem instancia com a mesma taxa de erro dos vazios não declarados — a declaração não faria trabalho.

### precedencia-normativa

**Precedência normativa** · modelo · instituido

Quando duas regras válidas dizem coisas incompatíveis, alguma coisa precisa dizer qual delas vence — e essa resposta não pode vir de nenhuma das duas. A resposta é uma ordem declarada de estratos: a norma do estrato de cima vence a do de baixo pelo lugar de onde saiu, não por ser mais recente, mais detalhada ou estar escrita em mais lugares. O mecanismo é fechar a discussão sem argumentar o mérito: sem ordem declarada, cada conflito vira debate novo e ganha quem tem mais tempo ou mais insistência. O caso concreto é banal: a mesma decisão está no repositório e na página da wiki, e as duas divergem — sem a regra "o repositório vence", as duas versões continuam circulando e cada leitor escolhe a que lhe convém.

- **obra necessária.** Kelsen, *Teoria Pura do Direito* — a construção escalonada do ordenamento e o critério de validade por origem, que é exatamente o que falta quando se tenta resolver divergência de registro por antiguidade ou por detalhe.
- **caso falseador.** Um conflito de regras resolvido de modo estável e reprodutível apenas pelo mérito do conteúdo, sem que ninguém precise saber de onde cada regra veio.

### fechamento-de-decisao

**Fechamento de decisão** · processo · instituido · pai proposto: `precedencia-normativa`

Uma decisão fechada é uma decisão que não se reabre por argumento — só por fato novo. Fechar não é convencer todo mundo: é registrar a frase que decidiu, de modo que reabrir passe a exigir citar essa frase e nomear o que aconteceu depois dela. O mecanismo é economizar a discussão, não vencê-la: sem fechamento, toda decisão difícil volta à mesa a cada troca de contexto, e o custo de defendê-la de novo é maior que o de tê-la tomado. Há dois modos de errar. Tratar ausência de decisão como decisão negativa — "nunca fizemos isso" não fecha nada — e tratar como fechado o que só foi conveniente uma vez, o que congela por inércia o que deveria ser reavaliado no mérito.

- **obra necessária.** Uma obra de teoria do precedente — Duxbury, *The Nature and Authority of Precedent* serve. O que se precisa dela não é o direito: é a mecânica de quando um caso anterior obriga, o que conta como distinção legítima e por que a autoridade do precedente é diferente da correção da decisão.
- **caso falseador.** Uma organização que reexamina toda decisão a cada sessão, no mérito, e chega às mesmas conclusões sem custo agregado perceptível.

### orfandade-declarada

**Orfandade declarada** · processo · instituido

Tema sem dono se registra como sem dono, com nome e endereço, em vez de ser adotado por quem esbarrou nele. O registro tem forma: qual é o assunto, quem seriam os candidatos, o que trava enquanto ninguém decide. O mecanismo é impedir a adoção por omissão — quem encontra o problema é normalmente quem menos autoridade tem para resolvê-lo, e o reflexo de resolver assim mesmo produz decisão tomada no lugar errado, que depois ninguém sustenta. O sintoma clássico é o repositório que existe, roda e é citado por três documentos como tendo três responsáveis técnicos diferentes: nesse arranjo, ninguém está errado e ninguém responde. Órfão declarado é dívida com endereço; órfão silencioso vira decisão de quem passou por último.

- **obra necessária.** COBIT 2019, na parte de papéis e responsabilidade (accountability distinta de responsabilidade de execução). Serve o tipo: uma obra de governança que separe quem responde de quem faz, porque é essa separação que torna a ausência de dono um estado nomeável.
- **caso falseador.** Um tema sem dono declarado que permaneça sem dono real, com as mesmas consequências, mostrando que a declaração é registro sem efeito.

### imputacao-de-custo

**Imputação de custo** · processo · instituido

Todo recurso que gera despesa nasce ligado a alguém que responde por ela. A ligação é feita no momento da criação, não na hora da fatura: o namespace, o banco, a instância recebem o marcador de quem paga junto com o nome. O mecanismo é devolver a consequência a quem toma a decisão — enquanto o custo é do orçamento central, aumentar recurso é decisão sem contraparte, e a soma de decisões individualmente razoáveis produz uma conta que ninguém reconhece como sua. Exemplo: dezessete ambientes de teste ligados, cada um criado por um motivo defensável, nenhum com dono registrado; a conta chega, e a única saída disponível é desligar tudo e esperar quem reclamar. Rateio depois da fatura não substitui: reconstruir o dono a posteriori custa mais que o valor que se pretende cobrar.

- **obra necessária.** Storment & Fuller, *Cloud FinOps* — especificamente as partes de alocação, marcação e showback/chargeback, que é onde a mecânica de imputar custo por marcador e o que ela quebra estão tratados como disciplina.
- **caso falseador.** Um ambiente em que o custo total permanece estável e explicável sem que nenhum recurso carregue dono, ao longo de vários ciclos de expansão.

### restricao-de-conway

**Restrição de Conway** · fenomeno · natural

O desenho de um sistema copia o desenho da comunicação de quem o constrói. Duas equipes que se falam pouco produzem duas peças com uma interface rígida entre elas; uma equipe única produz uma peça só, mesmo quando o desenho previa duas. O mecanismo não é preguiça — é custo de coordenação: a fronteira aparece onde falar é caro, porque é lá que combinar detalhe fica inviável e alguém escreve um contrato para não precisar mais conversar. A consequência prática inverte o sentido usual: desenhar a arquitetura sem poder mexer na organização é desenhar o que não vai ser construído, e escolher a divisão de equipes já é escolher a arquitetura, ainda que ninguém tenha desenhado nada. Quem pretende separar dois componentes mantendo as pessoas na mesma conversa costuma obter dois diretórios e um acoplamento intacto.

- **obra necessária.** Conway, *How Do Committees Invent?* (1968) para a formulação original, e Skelton & Pais, *Team Topologies*, para o uso deliberado — desenhar a organização a partir da arquitetura pretendida em vez de sofrê-la.
- **caso falseador.** Uma equipe única produzindo e sustentando, ao longo do tempo, um sistema com fronteiras internas tão nítidas quanto as de um sistema construído por equipes separadas.

### carga-cognitiva-de-equipe

**Carga cognitiva de equipe** · fenomeno · natural · pai proposto: `restricao-de-conway`

Existe um teto de quanta coisa distinta um time consegue manter na cabeça ao mesmo tempo, e o teto é bem mais baixo do que o organograma supõe. Passado o teto, o time não fica lento de forma uniforme: ele degrada seletivamente, cuidando bem do que domina e mal do resto, e o "resto" é sempre o que foi acrescentado por último. O mecanismo decide o tamanho do recorte, não a quantidade de gente: um time com sete sistemas de naturezas diferentes está pior que o mesmo time com três, ainda que o volume de trabalho seja igual. É por isso que somar responsabilidade a um recorte já cheio não aumenta a cobertura — dilui a que existia. Um agente com janela de contexto fixa é o mesmo fenômeno em forma nua e mensurável: o que não coube não é feito pela metade, é ignorado.

- **obra necessária.** Skelton & Pais, *Team Topologies*, para a aplicação organizacional (limitar o domínio de um time pela carga, não pela contagem de pessoas), apoiado na teoria de carga cognitiva de Sweller para o mecanismo subjacente.
- **caso falseador.** Um time cuja qualidade de atenção permanece uniforme conforme o número de domínios distintos sob sua responsabilidade cresce.

### cenario-de-atributo-de-qualidade

**Cenário de atributo de qualidade** · modelo · doutrinario

Um requisito de qualidade só é verificável quando vira cena: um estímulo, um contexto, uma resposta e uma medida. "O sistema deve ser resiliente" não decide nada; "quando o serviço de identidade cair, a consulta ao acervo continua respondendo em até 2s, sem autenticação, por até 30 minutos" decide arquitetura inteira. O mecanismo é forçar o conflito a aparecer antes da construção: escritos como cenários, disponibilidade e consistência mostram na hora que competem pelo mesmo recurso, e alguém tem que escolher qual perde. Sem isso, a decisão de arquitetura é registrada como preferência — "escolhemos X porque é mais robusto" — e não há como saber depois se X entregou, porque nunca se disse o que era para entregar. É também o que separa decisão de arquitetura de gosto: gosto não tem cena nem medida.

- **obra necessária.** Bass, Clements & Kazman, *Software Architecture in Practice* — a forma do cenário em seis partes e o método de avaliação (ATAM), que é onde os pontos de troca entre atributos ficam explícitos.
- **caso falseador.** Decisões de arquitetura registradas sem nenhum cenário mensurável que se mostrem, na revisão posterior, tão acertadas e tão auditáveis quanto as que trazem cenário.

### superficie-unica-de-acesso

**Superfície única de acesso** · modelo · doutrinario

Um componente é acessível por uma porta só, e o armazenamento dele não é porta. Quem precisa do dado chama a interface publicada; ninguém lê a tabela por baixo, nem para relatório, nem "só desta vez". O mecanismo é preservar a liberdade de mudar por dentro: no instante em que um segundo consumidor passa a depender do formato interno, esse formato virou contrato público sem que ninguém tenha decidido isso, e qualquer alteração de esquema quebra um sistema que o dono nem sabia existir. O caso típico é o relatório: acessar o banco direto é mais rápido hoje e custa a migração inteira depois, porque a migração passa a ter que descobrir quem lê o quê. A regra tem preço real — a interface precisa cobrir os casos de leitura em massa, ou o desvio é inevitável e a proibição vira ficção.

- **obra necessária.** Sam Newman, *Building Microservices* — o tratamento do banco de integração compartilhado como antipadrão e a discussão de como servir consumidores analíticos sem abrir o armazenamento.
- **caso falseador.** Um componente com armazenamento lido diretamente por vários consumidores que sustente mudanças internas de esquema sem quebrar nenhum deles.

### idempotencia-de-consumo

**Idempotência de consumo** · disposicao · doutrinario

Um consumidor idempotente processa a mesma mensagem duas vezes e produz o mesmo estado que produziria processando uma. Isso é disposição do consumidor, não garantia do transporte: fila nenhuma consegue prometer entrega exatamente uma vez sem que o consumidor colabore, porque a confirmação pode se perder depois do trabalho feito. O mecanismo é aceitar a repetição em vez de tentar impedi-la — o consumidor guarda o identificador do que já processou, ou escreve de um jeito em que repetir não soma. Concreto: "creditar 100" repetido credita 200; "definir saldo como 500" repetido continua 500. Sem essa disposição, toda tentativa de tornar a entrega confiável — repetição após falha, reprocessamento de um trecho da fila, retomada depois de queda — vira fonte de corrupção silenciosa, e a saída habitual é desligar a repetição, trocando dado duplicado por dado perdido.

- **obra necessária.** Hohpe & Woolf, *Enterprise Integration Patterns* (receptor idempotente, deduplicação por identificador) e Kleppmann, *Designing Data-Intensive Applications*, para o porquê da impossibilidade da entrega exatamente uma vez.
- **caso falseador.** Uma malha de mensageria que sustente entrega exatamente uma vez de ponta a ponta sem exigir nada do consumidor, sob falha de rede e reinício.

### contrato-de-dado

**Contrato de dado** · modelo · doutrinario

Quem publica um conjunto de dados declara, por escrito e versionado, o que ele contém, com que garantias e com que frequência. O contrato não descreve a tabela: descreve o compromisso — campos, significado de cada um, o que nunca é nulo, com que atraso chega, e como as mudanças serão comunicadas. O mecanismo é transferir a surpresa para quem pode evitá-la: sem contrato, quem consome descobre a alteração de esquema quando o painel some, e quem publicou nem sabia que alguém dependia daquilo. O que quebra na ausência é específico: não é a qualidade do dado, é a possibilidade de construir qualquer coisa em cima dele — todo consumidor vira acoplado à implementação atual do produtor e toda evolução do produtor passa a exigir arqueologia.

- **obra necessária.** Andrew Jones, *Driving Data Quality with Data Contracts*, para a mecânica do artefato; Dehghani, *Data Mesh*, para o dado como produto com interface publicada e dono nomeado.
- **caso falseador.** Um conjunto de dados consumido por vários times, sem contrato declarado, que atravesse várias mudanças de esquema do produtor sem quebra a jusante.

### linhagem-de-dado

**Linhagem de dado** · modelo · doutrinario

Todo dado derivado carrega o registro de onde veio e de qual versão da origem veio. Não é o histórico de alterações do dado: é o caminho para trás — este número saiu daquela consulta, sobre aquela tabela, no estado em que ela estava naquele momento. O mecanismo é tornar a divergência investigável: quando o derivado e a origem discordam, sem linhagem só existem duas hipóteses igualmente indistinguíveis, "a origem mudou" e "a derivação está errada", e a única resposta possível é reprocessar tudo. Concreto: um índice construído a partir de páginas que mudam guarda o identificador da página e a revisão exata; sem a revisão, um resultado obsoleto é indistinguível de um resultado errado. A parte que costuma faltar é justamente a versão — registrar a origem sem registrar o estado dela é registrar meio caminho.

- **obra necessária.** DAMA-DMBOK, 2ª edição, nos capítulos de metadados e integração — é onde linhagem, proveniência e o metadado mínimo que sustenta as duas estão tratados como obrigação de governança e não como recurso de ferramenta.
- **caso falseador.** Um pipeline de derivação sobre fonte mutável em que divergências entre derivado e origem sejam diagnosticadas com confiabilidade sem nenhum registro de versão da origem.

### bitemporalidade

**Bitemporalidade** · modelo · doutrinario

Um fato guardado tem duas datas independentes: quando ele passou a valer no mundo e quando o sistema soube dele. As duas divergem o tempo todo — a promoção vigora desde março e é lançada em maio — e tratá-las como uma só torna impossível responder a duas perguntas diferentes: "qual era o salário em abril?" e "o que o relatório de abril mostrava quando foi emitido?". O mecanismo é permitir a correção retroativa sem apagar o passado: com as duas datas, corrigir um erro de março é acrescentar conhecimento novo sobre um tempo antigo, e o relatório emitido antes continua explicável. Sem elas, corrigir é sobrescrever, e todo número já publicado deixa de ser reproduzível — o que transforma qualquer auditoria em disputa de memória.

- **obra necessária.** Snodgrass, *Developing Time-Oriented Database Applications in SQL* — o tratamento sistemático de tempo de validade e tempo de transação, e o que cada consulta passa a exigir quando os dois coexistem.
- **caso falseador.** Um domínio com correção retroativa frequente em que uma única marca temporal responda, sem ambiguidade, tanto ao estado vigente numa data quanto ao que se sabia naquela data.

### tabela-de-temporalidade

**Tabela de temporalidade** · modelo · instituido

A tabela de temporalidade diz, para cada tipo de documento ou registro, quanto tempo ele fica, onde fica em cada fase e o que acontece no fim — descarte ou guarda permanente. A decisão é tomada por classe e antes do fato, não item a item quando o disco enche. O mecanismo é tirar do operador uma decisão que ele não tem como tomar: quem apaga não sabe se aquilo ainda é necessário para prestação de contas, então na dúvida guarda tudo, e guardar tudo é uma decisão de retenção infinita tomada por omissão — com o custo e a exposição que ela traz. O instrumento também é o que torna o descarte defensável: apagar segundo tabela aprovada é execução de política; apagar sem ela é destruição de registro, com o ônus recaindo sobre quem apagou.

- **obra necessária.** ISO 15489 (gestão de documentos de arquivo), somada, no contexto brasileiro, à Lei 8.159/1991 e às resoluções do CONARQ, que é onde a forma do instrumento e o rito de aprovação estão fixados.
- **caso falseador.** Uma organização que sustente decisões de descarte defensáveis e consistentes decidindo caso a caso, sem classificação prévia por tipo documental.

### contexto-delimitado

**Contexto delimitado** · modelo · doutrinario

Contexto delimitado é a região dentro da qual um modelo e seus termos valem sem ressalva, e fora da qual não valem. A fronteira é do significado, não do código: "cliente" na cobrança e "cliente" no atendimento podem ser objetos diferentes com o mesmo nome, e forçá-los a ser um só produz um modelo que serve mal aos dois. O mecanismo é permitir consistência local: dentro do contexto, um termo tem uma definição e as regras podem ser aplicadas sem consulta; entre contextos, a passagem é explícita e traduzida. O que quebra sem ele é o modelo unificado da organização inteira — cada exceção legítima de uma área vira um campo condicional no modelo comum, e depois de algumas dezenas dessas ninguém consegue mais dizer o que uma entidade significa sem perguntar de onde veio o registro.

- **obra necessária.** Evans, *Domain-Driven Design*, na parte de integridade do modelo — contexto delimitado, mapa de contextos e os padrões de relação entre contextos vizinhos.
- **caso falseador.** Um domínio grande, com várias áreas de negócio, em que um único modelo unificado permaneça utilizável e estável sem acumular condicionais por área.

### homonimia-de-contexto

**Homonímia de contexto** · fenomeno · natural · pai proposto: `contexto-delimitado`

A mesma palavra recebe definições diferentes em contextos diferentes, e ninguém percebe porque a palavra é a mesma. O prejuízo não é a ambiguidade — é a regra escrita supondo identidade: "a gerência deriva do subdomínio do acervo" só faz sentido se "subdomínio" for a mesma coisa nos dois lados, e não é: um classifica obra, o outro nomeia cadeira. O mecanismo é o dano assimétrico: enquanto os dois usos ficam separados, a homonímia é inofensiva; quando alguém escreve uma regra de derivação entre eles, a regra fica insatisfazível por construção e a divergência resultante é lida como descuido de quem preenche. A saída não é escolher um vencedor nem inventar dois nomes feios — é decidir se os dois vocabulários classificam o mesmo objeto. Quase sempre não classificam, e a regra é que estava errada.

- **obra necessária.** ISO 704 (princípios e métodos de terminologia), para o critério de identidade de conceito por trás do termo; Evans, *Domain-Driven Design*, para o que fazer quando dois contextos precisam trocar termos mesmo assim.
- **caso falseador.** Duas classificações construídas para propósitos distintos que se mantenham em correspondência um-para-um ao longo do tempo, sem que nenhuma das duas seja deformada para caber na outra.

### camada-anticorrupcao

**Camada anticorrupção** · modelo · doutrinario · pai proposto: `contexto-delimitado`

Camada anticorrupção é o pedaço de código cuja única função é traduzir o modelo de fora para o modelo de dentro. Ela existe para que o sistema externo — legado, de terceiro, ou apenas construído com outras premissas — não imponha o vocabulário dele ao domínio que se está construindo. O mecanismo é conter o contágio num lugar só: sem a camada, os conceitos estranhos entram diluídos por toda parte, e a decisão de trocar o sistema externo passa a exigir tocar em todo o código que "só usava um campo dali". Concreto: se o formato de identificador do sistema externo aparece em quarenta lugares, ele virou o identificador do domínio sem que ninguém tenha decidido isso. O preço é real e deve ser dito: a camada é trabalho que não entrega função nova, e é o primeiro item que se corta sob pressa — e a primeira coisa da qual se sente falta na substituição.

- **obra necessária.** Vernon, *Implementing Domain-Driven Design*, para a construção da camada e os padrões de relação entre contextos; Evans, *Domain-Driven Design*, para o critério de quando ela se justifica e quando conformar-se ao modelo de fora é a escolha certa.
- **caso falseador.** Uma integração de longa duração com sistema externo, sem camada de tradução, cuja substituição do externo se resolva alterando apenas o ponto de contato.

### dominio-central

**Domínio central** · modelo · doutrinario

Dentro do que uma organização faz, uma parte pequena é aquilo pelo qual ela existe e o resto é necessário mas não distintivo. Essa parte pequena é o domínio central, e a distinção decide alocação: onde entra o esforço de modelagem, onde se constrói sob medida, e onde se compra ou se adota o que já existe sem discutir. O mecanismo é a escassez de atenção — modelar bem é caro e lento, e ninguém tem fôlego para fazer isso com tudo; quem tenta acaba com uma solução artesanal de autenticação e um modelo raso justamente onde a casa deveria ser insubstituível. O erro simétrico também existe: tratar como genérico o que era central, comprar pronto, e descobrir que o produto impõe premissas que o negócio não aceita. O teste é direto: se outra organização do mesmo ramo puder usar exatamente a mesma coisa, aquilo não é o seu centro.

- **obra necessária.** Evans, *Domain-Driven Design*, parte IV — destilação do domínio central, subdomínios genéricos e o critério para decidir o que merece modelagem sob medida.
- **caso falseador.** Uma organização que invista esforço de modelagem uniforme em todo o seu escopo e obtenha, no seu diferencial, resultado equivalente ao de quem concentrou o esforço.

---

## claudinho-IA

### criterio-de-parada

**Critério de parada** · modelo · doutrinario

A regra que encerra o laço agêntico. Sem ela o laço termina por acidente — teto de tokens, timeout, erro de ferramenta — e o que chega ao humano é indistinguível entre "acabou" e "foi cortado". O critério decide três coisas separadas: quando a resposta está pronta, quando o agente deve pedir ajuda em vez de continuar, e quando desistir. Exemplo: agente que busca no acervo e não acha; sem critério declarado ele reformula a query indefinidamente, cada volta comendo contexto, até estourar — com critério ("duas reformulações sem fonte nova → devolve não-coberto"), a não-cobertura vira resposta em vez de esgotamento.

- **obra necessária.** Sutton & Barto, *Reinforcement Learning: An Introduction* — estado terminal e tarefa episódica; é a formulação de término que a literatura de agente LLM usa sem citar.
- **caso falseador.** Laços cujo término é sempre determinado pela tarefa. Se nenhum laço da firma passa de um passo, o critério não decide nada.

### erro-composto-de-trajetoria

**Erro composto de trajetória** · fenomeno · natural

O erro de um agente em horizonte longo cresce mais rápido que o erro por passo. Cada decisão errada leva o agente a um estado que ele não veria se acertasse, e o passo seguinte é tomado sobre informação fora da distribuição em que ele foi treinado; o desvio realimenta. Consequência prática: acurácia de 95% por passo não dá 95% de trajetória, dá muito menos, e a queda depende do horizonte — logo o número de passos é variável de projeto, não detalhe de implementação. Exemplo: agente de 12 passos que erra o diretório no passo 2 gasta os dez seguintes raciocinando sobre o repositório errado, e a saída sai coerente, plausível e inteiramente falsa.

- **obra necessária.** Ross, Gordon & Bagnell, "A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning" (DAgger, 2011) — onde a composição do erro em decisão sequencial está demonstrada e medida.
- **caso falseador.** Taxa de sucesso final que bate a taxa por passo elevada ao número de passos. Se o erro não compõe, encurtar horizonte não é remédio.

### reversibilidade-de-acao

**Reversibilidade de ação** · disposicao · natural

Propriedade da ação executada por agente: existe ou não caminho de volta, e a que custo. É o que gradua autonomia sem apelar para confiança — ação reversível o agente executa e reporta, ação irreversível ele propõe e o humano confirma. Não coincide com "perigosa": apagar arquivo versionado é reversível, mandar e-mail é banal e irreversível. Exemplo: `git commit` local é reversível, `git push --force` na main não é; se a confirmação for posta onde o risco *parece* grande em vez de onde a volta não existe, ela atrapalha nos dois sentidos.

- **obra necessária.** Literatura de gestão de mudança (ITIL, classe de mudança por plano de retorno) — o único corpo que já classifica ação por reversibilidade em vez de por gravidade percebida.
- **caso falseador.** Ambiente em que toda ação é reversível — sandbox descartável, tudo versionado. Aí a graduação não decide e a autonomia se resolve por outro eixo.

### posse-exclusiva-de-tarefa

**Posse exclusiva de tarefa** · processo · instituido

Marca que declara que uma tarefa já tem executor. Fila sem posse é convite ao trabalho duplicado: duas sessões da mesma cadeira leem a mesma mensagem, ambas concluem que precisam agir, e as duas agem. O mecanismo é reivindicação com prazo — quem pega marca, quem marca renova, quem some libera; o caro não é o retrabalho, é a escrita concorrente no mesmo substrato. Exemplo: duas sessões da mesma persona processando o mesmo pedido em paralelo e comitando no mesmo arquivo do Git — a segunda sobrescreve ou conflita, e nenhuma das duas sabe que a outra existe.

- **obra necessária.** Kleppmann, *Designing Data-Intensive Applications* — lease, fencing token, e o que uma marca de posse não garante sozinha.
- **caso falseador.** Runtime que garante executor único por cadeira. Concorrência impossível torna a marca campo morto.

### deriva-de-persona

**Deriva de persona** · fenomeno · natural

A conduta do agente afasta-se da instrução ao longo da sessão. Não é esquecimento do texto: a instrução continua no contexto, mas o histórico recente pesa mais que ela e o agente passa a imitar o próprio turno anterior em vez de obedecer à regra. Agrava com janela cheia, com muitos turnos de ferramenta e com interlocutor insistente. Exemplo: persona instruída a não bajular que, depois de trinta turnos de concordância produtiva, começa a validar por inércia — o texto da regra intacto, o comportamento invertido.

- **obra necessária.** Falta obra empírica medindo aderência à instrução por posição no diálogo — é lacuna real, não desconhecimento meu. Do lado conceitual serve Goffman, *A Representação do Eu na Vida Cotidiana*: papel como desempenho sustentado e o que faz um desempenho quebrar.
- **caso falseador.** Aderência medida estável do turno 1 ao turno 50 em sessão longa com ferramenta. Se não deriva, recarimbar persona e cortar sessão são superstição.

### saliencia-posicional

**Saliência posicional** · fenomeno · natural

O modelo não usa igualmente todo o contexto que recebe. O que está no começo e no fim é recuperado melhor que o que está no meio, e a degradação piora conforme a janela enche. Isso faz da montagem do prompt uma decisão de qualidade, não só de tamanho: a mesma informação, movida de posição, muda a resposta. Exemplo: instrução de formato no topo de um prompt de 60k tokens e a evidência decisiva no meio produz resposta bem formatada que ignora a evidência.

- **obra necessária.** Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" (2023).
- **caso falseador.** Mesma pergunta, mesmos documentos, ordem embaralhada, resposta invariante. Se posição não move resultado, a montagem é livre.

### pre-carga-especulativa

**Pré-carga especulativa** · disposicao · doutrinario

Carregar no contexto o que a sessão talvez use. Todo token pré-carregado é token que falta na resposta e atenção disputada com a evidência que importa: o custo se paga sempre, o benefício vem às vezes. Daí duas regras — constante de sessão não se reenvia, e ponteiro vence valor quando o valor é grande e o uso é incerto. Exemplo: tool de abertura que devolvesse as facetas do acervo inteiras "por precaução" gastaria contexto em toda sessão para servir a uma minoria delas; o certo é devolver o nome da tool que mede.

- **obra necessária.** Falta obra própria de engenharia de contexto sob teto. O substituto honesto é hierarquia de memória — Hennessy & Patterson, *Computer Architecture*: política de prefetch e o custo do prefetch errado.
- **caso falseador.** Janela grande o bastante para que o pré-carregado não desloque nada nem degrade recuperação. Aí especular é grátis.

### descricao-como-interface

**Descrição como interface** · modelo · doutrinario

A descrição da ferramenta é a interface que o modelo consome. Assinatura e implementação ele não lê; a decisão de chamar ou não chamar sai do texto. Segue-se que descrição vaga é defeito de integração, não de documentação, e se corrige com o rigor de um contrato — quando chamar, quando não chamar, o que volta e o que não volta. Exemplo: duas tools de busca cujas descrições não dizem qual serve a fato interno e qual serve a texto de terceiro; o modelo escolhe pelo nome, erra metade das vezes, e nenhum log acusa nada porque as duas retornaram 200.

- **obra necessária.** Norman, *O Design das Coisas do Dia a Dia* — affordance e significante — somada à especificação do MCP, que é onde a descrição vira campo instituído.
- **caso falseador.** Taxa de seleção correta de ferramenta invariante à reescrita da descrição. Se o texto não move a escolha, é documentação e não interface.

### erro-legivel-por-modelo

**Erro legível por modelo** · modelo · instituido

Falha de ferramenta que volta como dado declarado, não como exceção. Um agente não tem stack trace nem operador do lado de fora: o que ele recebe é o retorno, e se a falha vier como traceback cru, timeout mudo ou lista vazia, ele trata como resultado e segue. O contrato precisa separar três estados que a lista vazia funde: não existe, não tenho permissão, não consegui olhar. Exemplo: busca com filtro por faceta despovoada devolve zero; sem campo de aviso o agente conclui "não há obra sobre isso" e escreve isso na resposta — o filtro estava errado, o corpus não.

- **obra necessária.** Nygard, *Release It!* — modo de falha, estado de falha, e o que uma fronteira deve devolver quando o outro lado quebra.
- **caso falseador.** Agentes que se recuperam igualmente bem de exceção crua e de erro estruturado. Se a forma do erro não muda a próxima ação, o contrato é enfeite.

### validade-de-construto

**Validade de construto** · modelo · doutrinario

Distância entre a capacidade que se quer medir e o número que a métrica produz. nDCG mede ordenação contra um gabarito, não mede se o agente respondeu certo; a pergunta que o conceito obriga é qual mundo faria esse número subir sem a capacidade melhorar. Enquanto essa resposta não estiver escrita, a métrica é proxy sem contrato e a subida dela não é evidência de nada. Exemplo: gold set cujas perguntas foram escritas olhando os documentos indexados mede fidelidade da recuperação ao próprio índice, e melhora quando o índice fica mais previsível.

- **obra necessária.** Cronbach & Meehl, "Construct Validity in Psychological Tests" (1955) — onde o problema foi formulado como problema, antes de virar checklist.
- **caso falseador.** Métrica cuja subida sempre corresponde a ganho observado em uso real, em toda faixa. Validade demonstrada torna a pergunta ociosa.

### piso-de-controle

**Piso de controle** · processo · doutrinario · pai proposto: `validade-de-construto`

Braço de comparação escolhido para ser fraco. Sem piso, métrica alta não distingue sistema bom de tarefa fácil: se o modelo pequeno e o pipeline sem recuperação acertam quase tanto, o que está sendo medido é a pergunta e não o sistema. O piso não existe para ser batido, existe para calibrar a régua. Exemplo: rodar o mesmo conjunto com um gerador declaradamente inferior; empate revela que as perguntas não discriminam e o defeito está no conjunto, não no arm em teste.

- **obra necessária.** Hastie, Tibshirani & Friedman, *The Elements of Statistical Learning* — baseline e a disciplina de comparar contra o trivial antes de comparar contra o rival.
- **caso falseador.** Conjunto em que o piso vai a zero e o sistema a um, sempre. Separação máxima dispensa calibração.

### juiz-modelo

**Juiz-modelo** · processo · doutrinario

Usar um modelo para avaliar a saída de outro. É o único caminho viável para medir qualidade de síntese em escala, e chega com vieses próprios: prefere resposta longa, prefere o próprio estilo, e concorda demais com quem lhe entregou o contexto. Juiz é instrumento, e instrumento se calibra contra julgamento humano antes de valer como medida. Exemplo: juiz que pontua fidelidade de citação e dá nota alta a resposta que cita a fonte certa para a frase errada — a checagem estrutural (a citação existe? aponta o trecho que sustenta?) é determinística e precisa vir antes dele, nunca depois.

- **obra necessária.** Falta obra fechada. Existe literatura recente sobre viés de posição, verbosidade e auto-preferência em LLM-as-a-judge; o que não existe é o tratado que trate o juiz-modelo como instrumento de medição — com erro, viés e curva de calibração — em vez de oráculo.
- **caso falseador.** Concordância alta e estável entre juiz-modelo e juiz humano em todas as faixas de qualidade. Instrumento calibrado dispensa a ressalva.

### abstencao-calibrada

**Abstenção calibrada** · processo · doutrinario

Devolver "não sei" quando não se sabe, na proporção certa. Duas taxas se movem em sentidos opostos — recusar o que era respondível e responder o que não era coberto — e um limiar único escolhe o ponto de troca entre elas; não existe valor que zere as duas. Abstenção é resposta, não falha do sistema, e a única medida honesta é o par de taxas, jamais um escalar. Exemplo: gate por similaridade de vetor passa alto para vizinho temático e reprova pergunta bem coberta com vocabulário incomum; trocar por revisor que lê pergunta e trecho juntos move a curva inteira, e o limiar tem de ser reescolhido — herdar o antigo é herdar um ponto de operação que não existe mais.

- **obra necessária.** Geifman & El-Yaniv, "Selective Classification for Deep Neural Networks", pelo lado da recusa; Guo et al., "On Calibration of Modern Neural Networks", pelo lado do escore que sustenta o limiar.
- **caso falseador.** Domínio em que responder errado custa o mesmo que não responder. Sem assimetria de custo, abstenção não decide nada.

### vizinho-plausivel

**Vizinho plausível** · fenomeno · natural

O trecho recuperado trata de assunto adjacente ao perguntado, não do assunto. É o modo de falha mais caro da recuperação porque passa em toda checagem superficial: escore alto, vocabulário batendo, documento legítimo, resposta fluente e errada. A causa é que similaridade mede proximidade temática, e proximidade temática não é identidade de conceito. Exemplo: pergunta sobre LGPD recuperando ISO 27701 — norma de privacidade, que não responde por lei brasileira. Nenhum sinal do pipeline separa esse caso de um acerto.

- **obra necessária.** Saracevic, "Relevance: A Review of the Literature" — a separação entre relevância tópica e relevância para a necessidade de informação, que é exatamente a fenda por onde o vizinho passa.
- **caso falseador.** Corpus de domínio único, sem obras adjacentes. Sem vizinho não há vizinho plausível, e o escore volta a valer como prova.

### fossilizacao-de-memoria

**Fossilização de memória** · fenomeno · natural

Fato verdadeiro no momento da escrita que segue sendo lido depois de deixar de ser verdade. Memória de agente acumula por adição e quase nunca por remoção: nada no substrato marca que um fato foi superado, e o registro velho carrega a mesma autoridade do novo. É o principal modo de falha de memória persistente e é silencioso — o agente age com convicção sobre estado que não existe mais. Exemplo: memória que registra um embedder já trocado; a dimensão do vetor é a mesma, o serviço responde, e a afirmação sobre o índice sai errada sem nenhum erro aparecer em lugar nenhum.

- **obra necessária.** Kleppmann, *Designing Data-Intensive Applications* — dado derivado, obsolescência, e por que sistema que só acrescenta precisa de mecanismo explícito de superação.
- **caso falseador.** Domínio cujos fatos não mudam. Em corpus estático, memória não fossiliza e acumular é seguro.

### invalidacao-na-escrita

**Invalidação na escrita** · processo · instituido · pai proposto: `fossilizacao-de-memoria`

Marcar o fato antigo como superado no ato de escrever o novo. É o mecanismo que falta na maioria dos substratos de memória, e falta por assimetria de custo: escrever é barato e invalidar é manual, então não acontece. Exige que o fato novo carregue a que ele se opõe — não basta gravar "o embedder é X", é preciso gravar que isso substitui o que dizia outra coisa. Exemplo: `Substitui: <caminho> (<data>)` no topo do documento torna a superação legível para quem consulta; a mesma informação deixada só no histórico do Git não é lida por ninguém que abra o documento.

- **obra necessária.** Kleppmann de novo, pelo lado de CDC e invalidação de cache; serve também norma de gestão documental que trate vigência e revogação de versão.
- **caso falseador.** Leitura que sempre vai à fonte primária em vez do registro derivado. Sem cópia não há o que invalidar.

### procedencia-de-assercao

**Procedência de asserção** · modelo · doutrinario

Quem disse, com que estatuto. Um histórico de conversa mistura o que o humano decidiu, o que o agente sugeriu, o que foi levantado como hipótese e o que foi transcrito de terceiro — e tudo isso, relido depois, tem a mesma aparência de texto afirmado. Sem procedência, a sugestão do próprio agente volta como decisão do dono, que é a forma mais direta de o sistema fabricar autoridade a partir de si mesmo. Exemplo: resumo de sessão que registra "decidiu-se por X" quando o que houve foi o agente propor X e o humano responder "interessante".

- **obra necessária.** W3C PROV-DM / *The Open Provenance Model* — entidade, atividade e agente, que é a estrutura mínima para separar quem gerou do que foi gerado.
- **caso falseador.** Memória composta apenas de asserções do dono. Fonte única torna a marcação supérflua.

### cache-de-prefixo

**Cache de prefixo** · processo · instituido

Reaproveitar o estado de atenção já calculado para o começo do prompt. O custo de gerar não é linear no tamanho do prompt: prefixo idêntico entre chamadas se computa uma vez e se reusa, o que transforma a ordem do prompt em decisão de custo e não só de qualidade. Regra que decorre: o estável primeiro — persona, manifesto, instrução — e o variável depois — pergunta, evidência recuperada. Exemplo: injetar timestamp no topo do system prompt derruba o acerto de cache a zero, porque o prefixo nunca mais é idêntico; o campo custa oito tokens e a decisão custa a sessão inteira.

- **obra necessária.** Kwon et al., "Efficient Memory Management for Large Language Model Serving with PagedAttention" (vLLM, 2023) — o mecanismo descrito junto com o preço em memória que ele cobra.
- **caso falseador.** Serving sem reuso de prefixo, ou prompts sem parte estável. Sem prefixo comum, a ordem não muda custo.

### orcamento-de-vram

**Orçamento de VRAM** · modelo · doutrinario

A memória da placa é o teto que decide o que roda junto. Pesos, cache de atenção e ativação disputam o mesmo espaço, e a conta nunca é do modelo isolado: embedder residente, revisor cross-encoder e gerador coexistindo mudam o que sobra para janela de contexto e para concorrência. O orçamento decide antes da qualidade — modelo que não cabe não tem métrica. Exemplo: em 16 GB, com um revisor ocupando ~1,1 GiB em fp16, aumentar o pool de candidatos não custa acurácia, custa a possibilidade de manter o gerador carregado ao mesmo tempo.

- **obra necessária.** Williams, Waterman & Patterson, "Roofline: An Insightful Visual Performance Model", para separar limite por memória de limite por cálculo; e o paper do vLLM para a contabilidade do cache de atenção.
- **caso falseador.** Inferência sempre remota, no hardware do fornecedor. O teto vira preço e o orçamento muda de moeda — mas não deixa de existir.

### degradacao-por-quantizacao

**Degradação por quantização** · fenomeno · natural · pai proposto: `orcamento-de-vram`

Reduzir a precisão numérica dos pesos custa qualidade, e o custo não é uniforme. A perda média em benchmark costuma ser pequena, mas se concentra: cauda longa, raciocínio de muitos passos e línguas menos representadas degradam bem mais que a média sugere, porque a informação que a quantização joga fora mora nos outliers de ativação. É o preço de caber no orçamento, e se mede na tarefa — nunca se aceita do card do modelo. Exemplo: modelo de 27B em q4 que mantém a nota de conhecimento geral e perde aderência a formato estruturado em resposta longa; a métrica publicada não vê, o loop agêntico vê no primeiro parse quebrado.

- **obra necessária.** Dettmers et al., "LLM.int8()" e Frantar et al., "GPTQ" — mecanismo da quantização e onde a perda se aloja.
- **caso falseador.** Paridade medida na própria tarefa entre fp16 e q4, ao longo de toda a distribuição. Se não degrada onde importa, quantizar é decisão livre.

---

## claudinho-conhecimento

### sortal-fornecedor-de-identidade

**Sortal fornecedor de identidade** · modelo · doutrinario

Tipo que carrega o critério de contagem e de reidentificação das suas instâncias. Todo indivíduo instancia exatamente um desses tipos, e é dele — não do rótulo mais conveniente — que vem a resposta para "é o mesmo ou é outro". Sem ele, entidade nenhuma tem condição de identidade e qualquer deduplicação vira arbítrio de quem está com o teclado. Exemplo: `obra` fornece identidade (duas edições da mesma obra são a mesma obra); `referência do acervo` não fornece, é papel que uma obra desempenha perante um domínio.

- **obra necessária.** Giancarlo Guizzardi, *Ontological Foundations for Structural Conceptual Models* (2005) — é a obra que dá a régua de sortal, papel e fase em forma aplicável a modelo conceitual, não só a metafísica. Serve também a `rigidez-de-tipo` e a `relator-de-relacao`.
- **caso falseador.** Uma entidade do modelo cuja identidade seja decidida sem apelo a tipo nenhum — chave técnica basta, ninguém jamais discute se dois registros são o mesmo indivíduo, e a fusão de duplicatas nunca gera disputa.

### rigidez-de-tipo

**Rigidez de tipo** · disposicao · doutrinario · pai proposto: `sortal-fornecedor-de-identidade`

Propriedade de um tipo aplicar-se necessariamente a cada instância durante toda a existência dela. Tipo rígido não se perde sem que o indivíduo deixe de existir; tipo anti-rígido pode ser assumido e abandonado com o indivíduo intacto. A distinção decide o que vira classe e o que vira atributo temporal ou associação datada — modelar como classe rígida algo que a instância perde produz mudança de identidade espúria toda vez que o estado muda. Exemplo: `pessoa` é rígido; `dono de domínio` é anti-rígido, e tratar os dois como o mesmo tipo de coisa faz a troca de dono parecer morte e nascimento.

- **obra necessária.** Guizzardi, *Ontological Foundations for Structural Conceptual Models*; complementar com a literatura de OntoUML aplicada (Guizzardi et al., *Ontology-Driven Conceptual Modeling*) para os padrões de kind/role/phase já formalizados.
- **caso falseador.** Um modelo em que toda classe declarada se comporte igual sob mudança de estado — nenhuma reclassificação de instância jamais force pergunta sobre identidade.

### relator-de-relacao

**Relator de relação** · modelo · doutrinario

Entidade que existe para fundamentar uma relação material entre duas outras. É o portador das propriedades da relação — data, condição, autoridade, escopo — e o que torna a relação falseável em vez de mero par ordenado. Sem relator explícito, toda relação com qualificação vira atributo pendurado em uma das pontas, e a pergunta "desde quando, por decisão de quem, sob que régua" não tem onde morar. Exemplo: `obra trata de domínio` não é um par: tem quem classificou, quando, com que confiança — isso é um relator, não um campo em `obra`.

- **obra necessária.** Guizzardi, *Ontological Foundations for Structural Conceptual Models*, capítulos sobre relações materiais e moments; para eventos, o desdobramento em UFO-B (Guizzardi et al., *Towards Ontological Foundations for the Conceptual Modeling of Events*).
- **caso falseador.** Toda relação do modelo ser satisfeita por par ordenado simples — nenhuma precisar de data, autor, condição de vigência ou grau, e nenhuma disputa surgir sobre quando a relação passou a valer.

### dependencia-existencial

**Dependência existencial** · fenomeno · natural

Condição em que um indivíduo só pode existir havendo outro indivíduo específico. Decide cardinalidade mínima, propagação de exclusão e a fronteira entre entidade própria e parte de outra. Sem ela declarada, apaga-se o pai e ficam órfãos que o modelo diz serem válidos e o mundo diz serem nada. Exemplo: um trecho indexado depende existencialmente da obra de onde foi extraído; uma anotação de leitura, não — sobrevive à saída da obra do acervo e precisa de destino próprio.

- **obra necessária.** Peter Simons, *Parts: A Study in Ontology* — é onde dependência, fundação e parte-todo estão separadas com rigor suficiente para virar regra de modelo; a literatura de modelagem cita mas não deriva.
- **caso falseador.** Todas as exclusões do sistema serem seguras em qualquer ordem, sem cascata e sem órfão, porque nenhuma entidade tem sua existência condicionada a outra.

### fundamento-unico-de-divisao

**Fundamento único de divisão** · modelo · doutrinario

Regra de que cada nível de uma classificação se divide por um só critério. Divisão com dois critérios no mesmo nível produz classes que se sobrepõem e casos que caem em duas ao mesmo tempo, e a partir daí nenhuma pergunta sobre pertencimento tem resposta única. É o teste mais barato para saber se uma hierarquia proposta é hierarquia ou é lista com recuo. Exemplo: dividir domínios em "técnico, jurídico e urgente" mistura assunto com prioridade — a norma jurídica urgente pertence a dois ramos, e a taxonomia deixou de decidir.

- **obra necessária.** S. R. Ranganathan, *Prolegomena to Library Classification* — os cânones de divisão estão lá enunciados como regra operável; a raiz lógica está em Aristóteles, mas não em forma aplicável a esquema de classificação.
- **caso falseador.** Uma classificação em uso com critérios misturados por nível que jamais produza item em duas classes irmãs nem disputa de alocação.

### analise-facetada

**Análise facetada** · processo · doutrinario · pai proposto: `fundamento-unico-de-divisao`

Decomposição de um assunto em eixos independentes antes de qualquer hierarquia. Cada eixo classifica sozinho e combina-se com os outros na hora da consulta, o que evita a explosão combinatória de uma árvore enumerativa e permite recorte que ninguém previu ao montar o esquema. Sem isso, todo cruzamento novo exige ramo novo, e o esquema envelhece a cada pergunta inédita. Exemplo: domínio, coleção, frente e fase são eixos ortogonais; enumerá-los como uma árvore só produziria um ramo morto para cada combinação que ninguém usou.

- **obra necessária.** Ranganathan, *Prolegomena to Library Classification* (PMEST); para a versão moderna e operável, Brian Vickery, *Faceted Classification: A Guide to Construction and Use of Special Schemes*.
- **caso falseador.** Um domínio cujo assunto se esgote em eixo único — toda pergunta legítima respondida por um só ramo, sem cruzamento entre dimensões.

### pre-coordenacao

**Pré-coordenação** · processo · doutrinario · pai proposto: `analise-facetada`

Montagem do assunto composto no momento da indexação, e não no momento da busca. Decide se "desenvolvimento seguro de software" é um termo lavrado ou o encontro de dois termos na consulta — e com isso decide o tamanho do vocabulário, o custo de manutenção e o que o usuário precisa saber para achar. Sem a escolha declarada, o vocabulário cresce com compostos ad hoc que ninguém consegue mais reconciliar com suas partes. Exemplo: lavrar `criptografia em repouso` como conceito próprio é pré-coordenar; deixar `criptografia` + `dado em repouso` combinarem na consulta é pós-coordenar. As duas decisões são defensáveis; não escolher não é.

- **obra necessária.** ANSI/NISO Z39.19, *Guidelines for the Construction, Format and Management of Monolingual Controlled Vocabularies*, e ISO 25964-1 — as duas tratam a escolha como decisão de projeto do vocabulário, com consequência declarada.
- **caso falseador.** Um acervo em que todo assunto seja atômico — nenhum composto legítimo, nenhuma consulta precisando de dois termos juntos.

### distincao-obra-manifestacao

**Distinção obra–manifestação** · modelo · doutrinario

Separação entre o conteúdo intelectual, sua versão textual, sua materialização e o exemplar concreto. Decide o que conta como duplicata, a que nível se prende cada atributo e qual camada sofre sucessão. Sem ela, a segunda edição vira obra nova, o PDF vira obra, e a contagem do acervo deixa de significar coisa alguma. Exemplo: a ABNT NBR ISO/IEC 27001 é uma obra; a versão 2022 é uma expressão; o PDF baixado é manifestação; o arquivo no MinIO é item — `sucede` opera entre expressões, não entre arquivos.

- **obra necessária.** IFLA *Library Reference Model* (LRM, 2017) — consolida e corrige FRBR; é a única formulação da distinção com definições e restrições declaradas em vez de exemplos.
- **caso falseador.** Um acervo em que cada obra tenha exatamente um arquivo, para sempre, sem edição, tradução, revisão ou formato alternativo.

### garantia-literaria

**Garantia literária** · processo · doutrinario

Critério de admitir um termo ao vocabulário apenas mediante evidência de uso na literatura do campo. O que autoriza o termo é ele aparecer no que se escreve e no que se pergunta, não a elegância da árvore que ele completa. Sem essa régua, o vocabulário cresce por simetria — ramos criados porque a estrutura pedia, não porque alguém precisou dizer aquilo. Exemplo: criar um subdomínio porque os irmãos têm três cada é o vício exato que a garantia literária proíbe.

- **obra necessária.** E. Wyndham Hulme, *Principles of Book Classification* (1911), onde o critério é formulado; a operacionalização moderna, incluindo garantia de uso e garantia organizacional, está em ANSI/NISO Z39.19.
- **caso falseador.** Um vocabulário cujos termos criados por simetria estrutural tenham depois se mostrado tão usados quanto os criados a partir de evidência de uso.

### politica-de-formacao-de-acervo

**Política de formação de acervo** · processo · instituido

Documento que declara, antes do caso concreto, o que entra e o que não entra na coleção. Fixa escopo temático, nível de profundidade por domínio, critérios de idioma, atualidade e autoridade da fonte, e nomeia quem decide o caso duvidoso. Sem ela, a fronteira do acervo é a soma das decisões pontuais de quem estava ingerindo naquele dia, e não há como recusar uma obra sem parecer arbitrário. Exemplo: recusar um blog post excelente porque a política exige obra com autoridade declarada é uma decisão defensável; recusá-lo por gosto é a mesma decisão sem defesa.

- **obra necessária.** Evans & Saponaro, *Developing Library and Information Center Collections*, complementado pelo *Guide for Written Collection Policy Statements* da ALA — o segundo dá a forma do documento, o primeiro o método de decidir profundidade por assunto.
- **caso falseador.** Um acervo em que nenhuma candidatura de obra tenha sido recusada nem gerado dúvida de escopo em toda a sua história.

### desbaste-de-acervo

**Desbaste de acervo** · processo · instituido · pai proposto: `politica-de-formacao-de-acervo`

Retirada deliberada de obras da coleção segundo critério declarado. É o lado simétrico da admissão e o único mecanismo que impede o acervo de virar depósito: obra superada, nunca recuperada, fora de escopo ou substituída por edição posterior sai, e sai com registro do motivo. Sem desbaste, a precisão do RAG cai por acúmulo e ninguém consegue apontar a culpa em obra alguma. Exemplo: mantida a edição de 2013 ao lado da de 2022, a recuperação passa a devolver as duas e o leitor decide por conta própria qual vale — decisão que era do curador.

- **obra necessária.** *CREW: A Weeding Manual for Modern Libraries* (Texas State Library) — é o único método de desbaste com critérios operacionais e não apenas princípios; nada equivalente existe para acervo digital curado, o que é em si um achado.
- **caso falseador.** Uma coleção que cresça indefinidamente sem que a adição de obras degrade a recuperação nem produza obra jamais consultada.

### controle-de-autoridade

**Controle de autoridade** · processo · instituido

Fixação de uma forma canônica para cada entidade nomeada, com todas as variantes remetidas a ela. Decide qual grafia é a válida, registra as rejeitadas como sinônimo de entrada, e mantém o vínculo quando a forma canônica muda. Sem isso, a mesma norma entra três vezes com três grafias e o cruzamento por autor ou por emissor deixa de fechar. Exemplo: "ISO/IEC 27001", "ISO 27001" e "NBR ISO/IEC 27001" precisam apontar para um registro de autoridade só, com a distinção entre norma internacional e adoção nacional resolvida ali e não em cada citação.

- **obra necessária.** IFLA *Functional Requirements for Authority Data* (FRAD) para o modelo, e Z39.19 para a mecânica de termo preferido e variante — a segunda sozinha não cobre entidades nomeadas, a primeira sozinha não vira procedimento.
- **caso falseador.** Um acervo em que toda entidade nomeada tenha uma só forma corrente, estável no tempo, sem sigla, sem tradução e sem renomeação do emissor.

### descricao-multinivel

**Descrição multinível** · modelo · instituido

Regra de declarar cada informação no nível mais alto a que se aplica e não repeti-la abaixo. O que vale para o conjunto fica no conjunto; o nível inferior só carrega o que o distingue dos irmãos. Decide onde um atributo mora e resolve a pergunta que mais gera divergência de catalogação: repetir ou herdar. Sem a regra, o mesmo dado é declarado em três níveis e as três cópias divergem na primeira atualização. Exemplo: a coleção declara proveniência e restrição de uso; a obra individual só declara o que difere — e nunca redeclara o que herdou.

- **obra necessária.** ISAD(G) — *Norma Geral Internacional de Descrição Arquivística*, Conselho Internacional de Arquivos, especialmente as regras de descrição do geral para o específico e de não-repetição da informação.
- **caso falseador.** Um acervo plano em que nenhum atributo seja compartilhado por conjunto de obras — cada obra descrita inteiramente por si, sem herança possível.

### proveniencia-de-assercao

**Proveniência de asserção** · modelo · instituido

Registro de quem afirmou o quê, quando, a partir de qual fonte e por qual processo. Cada afirmação da base carrega o agente, a atividade e o insumo que a geraram, o que permite revogar em bloco tudo que veio de um processo depois desacreditado. Sem proveniência, classificação feita por script e classificação feita por dono de domínio são indistinguíveis, e a regra de nunca sobrescrever julgamento humano não tem como ser aplicada. Exemplo: descoberto um erro no classificador automático, com proveniência revogam-se as 200 asserções dele e preservam-se as 40 humanas; sem proveniência, revisa-se tudo à mão ou não se revisa nada.

- **obra necessária.** W3C *PROV-DM* e *PROV-O* — o modelo entidade/atividade/agente é o único padrão fechado sobre isso; a implementação em grafo é decisão de outra cadeira, o compromisso semântico é meu.
- **caso falseador.** Uma base em que toda asserção tenha a mesma origem e a mesma confiabilidade — nenhuma revogação seletiva jamais necessária.

### designacao-de-fonte-autoritativa

**Designação de fonte autoritativa** · processo · instituido

Ato de nomear, por elemento de dado, qual sistema tem a palavra final. Não é onde o dado está armazenado nem onde é mais fácil de ler: é onde a divergência se resolve. Decide o sentido da sincronização e encerra a discussão de quem venceu quando wiki, banco e repositório discordam. Sem a designação por elemento, cada conflito vira negociação e a cópia mais recente ganha por acidente. Exemplo: se a wiki é autoritativa para a definição do conceito e o Postgres para a associação obra–domínio, um script que reescreva definição a partir do banco está errado por construção, não por bug.

- **obra necessária.** DAMA *DMBOK2*, capítulo de Master and Reference Data Management — é onde system of record, system of reference e golden record estão separados; Berson & Dubov, *Master Data Management and Data Governance*, para o desenho da arbitragem.
- **caso falseador.** Um ecossistema com um só sistema de escrita por elemento de dado, em que divergência entre cópias seja impossível.

### obsolescencia-declarada

**Obsolescência declarada** · processo · instituido

Marcação explícita de um registro como superado, com apontamento para o que o substitui. O registro velho não some — permanece endereçável e legível, mas informa ao leitor que não vale mais e para onde ir. Decide o destino de decisão revogada e de página substituída, e é a única alternativa honesta a apagar (que quebra referência) ou a deixar em pé (que engana quem chega depois). Exemplo: uma decisão de 2025 revogada em 2026 continua acessível pelo endereço citado no chat de 2025, exibindo a revogação e o sucessor no topo.

- **obra necessária.** RFC 2026, *The Internet Standards Process*, pelos mecanismos de obsoletes/updates e pela distinção entre retirar e substituir; complementar com ISO/IEC Directives Parte 1 para o ciclo de revisão e retirada de norma.
- **caso falseador.** Um corpo de registros em que nenhuma decisão jamais seja revogada ou substituída, ou em que ninguém cite endereço de registro fora do próprio registro.

### unidade-de-registro

**Unidade de registro** · modelo · instituido

Critério do que merece página própria. Fixa o grão do sistema de registro — um assunto por página, autossuficiente para quem chega por busca e não por navegação — e com isso decide toda disputa de partir ou juntar. Sem o critério, a wiki oscila entre página monolítica que ninguém acha e migalha que não se sustenta sozinha, e cada autor resolve por conta própria. Exemplo: se o critério é "uma unidade de registro por coisa que pode ser citada isoladamente", conceito tem página e cada atributo do conceito não tem.

- **obra necessária.** Mark Baker, *Every Page is Page One* — trata o grão do documento para leitor que chega por busca, que é exatamente o caso da wiki; Rosenfeld, Morville & Arango, *Information Architecture*, para o vínculo entre grão e navegação.
- **caso falseador.** Um registro consumido apenas em leitura sequencial do começo ao fim, em que nenhuma página seja alcançada isoladamente por busca ou por link direto.

### objetivo-de-aprendizagem-observavel

**Objetivo de aprendizagem observável** · modelo · doutrinario

Enunciado do que o aprendiz fará ao final, em verbo verificável, com condição e critério. Decide se o material pode ser avaliado e se a trilha pode ser dada por concluída; verbo mental como "entender" ou "conhecer" não decide nada porque não há evidência que o contradiga. Sem objetivo observável, capacitação termina quando o material acaba, e não quando o aprendiz consegue fazer. Exemplo: "compreender ontologia" não é objetivo; "dado um modelo conceitual, apontar os tipos anti-rígidos modelados como classe rígida" é.

- **obra necessária.** Robert Mager, *Preparing Instructional Objectives*, pela forma do enunciado; Anderson & Krathwohl, *A Taxonomy for Learning, Teaching and Assessing*, pela classificação dos verbos por nível cognitivo.
- **caso falseador.** Uma formação em que o desempenho posterior dos aprendizes seja igual tendo ou não objetivos declarados em forma observável.

### sequenciamento-por-pre-requisito

**Sequenciamento por pré-requisito** · processo · doutrinario · pai proposto: `objetivo-de-aprendizagem-observavel`

Ordenação da trilha pela dependência cognitiva entre habilidades, não pela ordem em que os assuntos foram escritos. Deriva-se decompondo a tarefa final até as habilidades que já se possuem; cada passo só entra quando seus pré-requisitos estão dominados. Sem isso, a trilha reproduz o sumário do material e o aprendiz trava em um ponto cuja causa está três módulos atrás. Exemplo: ensinar critério de identidade antes de tipo rígido é ordem cognitiva; ensinar na ordem dos capítulos é ordem editorial, e as duas coincidem por sorte.

- **obra necessária.** Robert Gagné, *The Conditions of Learning*, pela hierarquia de aprendizagem e análise de pré-requisitos; van Merriënboer & Kirschner, *Ten Steps to Complex Learning*, para tarefa complexa e integrada, que é o caso aqui.
- **caso falseador.** Uma trilha cujas unidades sejam permutáveis em qualquer ordem sem perda de desempenho.

### avaliacao-criterial

**Avaliação criterial** · processo · doutrinario · pai proposto: `objetivo-de-aprendizagem-observavel`

Aferição do desempenho contra um critério fixo, e não contra o desempenho dos demais. O ponto de corte é definido antes da aplicação, a partir do que a tarefa real exige; a nota diz o que a pessoa é capaz de fazer, não em que posição ficou. Decide quem está habilitado a operar uma capability e torna a habilitação transferível entre turmas. Sem critério fixo, a habilitação depende de quem mais estava na sala. Exemplo: "acerta 9 de 10 classificações de tipo em modelo inédito" habilita; "está acima da média da turma" habilita em turma fraca e reprova em turma forte a mesma pessoa.

- **obra necessária.** W. James Popham, *Criterion-Referenced Measurement*, pela derivação do ponto de corte a partir do domínio da tarefa; Mager serve aos dois conceitos, já que o critério do objetivo é o mesmo da avaliação.
- **caso falseador.** Uma habilitação em que o desempenho relativo à turma preveja o desempenho na tarefa real tão bem quanto o critério absoluto.

---

## claudinha-gestao-estrategica

### linha-de-corte

**Linha de corte** · processo · instituido

A linha de corte é a fronteira declarada de uma carteira ordenada: acima dela o que a capacidade cobre, abaixo o que fica sem ser feito e é dito em voz alta. O que decide é a capacidade real do período, não o mérito de cada item — mérito só ordena, capacidade corta. Sem linha, a ordenação vira lista de desejos e todo item permanece formalmente vivo, o que transfere o corte para o esgotamento e não para a decisão. Exemplo: sete features ordenadas com a linha entre a terceira e a quarta, e as quatro de baixo carregando por escrito o que se perde por não fazê-las.

- **obra necessária.** Cooper, "Winning at New Products" — o Stage-Gate trata a carteira como lista ranqueada limitada por recurso, com corte explícito no gate; é a obra que descreve o corte como ato de portfólio e não como falha de execução.
- **caso falseador.** Uma carteira em que nenhum item abaixo da linha deixa de ser feito no período e todos entram por folga de capacidade — se a linha nunca vincula, ela não decidiu nada e o critério de capacidade estava errado.

### custo-de-atraso

**Custo de atraso** · modelo · doutrinario · pai proposto: `linha-de-corte`

Custo de atraso é o valor que se perde por unidade de tempo enquanto uma iniciativa não está pronta. É o que permite comparar itens incomparáveis: dois trabalhos de tamanho igual e custo de atraso diferente têm ordem definida, e dois de custo de atraso igual se ordenam pelo menor tamanho. Sem ele, a fila é ordenada por quem falou mais alto ou pelo que já está começado. Exemplo: um bloqueador de outras três frentes tem custo de atraso multiplicado pelo que ele trava, e sobe na fila mesmo tendo valor próprio baixo.

- **obra necessária.** Reinertsen, "The Principles of Product Development Flow" — é a obra que formaliza cost of delay e a regra de sequenciamento por custo de atraso dividido por duração.
- **caso falseador.** Duas iniciativas com custos de atraso muito distintos cuja inversão de ordem não produz perda observável — se a ordem não muda o resultado, o custo estimado era ficção.

### suficiencia-decisoria

**Suficiência decisória** · disposicao · doutrinario

Suficiência decisória é o estado de um pacote em que informação adicional não mudaria a escolha do decisor. É a propriedade que encerra a coleta: enquanto um dado novo puder inverter a decisão, o pacote está incompleto; quando nenhum puder, continuar apurando é custo puro. O que quebra sem ela é o pacote infinito — a cadeira que empacota vira a cadeira que decide, por acúmulo. Exemplo: para escolher entre duas ordens de execução, saber o esforço exato de cada uma é irrelevante se ambas cabem no período; o dado que decide é a precedência, e só ele precisa entrar.

- **obra necessária.** Howard & Abbas, "Foundations of Decision Analysis" — o valor da informação (e o valor da clarividência como teto) é a régua que diz quando parar de apurar.
- **caso falseador.** Um pacote declarado suficiente cuja decisão se inverte com o primeiro dado que aparece depois — a suficiência era conveniência de quem empacotou.

### direito-de-decisao

**Direito de decisão** · disposicao · instituido

Direito de decisão é a alocação nominal de quem fecha uma classe de questão, separada de quem executa, de quem opina e de quem é afetado. O que decide é a classe da matéria, não a hierarquia nem quem levantou o assunto. Sem ele, toda questão sobe para o único humano ou desce para quem estava com o teclado na mão, e a mesma matéria é decidida duas vezes com respostas diferentes. Exemplo: vocabulário canônico é do head de conhecimento — quem monta a carteira leva a régua citada como insumo e não a reescreve, mesmo discordando.

- **obra necessária.** Blenko, Mankins & Rogers, "Decide & Deliver" (framework RAPID) — é a obra que separa os papéis de recomendar, concordar, executar, insumo e decidir como alocações distintas.
- **caso falseador.** Uma matéria com dono nominal claro que, ocorrendo três vezes, é decidida três vezes por cadeiras diferentes sem que ninguém registre conflito — o direito estava escrito e não vinculava.

### limite-de-iniciativas-ativas

**Limite de iniciativas ativas** · processo · instituido · pai proposto: `gargalo-de-decisao`

Limite de iniciativas ativas é o teto numérico de frentes que podem estar em andamento simultâneo, fixado antes de saber quais serão. O que decide é o gargalo do sistema, não a soma das capacidades individuais: cada frente ativa consome atenção do decisor mesmo quando ninguém está executando nela. Sem o teto, começar é grátis e terminar é caro, e a carteira acumula trabalho parado que já custou o preço de entrada. Exemplo: com teto de três, abrir uma quarta frente exige nomear qual das três volta ao dormente — a pergunta "o que sai" passa a ser obrigatória por construção.

- **obra necessária.** Anderson, "Kanban: Successful Evolutionary Change" — limite de WIP como política explícita de sistema; complementada por Reinertsen no efeito de fila.
- **caso falseador.** Um período em que o teto é dobrado e a taxa de conclusão dobra junto, sem aumento de retrabalho ou de tempo de ciclo — o limite estava abaixo da capacidade real e era arbitrário.

### gargalo-de-decisao

**Gargalo de decisão** · fenomeno · natural

Gargalo de decisão é a restrição de um sistema cujo recurso escasso é a atenção de quem decide, e não a capacidade de quem executa. Ele se reconhece pelo acúmulo de trabalho pronto-para-decidir na frente de uma pessoa; toda melhoria de execução a montante engorda essa fila em vez de encurtá-la. O que quebra sem o conceito é a leitura de que "falta gente" — subordinar o sistema ao gargalo significa reduzir decisões, não aumentar produção. Exemplo: quatro cadeiras executando em paralelo produzem quatro pacotes por dia para um único diretor humano; contratar uma quinta cadeira piora a vazão.

- **obra necessária.** Goldratt, "The Goal" — os cinco passos de focalização (identificar, explorar, subordinar, elevar, repetir) aplicados a um gargalo que é atenção humana e não máquina.
- **caso falseador.** Um período em que a fila de pacotes na frente do decisor encurta espontaneamente enquanto a produção das cadeiras aumenta — a restrição estava em outro lugar.

### reativacao-condicionada

**Reativação condicionada** · processo · instituido

Reativação condicionada é o arquivamento de uma iniciativa junto com o gatilho escrito que a traz de volta. O que decide não é a data nem a lembrança de alguém, é o evento nomeado no momento em que se manda para o dormente: qual fato, observável por quem, faz o item voltar à carteira. Sem o gatilho, dormente e morto ficam indistinguíveis na prática, e a reativação depende de memória individual. Exemplo: uma frente bloqueada por decisão externa dorme com o gatilho "publicação da norma X" — quem vê a publicação sabe que precisa mexer na carteira, sem precisar lembrar da frente.

- **obra necessária.** McGrath & MacMillan, "Discovery-Driven Growth" — planejamento por pressupostos e checkpoints; é a obra que trata compromisso adiado como opção mantida aberta, com teste declarado.
- **caso falseador.** Uma iniciativa dormente cujo gatilho ocorre e ninguém reativa, mesmo com o gatilho escrito e visível — o gatilho não era observável por ninguém em particular e o mecanismo é decorativo.

### dependencia-exogena

**Dependência exógena** · fenomeno · natural · pai proposto: `reativacao-condicionada`

Dependência exógena é o bloqueio de uma iniciativa por ato de quem está fora da nossa capacidade de decisão. Ela se distingue da dependência interna por um teste único: aumentar a prioridade não muda a data. O que quebra sem o conceito é a carteira contaminada por itens que ocupam posição alta e não andam, empurrando para baixo trabalho que andaria. Exemplo: um projeto travado em resposta de terceiro fica na carteira como se fosse escolha nossa e distorce toda a ordenação abaixo dele.

- **obra necessária.** PMI, "The Standard for Program Management" — tratamento de dependências externas e de restrições fora do controle do programa; serve também para separar o que é risco do que é bloqueio.
- **caso falseador.** Um item classificado como exógeno que destrava por pressão, insistência ou reformulação nossa — a dependência era interna e mal diagnosticada.

### criterio-de-encerramento

**Critério de encerramento** · processo · instituido · pai proposto: `linha-de-corte`

Critério de encerramento é a condição de morte de uma iniciativa, escrita no momento em que ela começa. O que decide é a condição pré-acordada, não o julgamento no calor da hora, quando já existe investimento feito e defensor nomeado. Sem ele, encerrar exige que alguém admita erro, e o custo social de admitir mantém viva a frente que já falhou. Exemplo: uma linha de trabalho aberta com "morre se, após duas rodadas, a saída ainda exigir revisão manual integral" morre por comparação, e não por briga.

- **obra necessária.** Duke, "Quit: The Power of Knowing When to Walk Away" — critérios de saída definidos ex ante (kill criteria) contra o viés de escalada de compromisso.
- **caso falseador.** Uma iniciativa que atinge o critério escrito e continua, com todos concordando que continuar é certo — o critério não capturava o que importava e o encerramento nunca foi função dele.

### precedencia-tecnica

**Precedência técnica** · fenomeno · natural

Precedência técnica é a relação entre dois trabalhos em que um não pode começar antes do outro terminar, por razão de matéria e não de conveniência. Ela se distingue da ordem preferida por um teste: inverter a precedência técnica produz retrabalho, inverter a preferência produz apenas desconforto. O que quebra sem a distinção é a carteira que trata toda ordem como negociável e descobre a dependência no meio da execução. Exemplo: identidade e autorização antes de agente externo — não é preferência de sequência, é a condição sem a qual o segundo trabalho não tem o que consumir.

- **obra necessária.** Goldratt, "Critical Chain" — cadeia de dependências e a diferença entre restrição de precedência e folga de agenda; complementada por qualquer tratamento formal de CPM.
- **caso falseador.** Uma precedência declarada técnica que é invertida em execução sem retrabalho nem perda — era preferência disfarçada de necessidade.

### fidelidade-do-rastreador

**Fidelidade do rastreador** · fenomeno · natural

Fidelidade do rastreador é o grau em que o instrumento que representa a carteira corresponde ao trabalho real. Toda decisão de portfólio é tomada sobre a representação, nunca sobre o trabalho; divergência silenciosa entre os dois invalida a decisão sem produzir sintoma até tarde. O que decide é a taxa de divergência observada, não a confiança na ferramenta. Exemplo: itens apagados que continuam aparecendo em consulta, ou identificadores que divergem entre a interface e o banco, produzem carteiras inteiras decididas sobre um retrato falso.

- **obra necessária.** Scott, "Seeing Like a State" — legibilidade imposta pelo instrumento e o que ela apaga do território; é a obra que trata a representação administrativa como distorção com consequência, não como espelho imperfeito.
- **caso falseador.** Uma carteira decidida sobre um rastreador comprovadamente divergente cujas decisões se mostram todas corretas ao fim do período — a divergência não tocava nada que decidia.

### mix-de-exploracao

**Mix de exploração** · modelo · doutrinario · pai proposto: `linha-de-corte`

Mix de exploração é a proporção declarada da carteira dedicada a trabalho de retorno incerto e prazo longo, contra trabalho de retorno conhecido e prazo curto. O que decide é a proporção fixada antes, não o mérito item a item: comparadas caso a caso, iniciativas exploratórias perdem sempre para as de retorno conhecido, e a carteira converge para manutenção sem que ninguém tenha decidido isso. Exemplo: reservar uma fatia fixa para spikes e frentes novas faz a comparação acontecer dentro da fatia, entre exploratórias, e não contra o que já dá retorno.

- **obra necessária.** March, "Exploration and Exploitation in Organizational Learning" — é o texto que formula o trade-off e mostra por que a seleção míope elimina exploração; complementado por Christensen no efeito de portfólio.
- **caso falseador.** Uma carteira sem fatia reservada que, ao longo de vários períodos, mantém sozinha a proporção de exploração — o mecanismo de reserva não era necessário e a convergência para manutenção não ocorre aqui.

### capacidade-de-dominio

**Capacidade de domínio** · modelo · doutrinario

Capacidade de domínio é o que uma organização é capaz de fazer numa matéria, enunciada como capacidade e não como função, processo ou time. A distinção decide: função descreve quem existe, processo descreve como se faz, capacidade descreve o que se consegue — e só a última permite perguntar o que falta sem partir da estrutura atual. Sem ela, todo diagnóstico de lacuna vira reorganograma. Exemplo: "decidir onde investir esforço" é capacidade; "gestão de portfolio" é a gerência que a exerce hoje, e as duas coisas mudam em ritmos diferentes.

- **obra necessária.** BIZBOK (Business Architecture Body of Knowledge) — o mapa de capacidades como camada estável, separada de estrutura organizacional e de processo; qualquer tratado sério de arquitetura de negócio serve.
- **caso falseador.** Um mapa de capacidades que muda toda vez que a estrutura organizacional muda — se acompanha o organograma, é organograma com outro nome.

### papel-instanciavel

**Papel instanciável** · modelo · instituido · pai proposto: `capacidade-de-dominio`

Papel instanciável é o papel definido de forma independente de quem o ocupa, executável em várias cópias simultâneas sem perda de identidade. O que decide é a especificação — remit, permissões, fronteiras, obrigações — e não a experiência acumulada de um ocupante. Sem o conceito, escrever papel para agentes é confundido com escrever descrição de cargo para pessoa, e importa pressupostos que não valem: continuidade, aprendizado entre ocupações, custo de substituição. Exemplo: duas instâncias do mesmo papel rodando em paralelo sobre matérias diferentes não são "duas pessoas no mesmo cargo" — são duas execuções da mesma especificação, e qualquer conflito entre elas é defeito da especificação.

- **obra necessária.** Wooldridge, Jennings & Kinny, metodologia Gaia para análise e design orientado a agentes — papéis definidos por responsabilidades, permissões, atividades e protocolos; é o tratamento que separa papel de ocupante por construção.
- **caso falseador.** Duas instâncias do mesmo papel produzindo saídas incompatíveis sobre a mesma matéria sem que a especificação contenha ambiguidade identificável — o papel dependia de algo não especificável.

### fronteira-negativa

**Fronteira negativa** · processo · instituido · pai proposto: `papel-instanciavel`

Fronteira negativa é a enunciação do que um papel não faz, escrita com a mesma força do que ele faz. O que decide é o comportamento sob ambiguidade: papel definido só pelo positivo se expande para o vácuo adjacente, porque ser útil é sempre a saída mais barata no turno. Sem ela, toda matéria sem dono é absorvida por quem estiver perto, e a repartição desenhada dura até a primeira pergunta fora do escopo. Exemplo: "não decido schema — aponto o dono e empacoto" impede que a cadeira de carteira decida schema por ninguém ter respondido a tempo.

- **obra necessária.** Uma obra sobre desenho de cargo e ambiguidade de papel — Kahn et al., "Organizational Stress: Studies in Role Conflict and Ambiguity" é a raiz; serve porque trata ambiguidade de papel como causa de comportamento, não como falha de redação.
- **caso falseador.** Um papel sem nenhuma fronteira negativa escrita que, sob matéria ambígua repetida, devolve a matéria em vez de absorvê-la — a negativa era redundante e a contenção vinha de outro lugar.

### deriva-de-papel

**Deriva de papel** · fenomeno · natural · pai proposto: `papel-instanciavel`

Deriva de papel é o afastamento gradual entre o que um papel faz na prática e o que sua especificação diz. Ela avança por incrementos que são individualmente razoáveis — um favor aqui, uma matéria adotada ali — e por isso não produz alarme em nenhum ponto isolado; o que a torna visível é a comparação entre a saída de hoje e a especificação, nunca entre a saída de hoje e a de ontem. Sem o conceito, manutenção de papel é reativa: só se reescreve depois do conflito. Exemplo: uma cadeira que passa a redigir o mérito para fechar pacotes rápido deixa de ser quem empacota e vira quem decide, sem nenhum turno em que a mudança tenha sido acordada.

- **obra necessária.** Uma obra sobre role-making e negociação de papel na prática — a tradição de Graen sobre role episodes, ou tratamento equivalente de job crafting; é preciso um texto que descreva a deriva como processo normal e não como indisciplina.
- **caso falseador.** Um papel comparado à especificação após muitos ciclos e encontrado idêntico, sem manutenção nenhuma no período — a deriva não é inevitável e o monitoramento é desnecessário.

### materia-orfa

**Matéria órfã** · fenomeno · natural · pai proposto: `fronteira-negativa`

Matéria órfã é o assunto que precisa de decisão e não cai no remit escrito de nenhum papel. Ela aparece na fronteira entre dois papéis bem definidos, e por isso o desenho de papéis não a elimina — quanto mais nítidas as fronteiras, mais visível o interstício. O que decide é a nomeação: órfã nomeada tem dono candidato e uma lista do que falta para ele aceitar; órfã silenciosa é adotada por quem a viu primeiro e desaparece como problema. Exemplo: uma matéria que exige régua de domínio e decisão de sequenciamento ao mesmo tempo não é de nenhum dos dois heads até que um deles aceite a régua do outro como insumo.

- **obra necessária.** Uma obra sobre lacunas de accountability em repartições formais — o tratamento clássico de zonas de indefinição em desenho organizacional, ou Coase e a tradição de custos de transação, que explica por que a fronteira sempre deixa resíduo.
- **caso falseador.** Uma repartição de papéis suficientemente detalhada em que, durante um período longo, nenhuma matéria nova cai fora de todos os remits — o interstício era efeito de definição frouxa, não estrutural.

### triagem-de-entrada

**Triagem de entrada** · processo · instituido

Triagem de entrada é a classificação de tudo que chega por destino, feita sem avaliar mérito. O que decide é uma pergunta única e mecânica — isso é acionável, e por quem — que separa em descartar, delegar, agendar, arquivar como referência e "requer decisão do titular". Misturar triagem com mérito é o defeito central: quem tria e julga ao mesmo tempo trava no primeiro item difícil e a entrada acumula atrás dele. Exemplo: um pedido que chega no meio do dia é classificado como "requer decisão" em cinco segundos e vai para o lote de decisões, sem que ninguém tenha pensado sobre ele ainda.

- **obra necessária.** Allen, "Getting Things Done" — o fluxo capturar/esclarecer/organizar é a formulação canônica da triagem como passo separado do fazer e do decidir.
- **caso falseador.** Uma entrada triada sem julgamento de mérito cujo destino se mostra sistematicamente errado na revisão — a classificação exigia mérito e a separação é impossível nesse domínio.

### suporte-a-funcao-executiva

**Suporte à função executiva** · modelo · doutrinario

Suporte à função executiva é o arranjo externo que substitui iniciação, sequenciamento, retenção de contexto e monitoramento de tempo quando esses recursos internos são escassos. O que decide o desenho é a natureza do déficit: função executiva prejudicada não se compensa com mais esforço nem com mais informação, e sim com estrutura fora da cabeça — o próximo passo visível, o gatilho externo, o contexto reapresentado em vez de recuperado. Sem o conceito, o apoio é desenhado para alguém que apenas está ocupado, e falha por excesso de opções apresentadas de uma vez. Exemplo: uma decisão apresentada como parágrafo denso não é decidida; a mesma decisão numerada, com a opção recomendada marcada, é decidida em segundos.

- **obra necessária.** Barkley, "Executive Functions: What They Are, How They Work, and Why They Evolved" — o modelo de função executiva como autorregulação dependente de suporte externo; complementado por qualquer tratado clínico sobre acomodação no adulto.
- **caso falseador.** Um decisor com déficit declarado que decide igualmente bem com material denso e com material estruturado — a estrutura era preferência estética e não acomodação.

### ponto-de-retomada

**Ponto de retomada** · disposicao · instituido · pai proposto: `suporte-a-funcao-executiva`

Ponto de retomada é a propriedade de um trabalho interrompido que permite recomeçá-lo sem reconstruir o contexto perdido. O que decide é o registro do que estava aberto no instante da parada — decisão tomada e não escrita, hipótese em teste, próxima ação — e não o resumo do que foi feito, que é justamente o que se recupera sozinho. Sem ele, cada retomada custa uma releitura integral e decisões já fechadas são relitigadas por não terem deixado rastro. Exemplo: um encerramento que registra "decidiu-se matar a frente X, motivo Y" evita que a sessão seguinte reabra X como se fosse pergunta em aberto.

- **obra necessária.** Gloria Mark, "Attention Span" — pesquisa empírica sobre interrupção e custo de retomada; é a obra que quantifica o que se perde e o que basta preservar.
- **caso falseador.** Retomadas de trabalho complexo que ocorrem sem custo mensurável mesmo sem registro nenhum do estado aberto — o contexto se reconstrói sozinho e o registro é cerimônia.

---

## claudinha-produto

### criterio-de-aceite-executavel

**Critério de aceite executável** · processo · doutrinario

Exigência escrita na forma de um teste que qualquer pessoa roda e vê passar ou falhar. O mecanismo é o deslocamento do juízo: a construção deixa de precisar do autor da exigência para saber se acertou, e a reprovação deixa de depender de quem estava na sala. Sem isso, queixa qualitativa não deixa rastro verificável e a versão seguinte cai pelo mesmo motivo — o caso vivo é a reprovação da interface do rastreador, cujo motivo nunca virou teste e por isso não protege o substituto.

- **obra necessária.** Gojko Adzic, *Specification by Example* — trata da conversão de exigência qualitativa em exemplo executável, que é exatamente o passo que falta.
- **caso falseador.** Uma queixa virada em teste, o teste passando, e o dono continuando a reprovar a mesma tela pelo mesmo motivo.

### porta-de-mao-unica

**Porta de mão única** · modelo · doutrinario

Decisão cujo custo de desfazer é ordens de grandeza maior que o de fazer. O mecanismo é a alocação de rigor: decisão barata de reverter se toma rápido e se corrige no uso; decisão cara de reverter paga análise antes. O que quebra sem ele é o rigor uniforme — ou tudo vira comitê, ou o irreversível passa junto com o trivial. Escolher a fonte do identificador do item do rastreador é mão única; escolher a cor do chip de prioridade não é.

- **obra necessária.** Mark Richards e Neal Ford, *Fundamentals of Software Architecture* — reversibilidade e último momento responsável tratados como variável de projeto, não como estilo de gestão.
- **caso falseador.** Uma decisão classificada como irreversível ser desfeita numa tarde, sem custo relevante.

### descoberta-continua

**Descoberta contínua** · processo · doutrinario

Contato com quem usa em cadência curta e fixa, feito por quem decide o produto. O mecanismo é a frequência: a decisão semanal se apoia em evidência da semana, não em pesquisa feita antes do ciclo e já vencida. Sem ele, o intervalo entre a suposição e o desmentido cresce até o custo de errar virar irrecuperável.

- **obra necessária.** Teresa Torres, *Continuous Discovery Habits* — dá a cadência e o formato mínimo, que é o que falta; existe intenção de feedback e não existe periodicidade.
- **caso falseador.** Um produto de usuário único em que o decisor é o próprio usuário, e a cadência não produz nenhuma informação que ele já não tivesse.

### incidente-critico

**Incidente crítico** · processo · doutrinario · pai proposto: `descoberta-continua`

Episódio específico e datado em que algo deu notavelmente certo ou errado, coletado como unidade de evidência. O mecanismo é a substituição da opinião pelo caso: em vez de "a lista está apertada", registra-se o dia, a tela, o item e o que o usuário não conseguiu fazer. O que quebra sem ele é a rastreabilidade do requisito — requisito derivado de impressão não sobrevive à primeira discordância.

- **obra necessária.** John Flanagan, "The Critical Incident Technique" (1954) — o método formal de coleta e de derivação de requisito a partir de episódio, que a página de atrito faz por intuição.
- **caso falseador.** Trinta episódios datados produzirem a mesma lista de requisitos que a queixa geral já dava.

### ignorancia-de-segunda-ordem

**Ignorância de segunda ordem** · fenomeno · natural

Falta de repertório para reconhecer a própria falta. O mecanismo é a invisibilidade: quem não tem o vocabulário de um domínio não percebe a ausência de uma peça dele, e por isso refaz do zero o que já estava decidido sem nunca procurar. É a aposta central da plataforma escrita como fenômeno — a estrutura precisa apresentar o que o recém-chegado não sabe perguntar.

- **obra necessária.** Obra de epistemologia da ignorância que dê taxonomia do não-sabido — Ann Kerwin, "None Too Solid", serve; falta a peça que distingue lacuna percebida de lacuna imperceptível.
- **caso falseador.** Alguém sem repertório do domínio listar corretamente o que não sabe sobre ele.

### calibragem-de-confianca

**Calibragem de confiança** · fenomeno · natural

A confiança de quem usa acompanha, ou não, a competência real do sistema faixa a faixa. Excesso e déficit são falhas simétricas: quem confia demais aceita resposta errada, quem confia de menos refaz à mão o que já estava certo. O mecanismo de correção é a exposição de proveniência e incerteza no ponto de uso — o carimbo de `acervo_sha` e o rótulo de cobertura existem por isso, e não por auditoria.

- **obra necessária.** John D. Lee e Katrina See, "Trust in Automation: Designing for Appropriate Reliance" (2004) — dá a régua de confiança apropriada, que hoje se decide por intuição de tela.
- **caso falseador.** Usuário que confia cegamente e usuário que desconfia de tudo chegarem à mesma taxa de erro no uso do sistema.

### fluencia-como-sinal-falso

**Fluência como sinal falso** · fenomeno · natural · pai proposto: `calibragem-de-confianca`

Texto que se lê sem esforço é julgado mais verdadeiro que texto difícil, independentemente de sê-lo. O mecanismo é a transferência da facilidade de processamento para o juízo de verdade, e é o que torna o erro do modelo caro: ele não hesita, não titubeia e escreve bonito. Decide forma de interface — resposta sem citação exibida com o mesmo acabamento da resposta ancorada é desenho que amplifica o efeito.

- **obra necessária.** Daniel Kahneman, *Rápido e devagar* (facilidade cognitiva) — e, para o lado do modelo, obra que trate geração fluente sem compromisso com referente.
- **caso falseador.** Leitores identificarem respostas erradas na mesma taxa em texto polido e em texto truncado.

### ironia-da-automacao

**Ironia da automação** · fenomeno · natural

Automatizar a parte fácil de um trabalho deixa ao humano só a parte difícil, e retira dele a prática que sustentava essa parte. O mecanismo é duplo: o resíduo humano fica mais exigente que o trabalho original, e a competência para exercê-lo decai por desuso. Decide onde colocar o gate humano — o dono como revisor de tudo que o agente produz é exatamente a posição que este fenômeno erode.

- **obra necessária.** Lisanne Bainbridge, "Ironies of Automation" (1983) — o texto fundador; não há substituto e o problema é estrutural na plataforma inteira.
- **caso falseador.** O revisor humano acertar tanto depois de meses só supervisionando quanto quando fazia o trabalho à mão.

### sinal-implicito-de-uso

**Sinal implícito de uso** · modelo · doutrinario · pai proposto: `descoberta-continua`

O que a pessoa faz e o que a pessoa declara medem coisas diferentes sobre a mesma tela. O comportamento é abundante e enviesado pela posição do que foi mostrado; a declaração é rara e enviesada pela cortesia. O mecanismo de uso é o cruzamento: nenhum dos dois vale sozinho, e tratar clique como aprovação é o erro clássico.

- **obra necessária.** Thorsten Joachims et al., "Accurately Interpreting Clickthrough Data as Implicit Feedback" (2005) — mostra como extrair preferência relativa de comportamento sem tomá-lo por juízo absoluto.
- **caso falseador.** O sinal declarado e a sequência de ações medida apontarem sempre para a mesma tela.

### operador-nao-humano

**Operador não humano** · modelo · doutrinario

Superfície cujo consumidor primário é um programa que lê linguagem natural e age. O mecanismo é a inversão das affordâncias que a interface humana assume: não há olhar periférico, não há memória do que estava na tela anterior, não há dúvida ao encontrar vazio. Decide o que a superfície precisa dizer em texto por não poder dizer em posição — e é o fato definidor deste produto, cujo operador do dia a dia não é gente.

- **obra necessária.** Christopher Noessel, *Designing Agentive Technology* — cobre o agente que serve o humano; falta a obra do caso inverso, interface desenhada para ser consumida por agente, e é aceitável que ela não exista ainda.
- **caso falseador.** Um agente completar as mesmas tarefas na mesma taxa numa superfície desenhada só para humano e numa desenhada para ele.

### carga-cognitiva-extranea

**Carga cognitiva estranha** · fenomeno · natural

Parte do esforço mental exigido por uma tarefa vem da forma como o material foi apresentado, não da dificuldade da matéria. O mecanismo é a competição por memória de trabalho: cada elemento que o olho precisa reconciliar consome capacidade que a decisão deixaria de ter. Decide o corte da tela — a zona de vizinhança da bancada de classificação existe para reduzir essa parcela, e cresce até virar a própria fonte dela.

- **obra necessária.** John Sweller, *Cognitive Load Theory* — dá a separação entre carga intrínseca e a introduzida pelo desenho, que é o critério de corte que hoje se aplica por gosto.
- **caso falseador.** Reduzir a apresentação ao mínimo e o desempenho na tarefa não mudar.

### lei-de-fitts

**Lei de fitts** · modelo · natural

O tempo para acertar um alvo cresce com a distância até ele e cai com o tamanho dele. O mecanismo é geométrico e mensurável, e por isso decide número: alvo mínimo, distância entre controle primário e destrutivo, borda da tela valendo mais que o meio. É a obra que sustenta os 24px e os 44px já escritos na régua de affordance sem fonte declarada.

- **obra necessária.** I. Scott MacKenzie, *Human-Computer Interaction: An Empirical Research Perspective* — trata a lei com o aparato experimental, não como número de checklist.
- **caso falseador.** Alvo de 24px e de 44px produzirem a mesma taxa de erro de toque na mesma superfície.

### golfo-de-execucao

**Golfo de execução e de avaliação** · modelo · doutrinario

A distância entre o que a pessoa quer fazer e o que os controles disponíveis permitem expressar, e a distância entre o que o sistema fez e o que a pessoa consegue interpretar da tela. São duas falhas diferentes e o remédio de uma não serve à outra: a primeira se fecha com controle; a segunda, com retorno visível. Diagnostica antes de desenhar — usuário que não sabe onde clicar e usuário que clicou e não sabe se funcionou não têm o mesmo problema.

- **obra necessária.** Donald Norman, *O design do dia a dia* — os dois golfos como par diagnóstico, e não a leitura corrente que retém só metade do livro.
- **caso falseador.** Usuário que sabe exatamente o que quer errar tanto quanto o que não sabe, na mesma tela.

### forrageamento-de-informacao

**Forrageamento de informação** · modelo · doutrinario

Quem procura segue pistas de proximidade e abandona a trilha quando o rendimento esperado do próximo passo cai abaixo do custo dele. O mecanismo transforma rótulo em variável de projeto: o link informa a decisão de segui-lo, e rótulo honesto mas vago mata a trilha antes do destino. Decide navegabilidade como propriedade medível, não como opinião sobre menu.

- **obra necessária.** Peter Pirolli, *Information Foraging Theory* — dá o modelo de pista e rendimento; a prioridade de experiência já escrita ("navegabilidade primeiro") não tem obra que a sustente.
- **caso falseador.** Trocar o rótulo de um link por outro igualmente honesto e menos informativo, e a taxa de chegada à página não mudar.

### atrito-deliberado

**Atrito deliberado** · processo · doutrinario

Custo inserido de propósito num caminho, para desacelerar, sinalizar importância ou impedir ação irreversível. O mecanismo é a assimetria: o caminho crítico fica barato, o caminho perigoso fica caro, e a diferença entre os dois passa a ser informação. Sem ele, superfície plana deixa instrução crítica e trivial equidistantes — e o custo uniforme apaga a hierarquia que a geografia de um escritório real dá de graça.

- **obra necessária.** Richard Thaler e Cass Sunstein, *Nudge* (edição com o tratamento de sludge) — a única que trata custo inserido como instrumento de desenho e não como defeito a eliminar.
- **caso falseador.** Passo extra inserido antes de uma ação destrutiva e a taxa de arrependimento não cair.

### falha-ruidosa

**Falha ruidosa** · disposicao · doutrinario

Propriedade da superfície que, ao não encontrar o pedido, devolve a diferença entre "não existe" e "não achei". O mecanismo é a conversão de ausência em dado: retorno vazio silencioso vira conclusão de inexistência, e quem conclui não tem como saber que concluiu. Vale para tela e para ferramenta — o aviso de cobertura fraca de uma busca é o embrião disso, e precisa ser propriedade de toda a superfície, não recurso de uma ferramenta.

- **obra necessária.** Marti Hearst, *Search User Interfaces* — desenho do resultado vazio e da consulta sem retorno; complementada por obra de engenharia sobre falha explícita em fronteira de serviço.
- **caso falseador.** Retorno vazio e retorno com aviso de cobertura fraca levarem à mesma conclusão de quem perguntou.

### tempo-percebido

**Tempo percebido** · fenomeno · natural

A sensação de rapidez depende de quanto o sistema mostra do que está fazendo, e não da duração medida no relógio. O mecanismo é a ocupação da espera: espera preenchida e progresso legível encurtam a percepção; espera vazia alonga, e a mesma tela é avaliada como lenta ou rápida conforme o que exibe enquanto carrega. Decide se a tela de carregamento é esqueleto, contador ou nada.

- **obra necessária.** Steven Seow, *Designing and Engineering Time* — liga a medida de engenharia à percepção; a régua de legibilidade atual não trata tempo.
- **caso falseador.** Tela com indicador de progresso e tela sem, com a mesma duração real, serem avaliadas como igualmente rápidas.

### degradacao-declarada

**Degradação declarada** · disposicao · doutrinario

Cada dependência que pode faltar tem comportamento desenhado para a falta, e a tela nessa condição é caso normal do produto. O mecanismo é a inversão do padrão: a versão sem a dependência é a que se desenha primeiro, e a completa é o incremento. Sem isso, a ausência vira exceção não desenhada e chega ao usuário como quebra — obra sem PDF na bancada de classificação é o caso, e é maioria em fase de aquisição.

- **obra necessária.** Jeremy Keith, *Resilient Web Design* — camada por camada, com a versão degradada como ponto de partida e não como plano de contingência.
- **caso falseador.** Toda dependência que faltou até hoje ter produzido tela utilizável sem desenho específico para a falta.

### paridade-de-superficie

**Paridade de superfície** · disposicao · doutrinario

Dois clientes do mesmo substrato alcançam o mesmo conjunto de fatos, ou a divergência entre eles é falha nomeada com dono. O mecanismo é a comparação sistemática: a interface humana e a superfície de agente sobre a mesma base são produtos distintos, e a página que um alcança e o outro não é classe de falha própria — não é bug de nenhum dos dois. Sem o conceito, a divergência não tem responsável e só aparece quando alguém conclui errado.

- **obra necessária.** Arnaud Lauret, *The Design of Web APIs* — contrato desenhado para consumidor que não é o autor, que é a disciplina que falta quando a GUI vira cliente da API.
- **caso falseador.** Página alcançável por um cliente e invisível ao outro sem que isso jamais produza conclusão errada.

---

## claudinho-TI

### mudanca-padrao

**Mudança padrão** · processo · instituido

Mudança pré-autorizada, cujo risco foi avaliado uma vez na aprovação do procedimento e não a cada execução. O que a define não é ser pequena: é ser repetível, com resultado conhecido e caminho de volta escrito — o objeto aprovado é o procedimento, não a ocorrência. Sem essa categoria só há dois regimes ruins: tudo passa por aprovação e a aprovação vira carimbo, porque ninguém analisa cem casos iguais; ou nada passa e a mudança acontece sem registro. Exemplo: republicar um contêiner a partir do mesmo commit já em produção.

- **obra necessária.** ITIL 4 — Create, Deliver and Support, pela tripartição padrão/normal/emergencial e pelo critério de pré-autorização. Uma norma de sistema de gestão de serviço (ISO/IEC 20000-1) serve ao mesmo conceito com força de requisito auditável.
- **caso falseador.** Um catálogo de mudanças padrão cuja taxa de falha se mostre igual à das mudanças aprovadas caso a caso mostraria que a pré-autorização não separa risco nenhum.

### reversibilidade-de-mudanca

**Reversibilidade de mudança** · disposicao · doutrinario

Propriedade de uma mudança que pode ser desfeita em tempo menor que o dano que ela causa. É a régua que decide quanto rigor a mudança merece: reversível pode ser verificada em produção; irreversível precisa acertar de primeira e paga a diferença em ensaio, revisão e janela. O que rouba reversibilidade quase nunca é o código — é o estado: migração que apaga coluna, mensagem já consumida, e-mail enviado, credencial já exposta.

- **obra necessária.** Continuous Delivery (Humble e Farley), pelo tratamento de rollback, migração de banco e liberação desacoplada de implantação.
- **caso falseador.** Uma operação que trate as duas classes com a mesma régua de aprovação e não pague diferença mensurável em duração de incidente irreversível.

### registro-autoritativo-de-configuracao

**Registro autoritativo de configuração** · modelo · instituido

Registro único que responde o que existe, em que versão e do que depende — e que é autoridade, não cópia. Autoridade quer dizer uma coisa operacional: divergência entre ele e o runtime é defeito do runtime, a corrigir, não do registro, a atualizar. Registro alimentado por varredura periódica não é autoridade, é fotografia, e envelhece entre fotos.

- **obra necessária.** A prática de gestão de ativos de serviço e configuração em ITIL 4 / ISO/IEC 20000-1, pela definição de item de configuração e de linha de base; complementar com literatura de infraestrutura declarativa para o mecanismo de autoridade.
- **caso falseador.** Uma operação que sustente resposta correta a "o que está no ar" a partir de registro reconstruído por inspeção, ao longo de um período com mudança fora do registro.

### labuta-operacional

**Labuta operacional** · fenomeno · doutrinario

Trabalho operacional manual, repetitivo, automatizável e sem valor duradouro, que cresce na mesma proporção da frota. Não é sinônimo de trabalho difícil: a labuta não deixa nada atrás de si, então o time que a absorve parece ocupado e produz menos a cada mês. A régua é o crescimento — tarefa que dobra quando o número de serviços dobra é labuta; tarefa que não dobra é operação.

- **obra necessária.** Site Reliability Engineering (Google), capítulo de eliminação de toil, pela definição operacional e pelo teto percentual de carga.
- **caso falseador.** Um time cuja carga manual repetitiva cresça com a frota sem degradação da capacidade de projeto ao longo de vários ciclos.

### consulta-nao-antecipada

**Consulta não antecipada** · disposicao · doutrinario

Propriedade de um sistema que permite responder perguntas não formuladas antes da falha. Painel e alerta respondem à pergunta prevista; o incidente novo é por definição imprevisto, e ali o que decide é poder recortar o dado por dimensão que ninguém pensou antes — versão, host, conta, tenant. O custo mora na cardinalidade: telemetria pré-agregada é barata e não responde nada novo. Exemplo: "está lento" só vira diagnóstico quando se pode perguntar "lento para qual versão do cliente".

- **obra necessária.** Observability Engineering (Majors, Fong-Jones e Miranda), por separar observabilidade de monitoramento e tratar o custo de cardinalidade.
- **caso falseador.** Uma sequência de incidentes inéditos diagnosticados no mesmo tempo por operação que só dispõe de métrica pré-agregada.

### fadiga-de-alerta

**Fadiga de alerta** · fenomeno · natural

Excesso de alerta destrói a capacidade de responder ao alerta que importa. O mecanismo é humano e mensurável: taxa alta de alarme falso treina o operador a silenciar por reflexo, e a conta chega no alarme verdadeiro que aparece no meio do ruído. Não se corrige com disciplina — corrige-se removendo alerta que não pede ação. Exemplo: alerta cuja ação correta é "ignorar" já é ruído; desligá-lo aumenta a segurança do sistema.

- **obra necessária.** EEMUA 191 (Alarm Systems: a Guide to Design, Management and Procurement), norma da indústria de processo que fixa taxa aceitável de alarme por operador — a literatura de SRE herda o problema sem essa régua quantitativa.
- **caso falseador.** Uma operação com alta taxa de alarme falso que sustente tempo de resposta constante ao alarme verdadeiro ao longo de meses.

### veracidade-do-sinal-de-saude

**Veracidade do sinal de saúde** · disposicao · doutrinario

Um sinal de saúde vale o quanto ele consegue mentir. Sonda que verifica camada acima do que interessa devolve verde com o serviço inútil: o processo responde, a porta abre, a função não funciona. O critério é a sonda exercitar o caminho que o cliente usa e verificar conteúdo, não envelope. Exemplo: HTTP 200 de uma wiki prova servidor web, não wiki; provar exige interpretar a resposta da API.

- **obra necessária.** Obra de engenharia de dependabilidade que trate cobertura de detecção e falha silenciosa (tradição de fault detection coverage e do modelo falha/erro/defeito), porque o ponto não é como escrever a sonda, é como medir o que ela não vê.
- **caso falseador.** Uma operação cuja sonda de camada superficial detecte a totalidade das falhas funcionais ocorridas num período, sem falso verde.

### deriva-de-configuracao

**Deriva de configuração** · fenomeno · natural

A distância entre o que está declarado e o que está rodando cresce sozinha com o tempo. Cada correção feita direto no runtime, cada pacote atualizado à mão, cada variável mudada "só para testar" some do registro no instante seguinte. O dano não é a mudança em si: é que a reconstrução do ambiente deixa de reproduzir o ambiente, e isso só se descobre no dia em que reconstruir virou obrigatório.

- **obra necessária.** Infrastructure as Code (Kief Morris), pelo tratamento de drift, reconstrução e servidor descartável.
- **caso falseador.** Um ambiente mantido por edição manual que se reproduza integralmente após destruição total, sem intervenção de quem o editou.

### estado-desejado-reconciliado

**Estado desejado reconciliado** · processo · doutrinario

Regime em que se declara o estado que se quer e um laço contínuo corrige a diferença, em vez de se executarem passos que levam de um estado a outro. A diferença prática aparece quando algo sai do lugar sem ninguém pedir: no regime imperativo nada acontece; no reconciliado o laço traz de volta. O preço é simétrico — o mesmo laço que corrige a falha desfaz o conserto feito à mão, e por isso conserto manual precisa virar declaração no mesmo turno.

- **obra necessária.** Kubernetes Patterns (Ibryam e Huß) ou obra equivalente sobre controlador declarativo; alternativa com o mecanismo mais nu: fundamentos de controle em malha fechada.
- **caso falseador.** Um sistema declarativo com laço ativo que exija intervenção manual para restaurar o estado após perturbação externa.

### recurso-indivisivel

**Recurso indivisível** · fenomeno · natural

Recurso que degrada em vez de recusar quando dois consumidores o usam ao mesmo tempo. É o caso difícil de diagnosticar, porque não falha alto como porta ocupada: os dois processos rodam, os dois entregam, e os dois ficam lentos — o sintoma chega como lentidão intermitente sem causa local. A correção é fila, não capacidade: serializar o acesso entrega mais trabalho por hora do que repartir o recurso. Exemplo: dois modelos carregados na mesma GPU disputando banda de memória.

- **obra necessária.** Guerrilla Capacity Planning (Neil Gunther) ou obra equivalente de teoria de filas aplicada a capacidade, pela relação entre utilização, concorrência e vazão; para o mecanismo de exclusão mútua, fundamentos de sistemas operacionais.
- **caso falseador.** Um recurso sob contenção cuja vazão agregada suba com o aumento de concorrência, sem serialização.

### dependencia-nao-declarada

**Dependência não declarada** · fenomeno · natural

Todo sistema depende de coisas que não estão escritas em lugar nenhum. Binário que existe no PATH de quem instalou, nome que resolve porque o cache local guarda, variável exportada no perfil do shell, ordem de subida que sempre deu certo por acaso. A dependência oculta não causa falha enquanto o ambiente não muda; ela cobra na primeira máquina limpa, e o sintoma aponta para qualquer lugar menos para ela. Exemplo: comando com `~` funciona para uma conta e falha para outra, com erro de arquivo inexistente.

- **obra necessária.** The Twelve-Factor App pelo critério de declaração e isolamento explícitos; complementar com obra de build reprodutível (Nix ou Bazel) para o caso em que a declaração precisa ser executável.
- **caso falseador.** Um ambiente reproduzido em máquina limpa sem que nenhuma dependência implícita apareça na tentativa.

### imutabilidade-de-artefato

**Imutabilidade de artefato** · disposicao · doutrinario

O pacote que vai para produção é construído uma vez e nunca reconstruído para ser promovido. Reconstruir para publicar significa que o artefato testado e o artefato no ar são objetos diferentes, ainda que saiam do mesmo commit — dependência transitiva muda, imagem base muda, relógio muda. Promove-se o binário, versiona-se o commit, e os dois precisam estar amarrados por identificador de conteúdo, não por data.

- **obra necessária.** Continuous Delivery (Humble e Farley), pelo princípio de construir uma vez e promover o mesmo binário entre ambientes.
- **caso falseador.** Um pipeline que reconstrua a cada promoção e demonstre equivalência do artefato entre ambientes ao longo do tempo, sem fixar dependência.

### procedencia-do-que-esta-no-ar

**Procedência do que está no ar** · modelo · doutrinario · pai proposto: `imutabilidade-de-artefato`

Cadeia verificável que liga o processo em execução ao commit e ao processo de construção que o produziu. Não é o registro de quem publicou: é prova obtida do próprio artefato em execução. Data de build não serve — imagem construída antes do commit tem data posterior e conteúdo anterior, e um serviço pode servir versão velha por dias sem que nada acuse. O que resolve é comparar conteúdo com conteúdo.

- **obra necessária.** SLSA (Supply-chain Levels for Software Artifacts), pelos níveis de proveniência e pelo que cada nível permite afirmar; alternativa normativa com o mesmo eixo: NIST SP 800-218 (SSDF).
- **caso falseador.** Uma operação que responda corretamente "qual commit está no ar" apenas por metadado de publicação, num período que inclua falha parcial de publicação.

### paridade-entre-ambientes

**Paridade entre ambientes** · disposicao · doutrinario

Ambiente de verificação e ambiente de produção divergem por padrão, e cada divergência enfraquece o que o teste prova. A régua é a distância que importa — versão de runtime, dependência, dado e topologia — não a semelhança cosmética. O problema é que a fraqueza não é visível no resultado: verde continua verde. Exemplo: rodar a suíte num ambiente virtual encontrado na árvore, que pode ser de outra conta e outro interpretador, não é o verde do runtime.

- **obra necessária.** The Twelve-Factor App (fator de paridade dev/prod) para o critério; Continuous Delivery para o ambiente de aceitação semelhante a produção e o custo de mantê-lo.
- **caso falseador.** Um defeito recorrente de produção capturado com a mesma taxa por suíte executada em ambiente reconhecidamente divergente.

### raio-de-alcance

**Raio de alcance** · fenomeno · natural

Toda mudança e toda falha têm alcance, e o alcance é decisão de desenho, não sorte. Sistema sem compartimento propaga: uma dependência lenta consome as conexões de tudo que a chama, e um componente secundário derruba o principal. Compartimentar custa capacidade ociosa — é o preço explícito de limitar o estrago. Exemplo: derrubar o projeto inteiro para publicar um serviço amplia o raio sem que ninguém tenha pedido.

- **obra necessária.** Release It! (Michael Nygard), pelos padrões de estabilidade — anteparo, disjuntor, tempo limite — e pelos antipadrões que propagam falha.
- **caso falseador.** Um sistema sem compartimentação cujo histórico de falhas mostre alcance sistematicamente confinado ao componente que falhou.

### tamanho-de-lote

**Tamanho de lote** · fenomeno · doutrinario

Quanto maior o pacote liberado de uma vez, mais que proporcionalmente cresce o custo de descobrir o que deu errado. Lote grande esconde: o defeito chega junto com vinte mudanças e o diagnóstico vira busca; lote pequeno chega sozinho e se aponta na hora. O contrapeso é o custo fixo por liberação — reduzir lote só compensa depois de baratear a liberação, e é por isso que a automação vem antes do lote pequeno, nunca depois.

- **obra necessária.** The Principles of Product Development Flow (Donald Reinertsen), pela economia de tamanho de lote e pela relação entre custo de transação e lote ótimo.
- **caso falseador.** Uma organização com custo de liberação baixo em que o tempo de diagnóstico cresça apenas proporcionalmente ao número de mudanças no lote.

### assimetria-de-contexto-do-executor

**Assimetria de contexto do executor** · fenomeno · natural

Quem executa não compartilha o contexto de quem pede, e o pedido escrito no registro interno de quem pede chega incompleto sem que nenhum dos dois perceba. Competência técnica não compensa a lacuna — piora o sintoma: o executor competente preenche o vazio com a hipótese mais plausível e entrega coisa errada com aparência de certa, o que custa mais que devolver pergunta. O que fecha a assimetria não é mais texto, é precedente apontado e critério de aceite.

- **obra necessária.** Economics, Organization and Management (Milgrom e Roberts) ou obra equivalente de relação principal-agente, pelo mecanismo de assimetria informacional e pelo que ela produz em contrato incompleto; complementar com Specification by Example (Adzic) para a forma escrita do pedido.
- **caso falseador.** Um executor sem contexto de domínio que, recebendo especificação redigida no registro interno do solicitante, entregue conforme de forma sistemática.

### aceite-executavel

**Aceite executável** · disposicao · doutrinario · pai proposto: `assimetria-de-contexto-do-executor`

Critério de aceite é um comando e um número esperado, não uma frase. "Funciona" transfere para quem aceita o trabalho de descobrir o que provaria funcionamento, e o resultado previsível é aceite por leitura de mensagem de commit — que é declaração de quem entregou, não verificação. O critério executável inverte a conta: quem escreve o pedido paga antes o custo de saber o que prova. Exemplo: `369 ms → 44 ms` é aceite; "melhorar o desempenho" é intenção.

- **obra necessária.** Specification by Example (Gojko Adzic), pelo mecanismo de exemplo verificável como especificação; alternativa pelo lado do teste: Growing Object-Oriented Software, Guided by Tests.
- **caso falseador.** Entregas aceitas por critério textual cuja taxa de retrabalho seja igual à de entregas com critério executável, no mesmo time e período.

### carga-cognitiva-de-time

**Carga cognitiva de time** · fenomeno · doutrinario

Um time sustenta apenas a quantidade de sistema que cabe na cabeça dele. Passado o limite, a degradação não se manifesta como recusa e sim como lentidão difusa, retrabalho e dependência de quem lembra — e a reação usual, somar responsabilidade porque "é só mais um repositório", agrava exatamente o que se queria resolver. A fronteira certa de responsabilidade é a que cabe, não a que o organograma desenha.

- **obra necessária.** Team Topologies (Skelton e Pais), pelo tratamento de carga cognitiva como restrição de desenho organizacional e pelo tamanho de domínio por time.
- **caso falseador.** Um time cujo número de domínios sob responsabilidade cresça sem degradação de tempo de resposta nem concentração de conhecimento em um indivíduo.

### custo-de-transferencia

**Custo de transferência** · fenomeno · natural

Toda passagem de trabalho de um responsável para outro perde informação e adiciona espera. A perda cresce com o quanto do contexto é tácito; a espera cresce quando o transporte depende de um intermediário que não é dono de nenhum dos dois lados. Duas transferências em série custam mais que o dobro de uma, porque a segunda recebe o que a primeira já degradou. Exemplo: encaminhamento vago não chega — o que chega é pacote com destinatário, verbo e o que há para decidir.

- **obra necessária.** Implementing Lean Software Development (Poppendieck) pelo custo de handoff e pela perda de conhecimento tácito; Reinertsen para a medida da fila que a transferência cria.
- **caso falseador.** Uma cadeia com várias transferências em série cujo conteúdo decisório chegue íntegro ao destino, medido por retrabalho nulo no receptor.
