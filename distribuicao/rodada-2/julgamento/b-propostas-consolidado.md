# Rodada 2 — propostas consolidadas das 7 cadeiras

84 conceitos propostos. Agrupados pelo domínio em que **ocorrem** (domínio das obras-âncora, ont:0062). Conceito com âncoras em mais de um domínio aparece em cada um — a ocorrência é plural.

## arquiteturas

* **contexto-delimitado** — Contexto delimitado `[claudinho-conhecimento]`
   * definição: A mesma palavra significa coisas diferentes em partes diferentes de uma organização, e isso não é confusão a ser corrigida: para o time de vendas, "cliente" é quem pode comprar; para o financeiro, é quem tem contrato ativo. O contexto delimitado é a fronteira declarada dentro da qual cada palavra tem um significado só. Declarar a fronteira decide o que fazer quando duas definições divergem. Dentro da mesma fronteira, divergência é defeito e alguém tem que ceder. Entre fronteiras diferentes, não há defeito nenhum — o que se constrói é a tradução de um lado para o outro, e tentar unificar destrói informação dos dois lados.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Domain-Driven Design
      * Learning Domain-Driven Design
      * An Ontology-based Approach for Domain-driven Design of Microservice Architectures

* **dado-aberto-por-padrao** — Dado aberto por padrão `[claudinho-arquiteto]`
   * definição: Todo dado que a organização produz nasce público. Quem quiser fechar um deles tem que dizer em qual das hipóteses de sigilo já previstas ele se encaixa — e a hipótese existia antes do pedido. Isso inverte quem tem trabalho a fazer: no arranjo comum, quem quer o dado justifica por que merece; aqui quem guarda justifica por que reteve, e "não vejo por que abrir" não é justificativa. O efeito prático é que o acesso deixa de ser negociado caso a caso entre dois setores e passa a ser decidido de antemão, pelo enquadramento que já está escrito.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Decreto nº 8.777/2016 — Política de Dados Abertos do Poder Executivo federal
      * Decreto nº 10.046/2019 — Governança no compartilhamento de dados na administração pública federal _(ocorre em seguranca-privacidade)_

* **estruturacao-de-problema** — Estruturação de problema `[claudinha-gestao-estrategica]`
   * definição: Escrever qual é o problema, de quem ele é e o que contaria como resolvido, antes de listar soluções. Um prédio com fila no elevador pode ter um problema de engenharia — os elevadores são lentos — ou um problema de espera: quem espera se irrita, e um espelho no hall resolve. As duas leituras nascem do mesmo fato e levam a investimentos que não se parecem em nada. Enquanto o enunciado não estiver escrito e aceito por quem paga a conta, comparar alternativas é responder bem a uma pergunta que ninguém fez. O sinal de que a etapa foi pulada é a reunião que começa direto na lista de opções, com cada pessoa achando que todo mundo fala da mesma coisa.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Systems thinking, systems practice
      * Are Your Lights On? _(ocorre em produtos-digitais)_
      * Dirty Rotten Strategies _(ocorre em produtos-digitais)_
      * Dilemmas in a General Theory of Planning _(ocorre em produtos-digitais)_

* **fluxo-de-valor** — Fluxo de valor `[claudinho-arquiteto]`
   * definição: Do momento em que alguém de fora pede alguma coisa até o momento em que recebe o que queria há uma sequência de etapas, e ela quase nunca cabe dentro de um departamento só. Comprar passagem, embarcar e chegar é um fluxo de valor: passa por venda, operação e atendimento, e o passageiro não vê nenhuma dessas divisões. Cada etapa tem uma condição para começar, uma condição para terminar e algo que o solicitante ganha ao atravessá-la — se uma etapa não acrescenta nada que ele perceba, ela está lá por conveniência interna. Enxergar o trabalho assim mostra atrasos que nenhum organograma mostra: eles moram nas passagens entre as áreas, e cada área, olhando só para si, se vê em dia.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * BIZBOK Guide
      * Guia Prático de Gestão de Processos: gestão que simplifica, conecta e entrega — 2ª edição

* **fronteira-por-custo-de-transacao** — Fronteira por custo de transação `[claudinho-arquiteto]`
   * definição: Fazer dentro de casa custa coordenação: reunião, alinhamento, gente para gerenciar gente. Comprar de fora custa outra coisa: escolher fornecedor, escrever contrato, conferir se entregou. A fronteira fica onde o primeiro custo passa a ser maior que o segundo, e isso vale igual para uma empresa decidindo o que terceiriza e para um sistema decidindo o que vira componente separado. Como os dois custos mudam com o tempo, a fronteira certa também muda: quando ficou barato alugar servidor por hora, montar data center virou má ideia para quase todo mundo, sem que nada tivesse mudado no negócio. Separar bem tem um ganho extra que raramente entra na conta — uma parte bem isolada pode ser trocada por outra melhor depois, e essa possibilidade vale dinheiro mesmo enquanto ninguém a exerce.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The Nature of the Firm: Origins, Evolution, and Development _(ocorre em gestao-organizacional)_
      * Design Rules, Vol. 1

* **governanca-dados** — Governança de dados `[claudinho-arquiteto]`
   * definição: Duas áreas discordam sobre quem conta como "cliente ativo" e cada uma leva o seu número para a reunião. Governança de dados é o arranjo que responde quem decide isso — e quem responde quando o número sai errado. Não é quem executa: é quem fixa a regra, quem autoriza exceção e quem presta contas. A separação entre decidir e executar é o que faz o arranjo funcionar, porque quando a mesma equipe define a regra e é medida por ela, a regra cede. E o arranjo é transversal por necessidade: dado atravessa áreas, então a autoridade sobre ele não cabe dentro de nenhuma. O sinal de que amadureceu é ter virado rotina invisível, não departamento novo com nome próprio.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Data Governance (2nd)
      * Cartilha de Governança de Dados — Volume III: Papéis e Responsabilidades de Governança de Dados no Poder Executivo Federal

* **implantabilidade-independente** — Implantabilidade independente `[claudinho-TI]`
   * definição: Propriedade de uma parte do sistema que pode ir ao ar sozinha: muda-se ali, publica-se ali, e nada mais precisa ser publicado junto. Para isso a fronteira precisa de um contrato explícito e estável — o que ela aceita e o que devolve — e cada mudança tem que continuar honrando o que os vizinhos já usam. Partes que dividem o mesmo banco de dados ou que só sobem em bloco coordenado não têm essa propriedade, ainda que se chamem serviços ou microsserviços.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * Building Microservices (2nd)
      * Building Event-Driven Microservices
      * Continuous Delivery Pipelines: How To Build Better Software Faster _(ocorre em engenharia-software)_

* **ordenacao-causal** — Ordenação causal de eventos `[claudinho-TI]`
   * definição: Em um sistema espalhado por várias máquinas, não há relógio comum confiável. A única ordem real entre acontecimentos é a que a causalidade dá: A veio antes de B se os dois ocorreram em sequência na mesma máquina, ou se A enviou uma mensagem que B recebeu. Acontecimentos sem esse elo são simultâneos de verdade — não existe resposta para qual veio primeiro. Qualquer ordem total que o sistema exiba entre eles foi imposta por uma regra de desempate, e tratar essa convenção como fato é fonte clássica de erro em sistema distribuído.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * Time, Clocks, and the Ordering of Events in a Distributed System
      * Designing Data-Intensive Applications

* **problema-perverso** — Problema perverso `[claudinha-gestao-estrategica]`
   * definição: Alguns problemas não têm enunciado fechado nem linha de chegada: reduzir a violência de um bairro, integrar imigrantes, reformar um currículo. Cada tentativa muda a situação que se queria estudar, então não há como testar duas vezes, e nunca chega o momento em que alguém possa dizer "pronto, acabou". Isso decide o formato do compromisso, e é aí que a distinção paga. Problema com fim declarado se organiza como projeto, com prazo e entrega. Problema perverso não aceita esse formato: o que se pode prometer é uma intervenção assumida como sem volta, com revisão periódica e recursos renovados a cada volta. Prometer conclusão é prometer o que a natureza do problema não entrega, e o custo aparece anos depois, na forma de programa que ninguém consegue encerrar nem defender.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dilemmas in a General Theory of Planning _(ocorre em produtos-digitais)_
      * Systems thinking, systems practice

* **processo-de-negocio** — Processo de negócio `[claudinho-arquiteto]`
   * definição: Um pedido entra, várias pessoas fazem várias coisas em ordem, e algo sai pronto do outro lado. Esse caminho é o processo, e ele é uma coisa em si: desenha-se, mede-se e melhora-se, separado das áreas que executam cada pedaço. A diferença aparece quando algo vai mal. Olhando por área, cada uma mostra seus números em dia e o cliente continua esperando; olhando pelo caminho inteiro, aparece onde o pedido fica parado entre uma mesa e outra. O processo também é a parte que se pode redesenhar sem trocar o que a organização sabe fazer — a habilidade continua a mesma, o caminho até ela muda.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Guia Prático de Gestão de Processos: gestão que simplifica, conecta e entrega — 2ª edição
      * COBIT 5: Enabling Processes _(ocorre em engenharia-software)_

* **registro-de-decisao** — Registro de decisão `[claudinho-conhecimento]`
   * definição: Uma equipe encontra no sistema uma regra esquisita e ninguém sabe por que ela está ali: quem decidiu já saiu, e o que sobrou foi a regra sem o motivo. O registro de decisão é o documento curto e datado que se escreve na hora da escolha, guardando quatro coisas — o que se decidiu, o que estava acontecendo que obrigou a decidir, o que mais se cogitou, e por que se preferiu esta saída. Guardar o motivo é o que permite reabrir a decisão depois sem chutar. Quem chega anos mais tarde consegue ver se as circunstâncias que justificaram a escolha ainda valem e, não valendo, mudar sabendo o que está trocando. Sem o motivo escrito sobram duas saídas ruins: obedecer sem entender, ou desfazer sem saber o que se perde junto.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Documenting Architecture Decisions
      * A documentation framework for architecture decisions
      * Ontology of architectural design decisions in software-intensive systems

* **registro-de-decisao-arquitetural** — Registro de decisão arquitetural `[claudinho-TI]`
   * definição: Documento de uma página que fixa uma decisão técnica importante: qual era a situação, o que se decidiu e o que isso custa daqui para frente. Escreve-se no momento da decisão e não se edita depois — mudou a decisão, escreve-se um registro novo que declara substituir o antigo, e o antigo fica. O que ele protege é o porquê: sem o registro, quem chega meses depois vê só a escolha, desfaz sem conhecer o motivo e paga o problema que a escolha original evitava.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Documenting Architecture Decisions
      * Software Architecture Knowledge Management: Theory and Practice
      * Fundamentals of Software Architecture (2025)

## engenharia-software

* **cascata-de-objetivos** — Cascata de objetivos `[claudinho-arquiteto]`
   * definição: Cada meta de uma equipe tem que poder ser rastreada, degrau por degrau, até uma meta da organização inteira — e essa, até alguém de fora que espera algo dela: quem paga, quem fiscaliza, quem usa o serviço. Uma equipe que não consegue mostrar esse caminho está trabalhando em algo que ninguém pediu, por mais bem-feito que seja. O que caracteriza a cascata é a direção: a meta desce de cima, já decidida, e o de baixo justifica o que faz mostrando a ligação. Não é o único jeito de definir metas — há métodos em que a equipe propõe e a chefia referenda —, e o que muda entre eles é quem formula primeiro, não se há acordo.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * COBIT 2019 Framework: Governance and Management Objectives
      * COBIT 5: A Business Framework for the Governance and Management of Enterprise IT
      * COBIT 5: Enabling Processes

* **teto-de-compromisso** — Teto de compromisso `[claudinha-gestao-estrategica]`
   * definição: O limite do que se promete num período, declarado antes de escolher o que entra. Pode ser tempo fixo — seis semanas e o que não ficou pronto não ganha prorrogação —, número de coisas em andamento ao mesmo tempo, ou a capacidade estimada da equipe. O que não couber é dito em voz alta como fora, e não como "depois". Sem teto, priorizar vira ordenar: o item continua na lista, alguém continua esperando por ele, e o custo de dizer não fica escondido de quem pediu. Com teto, para entrar alguma coisa tem que sair, e essa troca é a decisão — o resto é conversa sobre importância, e tudo é importante. Quando o teto acaba, continuar exige uma decisão nova e explícita; a renovação automática é o mecanismo pelo qual um investimento ruim dura anos.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Guia de Elaboração de PDTIC do SISP, versão 2.1 _(ocorre em gestao-organizacional)_
      * The Standard for Project Management and A Guide to the Project Management Body of Knowledge (PMBOK Guide) _(ocorre em gestao-organizacional)_
      * Shape Up _(ocorre em produtos-digitais)_
      * Essential Kanban Condensed

* **desempenho-de-entrega** — Desempenho de entrega de software `[claudinho-TI]`
   * definição: Quatro medidas dizem se uma equipe entrega software bem: quanto tempo uma mudança leva do código pronto até o ar, com que frequência se publica, que fração das publicações quebra algo, e quanto tempo leva para consertar quando quebra. As duas primeiras medem velocidade; as duas últimas, estabilidade — e uma década de pesquisa mostra que as melhores equipes são boas nas quatro ao mesmo tempo: velocidade não se compra com quebra, nem estabilidade com lentidão. A medida olha o resultado do processo inteiro, não o esforço de cada etapa — medir esforço local premia gente ocupada, não software entregue.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Accelerate: The Science of Lean Software and DevOps
      * Accelerate: State of DevOps 2024
      * Accelerate: State of DevOps 2018
      * Accelerate: State of DevOps 2019

* **esteira-de-implantacao** — Esteira de implantação `[claudinho-TI]`
   * definição: Caminho automatizado que toda mudança de código percorre até estar pronta para publicação: testes rápidos primeiro, depois o pacote versionado, depois testes de aceitação num ambiente igual ao de produção. Cada etapa pode reprovar e devolver a mudança; o que atravessa tudo está pronto para o ar. O ponto é ser o caminho único: existindo um atalho manual por fora, a garantia da esteira vale zero, porque ninguém sabe o que entrou sem passar por ela.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Continuous Delivery Pipelines: How To Build Better Software Faster
      * Accelerate: The Science of Lean Software and DevOps

* **fabrica-de-software** — Fábrica de software (modelo de contratação) `[claudinho-TI]`
   * definição: Modelo de contratação de desenvolvimento em que o cliente especifica, o fornecedor produz e o pagamento sai de uma métrica sobre o artefato — tanto por ponto de função, uma unidade que estima o tamanho do que foi construído. É o arranjo dominante na administração pública federal brasileira. O mecanismo que o define: a métrica de pagamento passa a governar a produção — o fornecedor otimiza o que o contrato mede, não o que o software resolve em uso — e a fronteira contratual entre especificar e construir se ergue antes de qualquer linha de código.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Análise dos modelos e contratos de desenvolvimento de software na administração direta do governo federal: a crise na produção de software e as alternativas à fábrica de software
      * Gestão ágil e clientes cascata: desafios e alternativas para fábricas de software

* **falha-sistemica** — Falha sistêmica `[claudinho-TI]`
   * definição: Em sistema grande e cheio de proteções, o desastre nunca vem de um erro só: vem de várias falhas pequenas, cada uma inofensiva sozinha, que se alinham e atravessam as defesas juntas. Por isso a pergunta "qual foi a causa raiz?" engana — apontar uma causa única é escolha de quem analisa depois, não fato do acidente. A análise que ensina algo procura as condições que já estavam armadas antes, e o que segurou o sistema nas tantas vezes em que não caiu.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * Cook.1998.HowComplexSystemsFailRevG.pages
      * The Site Reliability Workbook

* **implantabilidade-independente** — Implantabilidade independente `[claudinho-TI]`
   * definição: Propriedade de uma parte do sistema que pode ir ao ar sozinha: muda-se ali, publica-se ali, e nada mais precisa ser publicado junto. Para isso a fronteira precisa de um contrato explícito e estável — o que ela aceita e o que devolve — e cada mudança tem que continuar honrando o que os vizinhos já usam. Partes que dividem o mesmo banco de dados ou que só sobem em bloco coordenado não têm essa propriedade, ainda que se chamem serviços ou microsserviços.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * Building Microservices (2nd) _(ocorre em arquiteturas)_
      * Building Event-Driven Microservices _(ocorre em arquiteturas)_
      * Continuous Delivery Pipelines: How To Build Better Software Faster

* **janela-de-exposicao** — Janela de exposição `[claudinho-seguranca]` `balde B`
   * definição: Entre o dia em que uma falha vira conhecida e o dia em que a correção está no ar, o sistema fica aberto — e quem ataca sabe disso, porque a falha foi anunciada em público junto com o remendo. Tudo que se coloca dentro desse intervalo para reduzir o risco de quebrar a operação — testar em homologação, esperar a janela de manutenção do fim de semana, colher aprovação — é pago em tempo de exposição. Não existe escolha entre seguro e inseguro: existe escolher qual dos dois riscos se prefere correr, o de a correção derrubar o serviço ou o de alguém entrar antes de ela chegar.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-40 Rev.4 — Patch Management
      * ISO/IEC 27002:2013 — Information technology — Security techniques — Code of practice for information security controls _(ocorre em seguranca-privacidade)_
      * ISC2 CISSP Certified Information Systems Security Professional Official Study Guide _(ocorre em seguranca-privacidade)_

* **orcamento-de-erro** — Orçamento de erro `[claudinho-TI]`
   * definição: A quantidade de falha que um serviço tem permissão de acumular num período, derivada da meta de confiabilidade prometida: prometeu 99,9% de sucesso no mês, o 0,1% restante é o orçamento — cerca de 43 minutos de indisponibilidade que podem ser gastos. As decisões do dia a dia saem do ritmo de gasto, não do incidente isolado: queimando rápido, congela-se mudança e prioriza-se estabilidade; sobrando orçamento, há espaço para arriscar. O alerta certo dispara quando o ritmo projetado esgota o orçamento antes do fim do período — cedo o bastante para agir, não depois da promessa quebrada.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The Site Reliability Workbook
      * Observability Engineering

* **processo-de-negocio** — Processo de negócio `[claudinho-arquiteto]`
   * definição: Um pedido entra, várias pessoas fazem várias coisas em ordem, e algo sai pronto do outro lado. Esse caminho é o processo, e ele é uma coisa em si: desenha-se, mede-se e melhora-se, separado das áreas que executam cada pedaço. A diferença aparece quando algo vai mal. Olhando por área, cada uma mostra seus números em dia e o cliente continua esperando; olhando pelo caminho inteiro, aparece onde o pedido fica parado entre uma mesa e outra. O processo também é a parte que se pode redesenhar sem trocar o que a organização sabe fazer — a habilidade continua a mesma, o caminho até ela muda.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Guia Prático de Gestão de Processos: gestão que simplifica, conecta e entrega — 2ª edição _(ocorre em arquiteturas)_
      * COBIT 5: Enabling Processes

* **refatoracao-segura** — Refatoração segura `[claudinho-TI]`
   * definição: Mudar a estrutura interna do código sem mudar o que ele faz, em passos pequenos, rodando os testes a cada passo — o teste verde confirma que o comportamento sobreviveu à mudança. Código sem teste exige um passo anterior: primeiro criar o teste que fotografa o comportamento atual, mesmo com defeitos, e só então mexer. Mexer em estrutura sem verificação a cada passo não é refatorar, é editar no escuro — e é assim que a limpeza bem-intencionada quebra o que funcionava.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Refactoring: Improving the Design of Existing Code
      * Working Effectively with Legacy Code
      * Test-Driven Development: By Example

* **servico-de-ti** — Serviço de TI `[claudinho-TI]`
   * definição: Aquilo que uma área de TI entrega e que o cliente reconhece como valor por si — o e-mail que funciona, o sistema no ar — sem carregar o custo e o risco de fazer funcionar. O que existe por baixo (servidor, banco, rede) habilita a entrega mas não vale nada sozinho para o cliente: é componente, não serviço. Confundir os dois infla o catálogo com itens que ninguém contrataria, gera cobrança que o cliente não reconhece e impede priorizar o portfólio, porque tudo virou serviço.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * FitSM Part 0: Overview and vocabulary, Version 3.0.1
      * FitSM-5 Guide: Identifying Services
      * ITIL Foundation: ITIL 4 Edition
      * FitSM-5 Guide: Specifying Services for Portfolios and Catalogues v1.0

* **transparencia-de-composicao** — Transparência de composição `[claudinho-seguranca]` `balde B`
   * definição: Um software é montado com centenas de pedaços escritos por outras pessoas, e cada pedaço traz outros dentro. Transparência de composição é o produtor entregar, junto com o produto, a lista do que tem lá dentro — fornecedor, nome, versão e quem depende de quem — num formato que um programa consiga ler. No mundo do software essa lista tem nome próprio: SBOM. Ela existe para a pergunta que aparece de madrugada: saiu uma falha grave numa biblioteca, a gente usa? Sem a lista, a resposta depende de perguntar ao fornecedor e esperar. Com ela, quem só opera responde sozinho, em minutos. O que o produtor não conseguiu mapear entra declarado como desconhecido — buraco anunciado se procura, buraco omitido vira surpresa.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * The Minimum Elements For a Software Bill of Materials (SBOM)
      * Strategies for the Integration of Software Supply Chain Security in DevSecOps CI/CD Pipelines
      * Software Supply Chain Security _(ocorre em seguranca-privacidade)_

## estudos-ontologias

* **conhecimento-tacito** — Conhecimento tácito `[claudinho-conhecimento]`
   * definição: Um servidor com trinta anos de casa sabe qual pedido vai emperrar só de bater o olho, e não consegue explicar como sabe. Isso é conhecimento tácito: o que a pessoa usa para agir bem sem conseguir enunciar por inteiro, porque aprendeu fazendo, errando e vendo alguém mais velho fazer. A consequência para quem monta formação é dura: parte do que se quer passar adiante não cabe em manual. Escrever ajuda e sempre perde alguma coisa no caminho; o resto só atravessa por convivência, acompanhamento e prática ao lado de quem já sabe. Tratar tudo como escrevível é a origem do treinamento que todo mundo faz e ninguém aprende.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * A Dynamic Theory of Organizational Knowledge Creation.
      * The Knowledge-Creating Company

* **criterio-de-identidade** — Critério de identidade `[claudinho-conhecimento]`
   * definição: Duas fichas com o mesmo nome: é a mesma pessoa ou são duas? A resposta não sai do bom senso, sai de uma regra escolhida antes — mesmo CPF, digamos. Essa regra é o critério de identidade: o que decide quando dois registros falam do mesmo indivíduo, e quanto esse indivíduo pode mudar continuando a ser ele. A regra vem sempre da categoria mais funda a que a coisa pertence: pessoa, nunca "cliente". Daí uma consequência prática que pega muito modelo de dados: as categorias que alguém pode largar sem deixar de existir — cliente, paciente, fornecedor — não podem ficar acima das que nunca se larga — pessoa, empresa. Invertido, o modelo passa a exigir que alguém deixe de ser gente ao cancelar o contrato.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Ontological Foundations for Structural Conceptual Models
      * Evaluating ontological decisions with OntoClean

* **custo-da-expressividade** — Custo da expressividade `[claudinho-conhecimento]`
   * definição: Quanto mais coisas uma linguagem formal deixa você afirmar, mais caro fica para o computador calcular o que essas afirmações implicam. Passado certo ponto, a conta não fecha em tempo útil: a máquina roda por horas, ou não termina. Por isso as linguagens usadas para escrever ontologia vêm em versões deliberadamente aparadas, cada uma abrindo mão de um tipo de afirmação em troca de resposta rápida e garantida. Escolher uma dessas versões é pagar o preço na frente: o que ela não deixa dizer fica proibido de escrever, e o que se ganha em troca é a certeza de que toda pergunta terá resposta em tempo previsível.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * The Description Logic Handbook: Theory, Implementation and Applications
      * OWL 2 Web Ontology Language Profiles (Second Edition)

* **descricao-multinivel** — Descrição multinível `[claudinho-conhecimento]`
   * definição: Duzentas caixas de documentos de um mesmo órgão não se descrevem caixa por caixa, cada uma do zero. Descreve-se primeiro o conjunto inteiro — quem produziu, em que período, para quê —, depois cada série dentro dele, depois cada dossiê, e assim por diante, do maior para o menor. A regra que faz isso funcionar é registrar cada informação uma vez só, no nível mais alto em que ela é verdadeira, e nunca repeti-la abaixo. Sem isso acontece um dos dois estragos: ou a mesma informação é copiada milhares de vezes e passa a divergir na primeira correção, ou o documento isolado chega a quem consulta sem o contexto que explica o que ele é.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * ISAD(G): General International Standard Archival Description, Second Edition
      * ISAD(G): Norma geral internacional de descrição arquivística — Segunda Edição
      * NOBRADE: Norma brasileira de descrição arquivística

* **documento-de-arquivo** — Documento de arquivo `[claudinho-conhecimento]`
   * definição: Um contrato assinado e um livro sobre contratos são coisas diferentes, e a diferença não está no papel. Documento de arquivo é o que foi produzido ou recebido no meio de uma atividade — o contrato, o ofício, a folha de ponto —, e o que o torna prova é justamente o vínculo com essa atividade: quem fez, quando, no curso de quê, junto de quais outros documentos. Daí uma consequência que costuma surpreender: tirar o documento do conjunto onde ele nasceu destrói parte do seu valor. Um livro continua o mesmo livro em qualquer estante, porque nele o que vale é o conteúdo. Um documento de arquivo solto do processo perde a capacidade de provar, mesmo com todas as palavras ainda legíveis.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Lei nº 8.159, de 8 de janeiro de 1991 — Política nacional de arquivos públicos e privados
      * e-ARQ Brasil: Modelo de Requisitos para Sistemas Informatizados de Gestão Arquivística de Documentos, Versão 2

* **esquema-de-organizacao** — Esquema de organização `[claudinha-produto]`
   * definição: Toda lista grande é arrumada por algum critério, e os critérios são de dois tipos. O exato — alfabético, por data, por lugar — põe cada item num só lugar e não deixa dúvida, mas só serve para quem já sabe o nome do que procura. O ambíguo — por assunto, por tarefa, por público — depende de julgamento, dois curadores arrumam diferente, e é o único que serve para quem sabe o problema e não sabe o nome. A escolha decide quem consegue encontrar. Num catálogo em ordem alfabética de título, quem quer "alguma coisa sobre contratar melhor" não acha nada; por assunto, acha, ao custo de o mesmo item caber em dois lugares. Coleção grande costuma precisar dos dois, e a decisão é qual deles é a porta de entrada.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Information Architecture: For the Web and Beyond
      * Designing Interfaces Patterns for Effective Interaction Design _(ocorre em produtos-digitais)_

* **evento-como-entidade** — Evento como entidade `[claudinho-conhecimento]`
   * definição: Numa ficha de livro é comum existir um campo "data de catalogação". Funciona até alguém perguntar quem catalogou, se houve uma segunda catalogação e o que ela mudou em relação à primeira — perguntas que um campo de data não responde. Tratar o evento como entidade é dar ficha própria ao acontecimento: a catalogação vira um registro com responsável, início, fim e etapas, em vez de ser um campo do livro. O que decide entre os dois é o tipo de pergunta que se pretende responder. Bastando saber quando aconteceu, o campo de data resolve e criar ficha só encarece. Sendo preciso saber quem participou, separar o acontecimento em etapas, ou amarrar um acontecimento a outro que veio antes, o campo não sustenta e o evento precisa existir por conta própria.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Events as Entities in Ontology-Driven Conceptual Modeling
      * Towards Ontological Foundations for the Conceptual Modeling of Events

* **pratica-de-recuperacao** — Prática de recuperação `[claudinho-conhecimento]`
   * definição: Reler a apostila dá a sensação de estar aprendendo e é uma das formas mais fracas de estudar. Aprende-se mais fechando o material e tentando lembrar: o esforço de puxar da memória, mesmo errando, é o que fixa. Reconhecer um trecho já visto engana, porque parece domínio e não é. Duas consequências para o desenho de um exercício. A primeira: ele tem que ter a forma em que a pessoa vai precisar se sair depois — se o trabalho é redigir um parecer, o exercício é redigir, não marcar a alternativa certa. A segunda: repetir espalhado no tempo, voltando quando já se começou a esquecer, custa mais no momento e rende mais no fim do que estudar tudo de uma vez.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Make It Stick
      * Design for How People Learn

* **vocabulario-controlado** — Vocabulário controlado `[claudinho-conhecimento]`
   * definição: Quem procura por "demissão", quem procura por "desligamento" e quem procura por "rescisão" deveria achar as mesmas coisas. O vocabulário controlado é a lista fechada de termos que garante isso: cada assunto tem um termo oficial, os sinônimos remetem a ele em vez de virarem entradas próprias, e palavras iguais com sentidos diferentes ganham um qualificador para não se misturarem. O trabalho é decidir, para cada palavra que aparece, uma de três coisas: vira termo oficial, vira apelido que aponta para um termo já existente, ou fica de fora. As ligações entre termos também são poucas de propósito — o mesmo que, mais amplo que, mais estreito que, relacionado a. Permitir mais tipos de ligação deixa a lista impossível de manter coerente conforme ela cresce.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * ANSI/NISO Z39.19-2005 (R2010), Guidelines for the Construction, Format, and Management of Monolingual Controlled Vocabularies
      * SKOS Simple Knowledge Organization System Reference [snapshot 2026-08-01]
      * VCGE — Vocabulário Controlado do Governo Eletrônico

## gestao-organizacional

* **cadeia-de-resultados** — Cadeia de resultados `[claudinha-gestao-estrategica]`
   * definição: O caminho escrito entre o dinheiro que se gasta e a mudança que se espera: com este recurso faz-se esta atividade, que produz esta entrega, que provoca este efeito imediato, que leva àquele resultado final. Cada seta é uma aposta sobre como o mundo funciona, e escrevê-las obriga a mostrar em que ponto a explicação fica fina — quase sempre na última. Serve em dois momentos. Antes de gastar, revela o degrau que ninguém sabe explicar, e é mais barato descobrir isso no papel. Depois de gastar, é o que permite avaliar sem discussão de opinião: com o caminho escrito, dá para verificar em que elo a coisa parou; sem ele, não há como separar o que o programa causou daquilo que teria acontecido de qualquer jeito.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Nota Técnica — Como elaborar modelo lógico de programa: um roteiro básico
      * Guia técnico de gestão estratégica
      * Guia de Monitoramento e Avaliação da Estratégia do MGI — 2ª edição

* **teto-de-compromisso** — Teto de compromisso `[claudinha-gestao-estrategica]`
   * definição: O limite do que se promete num período, declarado antes de escolher o que entra. Pode ser tempo fixo — seis semanas e o que não ficou pronto não ganha prorrogação —, número de coisas em andamento ao mesmo tempo, ou a capacidade estimada da equipe. O que não couber é dito em voz alta como fora, e não como "depois". Sem teto, priorizar vira ordenar: o item continua na lista, alguém continua esperando por ele, e o custo de dizer não fica escondido de quem pediu. Com teto, para entrar alguma coisa tem que sair, e essa troca é a decisão — o resto é conversa sobre importância, e tudo é importante. Quando o teto acaba, continuar exige uma decisão nova e explícita; a renovação automática é o mecanismo pelo qual um investimento ruim dura anos.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Guia de Elaboração de PDTIC do SISP, versão 2.1
      * The Standard for Project Management and A Guide to the Project Management Body of Knowledge (PMBOK Guide)
      * Shape Up _(ocorre em produtos-digitais)_
      * Essential Kanban Condensed _(ocorre em engenharia-software)_

* **entrega-vs-resultado** — Entrega vs. resultado `[claudinha-gestao-estrategica]`
   * definição: Entregar é ter construído a coisa; resultado é alguém ter passado a fazer diferente por causa dela. Um sistema pode estar no ar, no prazo, com todas as funcionalidades combinadas, e ninguém ter mudado de comportamento — os servidores continuam preenchendo a planilha antiga por fora, e o problema que motivou o gasto segue igual. Medir por entrega é fácil e engana, porque sempre haverá o que mostrar na reunião. Medir por resultado exige dizer, antes de começar, que comportamento deveria mudar e em quem. Iniciativa que não consegue responder isso não tem como falhar — e é exatamente por isso que ela também não tem como acertar.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Escaping the Build Trap _(ocorre em produtos-digitais)_
      * Nota Técnica — Como elaborar modelo lógico de programa: um roteiro básico

* **estruturacao-de-problema** — Estruturação de problema `[claudinho-arquiteto]`
   * definição: Antes de escolher entre soluções, alguém precisa escrever qual é o problema — e essa frase não vem pronta do mundo, é uma escolha. "A fila do atendimento está grande" e "as pessoas não deveriam precisar vir até aqui" descrevem a mesma cena e levam a projetos diferentes. Estruturar o problema é fazer essa escolha em aberto, com quem discorda na sala, e aceitar que o resultado é um enunciado ainda discutível, não uma resposta. Pular a etapa não elimina a escolha: só faz com que ela seja feita em silêncio, por quem escreveu o primeiro documento — e comparar alternativas com muito rigor a partir de um enunciado que ninguém examinou é resolver bem uma pergunta que talvez não interesse a ninguém.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Rational analysis for a problematic world revisited
      * Redesigning the future
      * Are Your Lights On? _(ocorre em produtos-digitais)_

* **fronteira-por-custo-de-transacao** — Fronteira por custo de transação `[claudinho-arquiteto]`
   * definição: Fazer dentro de casa custa coordenação: reunião, alinhamento, gente para gerenciar gente. Comprar de fora custa outra coisa: escolher fornecedor, escrever contrato, conferir se entregou. A fronteira fica onde o primeiro custo passa a ser maior que o segundo, e isso vale igual para uma empresa decidindo o que terceiriza e para um sistema decidindo o que vira componente separado. Como os dois custos mudam com o tempo, a fronteira certa também muda: quando ficou barato alugar servidor por hora, montar data center virou má ideia para quase todo mundo, sem que nada tivesse mudado no negócio. Separar bem tem um ganho extra que raramente entra na conta — uma parte bem isolada pode ser trocada por outra melhor depois, e essa possibilidade vale dinheiro mesmo enquanto ninguém a exerce.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The Nature of the Firm: Origins, Evolution, and Development
      * Design Rules, Vol. 1 _(ocorre em arquiteturas)_

* **gestao-estrategica** — Gestão estratégica `[claudinha-gestao-estrategica]`
   * definição: Manter viva a escolha de onde a organização aposta seus recursos: decidir, desdobrar a decisão em planos, acompanhar por indicadores e voltar a decidir quando o número desmentir a aposta. É um ciclo que não termina — e é isso que a separa do plano estratégico, que é apenas o documento produzido numa das voltas. A peça que faz o ciclo existir de verdade é o gatilho de revisão. Sem gatilho, revisa-se por calendário, e a organização descobre em dezembro que a aposta furou em março. Com gatilho, o desvio medido reabre a decisão no mês em que aparece, mesmo que o ciclo oficial só termine no fim do ano.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Guia técnico de gestão estratégica
      * Guia de Monitoramento e Avaliação da Estratégia do MGI — 2ª edição

* **pacto-de-entrega** — Pacto de entrega `[claudinha-gestao-estrategica]`
   * definição: Combinar por escrito o que a pessoa vai entregar num período e avaliá-la por isso, em vez de por hora de presença. O acordo diz as entregas, como serão medidas, em quanto tempo ela precisa responder a um chamado e quando pode ser convocada ao posto. Ao contrário do controle de ponto, sair da cadeira não é falta e ficar nela não é desempenho. Duas consequências costumam pegar as chefias de surpresa. A primeira é que agora é preciso dizer, antes, o que se quer — trabalho maior do que conferir quem chegou. A segunda é que a adesão é condicionada e não vira direito: descumprido o combinado, a pessoa volta ao regime comum, e o que serve de prova é o documento assinado, não a impressão de quem observa.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Instrução Normativa Conjunta SEGES-SGPRT/MGI nº 24, de 28 de julho de 2023 — Programa de Gestão e Desempenho (versão comparada e consolidada)
      * Guia prático para implementação e execução do PGD na Administração Pública Federal — Módulo 6: Complementares, 3ª edição

* **governanca-publica** — Governança pública `[claudinha-gestao-estrategica]`
   * definição: O arranjo que decide quem manda, para onde se vai e quem cobra dentro de uma organização pública. São três peças: liderança, que é quem responde por quê; estratégia, que é o rumo declarado; e controle, que é quem verifica se o rumo está sendo seguido. Juntas, servem para avaliar, direcionar e monitorar a gestão. O que se cobra desse arranjo é valor público: serviço e efeito que a sociedade reconhece como resposta a uma necessidade dela. Aí está a diferença para o arranjo de uma empresa, que responde a quem é dono e pode ser trocado por quem não gosta. Aqui responde-se a quem não escolheu ser cliente e não tem para onde levar sua preferência.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Decreto nº 9.203/2017 — Política de governança da administração pública federal
      * Guia da Política de Governança Pública

* **isomorfismo-institucional** — Isomorfismo institucional `[claudinha-gestao-estrategica]`
   * definição: Organizações copiam a forma umas das outras — a mesma diretoria, o mesmo comitê, o mesmo processo formal — e o motivo raramente é que aquilo funciona. Adota-se porque um órgão de controle exige, porque o vizinho fez e ninguém sabe o que fazer no lugar, ou porque a profissão ensina que é assim que se faz. Ter a forma faz a organização parecer séria, e parecer séria traz orçamento, convênio e sossego com a fiscalização. O efeito colateral é que a forma adotada se descola do trabalho real: o comitê existe no organograma e nunca decidiu nada, o processo está publicado e a operação segue por outro caminho. O sinal é a distância que se mantém estável e que ninguém corrige — porque corrigir custaria caro e a legitimidade já foi obtida com o papel.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Institutionalized Organizations: Formal Structure as Myth and Ceremony
      * The Iron Cage Revisited: Institutional Isomorphism and Collective Rationality in Organizational Fields

* **mecanismo-de-coordenacao** — Mecanismo de coordenação `[claudinho-arquiteto]`
   * definição: Quando o trabalho é dividido entre pessoas, alguma coisa precisa juntá-lo de volta. Só existem alguns jeitos de fazer isso: as pessoas se falam e combinam na hora; alguém manda; ou o encaixe já está definido de antemão, por regra escrita, por treinamento comum ou por uma peça que só serve de um jeito. Cada jeito tem um teto — combinar na hora funciona entre poucos e para de funcionar quando o grupo cresce, mandar não escala porque o chefe vira gargalo, regra escrita escala mas não lida com o caso imprevisto. Trocar as caixas do organograma sem trocar o jeito de coordenar não muda nada: a organização volta ao mesmo formato, porque é o jeito de coordenar que a sustenta.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The Structuring of Organizations
      * Team Topologies

* **problema-perverso** — Problema perverso `[claudinho-arquiteto]`
   * definição: Alguns problemas não têm enunciado fixo nem hora de acabar. Reduzir a violência num bairro é assim: não existe a formulação certa do problema, não existe teste que diga se a solução está correta, e a primeira tentativa já muda o bairro — não dá para voltar e tentar outra coisa nas mesmas condições. A consequência prática é sobre o formato do compromisso, não sobre o esforço. Tratar isso como projeto, com escopo fechado e data de entrega, produz entrega no prazo e problema intacto. O que cabe é intervir assumindo que cada movimento é definitivo e vale por si, e continuar acompanhando depois do fim previsto, porque não haverá um momento em que alguém possa dizer, apoiado em algum teste, que acabou.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dilemmas in a General Theory of Planning _(ocorre em produtos-digitais)_
      * The Structure of Ill Structured Problems

## ia

* **acesso-delegado** — Acesso delegado `[claudinho-seguranca]` `balde A`
   * definição: Você quer que um aplicativo de notas fiscais leia seu e-mail, mas não quer entregar sua senha — com ela, o aplicativo lê tudo, para sempre, e você só corta trocando a senha. Acesso delegado é o arranjo que resolve isso: um terceiro serviço confirma com você o que será permitido e entrega ao aplicativo uma autorização própria, limitada ao que você aprovou e com prazo. O ganho está na revogação. Cancelar aquela autorização derruba aquele aplicativo e não afeta mais nada que você tenha autorizado, porque cada um recebeu a sua — impossível quando todos usam a mesma senha.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15) _(ocorre em seguranca-privacidade)_
      * Final: OpenID Connect Core 1.0 incorporating errata set 2 [snapshot 2026-08-01] _(ocorre em seguranca-privacidade)_
      * Model Context Protocol — Specification 2026-07-28

* **confundimento-de-ambiente-em-avaliacao** — Confundimento de ambiente em avaliação `[claudinho-IA]`
   * definição: Quando se testa de ponta a ponta um sistema que usa IA, o número que sai não mede só o modelo. Mede também a máquina, a rede, a fila do servidor e a versão do programa que orquestra tudo — e essas coisas variam sozinhas, a ponto de o mesmo teste dar resultado diferente conforme a hora do dia. Daí a consequência: diferença entre dois testes não autoriza, sozinha, a frase "o modelo piorou". Para dizer isso é preciso ter rodado os dois no mesmo ambiente, ou ter medido antes quanto o ambiente sozinho faz o número oscilar. Sem isso, culpar o modelo é palpite — e é o palpite mais fácil, porque o modelo é a única peça que se anuncia.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * Quantifying infrastructure noise in agentic coding evals [snapshot 2026-08-01]
      * An update on recent Claude Code quality reports [snapshot 2026-08-01]

* **degradacao-diferencial-sob-compressao** — Degradação diferencial sob compressão `[claudinho-IA]`
   * definição: Modelos são encolhidos para caber em máquina menor, por exemplo guardando cada número com menos casas. O encolhimento tem preço, e o preço não se distribui por igual: responder uma pergunta isolada quase não piora, enquanto tarefa de muitos passos encadeados — chamar uma ferramenta, ler o retorno, decidir o passo seguinte — piora bastante. O erro comum é medir a versão encolhida por um teste de pergunta única, ver empate com a original e concluir que o encolhimento saiu de graça. Saiu de graça naquilo que foi medido. O efeito aparece na tarefa longa, e cada modelo degrada de um jeito próprio, o que impede transportar a medida de um para outro.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * Can Compressed LLMs Truly Act? An Empirical Evaluation of Agentic Capabilities in LLM Compression
      * Quantize with Confidence? An Empirical Study of Quantization for Code Generation

* **autoridade-do-intermediario** — Autoridade do intermediário `[claudinho-seguranca]` `balde B`
   * definição: Um programa que atende várias pessoas costuma ter mais poder do que qualquer uma delas: o sistema de folha pode ler o salário de todo mundo, e cada funcionário só pode ler o seu. Quando alguém faz um pedido a esse programa, quem aparece do outro lado é o programa, com o poder dele — não a pessoa, com o poder dela. É o problema que a literatura chama de delegado confuso. A correção não é confiar menos no intermediário, é amarrar cada pedido a quem o originou: a credencial declara para qual destino foi emitida e é recusada em qualquer outro, o consentimento é dado por ato e não uma vez para sempre, e a credencial recebida de um lado nunca é repassada adiante para o outro.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Model Context Protocol — Specification 2026-07-28
      * Resource Indicators for OAuth 2.0 _(ocorre em seguranca-privacidade)_
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15) _(ocorre em seguranca-privacidade)_

* **interacao-tardia** — Interação tardia `[claudinho-IA]`
   * definição: Uma pergunta com dois assuntos — "multa de trânsito em veículo de aluguel" — vira um ponto só quando é comprimida em uma lista de números, e esse ponto cai na média entre os dois assuntos, um lugar onde não existe documento nenhum. A interação tardia evita a média: cada palavra da pergunta e cada palavra do documento vira o seu próprio ponto, e o encontro entre os dois é deixado para o fim. Cada palavra da pergunta procura a palavra do documento mais próxima dela, e o documento fica com a soma desses melhores encontros. Assim "multa" casa com "multa" e "aluguel" com "locação" ao mesmo tempo, sem um borrar o outro; os pontos do documento continuam calculados de antemão, então a busca segue rápida. O custo é espaço: guardar um ponto por palavra ocupa cerca de dez vezes mais que guardar um por documento.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT
      * ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction

* **isolamento-de-contexto-por-delegacao** — Isolamento de contexto por delegação `[claudinho-IA]`
   * definição: Todo modelo tem um limite de quanto texto cabe numa conversa, e uma investigação longa — abrir vinte arquivos para responder uma pergunta — enche esse limite com material que não é a resposta. A saída é entregar a investigação a uma segunda instância, que gasta o próprio limite lendo tudo e devolve só o que achou. O motivo é contabilidade, não competência: quem recebe a tarefa não precisa saber mais que quem delegou, precisa ter espaço próprio para queimar. A conta só fecha se o que volta for muito menor do que foi lido. Quando quase tudo que se leu importa na resposta, dividir custa mais do que rende, porque o material acaba voltando inteiro.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * How we built our multi-agent research system [snapshot 2026-08-01]
      * Best practices for Claude Code - Claude Code Docs [snapshot 2026-08-01]
      * Scaling Managed Agents: Decoupling the brain from the hands [snapshot 2026-08-01]

* **mediacao-do-loop-agentico** — Mediação do loop agêntico `[claudinho-IA]`
   * definição: Um programa que executa ações sozinho — mexer em arquivo, rodar comando, chamar serviço — precisa de algum ponto em que alguém, ou alguma coisa, diga "pode". Há três formas: pedir aprovação humana a cada ação; deixar uma regra automática revisar cada ação e barrar o que sai do combinado; ou dar liberdade dentro de uma cerca fechada de antemão, em que só existe o que ele tem direito de tocar. A escolha troca incômodo por estrago possível, e traz uma armadilha. Pedir aprovação a cada passo parece a opção mais segura, mas na décima janela a pessoa aprova sem ler: a frequência do pedido destrói a vigilância que o justificava. Quem escolhe essa forma tem que contar com aprovação distraída, não com atenção constante.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Making Claude Code more secure and autonomous with sandboxing [snapshot 2026-08-01] _(ocorre em seguranca-privacidade)_
      * How we built Claude Code auto mode: a safer way to skip permissions [snapshot 2026-08-01] _(ocorre em seguranca-privacidade)_
      * Best practices for Claude Code - Claude Code Docs [snapshot 2026-08-01]

* **quando-cabe-um-agente** — Quando cabe um agente `[claudinho-IA]`
   * definição: Antes de montar um sistema com IA, uma pergunta decide a forma dele: dá para escrever de antemão os passos que ele vai dar? Se dá — ler a nota fiscal, conferir contra a tabela, emitir o aviso —, o certo é um roteiro fixo, em que cada passo é um pedaço testável e barato. Se não dá, porque o passo seguinte depende do que aparecer no anterior, entra o agente, que decide o próximo passo a cada volta. O agente custa mais por tarefa, erra de formas que o roteiro não erra e é mais difícil de investigar, porque cada execução segue um caminho diferente. Em troca, aguenta o caso que ninguém mapeou. Escolher agente onde o roteiro daria conta é pagar essa conta sem precisar.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Building Effective AI Agents [snapshot 2026-08-01]
      * Prompt Engineering for LLMs (for True Epub)

* **ranqueamento-multiestagio** — Ranqueamento multiestágio `[claudinho-IA]`
   * definição: Busca feita em etapas, como peneira: a primeira passa por todo o acervo e é barata e grosseira, separando algumas centenas de candidatos; só sobre esses roda a etapa cara, que ordena com cuidado. O custo alto é pago por poucos itens em vez de por milhões. A consequência decide projeto: o que a primeira etapa não pescou está perdido. Nenhuma etapa seguinte inventa um documento que não recebeu — melhorar o reordenador não conserta o que ficou fora da peneira. Por isso a primeira etapa se ajusta para não deixar escapar, e não para acertar em cheio; acertar em cheio é serviço da última.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Pretrained Transformers for Text Ranking: BERT and Beyond
      * A Simple Guide to Retrieval Augmented Generation
      * LLM Engineer’s Handbook

* **recuperacao-densa** — Recuperação densa `[claudinho-IA]`
   * definição: Busca por significado em vez de por palavra: a pergunta e cada documento viram uma lista de números que funciona como coordenada, e devolve-se o que caiu perto da pergunta. Como cada documento é convertido sozinho, sem saber que pergunta virá, dá para converter tudo de antemão e guardar — na hora da busca só se procura o vizinho mais próximo, o que é rápido mesmo com milhões de itens. O preço é a comparação grosseira, feita entre dois pontos já fechados. Existe a alternativa de ler pergunta e documento juntos, que casa muito melhor e é inviável como busca, porque exigiria reler o acervo inteiro a cada pergunta. Por isso a leitura conjunta costuma entrar depois, sobre os poucos candidatos que a busca por vizinhança trouxe.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Dense Passage Retrieval for Open-Domain Question Answering
      * M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation
      * Pretrained Transformers for Text Ranking: BERT and Beyond

* **relevancia-graduada** — Relevância graduada `[claudinho-IA]`
   * definição: Nem todo acerto vale igual: num resultado de busca, o documento que responde a pergunta inteira vale mais que o que tangencia o assunto. A relevância graduada mede um sistema de busca tratando isso como grau — cada resultado entra com um valor conforme quanto responde, e esse valor pesa menos quanto mais embaixo ele aparece na lista. A soma desses valores, dividida pela soma da melhor ordem possível, dá uma nota entre 0 e 1. Contar apenas acerto e erro esconde duas coisas que essa nota mostra: quem põe o resultado excelente em quinto perde para quem o põe em primeiro, e quem enche as primeiras posições de resultados apenas aceitáveis não empata com quem acertou em cheio.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Cumulated gain-based evaluation of IR techniques
      * IR evaluation methods for retrieving highly relevant documents

* **transporte-de-estado-entre-sessoes** — Transporte de estado entre sessões `[claudinho-IA]`
   * definição: Um trabalho que não cabe numa conversa só precisa continuar em outra, e a seguinte começa sem lembrar nada da anterior. É uma obra tocada por turnos em que nenhum turno conversa com o próximo: chega adiante apenas o que ficou escrito em lugar durável — lista de pendências, diário de bordo, o próprio código já salvo. A regra prática é dura: o que não foi escrito não existe para quem vem depois. Isso inclui o que se perdeu quando a conversa foi resumida para caber. Decisão tomada e não anotada volta a ser tomada, às vezes ao contrário da primeira vez — por isso escrever o estado é parte da tarefa, e não relatório dela.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Effective harnesses for long-running agents [snapshot 2026-08-01]
      * Harness design for long-running application development [snapshot 2026-08-01]
      * Code execution with MCP: building more efficient AI agents [snapshot 2026-08-01]

## produtos-digitais

* **affordance** — Affordance `[claudinha-produto]`
   * definição: Um objeto sinaliza, pela própria forma, o que dá para fazer com ele: uma maçaneta vertical pede puxar, uma placa lisa pede empurrar. Affordance é essa relação entre o que o objeto permite e o que quem usa consegue fazer. O que produz veredito é que permitir e sinalizar são coisas separadas. A ação pode existir sem aparecer — a porta abre, mas nada indica para que lado — ou aparecer sem existir, como a maçaneta que convida a puxar numa porta trancada. Julgar uma tela é comparar as duas listas: o que ela deixa fazer e o que ela avisa que deixa.
   * natureza: disposicao
   * estatuto: natural
   * âncoras:
      * Technology Affordances
      * The Design of Everyday Things

* **avaliacao-heuristica** — Avaliação heurística `[claudinha-produto]`
   * definição: Antes de chamar qualquer usuário, uma pessoa percorre a tela sozinha conferindo-a contra uma lista curta e fixa de perguntas: o sistema mostra em que estado está? dá para desfazer o que foi feito? usa as palavras de quem usa ou as do banco de dados? avisa antes de deixar errar? Avaliação heurística é essa inspeção contra lista. O ganho é que a reprovação sai com nome. Não é "não gostei desta tela", é "esta tela esconde o estado do sistema, aqui" — e quem construiu pode discordar do veredito, não do critério. O limite é igualmente claro: a lista pega violação de princípio, não pega o que só aparece quando gente de verdade tenta cumprir a tarefa.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Jakob's Ten Usability Heuristics
      * Designing Interfaces Patterns for Effective Interaction Design
      * Cracking the PM Career

* **teto-de-compromisso** — Teto de compromisso `[claudinha-gestao-estrategica]`
   * definição: O limite do que se promete num período, declarado antes de escolher o que entra. Pode ser tempo fixo — seis semanas e o que não ficou pronto não ganha prorrogação —, número de coisas em andamento ao mesmo tempo, ou a capacidade estimada da equipe. O que não couber é dito em voz alta como fora, e não como "depois". Sem teto, priorizar vira ordenar: o item continua na lista, alguém continua esperando por ele, e o custo de dizer não fica escondido de quem pediu. Com teto, para entrar alguma coisa tem que sair, e essa troca é a decisão — o resto é conversa sobre importância, e tudo é importante. Quando o teto acaba, continuar exige uma decisão nova e explícita; a renovação automática é o mecanismo pelo qual um investimento ruim dura anos.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Guia de Elaboração de PDTIC do SISP, versão 2.1 _(ocorre em gestao-organizacional)_
      * The Standard for Project Management and A Guide to the Project Management Body of Knowledge (PMBOK Guide) _(ocorre em gestao-organizacional)_
      * Shape Up
      * Essential Kanban Condensed _(ocorre em engenharia-software)_

* **design-centrado-no-humano** — Design centrado no humano `[claudinha-produto]`
   * definição: Um sistema pode cumprir tudo que foi especificado e mesmo assim ser abandonado por quem deveria usá-lo, porque as pessoas, as tarefas e o lugar reais nunca foram olhados de perto. O design centrado no humano é o conjunto de exigências que fecha essa porta: entender antes quem usa, o que faz e onde; envolver essas pessoas durante o trabalho, não só no fim; submeter cada versão à avaliação de usuários, inclusive na hora de aceitar o produto pronto; e repetir o ciclo enquanto ainda houver dúvida sobre o uso. O que separa isso de "conversamos com uns usuários" é o registro: cada uma das quatro exigências deixa evidência datada, e quem confere é a evidência, não a boa intenção de quem fez. Vale igual para formulário de papel e atendimento de balcão — não é regra de aplicativo.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Ergonomics of human-system interaction — Part 210: Human-centred design for interactive systems
      * Design Thinking Bootleg
      * About Face

* **entrega-vs-resultado** — Entrega vs. resultado `[claudinha-gestao-estrategica]`
   * definição: Entregar é ter construído a coisa; resultado é alguém ter passado a fazer diferente por causa dela. Um sistema pode estar no ar, no prazo, com todas as funcionalidades combinadas, e ninguém ter mudado de comportamento — os servidores continuam preenchendo a planilha antiga por fora, e o problema que motivou o gasto segue igual. Medir por entrega é fácil e engana, porque sempre haverá o que mostrar na reunião. Medir por resultado exige dizer, antes de começar, que comportamento deveria mudar e em quem. Iniciativa que não consegue responder isso não tem como falhar — e é exatamente por isso que ela também não tem como acertar.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Escaping the Build Trap
      * Nota Técnica — Como elaborar modelo lógico de programa: um roteiro básico _(ocorre em gestao-organizacional)_

* **entrevista-por-comportamento-passado** — Entrevista por comportamento passado `[claudinha-produto]`
   * definição: Perguntar "você usaria isso?" rende resposta educada e inútil: quase todo mundo diz que sim, e quase ninguém usa. Numa conversa de descoberta conta o que a pessoa já fez — a última vez que enfrentou o problema, o que ela fez naquele dia, quanto tempo ou dinheiro gastou — e o que ela se compromete a fazer agora: marcar a próxima conversa, apresentar um colega, pagar adiantado. Por isso a própria ideia entra tarde na conversa, ou não entra. Mencionada cedo, ela vira o assunto: o interlocutor passa a opinar sobre a ideia, em vez de contar a própria vida — que é a única coisa que ele sabe melhor do que quem pergunta.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * The Mom Test
      * Continuous Discovery Habits
      * Empowered

* **erro-de-tipo-tres** — Erro de tipo três `[claudinha-gestao-estrategica]`
   * definição: Acertar a resposta da pergunta errada. O time entrega no prazo, a solução funciona como projetada, os indicadores da entrega fecham em verde — e nada do que incomodava alguém melhorou, porque o problema atacado não era o que estava ali. Chama-se de tipo três porque os erros de tipo um e dois, na estatística, são enganos cometidos dentro da pergunta certa; este é o engano na pergunta. O que torna esse erro caro é justamente a qualidade da execução: quanto melhor feito o trabalho, mais difícil convencer alguém de que a pergunta estava errada. Erro de execução se denuncia sozinho, porque algo quebra. Este só aparece quando alguém volta ao enunciado — e ninguém volta ao enunciado de um projeto bem-sucedido.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dirty Rotten Strategies
      * Are Your Lights On?

* **esquema-de-organizacao** — Esquema de organização `[claudinha-produto]`
   * definição: Toda lista grande é arrumada por algum critério, e os critérios são de dois tipos. O exato — alfabético, por data, por lugar — põe cada item num só lugar e não deixa dúvida, mas só serve para quem já sabe o nome do que procura. O ambíguo — por assunto, por tarefa, por público — depende de julgamento, dois curadores arrumam diferente, e é o único que serve para quem sabe o problema e não sabe o nome. A escolha decide quem consegue encontrar. Num catálogo em ordem alfabética de título, quem quer "alguma coisa sobre contratar melhor" não acha nada; por assunto, acha, ao custo de o mesmo item caber em dois lugares. Coleção grande costuma precisar dos dois, e a decisão é qual deles é a porta de entrada.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Information Architecture: For the Web and Beyond _(ocorre em estudos-ontologias)_
      * Designing Interfaces Patterns for Effective Interaction Design

* **estruturacao-de-problema** — Estruturação de problema `[claudinha-gestao-estrategica]`
   * definição: Escrever qual é o problema, de quem ele é e o que contaria como resolvido, antes de listar soluções. Um prédio com fila no elevador pode ter um problema de engenharia — os elevadores são lentos — ou um problema de espera: quem espera se irrita, e um espelho no hall resolve. As duas leituras nascem do mesmo fato e levam a investimentos que não se parecem em nada. Enquanto o enunciado não estiver escrito e aceito por quem paga a conta, comparar alternativas é responder bem a uma pergunta que ninguém fez. O sinal de que a etapa foi pulada é a reunião que começa direto na lista de opções, com cada pessoa achando que todo mundo fala da mesma coisa.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Systems thinking, systems practice _(ocorre em arquiteturas)_
      * Are Your Lights On?
      * Dirty Rotten Strategies
      * Dilemmas in a General Theory of Planning

* **estruturacao-de-problema** — Estruturação de problema `[claudinho-arquiteto]`
   * definição: Antes de escolher entre soluções, alguém precisa escrever qual é o problema — e essa frase não vem pronta do mundo, é uma escolha. "A fila do atendimento está grande" e "as pessoas não deveriam precisar vir até aqui" descrevem a mesma cena e levam a projetos diferentes. Estruturar o problema é fazer essa escolha em aberto, com quem discorda na sala, e aceitar que o resultado é um enunciado ainda discutível, não uma resposta. Pular a etapa não elimina a escolha: só faz com que ela seja feita em silêncio, por quem escreveu o primeiro documento — e comparar alternativas com muito rigor a partir de um enunciado que ninguém examinou é resolver bem uma pergunta que talvez não interesse a ninguém.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Rational analysis for a problematic world revisited _(ocorre em gestao-organizacional)_
      * Redesigning the future _(ocorre em gestao-organizacional)_
      * Are Your Lights On?

* **fatiamento-por-jornada** — Fatiamento por jornada completa `[claudinha-produto]`
   * definição: Uma entrega parcial só vale se alguém conseguir chegar ao fim de alguma coisa com ela. Fatiar por jornada é recortar a próxima entrega como o menor pedaço que permite a uma pessoa começar uma tarefa e terminá-la — do momento em que ela precisa até o momento em que ela tem o que queria, ou desistiu por um caminho previsto. O recorte oposto é por camada: primeiro o banco de dados, depois a tela, depois o envio. Cada pedaço fica pronto e ninguém consegue fazer nada com nenhum, então não há o que testar com usuário nem o que pôr no ar. Por isso o aceite se escreve como o caminho inteiro, antes de construir: se ninguém completa nada, não é fatia.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * User Story Mapping
      * WritingEffectiveUCs.book

* **gap-desenho-realidade** — Gap desenho-realidade `[claudinha-produto]`
   * definição: Todo sistema novo carrega uma imagem de como o mundo é: que dados existem, quem faz o quê, que equipamento tem na ponta, o que as pessoas ali valorizam. Quando essa imagem está longe do lugar onde o sistema vai ser instalado, ele fracassa mesmo bem construído — e a distância se mede uma dimensão de cada vez: informação, tecnologia, processos de trabalho, objetivos e valores, pessoal, gestão, demais recursos. Um telecentro projetado supondo energia estável, técnico morando perto e gente querendo internet, instalado onde falta as três coisas, já tem distância grande em quatro dimensões: o prognóstico é ruim antes da primeira linha de código. E só duas coisas mudam o prognóstico — aproximar o desenho da realidade, ou mexer na realidade para perto do desenho.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * The origins of failure: seeking the causes of design-reality gaps
      * Minding the Design Reality Gap: An Empirical Evaluation of Telecentre Initiatives in Rural Ghana
      * Towards design of citizen centric e-government projects in developing country context: the design-reality gap in Uganda

* **problema-perverso** — Problema perverso `[claudinha-gestao-estrategica]`
   * definição: Alguns problemas não têm enunciado fechado nem linha de chegada: reduzir a violência de um bairro, integrar imigrantes, reformar um currículo. Cada tentativa muda a situação que se queria estudar, então não há como testar duas vezes, e nunca chega o momento em que alguém possa dizer "pronto, acabou". Isso decide o formato do compromisso, e é aí que a distinção paga. Problema com fim declarado se organiza como projeto, com prazo e entrega. Problema perverso não aceita esse formato: o que se pode prometer é uma intervenção assumida como sem volta, com revisão periódica e recursos renovados a cada volta. Prometer conclusão é prometer o que a natureza do problema não entrega, e o custo aparece anos depois, na forma de programa que ninguém consegue encerrar nem defender.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dilemmas in a General Theory of Planning
      * Systems thinking, systems practice _(ocorre em arquiteturas)_

* **problema-perverso** — Problema perverso `[claudinho-arquiteto]`
   * definição: Alguns problemas não têm enunciado fixo nem hora de acabar. Reduzir a violência num bairro é assim: não existe a formulação certa do problema, não existe teste que diga se a solução está correta, e a primeira tentativa já muda o bairro — não dá para voltar e tentar outra coisa nas mesmas condições. A consequência prática é sobre o formato do compromisso, não sobre o esforço. Tratar isso como projeto, com escopo fechado e data de entrega, produz entrega no prazo e problema intacto. O que cabe é intervir assumindo que cada movimento é definitivo e vale por si, e continuar acompanhando depois do fim previsto, porque não haverá um momento em que alguém possa dizer, apoiado em algum teste, que acabou.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dilemmas in a General Theory of Planning
      * The Structure of Ill Structured Problems _(ocorre em gestao-organizacional)_

* **resultado-sobre-entrega** — Resultado sobre entrega `[claudinha-produto]`
   * definição: Entregar uma funcionalidade não é a mesma coisa que conseguir algo com ela. O resultado é a mudança de comportamento de gente de verdade — o cliente que passa a concluir a compra, o atendente que passa a resolver no primeiro contato — e é essa mudança que liga o que se constrói ao que a organização queria. Na prática a pergunta muda: sai "o que vamos construir neste trimestre?" e entra "quem vai passar a fazer o que de diferente, e como saberemos?". A pergunta nova admite resposta que não é software — mudar um texto, um preço, uma regra, um treinamento — e deixa visível a entrega que ficou pronta no prazo sem mudar o comportamento de ninguém, que pelo critério antigo passava por sucesso.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Outcomes Over Output
      * Impact Mapping

* **riscos-de-produto** — Riscos de produto `[claudinha-produto]`
   * definição: Uma ideia de produto pode morrer por quatro motivos diferentes, e a evidência que afasta um não diz nada sobre os outros três: as pessoas não querem (valor); querem e não conseguem usar (usabilidade); dá vontade e não dá para construir no prazo e no custo (viabilidade técnica); serve ao usuário e não fecha para quem banca, por causa de jurídico, suporte, canal de venda ou orçamento (viabilidade de negócio). O erro comum é parar no primeiro: entrevistas entusiasmadas viram autorização para construir, e a coisa morre depois na usabilidade ou no jurídico. Por isso o critério é evidência coletada contra os quatro, e não a convicção de quem decide — que costuma ser mais firme justamente onde ninguém olhou.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Inspired
      * Empowered

* **teste-de-usabilidade-informal** — Teste de usabilidade informal `[claudinha-produto]`
   * definição: Uma manhã por mês, três pessoas de fora tentam usar o que a equipe fez, falando em voz alta o que estão pensando, enquanto quem construiu assiste. É barato e não precisa de laboratório nem de recrutamento caprichado: problema grave aparece para quase qualquer pessoa que nunca viu aquela tela. O sucesso não é achar todos os problemas — é achar, a cada rodada, os poucos mais graves e sair da sala com o compromisso de consertá-los antes da próxima. Testar com trinta pessoas e conseguir consertar dois problemas rende menos que testar com três e consertar dois todo mês. Por isso a conversa depois do teste termina numa lista curta e combinada, não num relatório.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Rocket Surgery Made Easy: The Do-It-Yourself Guide to Finding and Fixing Usability Problems
      * Don't Make Me Think, Revisited

## seguranca-privacidade

* **acesso-delegado** — Acesso delegado `[claudinho-seguranca]` `balde A`
   * definição: Você quer que um aplicativo de notas fiscais leia seu e-mail, mas não quer entregar sua senha — com ela, o aplicativo lê tudo, para sempre, e você só corta trocando a senha. Acesso delegado é o arranjo que resolve isso: um terceiro serviço confirma com você o que será permitido e entrega ao aplicativo uma autorização própria, limitada ao que você aprovou e com prazo. O ganho está na revogação. Cancelar aquela autorização derruba aquele aplicativo e não afeta mais nada que você tenha autorizado, porque cada um recebeu a sua — impossível quando todos usam a mesma senha.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15)
      * Final: OpenID Connect Core 1.0 incorporating errata set 2 [snapshot 2026-08-01]
      * Model Context Protocol — Specification 2026-07-28 _(ocorre em ia)_

* **avaliacao-de-conformidade** — Avaliação de conformidade `[claudinho-seguranca]` `balde B`
   * definição: Três papéis separados de propósito: quem fabrica declara o que o produto faz, um laboratório credenciado testa contra requisitos escritos de antemão, e uma autoridade decide se emite o certificado. A separação é o mecanismo — se quem fabrica também testasse e certificasse, o selo não diria nada que a propaganda já não dissesse. O que costuma se perder na leitura é o alcance. O selo cobre aquele objeto, naquela configuração testada, contra aquela lista de requisitos. Um cofre certificado dentro de um sistema não certifica o sistema, e a versão seguinte do produto não herda o certificado da anterior.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Manual de Condutas Técnicas 11 — Volume I: requisitos, materiais e documentos técnicos para homologação de software de AC e AR no âmbito da ICP-Brasil
      * Manual de Condutas Técnicas 11 — Volume II: procedimentos de ensaios para avaliação de conformidade aos requisitos técnicos de softwares de AC e AR no âmbito da ICP-Brasil
      * CMVP Documentation Requirements: CMVP Validation Authority Updates to ISO/IEC 24759

* **avaliacao-de-impacto-a-privacidade** — Avaliação de impacto à privacidade `[claudinho-seguranca]` `balde A`
   * definição: Exame feito antes de ligar um tratamento novo, ou de mudar um que já roda, que descreve a operação, lista os riscos que ela cria para as pessoas e registra o que foi feito para reduzi-los. Em algumas situações a lei o exige: decisão automatizada com efeito jurídico sobre alguém, uso em larga escala de dado sensível. A palavra que carrega o peso é antes. Com o sistema no ar, mudar o desenho custa caro e a conclusão tende a acompanhar o que já foi construído. O documento serve para que a decisão exista por escrito enquanto ainda dá para decidir diferente.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * ABNT NBR ISO/IEC 27701:2019 — Técnicas de segurança — Extensão da ABNT NBR ISO/IEC 27001 e 27002 para gestão da privacidade da informação
      * Hipóteses legais de tratamento de dados pessoais - Legítimo Interesse
      * DPO Guide

* **base-legal-de-tratamento** — Base legal de tratamento `[claudinho-seguranca]` `balde B`
   * definição: Usar dado de pessoas exige uma permissão prevista em lei, escolhida antes de começar. Não basta o uso ser útil nem o dado estar bem guardado: a lei lista as situações em que se pode tratar dado pessoal — cumprir obrigação legal, executar contrato, consentimento, entre outras — e o uso precisa caber em uma delas. Duas consequências práticas. A permissão não se troca depois que o problema aparece, porque foi ela que justificou coletar aquele dado daquele jeito. E a lista muda conforme o dado: o que autoriza tratar um endereço não autoriza tratar um diagnóstico médico, que a lei protege à parte.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Hipóteses legais de tratamento de dados pessoais - Legítimo Interesse
      * LGPD - Saúde
      * Tratamento de dados pessoais pelo Poder Público: guia orientativo
      * Tratamento de dados pessoais para fins acadêmicos e para a realização de estudos e pesquisas — guia orientativo

* **comunicacao-de-incidente-ao-titular** — Comunicação de incidente ao titular `[claudinho-seguranca]` `balde A`
   * definição: Incidente com dado pessoal que possa trazer risco relevante às pessoas tem que ser avisado. A organização comunica a autoridade e as pessoas atingidas, em prazo definido, dizendo quais dados foram afetados, quem foi afetado, quais os riscos, o que os protegia e o que está sendo feito. O gatilho é o risco para a pessoa, não o tamanho técnico do estrago. Um incidente contido em dez minutos, sem prova de cópia, que expôs dados de saúde de mil pacientes, dispara o dever; uma invasão espetacular em servidor sem dado pessoal não dispara. É quem foi avisado que decide o que fazer com o aviso — trocar senha, vigiar a fatura —, e por isso segurar a informação é dano somado ao dano.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Lei nº 13.709, de 14 de agosto de 2018 — Lei Geral de Proteção de Dados Pessoais (LGPD)
      * The EU General Data Protection Regulation (GDPR): A Practical Guide
      * DPO Guide

* **controlador-e-operador** — Controlador e operador `[claudinho-seguranca]` `balde A`
   * definição: Responde pelo tratamento de dados quem decide para que servem e como serão usados, não quem opera os sistemas. A empresa que contrata um serviço de disparo de e-mail responde pela campanha; o fornecedor executa o contratado e responde por seguir a instrução. A regra tem uma virada importante. Se o fornecedor usa aqueles dados para finalidade própria — treinar um produto dele, montar uma base para vender — deixa de ser executor naquele ponto e passa a responder como quem decidiu. A responsabilidade acompanha quem escolheu a finalidade, e escolher sem contrato não isenta ninguém.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * ABNT NBR ISO/IEC 27701:2019 — Técnicas de segurança — Extensão da ABNT NBR ISO/IEC 27001 e 27002 para gestão da privacidade da informação
      * Guidelines on shaping pseudonymisation according to GDPR provisions
      * Tratamento de dados pessoais pelo Poder Público: guia orientativo

* **credenciamento-de-seguranca** — Credenciamento de segurança `[claudinho-seguranca]` `balde A`
   * definição: Para lidar com informação sigilosa do Estado não basta ter o cargo e a necessidade. A pessoa — e também o órgão ou a empresa contratada — precisa ter sido habilitada antes, por autoridade competente, mediante verificação de idoneidade, qualificação técnica e indicação de um responsável nomeado. A habilitação vale por grau: quem está habilitado num grau não trata os acima dele. O ponto que surpreende quem vem da iniciativa privada é que, sem essa habilitação vigente, o acesso é ilícito ainda que a pessoa precise da informação para trabalhar e o sistema técnico permita.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Decreto nº 7.845, de 14 de novembro de 2012 — Credenciamento de segurança e tratamento de informação classificada
      * Instrução Normativa GSI/PR nº 2, de 5 de fevereiro de 2013 — Credenciamento de segurança para o tratamento de informação classificada
      * Norma Complementar 01/IN02/NSC/GSI/PR — disciplina o credenciamento de segurança de pessoas naturais, órgãos e entidades públicas e privadas para o tratamento de informações classificadas

* **criptoperiodo** — Criptoperíodo `[claudinho-seguranca]` `balde A`
   * definição: Toda chave tem prazo de validade, curto por três razões concretas. Quanto mais tempo a mesma chave cifra coisas, mais material acumulado alguém tem para tentar quebrá-la. Quanto mais tempo ela vale, maior o estrago se vazar — tudo que protegeu, do começo ao fim. E nenhuma chave deve durar mais que o algoritmo que a usa, que envelhece por conta própria. É esse prazo que manda na rotação. Trocar chave dá trabalho e costuma ser adiado pela agenda da operação; adiar é decidir correr o risco, não evitá-lo.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * nist.sp.800-57pt1r5
      * Transitioning the Use of Cryptographic Algorithms and Key Lengths
      * ISC2 CISSP Certified Information Systems Security Professional Official Study Guide

* **dado-aberto-por-padrao** — Dado aberto por padrão `[claudinho-arquiteto]`
   * definição: Todo dado que a organização produz nasce público. Quem quiser fechar um deles tem que dizer em qual das hipóteses de sigilo já previstas ele se encaixa — e a hipótese existia antes do pedido. Isso inverte quem tem trabalho a fazer: no arranjo comum, quem quer o dado justifica por que merece; aqui quem guarda justifica por que reteve, e "não vejo por que abrir" não é justificativa. O efeito prático é que o acesso deixa de ser negociado caso a caso entre dois setores e passa a ser decidido de antemão, pelo enquadramento que já está escrito.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Decreto nº 8.777/2016 — Política de Dados Abertos do Poder Executivo federal _(ocorre em arquiteturas)_
      * Decreto nº 10.046/2019 — Governança no compartilhamento de dados na administração pública federal

* **dano-sem-vazamento** — Dano sem vazamento `[claudinho-seguranca]` `balde B`
   * definição: Nem todo prejuízo a uma pessoa vem de alguém invadindo alguma coisa. Cruzar três cadastros públicos e descobrir quem mora com quem; deduzir uma gravidez pelo histórico de compras; usar para reajustar um seguro o dado que foi coletado para marcar consulta. Em todos esses casos ninguém arrombou nada, todo mundo tinha acesso legítimo, e a pessoa saiu pior. Por isso não houve incidente de segurança não responde a houve dano. A lista de ameaças que serve para proteger sistema — invasão, adulteração, indisponibilidade — não enumera essas, e quem olha só por ela conclui que está tudo bem.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Threat Modeling: Designing for Security
      * NIST Privacy Framework: A Tool for Improving Privacy Through Enterprise Risk Management, Version 1.0
      * Understanding Privacy

* **autoridade-do-intermediario** — Autoridade do intermediário `[claudinho-seguranca]` `balde B`
   * definição: Um programa que atende várias pessoas costuma ter mais poder do que qualquer uma delas: o sistema de folha pode ler o salário de todo mundo, e cada funcionário só pode ler o seu. Quando alguém faz um pedido a esse programa, quem aparece do outro lado é o programa, com o poder dele — não a pessoa, com o poder dela. É o problema que a literatura chama de delegado confuso. A correção não é confiar menos no intermediário, é amarrar cada pedido a quem o originou: a credencial declara para qual destino foi emitida e é recusada em qualquer outro, o consentimento é dado por ato e não uma vez para sempre, e a credencial recebida de um lado nunca é repassada adiante para o outro.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Model Context Protocol — Specification 2026-07-28 _(ocorre em ia)_
      * Resource Indicators for OAuth 2.0
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15)

* **exercicio-adversarial** — Exercício adversarial `[claudinho-seguranca]` `balde A`
   * definição: Um grupo é contratado para agir como o inimigo — invadir, enganar funcionários, entrar no prédio — enquanto quem defende segue a rotina, muitas vezes sem saber que há exercício em curso. O que se mede é a defesa, não o alvo. Um teste de invasão comum responde se a falha existe e dá para explorar. Aqui a pergunta é outra: alguém percebeu, em quanto tempo, avisou quem, e o que fez depois. O resultado mais comum e mais desconfortável é a invasão ter dado certo por um caminho já conhecido e o alerta ter aparecido sem que ninguém olhasse.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * The Red Team Guide by Peerlyst
      * CompTIA CySA+ Cybersecurity Analyst Certification All-in-One Exam Guide (Exam CS0-002)

* **exercicio-de-plano** — Exercício de plano `[claudinho-seguranca]` `balde A`
   * definição: Reunir quem tem papel num plano — de crise, de recuperação, de continuidade — e apresentar um cenário: pegou fogo no datacenter às três da manhã de domingo, o que cada um faz? Pode ser conversa em volta da mesa ou pode chegar a executar as ações de verdade. O que se mede é o plano e o preparo de quem o executa, não o equipamento. A saída útil é a lacuna descoberta: o telefone do fornecedor que mudou, o passo que dependia de alguém que saiu, a decisão que ninguém sabe de quem é. Testar se o servidor reserva liga é outra coisa, e não substitui esta.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * nistspecialpublication800-84
      * CompTIA Security+ Certification Study Guide: Network Security Essentials

* **janela-de-exposicao** — Janela de exposição `[claudinho-seguranca]` `balde B`
   * definição: Entre o dia em que uma falha vira conhecida e o dia em que a correção está no ar, o sistema fica aberto — e quem ataca sabe disso, porque a falha foi anunciada em público junto com o remendo. Tudo que se coloca dentro desse intervalo para reduzir o risco de quebrar a operação — testar em homologação, esperar a janela de manutenção do fim de semana, colher aprovação — é pago em tempo de exposição. Não existe escolha entre seguro e inseguro: existe escolher qual dos dois riscos se prefere correr, o de a correção derrubar o serviço ou o de alguém entrar antes de ela chegar.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-40 Rev.4 — Patch Management _(ocorre em engenharia-software)_
      * ISO/IEC 27002:2013 — Information technology — Security techniques — Code of practice for information security controls
      * ISC2 CISSP Certified Information Systems Security Professional Official Study Guide

* **linha-de-base-de-controles** — Linha de base de controles `[claudinho-seguranca]` `balde A`
   * definição: Em vez de cada equipe escolher controle por controle, parte-se de um conjunto pronto para aquele tipo de sistema — servidor web, banco de dados, estação de trabalho — que passa a valer por padrão. O ajuste ao caso concreto se faz por decisões declaradas sobre essa base, e cada item de que se abre mão exige motivo escrito, revisão e plano para voltar a cumprir. O valor está em inverter o esforço. Sem a base, quem audita precisa reconstruir o que deveria estar configurado em cada máquina. Com ela, compara com a referência e discute a lista curta de desvios, que já vem com o motivo ao lado.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-53 Rev.5 — Security and Privacy Controls
      * CIS VMware ESXi 8.0 Benchmark v1.3.0
      * CIS Linux Mint 22 Benchmark v1.0.0
      * CIS Critical Security Controls, Version 8.1

* **mediacao-do-loop-agentico** — Mediação do loop agêntico `[claudinho-IA]`
   * definição: Um programa que executa ações sozinho — mexer em arquivo, rodar comando, chamar serviço — precisa de algum ponto em que alguém, ou alguma coisa, diga "pode". Há três formas: pedir aprovação humana a cada ação; deixar uma regra automática revisar cada ação e barrar o que sai do combinado; ou dar liberdade dentro de uma cerca fechada de antemão, em que só existe o que ele tem direito de tocar. A escolha troca incômodo por estrago possível, e traz uma armadilha. Pedir aprovação a cada passo parece a opção mais segura, mas na décima janela a pessoa aprova sem ler: a frequência do pedido destrói a vigilância que o justificava. Quem escolhe essa forma tem que contar com aprovação distraída, não com atenção constante.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Making Claude Code more secure and autonomous with sandboxing [snapshot 2026-08-01]
      * How we built Claude Code auto mode: a safer way to skip permissions [snapshot 2026-08-01]
      * Best practices for Claude Code - Claude Code Docs [snapshot 2026-08-01] _(ocorre em ia)_

* **modulo-criptografico** — Módulo criptográfico `[claudinho-seguranca]` `balde A`
   * definição: É a caixa onde as operações com chaves acontecem, com uma fronteira desenhada e declarada: um cartão, um chip, uma biblioteca, um equipamento de rede. Dentro dela ficam as chaves e as funções que as usam; fora circula só o resultado. Os padrões definem níveis crescentes de exigência para essa caixa, incluindo o que ela deve fazer ao ser aberta à força — apagar as chaves. A distinção que importa na hora de comprar: a garantia vale para o que está dentro da fronteira. Um equipamento com módulo certificado embutido não é um equipamento certificado. O certificado descreve a caixa, não a casa.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Security Requirements for Cryptographic Modules
      * FIPS 140-3 Derived Test Requirements (DTR): CMVP Validation Authority Updates to ISO/IEC 24759
      * Instrução Normativa ITI nº 22, de 23 de março de 2022 — Padrões e algoritmos criptográficos da ICP-Brasil (DOC-ICP-01.01)

* **necessidade-de-conhecer** — Necessidade de conhecer `[claudinho-seguranca]` `balde A`
   * definição: Dois requisitos independentes decidem quem vê um documento sigiloso, e é preciso passar nos dois. A habilitação prévia fixa o teto — até que grau aquela pessoa pode ir. A necessidade decorrente do que ela de fato faz no cargo fixa o que, dentro do teto, ela vê. Por isso um diretor habilitado no grau mais alto não tem direito a ler tudo daquele grau: falta a segunda condição, e ela não é dispensada por hierarquia. O inverso também vale — precisar muito não substitui a habilitação que não se tem. Cada requisito é concedido por autoridade diferente, e é essa separação que impede que um deles saia por conveniência.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Norma Complementar 01/IN02/NSC/GSI/PR — disciplina o credenciamento de segurança de pessoas naturais, órgãos e entidades públicas e privadas para o tratamento de informações classificadas
      * Coletânea de Normas de Segurança da Informação Classificada
      * Decreto nº 7.845, de 14 de novembro de 2012 — Credenciamento de segurança e tratamento de informação classificada

* **negar-por-padrao** — Negar por padrão `[claudinho-seguranca]` `balde A`
   * definição: O sistema recusa tudo que não estiver expressamente liberado. A lista que alguém mantém é a das exceções autorizadas, e o caso que ninguém previu cai na recusa — a instalação nova nasce fechada e vai abrindo conforme se justifica. A diferença em relação a conceder pouco é sutil e decide muito. Lá se discute o tamanho da permissão de quem já foi considerado; aqui se decide o que acontece com quem ninguém considerou. Como esquecer é a regra e não a exceção, a postura de recusa transforma o esquecimento em chamado de suporte, e a postura oposta transforma o mesmo esquecimento em porta aberta que ninguém vai procurar.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-53 Rev.5 — Security and Privacy Controls
      * Guidelines on Firewalls and Firewall Policy
      * CIS Linux Mint 22 Benchmark v1.0.0

* **valor-de-fabrica** — Valor de fábrica `[claudinho-seguranca]` `balde B`
   * definição: Quase ninguém abre as configurações. O valor que já vem marcado é o que vale para a maioria esmagadora das pessoas, e por isso ele não é detalhe técnico: é a política real do sistema. Um aplicativo que nasce com o perfil aberto e oferece o botão de fechar tem, na prática, perfil aberto. Daí a consequência incômoda para quem projeta: oferecer a opção contrária não corrige nada, apenas transfere ao usuário o trabalho de descobrir que ela existe. Quem escolhe o valor inicial está decidindo pelos outros, e o honesto é tratar isso como decisão, não como herança do fornecedor.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Guidelines 4/2019 on Article 25 — Data Protection by Design and by Default, Version 2.0
      * DPO Guide
      * CISSP All-in-One Exam Guide

* **politica-de-seguranca-institucional** — Política de segurança institucional `[claudinho-seguranca]` `balde A`
   * definição: Documento aprovado pelo dirigente máximo que diz o que a organização faz em segurança da informação e nomeia quem responde por cada parte: o gestor, o comitê, a equipe que atende incidentes. Vale para a organização inteira, inclusive para quem não gostou. O que separa isso de uma carta de intenções é o tratamento da exceção. Quando se decide não implementar uma medida declarada obrigatória, a justificativa e a análise de risco ficam registradas. Sem esse registro não há política — há um texto que todos contornam sem deixar rastro, e ninguém consegue dizer depois quem decidiu contornar.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Instrução Normativa GSI/PR nº 1, de 27 de maio de 2020 — Estrutura de Gestão da Segurança da Informação na administração pública federal
      * Portaria SGD/MGI nº 852/2023 — Programa de Privacidade e Segurança da Informação (PPSI)
      * Política de Segurança da Informação e Comunicação do Laboratório Nacional de Computação Científica

* **prova-de-identidade** — Prova de identidade `[claudinho-seguranca]` `balde A`
   * definição: Antes de existir login, alguém precisa estabelecer que aquela conta corresponde a uma pessoa real, e a essa pessoa. É o que o banco faz na abertura da conta: recebe documentos, confere junto a quem os emitiu se são autênticos, e verifica se quem está ali é a pessoa retratada neles. Não se confunde com o login de todo dia. Ali se reconhece um vínculo que já existe; aqui ele é criado. Um sistema pode ter senha forte e segundo fator impecáveis e ainda assim estar dando acesso a quem se cadastrou com o documento dos outros — são problemas diferentes, resolvidos em momentos diferentes.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-63A-4 — Identity Proofing
      * NIST SP 800-63-4 — Digital Identity Guidelines
      * Digital Identity Guidelines

* **regras-de-engajamento** — Regras de engajamento `[claudinho-seguranca]` `balde A`
   * definição: Documento assinado antes de qualquer teste que mexa em sistema de verdade. Ele fixa o que pode ser atacado, o que fica expressamente de fora, em que período, com quais técnicas, o que é proibido — derrubar serviço, tocar em dado real de cliente — e quem autoriza sair do combinado. É ele que separa o teste do crime. A mesma ação técnica, sem esse papel, é acesso não autorizado, e a boa intenção de quem executou não serve de defesa. Vale também para dentro de casa: sem escopo escrito, alguém varre uma faixa de rede que era de outra empresa e a conversa seguinte é com o jurídico.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * nistspecialpublication800-115
      * The Red Team Guide by Peerlyst

* **requisito-verificavel** — Requisito verificável `[claudinho-seguranca]` `balde B`
   * definição: Um requisito só governa se vier com duas coisas junto: como conferir se um caso concreto cumpre, e o que fazer quando não cumpre. O servidor deve ser seguro não separa quem cumpre de quem não cumpre — duas pessoas competentes olham a mesma máquina e discordam. O acesso remoto deve recusar senha e aceitar só chave, confira com tal comando, corrija em tal arquivo decide sozinho. Sem os dois procedimentos o texto é intenção declarada: não se audita, porque não há veredito; e não se delega, porque quem recebe a tarefa precisa adivinhar o que o autor queria.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * CIS Apache HTTP Server 2.4 Benchmark v2.3.0
      * Manual de Condutas Técnicas 11 — Volume II: procedimentos de ensaios para avaliação de conformidade aos requisitos técnicos de softwares de AC e AR no âmbito da ICP-Brasil
      * OWASP SAMM v2.2.0

* **token-portador** — Token portador `[claudinho-seguranca]` `balde A`
   * definição: Uma credencial de portador funciona como dinheiro em espécie: quem está com ela, gasta. O sistema que a recebe não pergunta se quem apresentou é o dono, porque não tem como perguntar — a posse é a prova. Isso torna tudo dependente do sigilo. Se ela aparece num registro de log, num histórico de navegação ou numa mensagem de erro, quem leu passa a poder o que o dono podia, até ela expirar. O arranjo alternativo exige que a cada uso o portador demonstre ter uma chave secreta que não trafega junto: mais caro de implementar, e imune ao roubo por cópia.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15)
      * JSON Web Token Best Current Practices
      * Resource Indicators for OAuth 2.0

* **transparencia-de-composicao** — Transparência de composição `[claudinho-seguranca]` `balde B`
   * definição: Um software é montado com centenas de pedaços escritos por outras pessoas, e cada pedaço traz outros dentro. Transparência de composição é o produtor entregar, junto com o produto, a lista do que tem lá dentro — fornecedor, nome, versão e quem depende de quem — num formato que um programa consiga ler. No mundo do software essa lista tem nome próprio: SBOM. Ela existe para a pergunta que aparece de madrugada: saiu uma falha grave numa biblioteca, a gente usa? Sem a lista, a resposta depende de perguntar ao fornecedor e esperar. Com ela, quem só opera responde sozinho, em minutos. O que o produtor não conseguiu mapear entra declarado como desconhecido — buraco anunciado se procura, buraco omitido vira surpresa.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * The Minimum Elements For a Software Bill of Materials (SBOM) _(ocorre em engenharia-software)_
      * Strategies for the Integration of Software Supply Chain Security in DevSecOps CI/CD Pipelines _(ocorre em engenharia-software)_
      * Software Supply Chain Security

* **vida-util-do-sigilo** — Vida útil do sigilo `[claudinho-seguranca]` `balde B`
   * definição: Todo segredo tem prazo. Uma senha precisa durar até a próxima troca; um plano de defesa precisa durar trinta anos. Some a esse prazo o tempo que a organização levaria para trocar a proteção que usa hoje e compare com o tempo estimado até essa proteção ser quebrada. Se a soma passa, o dado já está perdido no momento em que trafega — ainda que a proteção esteja intacta e a quebra só aconteça daqui a uma década. É esse cálculo que explica adversários guardarem hoje tráfego cifrado que não conseguem abrir. Não precisam abrir agora; precisam que o conteúdo ainda importe quando abrirem.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Transição Brasileira para a Prontidão Pós-Quântica (PQC) e Soberania Digital
      * Relatório executivo: estratégia de transição PQC e soberania digital do Brasil
      * Transitioning the Use of Cryptographic Algorithms and Key Lengths

