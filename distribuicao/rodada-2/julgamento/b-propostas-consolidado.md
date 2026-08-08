# Rodada 2 — propostas consolidadas das 7 cadeiras

84 conceitos propostos. Agrupados pelo domínio em que **ocorrem** (domínio das obras-âncora, ont:0062). Conceito com âncoras em mais de um domínio aparece em cada um — a ocorrência é plural.

## arquiteturas

* **abertura-por-padrao** — Abertura por padrão `[claudinho-arquiteto]`
   * definição: O regime fixa o acesso ao dado como presunção e a restrição como exceção enquadrada em categoria prévia; o ônus argumentativo é de quem restringe, e o rito de acesso é decidido pelo nível declarado ex ante, não por negociação bilateral caso a caso. Decide contra a classificação da informação (que atribui nível de sensibilidade sem fixar direção da presunção) e contra regimes de base legal, em que a presunção é inversa.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Decreto nº 8.777/2016 — Política de Dados Abertos do Poder Executivo federal
      * Decreto nº 10.046/2019 — Governança no compartilhamento de dados na administração pública federal _(ocorre em seguranca-privacidade)_

* **contexto-delimitado** — Contexto delimitado `[claudinho-conhecimento]`
   * definição: Fronteira explícita dentro da qual cada termo tem significado único e o modelo vale com exatidão; fora dela, o mesmo rótulo pode denotar outra régua sem que isso seja erro. A fronteira é declarada, não descoberta, e decide quando duas definições divergentes exigem reconciliação (mesmo contexto) e quando exigem apenas mapeamento entre contextos.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Domain-Driven Design
      * Learning Domain-Driven Design
      * An Ontology-based Approach for Domain-driven Design of Microservice Architectures

* **estruturacao-de-problema** — Estruturação de problema `[claudinha-gestao-estrategica]`
   * definição: Produzir a formulação do problema — de quem é, que diferença entre estado percebido e estado desejado, sob qual leitura de mundo — antes de tratá-lo como escolha entre meios para um fim conhecido. A saída é um enunciado disputável, não uma solução; enquanto a formulação segue em disputa, otimizar alternativas responde a uma pergunta que ninguém validou.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Systems thinking, systems practice
      * Are Your Lights On? _(ocorre em produtos-digitais)_
      * Dirty Rotten Strategies _(ocorre em produtos-digitais)_
      * Dilemmas in a General Theory of Planning _(ocorre em produtos-digitais)_

* **fluxo-de-valor** — Fluxo de valor `[claudinho-arquiteto]`
   * definição: Sequência de estágios, disparada por um stakeholder, que acumula itens de valor até a proposição de valor final; cada estágio tem critério de entrada e de saída e é habilitado por capacidades. É o "o quê" percebido de ponta a ponta, cruzando funções — decide contra business capability (bloco estável de habilidade, sem sequência) e contra o processo (o "como" de cada etapa).
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * BIZBOK Guide
      * Guia Prático de Gestão de Processos: gestão que simplifica, conecta e entrega — 2ª edição

* **fronteira-por-custo-de-transacao** — Fronteira por custo de transação `[claudinho-arquiteto]`
   * definição: A fronteira — da firma ou do módulo — se traça comparando o custo de coordenar dentro com o custo de transacionar fora através de uma interface; quando os custos relativos mudam, a fronteira economicamente sustentável se move, e a fronteira modular bem posta cria opção de substituição com valor próprio. Decide contra fronteiras traçadas por semântica de domínio ou por carga cognitiva: aqui o operador é o custo comparado.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The Nature of the Firm: Origins, Evolution, and Development _(ocorre em gestao-organizacional)_
      * Design Rules, Vol. 1

* **governanca-dados** — Governança de dados `[claudinho-arquiteto]`
   * definição: Alocação de autoridade sobre o dado — quem fixa política, quem decide exceção, quem responde pela qualidade — separada da gestão que executa; governar dados é decidir quem decide, em arranjo transversal às funções, e a operação madura desaparece no dia a dia em vez de virar departamento. Decide contra a gestão de dados: a obra entra se seu objeto é a alocação de autoridade e supervisão, não a execução de pipeline.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Data Governance (2nd)
      * Cartilha de Governança de Dados — Volume III: Papéis e Responsabilidades de Governança de Dados no Poder Executivo Federal

* **implantabilidade-independente** — Implantabilidade independente `[claudinho-TI]`
   * definição: Propriedade de uma fronteira de construção pela qual uma mudança dentro dela pode ser implantada e liberada sem implantar nenhuma outra parte do sistema. Exige contrato explícito e estável na fronteira, com evolução retrocompatível; fronteiras que compartilham banco ou exigem liberação coordenada não a possuem, qualquer que seja o nome que carreguem.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * Building Microservices (2nd)
      * Building Event-Driven Microservices
      * Continuous Delivery Pipelines: How To Build Better Software Faster _(ocorre em engenharia-software)_

* **ordenacao-causal** — Ordenação causal de eventos `[claudinho-TI]`
   * definição: Em sistema distribuído, a única ordem observável entre eventos é a relação aconteceu-antes — parcial, definida por sequência local e troca de mensagem. Eventos não conectados por essa relação são concorrentes; qualquer ordem total entre eles é imposta por convenção (relógio lógico, timestamp), não observada. Uma afirmação de ordem é causal se deriva da relação parcial; é convencional se exige desempate arbitrário.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * Time, Clocks, and the Ordering of Events in a Distributed System
      * Designing Data-Intensive Applications

* **problema-perverso** — Problema perverso `[claudinha-gestao-estrategica]`
   * definição: Classe de problema sem formulação definitiva, sem regra de parada e sem teste de certo ou errado: cada intervenção é operação de um tiro que altera a situação, e a formulação escolhida já embute a solução preferida. Decide o formato do compromisso — o que é perverso não se planeja como projeto com fim declarado, se governa por intervenção assumida como irreversível.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dilemmas in a General Theory of Planning _(ocorre em produtos-digitais)_
      * Systems thinking, systems practice

* **processo-de-negocio** — Processo de negócio `[claudinho-arquiteto]`
   * definição: O trabalho é gerido pela travessia — entrada, atividades coordenadas, saída de valor — e não pela função que o executa; o processo é objeto próprio de desenho, medição e melhoria cíclica, redesenhável sem que a capacidade que o sustenta mude. Decide contra automação de processos (execução por sistema, não a unidade de gestão) e contra gestão de projetos (empreendimento temporário, não travessia repetível).
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Guia Prático de Gestão de Processos: gestão que simplifica, conecta e entrega — 2ª edição
      * COBIT 5: Enabling Processes _(ocorre em engenharia-software)_

* **registro-de-decisao** — Registro de decisão `[claudinho-conhecimento]`
   * definição: A decisão tratada como entidade de primeira classe registrada: enunciado curto, contexto que a motivou, alternativas evitadas e racional, em unidade imutável e datada. O registro existe para que quem chega depois reavalie a decisão sem reconstituir a cabeça de quem decidiu; sem o racional preservado, a decisão vira regra inexplicável — aceita ou reaberta às cegas.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Documenting Architecture Decisions
      * A documentation framework for architecture decisions
      * Ontology of architectural design decisions in software-intensive systems

* **registro-de-decisao-arquitetural** — Registro de decisão arquitetural `[claudinho-TI]`
   * definição: Documento curto e imutável que fixa uma decisão de construção com contexto, decisão em voz afirmativa e consequências, portando estado próprio (proposta, aceita, substituída). Um documento é registro de decisão se preserva o porquê contra mudança de contexto e se muda por substituição encadeada, nunca por edição do registro original.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Documenting Architecture Decisions
      * Software Architecture Knowledge Management: Theory and Practice
      * Fundamentals of Software Architecture (2025)

## engenharia-software

* **cascata-de-objetivos** — Cascata de objetivos `[claudinho-arquiteto]`
   * definição: Necessidade de stakeholder se traduz em objetivo corporativo, que se traduz em objetivo de alinhamento, que seleciona e prioriza processos e recursos; a decisão local se justifica pelo rastro até o topo, e objetivo sem rastro não tem lastro. Decide contra OKR: lá o mecanismo é pactuação colaborativa de metas por ciclo, aqui é derivação rastreável entre níveis.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * COBIT 2019 Framework: Governance and Management Objectives
      * COBIT 5: A Business Framework for the Governance and Management of Enterprise IT
      * COBIT 5: Enabling Processes

* **corte-por-capacidade** — Corte por capacidade `[claudinha-gestao-estrategica]`
   * definição: A priorização só decide quando o compromisso tem teto explícito — capacidade de execução estimada, tempo fixo ou limite de itens em andamento — e o excedente é nomeado fora do compromisso; atingido o teto, continuar exige decisão nova, nunca renovação tácita. Ordenar sem teto produz fila, não decisão: nada foi excluído e tudo segue prometido.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Guia de Elaboração de PDTIC do SISP, versão 2.1 _(ocorre em gestao-organizacional)_
      * The Standard for Project Management and A Guide to the Project Management Body of Knowledge (PMBOK Guide) _(ocorre em gestao-organizacional)_
      * Shape Up _(ocorre em produtos-digitais)_
      * Essential Kanban Condensed

* **desempenho-de-entrega** — Desempenho de entrega de software `[claudinho-TI]`
   * definição: Medição do processo de entrega por quatro resultados pareados — tempo de ciclo da mudança, frequência de implantação, taxa de falha de mudança e tempo de recuperação — em que vazão e estabilidade são lidas juntas e movem juntas. Uma medida é de desempenho de entrega se afere resultado global do processo (não produção local de artefato) e se sua melhora não se compra com a piora do par.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Accelerate: The Science of Lean Software and DevOps
      * Accelerate: State of DevOps 2024
      * Accelerate: State of DevOps 2018
      * Accelerate: State of DevOps 2019

* **esteira-de-implantacao** — Esteira de implantação `[claudinho-TI]`
   * definição: Caminho único e automatizado que leva toda mudança de commit a artefato liberável, atravessando estágios eliminatórios (verificação rápida, artefato versionado, aceitação em ambiente similar a produção). Algo é esteira de implantação se nenhuma mudança chega ao ar por fora dela e se cada estágio pode rejeitar o candidato.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Continuous Delivery Pipelines: How To Build Better Software Faster
      * Accelerate: The Science of Lean Software and DevOps

* **fabrica-de-software** — Fábrica de software (modelo de contratação) `[claudinho-TI]`
   * definição: Arranjo contratual que separa quem especifica (cliente) de quem produz (fornecedor) e remunera a produção por artefato medido (ponto de função, UST). A métrica de pagamento passa a governar o comportamento de produção: otimiza-se o que o contrato mede, não o resultado do software em uso. Um arranjo é fábrica de software se a fronteira contratual e a métrica de remuneração precedem e condicionam o processo de construção.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Análise dos modelos e contratos de desenvolvimento de software na administração direta do governo federal: a crise na produção de software e as alternativas à fábrica de software
      * Gestão ágil e clientes cascata: desafios e alternativas para fábricas de software

* **falha-sistemica** — Falha sistêmica `[claudinho-TI]`
   * definição: Em sistema complexo defendido em camadas, a catástrofe exige a conjunção de múltiplas falhas pequenas atravessando defesas simultaneamente; falha de ponto único não basta. "Causa raiz" única é atribuição retrospectiva do analista, não propriedade do evento — a análise correta busca as condições latentes concorrentes, não um culpado singular.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * Cook.1998.HowComplexSystemsFailRevG.pages
      * The Site Reliability Workbook

* **implantabilidade-independente** — Implantabilidade independente `[claudinho-TI]`
   * definição: Propriedade de uma fronteira de construção pela qual uma mudança dentro dela pode ser implantada e liberada sem implantar nenhuma outra parte do sistema. Exige contrato explícito e estável na fronteira, com evolução retrocompatível; fronteiras que compartilham banco ou exigem liberação coordenada não a possuem, qualquer que seja o nome que carreguem.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * Building Microservices (2nd) _(ocorre em arquiteturas)_
      * Building Event-Driven Microservices _(ocorre em arquiteturas)_
      * Continuous Delivery Pipelines: How To Build Better Software Faster

* **janela-de-exposicao** — Janela de exposição `[claudinho-seguranca]` `balde B`
   * definição: Entre o momento em que um defeito conhecido passa a ser explorável e o momento em que a correção está em produção, o risco corre. Todo controle de processo interposto nesse intervalo — teste, aprovação, janela de mudança — reduz o risco de a correção quebrar a operação e aumenta o risco de o defeito ser explorado; a decisão não é entre seguro e inseguro, é a escolha de qual dos dois riscos se prefere pagar.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-40 Rev.4 — Patch Management
      * ISO/IEC 27002:2013 — Information technology — Security techniques — Code of practice for information security controls _(ocorre em seguranca-privacidade)_
      * ISC2 CISSP Certified Information Systems Security Professional Official Study Guide _(ocorre em seguranca-privacidade)_

* **orcamento-de-erro** — Orçamento de erro `[claudinho-TI]`
   * definição: Conversão de um alvo de confiabilidade (SLO) na quantidade de indisponibilidade que o negócio aceita gastar num período. A decisão operacional (alertar, congelar mudança, priorizar confiabilidade sobre feature) é tomada pela taxa projetada de queima do orçamento, não pelo evento pontual de falha.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The Site Reliability Workbook
      * Observability Engineering

* **processo-de-negocio** — Processo de negócio `[claudinho-arquiteto]`
   * definição: O trabalho é gerido pela travessia — entrada, atividades coordenadas, saída de valor — e não pela função que o executa; o processo é objeto próprio de desenho, medição e melhoria cíclica, redesenhável sem que a capacidade que o sustenta mude. Decide contra automação de processos (execução por sistema, não a unidade de gestão) e contra gestão de projetos (empreendimento temporário, não travessia repetível).
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Guia Prático de Gestão de Processos: gestão que simplifica, conecta e entrega — 2ª edição _(ocorre em arquiteturas)_
      * COBIT 5: Enabling Processes

* **refatoracao-segura** — Refatoração segura `[claudinho-TI]`
   * definição: Mudança de estrutura interna que preserva comportamento observável, executada em passos pequenos verificados por teste a cada passo. Código sem teste (legado) exige primeiro criar o ponto de verificação — costura e teste de caracterização — antes de qualquer mudança; intervenção estrutural sem verificação a cada passo não é refatoração, é edição arriscada.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Refactoring: Improving the Design of Existing Code
      * Working Effectively with Legacy Code
      * Test-Driven Development: By Example

* **servico-de-ti** — Serviço de TI `[claudinho-TI]`
   * definição: Meio de entregar valor a um cliente sem que ele carregue os custos e riscos específicos da entrega. Algo é serviço se cria valor para o cliente por si; o que habilita ou compõe a entrega sem valer sozinho para o cliente é componente de serviço, construído sobre itens de configuração.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * FitSM Part 0: Overview and vocabulary, Version 3.0.1
      * FitSM-5 Guide: Identifying Services
      * ITIL Foundation: ITIL 4 Edition
      * FitSM-5 Guide: Specifying Services for Portfolios and Catalogues v1.0

* **transparencia-de-composicao** — Transparência de composição `[claudinho-seguranca]` `balde B`
   * definição: Propriedade de um artefato entregue cuja árvore de constituintes — fornecedor, nome, versão, identificador e relação de dependência, inclusive as transitivas — é declarada pelo produtor em forma legível por máquina, de modo que quem apenas opera o artefato responda "isto contém o componente X na versão Y?" sem consultar o produtor. O que a declaração não alcança é declarado como tal, em vez de omitido.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * The Minimum Elements For a Software Bill of Materials (SBOM)
      * Strategies for the Integration of Software Supply Chain Security in DevSecOps CI/CD Pipelines
      * Software Supply Chain Security _(ocorre em seguranca-privacidade)_

## estudos-ontologias

* **conhecimento-tacito** — Conhecimento tácito `[claudinho-conhecimento]`
   * definição: Conhecimento que orienta o desempenho do portador sem que ele consiga enunciá-lo por completo; transmite-se por convivência e prática, e só vira registro por externalização deliberada, sempre com perda. Decide o que a formação consegue formalizar em material e o que exige prática acompanhada.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * A Dynamic Theory of Organizational Knowledge Creation.
      * The Knowledge-Creating Company

* **criterio-de-identidade** — Critério de identidade `[claudinho-conhecimento]`
   * definição: O princípio, fornecido por um tipo sortal, que determina quando dois registros denotam o mesmo indivíduo e o que o indivíduo pode mudar sem deixar de existir. Classe cujas instâncias respondem a princípios de identidade incompatíveis está mal construída; tipo anti-rígido (papel, fase) não pode subsumir o tipo rígido que fornece a identidade.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Ontological Foundations for Structural Conceptual Models
      * Evaluating ontological decisions with OntoClean

* **descricao-multinivel** — Descrição multinível `[claudinho-conhecimento]`
   * definição: Descrever do geral para o particular, com cada unidade herdando o contexto do nível superior, cada informação registrada uma única vez no nível mais alto a que se aplica, e a descrição limitada ao pertinente ao nível descrito. Decide onde uma informação se registra e o que a unidade filha não repete.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * ISAD(G): General International Standard Archival Description, Second Edition
      * ISAD(G): Norma geral internacional de descrição arquivística — Segunda Edição
      * NOBRADE: Norma brasileira de descrição arquivística

* **documento-de-arquivo** — Documento de arquivo `[claudinho-conhecimento]`
   * definição: Documento produzido ou recebido no exercício de uma atividade, cujo valor de prova depende do vínculo orgânico com essa atividade e do contexto de produção, qualquer que seja o suporte. Decide contra o item bibliográfico: este se cataloga pelo assunto e circula solto; o documento de arquivo se classifica pela atividade e perde valor probatório fora do conjunto.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Lei nº 8.159, de 8 de janeiro de 1991 — Política nacional de arquivos públicos e privados
      * e-ARQ Brasil: Modelo de Requisitos para Sistemas Informatizados de Gestão Arquivística de Documentos, Versão 2

* **esquema-de-organizacao** — Esquema de organização `[claudinha-produto]`
   * definição: Toda coleção exposta a busca se organiza por esquema exato (alfabético, cronológico, geográfico — uma resposta certa por item, exige que o usuário saiba o que procura) ou ambíguo (assunto, tarefa, público — agrupamento por julgamento, serve a quem não sabe nomear o que procura). O esquema escolhido decide se o usuário encontra sem dominar o vocabulário do sistema — e encontrar precede qualquer uso.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Information Architecture: For the Web and Beyond
      * Designing Interfaces Patterns for Effective Interaction Design _(ocorre em produtos-digitais)_

* **evento-como-entidade** — Evento como entidade `[claudinho-conhecimento]`
   * definição: Acontecimento modelado como entidade própria — com participações de objetos, partes e fronteiras temporais — em vez de atributo ou carimbo de tempo de outra entidade. Decide quando um ato (catalogação, sucessão, triagem) vira registro de primeira classe: quando o requisito pede participantes, decomposição ou ordenação própria; quando só ordena, fica atributo.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Events as Entities in Ontology-Driven Conceptual Modeling
      * Towards Ontological Foundations for the Conceptual Modeling of Events

* **expressividade-vs-tratabilidade** — Expressividade vs. tratabilidade `[claudinho-conhecimento]`
   * definição: Em linguagem de representação com semântica formal, cada construtor admitido fixa a classe de complexidade da inferência: ganhar poder de afirmação custa computabilidade. A escolha de fragmento (perfil) é a declaração desse compromisso, e um axioma é admissível quando cabe no fragmento cujo custo se aceitou.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * The Description Logic Handbook: Theory, Implementation and Applications
      * OWL 2 Web Ontology Language Profiles (Second Edition)

* **pratica-de-recuperacao** — Prática de recuperação `[claudinho-conhecimento]`
   * definição: Aprender pelo esforço de recuperar da memória supera a reexposição ao material: reconhecer não é dominar, e o exercício se desenha como recuperação na forma em que o desempenho será exigido. Decide, para cada item de trilha, o que sai (releitura, resumo passivo) e o que entra (teste de recuperação, prática espaçada).
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Make It Stick
      * Design for How People Learn

* **vocabulario-controlado** — Vocabulário controlado `[claudinho-conhecimento]`
   * definição: Conjunto de termos cuja admissão é governada: escopo de cada termo delimitado, sinônimos remetidos a um termo preferido por relação de equivalência, homógrafos distinguidos, e relações restritas a equivalência, hierarquia e associação. Decide, para um rótulo novo, se ele entra como termo, vira remissiva ou é recusado.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * ANSI/NISO Z39.19-2005 (R2010), Guidelines for the Construction, Format, and Management of Monolingual Controlled Vocabularies
      * SKOS Simple Knowledge Organization System Reference [snapshot 2026-08-01]
      * VCGE — Vocabulário Controlado do Governo Eletrônico

## gestao-organizacional

* **cadeia-de-resultados** — Cadeia de resultados `[claudinha-gestao-estrategica]`
   * definição: Explicitação das hipóteses que ligam recursos a ações, ações a produtos e produtos a resultados intermediários e finais, com as condições de contexto que as sustentam — a teoria de por que o investimento deve funcionar, escrita antes dele. É a referência contra a qual gestão e avaliação medem o programa; sem ela, avaliar é opinar.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Nota Técnica — Como elaborar modelo lógico de programa: um roteiro básico
      * Guia técnico de gestão estratégica
      * Guia de Monitoramento e Avaliação da Estratégia do MGI — 2ª edição

* **corte-por-capacidade** — Corte por capacidade `[claudinha-gestao-estrategica]`
   * definição: A priorização só decide quando o compromisso tem teto explícito — capacidade de execução estimada, tempo fixo ou limite de itens em andamento — e o excedente é nomeado fora do compromisso; atingido o teto, continuar exige decisão nova, nunca renovação tácita. Ordenar sem teto produz fila, não decisão: nada foi excluído e tudo segue prometido.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Guia de Elaboração de PDTIC do SISP, versão 2.1
      * The Standard for Project Management and A Guide to the Project Management Body of Knowledge (PMBOK Guide)
      * Shape Up _(ocorre em produtos-digitais)_
      * Essential Kanban Condensed _(ocorre em engenharia-software)_

* **entrega-vs-resultado** — Entrega vs. resultado `[claudinha-gestao-estrategica]`
   * definição: Separa o que foi construído e entregue (produto, funcionalidade) da mudança de comportamento ou de estado que a entrega deveria causar, e julga o investimento pelo segundo. Iniciativa que entrega sem mudar comportamento algum falhou mesmo cumprindo o prometido; a medição por entrega é o mecanismo que esconde essa falha.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Escaping the Build Trap _(ocorre em produtos-digitais)_
      * Nota Técnica — Como elaborar modelo lógico de programa: um roteiro básico

* **estruturacao-de-problema** — Estruturação de problema `[claudinho-arquiteto]`
   * definição: Produzir o enunciado do problema como artefato de trabalho — quem percebe, o que deseja, onde há conflito entre atores — antes de qualquer otimização; a escolha do enunciado predetermina o espaço de soluções, e a saída é uma formulação que sustenta acordo, não um ótimo. Decide contra a otimização (que exige enunciado dado) e contra product discovery (cujo objeto é a necessidade do usuário de um produto, não o enunciado disputado entre atores).
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Rational analysis for a problematic world revisited
      * Redesigning the future
      * Are Your Lights On? _(ocorre em produtos-digitais)_

* **fronteira-por-custo-de-transacao** — Fronteira por custo de transação `[claudinho-arquiteto]`
   * definição: A fronteira — da firma ou do módulo — se traça comparando o custo de coordenar dentro com o custo de transacionar fora através de uma interface; quando os custos relativos mudam, a fronteira economicamente sustentável se move, e a fronteira modular bem posta cria opção de substituição com valor próprio. Decide contra fronteiras traçadas por semântica de domínio ou por carga cognitiva: aqui o operador é o custo comparado.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The Nature of the Firm: Origins, Evolution, and Development
      * Design Rules, Vol. 1 _(ocorre em arquiteturas)_

* **gestao-estrategica** — Gestão estratégica `[claudinha-gestao-estrategica]`
   * definição: Processo contínuo que integra formulação (diagnóstico e escolha de objetivos com indicadores e metas), desdobramento em planos, implementação, monitoramento e avaliação, com revisão disparada por desvio medido e não apenas pelo calendário. Distingue-se do plano estratégico: o plano é produto de uma etapa; o processo é o que o mantém decidindo.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Guia técnico de gestão estratégica
      * Guia de Monitoramento e Avaliação da Estratégia do MGI — 2ª edição

* **gestao-por-resultado-pactuado** — Gestão por resultado pactuado `[claudinha-gestao-estrategica]`
   * definição: Regime de trabalho em que a relação se rege por plano de trabalho com entregas pactuadas, critérios de avaliação declarados e termo de ciência e responsabilidade, substituindo o controle de presença pela aferição do resultado. A participação é adesão condicionada, não direito adquirido; o descumprimento se apura contra o pactuado, não contra a frequência.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Instrução Normativa Conjunta SEGES-SGPRT/MGI nº 24, de 28 de julho de 2023 — Programa de Gestão e Desempenho (versão comparada e consolidada)
      * Guia prático para implementação e execução do PGD na Administração Pública Federal — Módulo 6: Complementares, 3ª edição

* **governanca-publica** — Governança pública `[claudinha-gestao-estrategica]`
   * definição: Mecanismos de liderança, estratégia e controle postos em prática para avaliar, direcionar e monitorar a gestão, com vistas à condução de políticas públicas e à prestação de serviços de interesse da sociedade; o resultado que a distingue é valor público. O objeto governado é a ação do Estado perante a sociedade, não a organização perante sócios.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Decreto nº 9.203/2017 — Política de governança da administração pública federal
      * Guia da Política de Governança Pública

* **isomorfismo-institucional** — Isomorfismo institucional `[claudinha-gestao-estrategica]`
   * definição: Organizações adotam estruturas e práticas para ganhar legitimidade no campo — por coerção, imitação sob incerteza ou pressão normativa — e não por eficiência técnica; a estrutura adotada tende a se desacoplar da atividade real, mantida por confiança e cerimônia em vez de inspeção. O sinal é a distância estável entre o que o artefato formal declara e o que a operação faz.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Institutionalized Organizations: Formal Structure as Myth and Ceremony
      * The Iron Cage Revisited: Institutional Isomorphism and Collective Rationality in Organizational Fields

* **mecanismo-de-coordenacao** — Mecanismo de coordenação `[claudinho-arquiteto]`
   * definição: Trabalho dividido exige um modo declarado de coordenação (ajuste mútuo, supervisão direta, padronização; colaboração, X-as-a-Service, facilitação), e a estrutura viável deriva do modo dominante — redesenhar caixas sem trocar o modo não muda a organização. Decide contra a lei de Conway, cujo objeto é o efeito da comunicação sobre a forma do artefato, não o modo pelo qual o trabalho se coordena.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The Structuring of Organizations
      * Team Topologies

* **problema-perverso** — Problema perverso `[claudinho-arquiteto]`
   * definição: A formulação do problema não é dada, é escolhida — e cada formulação já embute uma classe de solução; não há teste objetivo de correção nem critério de parada, e o trabalho encerra por esgotamento de recurso ou decisão, não por "resolver". Decide contra o problema domado, que tem enunciado estável e teste de solução fixado ex ante.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dilemmas in a General Theory of Planning _(ocorre em produtos-digitais)_
      * The Structure of Ill Structured Problems

## ia

* **acesso-delegado** — Acesso delegado `[claudinho-seguranca]` `balde A`
   * definição: Arranjo em que um terceiro obtém acesso limitado a um recurso em nome do dono sem receber a credencial do dono: uma autoridade separada media a aprovação e emite ao terceiro uma autorização própria, restrita em alcance e em prazo, revogável sem tocar na credencial original.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15) _(ocorre em seguranca-privacidade)_
      * Final: OpenID Connect Core 1.0 incorporating errata set 2 [snapshot 2026-08-01] _(ocorre em seguranca-privacidade)_
      * Model Context Protocol — Specification 2026-07-28

* **confundimento-de-ambiente-em-avaliacao** — Confundimento de ambiente em avaliação `[claudinho-IA]`
   * definição: Parte da variação de um escore de avaliação de sistema com modelo é atribuível ao ambiente de execução — serving, latência, concorrência, harness — e não ao modelo. Um escore único não separa as duas fontes; atribuir delta ao modelo exige controlar ou medir o ambiente. Decide quando um delta autoriza conclusão sobre o modelo.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * Quantifying infrastructure noise in agentic coding evals [snapshot 2026-08-01]
      * An update on recent Claude Code quality reports [snapshot 2026-08-01]

* **degradacao-diferencial-sob-compressao** — Degradação diferencial sob compressão `[claudinho-IA]`
   * definição: A perda de capacidade causada por compressão de modelo (quantização, esparsificação) não é uniforme: concentra-se em capacidades compostas de múltiplos turnos — uso de ferramenta, fluxo de trabalho agêntico — e pode ser invisível em benchmark de turno único. O efeito da compressão se mede na capacidade-alvo, não no benchmark genérico.
   * natureza: fenomeno
   * estatuto: natural
   * âncoras:
      * Can Compressed LLMs Truly Act? An Empirical Evaluation of Agentic Capabilities in LLM Compression
      * Quantize with Confidence? An Empirical Study of Quantization for Code Generation

* **delegado-confuso** — Delegado confuso `[claudinho-seguranca]` `balde B`
   * definição: Um intermediário autorizado a agir em nome de terceiros exerce a autoridade que ele próprio detém a pedido de quem não a detém, e o alvo não distingue as duas origens porque só vê a credencial do intermediário. A correção é vincular cada ato à parte pretendida — destinatário declarado na credencial, consentimento por ato, e proibição de repassar adiante a credencial recebida.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Model Context Protocol — Specification 2026-07-28
      * Resource Indicators for OAuth 2.0 _(ocorre em seguranca-privacidade)_
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15) _(ocorre em seguranca-privacidade)_

* **interacao-tardia** — Interação tardia `[claudinho-IA]`
   * definição: Variante da recuperação densa em que cada lado é representado por múltiplos vetores no nível do token e o casamento é adiado para o escore (soma de máximas similaridades), preservando a codificação independente. Compra granularidade de casamento ao preço de uma ordem de grandeza a mais de índice.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * ColBERT: Efficient and Effective Passage Search via Contextualized Late Interaction over BERT
      * ColBERTv2: Effective and Efficient Retrieval via Lightweight Late Interaction

* **isolamento-de-contexto-por-delegacao** — Isolamento de contexto por delegação `[claudinho-IA]`
   * definição: Delegação a subagente cuja função é separar orçamentos de contexto: a exploração queima tokens na janela do subagente e só o destilado volta ao orquestrador, que preserva a própria janela para síntese. Decide contra a delegação por especialização — aqui o motivo é a contabilidade de contexto, não a competência.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * How we built our multi-agent research system [snapshot 2026-08-01]
      * Best practices for Claude Code - Claude Code Docs [snapshot 2026-08-01]
      * Scaling Managed Agents: Decoupling the brain from the hands [snapshot 2026-08-01]

* **mediacao-do-loop-agentico** — Mediação do loop agêntico `[claudinho-IA]`
   * definição: Desenho do ponto em que a ação do agente é liberada: aprovação humana por ação, revisão automática por política, ou execução livre dentro de fronteira de isolamento previamente definida. A régua troca custo de mediação (fadiga de aprovação, latência, configuração) por raio de dano da ação não revisada — e prevê que mediação por ação degrada a própria vigilância que a justifica.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Making Claude Code more secure and autonomous with sandboxing [snapshot 2026-08-01] _(ocorre em seguranca-privacidade)_
      * How we built Claude Code auto mode: a safer way to skip permissions [snapshot 2026-08-01] _(ocorre em seguranca-privacidade)_
      * Best practices for Claude Code - Claude Code Docs [snapshot 2026-08-01]

* **ranqueamento-multiestagio** — Ranqueamento multiestágio `[claudinho-IA]`
   * definição: Pipeline de recuperação em que estágios sucessivos trocam volume de candidatos por custo de escore: um primeiro estágio barato e de alto recall gera o pool, estágios caros e precisos reordenam. O recall do primeiro estágio é teto do resultado — estágio tardio não recupera o que não entrou no pool.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Pretrained Transformers for Text Ranking: BERT and Beyond
      * A Simple Guide to Retrieval Augmented Generation
      * LLM Engineer’s Handbook

* **recuperacao-densa** — Recuperação densa `[claudinho-IA]`
   * definição: Recuperação em que consulta e documento são codificados independentemente em vetores densos, e a relevância é uma operação barata sobre vetores — o que permite pré-computar o índice e buscar por vizinhança. Decide contra o codificador cruzado, que lê o par junto e por isso não indexa: ganha expressividade, perde a pré-computação.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Dense Passage Retrieval for Open-Domain Question Answering
      * M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation
      * Pretrained Transformers for Text Ranking: BERT and Beyond

* **relevancia-graduada** — Relevância graduada `[claudinho-IA]`
   * definição: Relevância tratada como grau, não como binário: cada documento contribui ganho proporcional ao seu grau, acumulado ao longo do ranking com desconto por posição e normalizado pelo ranking ideal. Decide contra métrica binária (precisão@k) e contra métrica de primeiro acerto (MRR), que não distinguem o altamente relevante do marginal.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Cumulated gain-based evaluation of IR techniques
      * IR evaluation methods for retrieving highly relevant documents

* **transporte-de-estado-entre-sessoes** — Transporte de estado entre sessões `[claudinho-IA]`
   * definição: Trabalho que excede uma janela de contexto se divide em sessões sem memória compartilhada; artefatos duráveis fora da janela (nota, lista de tarefas, log, arquivo), escritos por uma sessão e lidos pela seguinte, carregam o estado. O que não foi inscrito em artefato não existe para a sessão seguinte — inclusive o que a compactação descartou.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Effective harnesses for long-running agents [snapshot 2026-08-01]
      * Harness design for long-running application development [snapshot 2026-08-01]
      * Code execution with MCP: building more efficient AI agents [snapshot 2026-08-01]

* **workflow-vs-agente** — Workflow vs. agente `[claudinho-IA]`
   * definição: A previsibilidade dos subpassos decide a topologia de execução: quando as subtarefas são conhecidas a priori, fluxo fixo composto (mais barato, auditável, otimizável por etapa); quando dependem do que se observa no caminho, loop aberto com orçamento. Régua de decisão, não taxonomia de sistemas.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Building Effective AI Agents [snapshot 2026-08-01]
      * Prompt Engineering for LLMs (for True Epub)

## produtos-digitais

* **affordance** — Affordance `[claudinha-produto]`
   * definição: Relação entre propriedades de um artefato e capacidades de um agente que determina as ações possíveis desse agente sobre o artefato. Existência e percepção são separáveis: a ação pode ser possível e não sinalizada (escondida), sinalizada e impossível (falsa), ou possível e sinalizada (percebida) — e é essa separação que produz veredito sobre uma interface: o que ela permite versus o que ela comunica que permite.
   * natureza: disposicao
   * estatuto: natural
   * âncoras:
      * Technology Affordances
      * The Design of Everyday Things

* **avaliacao-heuristica** — Avaliação heurística `[claudinha-produto]`
   * definição: Inspeção de interface, sem usuário presente, contra uma lista finita de princípios verificáveis (visibilidade do estado do sistema, correspondência com o mundo real, controle do usuário, consistência, prevenção de erro, reconhecimento em vez de memorização, entre outros), produzindo reprovação por violação nomeada. O veredito sai da correspondência tela-princípio, não do gosto do avaliador.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Jakob's Ten Usability Heuristics
      * Designing Interfaces Patterns for Effective Interaction Design
      * Cracking the PM Career

* **corte-por-capacidade** — Corte por capacidade `[claudinha-gestao-estrategica]`
   * definição: A priorização só decide quando o compromisso tem teto explícito — capacidade de execução estimada, tempo fixo ou limite de itens em andamento — e o excedente é nomeado fora do compromisso; atingido o teto, continuar exige decisão nova, nunca renovação tácita. Ordenar sem teto produz fila, não decisão: nada foi excluído e tudo segue prometido.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Guia de Elaboração de PDTIC do SISP, versão 2.1 _(ocorre em gestao-organizacional)_
      * The Standard for Project Management and A Guide to the Project Management Body of Knowledge (PMBOK Guide) _(ocorre em gestao-organizacional)_
      * Shape Up
      * Essential Kanban Condensed _(ocorre em engenharia-software)_

* **design-centrado-no-humano** — Design centrado no humano `[claudinha-produto]`
   * definição: Um processo de desenvolvimento é centrado no humano quando satisfaz quatro condições verificáveis: parte de entendimento explícito de usuários, tarefas e ambiente; envolve usuários ativamente ao longo do ciclo; é dirigido e refinado por avaliação centrada no usuário, inclusive no aceite final; e itera até eliminar a incerteza. A evidência de conformidade é a avaliação com usuário registrada em cada atividade, não a intenção declarada.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Ergonomics of human-system interaction — Part 210: Human-centred design for interactive systems
      * Design Thinking Bootleg
      * About Face

* **design-reality-gap** — Gap desenho-realidade `[claudinha-produto]`
   * definição: O risco de fracasso de um sistema é função da distância, medida dimensão a dimensão (informação, tecnologia, processos, objetivos e valores, pessoal, gestão, outros recursos), entre as premissas embutidas no desenho e a realidade presente no local de implantação. Distância grande em qualquer dimensão prediz fracasso independentemente da qualidade técnica do desenho; reduzir o gap — do lado do desenho ou da realidade — é o que muda o prognóstico.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * The origins of failure: seeking the causes of design-reality gaps
      * Minding the Design Reality Gap: An Empirical Evaluation of Telecentre Initiatives in Rural Ghana
      * Towards design of citizen centric e-government projects in developing country context: the design-reality gap in Uganda

* **entrega-vs-resultado** — Entrega vs. resultado `[claudinha-gestao-estrategica]`
   * definição: Separa o que foi construído e entregue (produto, funcionalidade) da mudança de comportamento ou de estado que a entrega deveria causar, e julga o investimento pelo segundo. Iniciativa que entrega sem mudar comportamento algum falhou mesmo cumprindo o prometido; a medição por entrega é o mecanismo que esconde essa falha.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Escaping the Build Trap
      * Nota Técnica — Como elaborar modelo lógico de programa: um roteiro básico _(ocorre em gestao-organizacional)_

* **entrevista-por-comportamento-passado** — Entrevista por comportamento passado `[claudinha-produto]`
   * definição: Em conversa de descoberta, conta como evidência o relato de comportamento passado específico e o compromisso concreto (tempo, dinheiro, reputação); opinião sobre a ideia, elogio e projeção de uso futuro não contam. Mencionar a própria ideia cedo contamina a coleta, porque o interlocutor passa a responder sobre a ideia, não sobre a própria vida.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * The Mom Test
      * Continuous Discovery Habits
      * Empowered

* **erro-de-tipo-tres** — Erro de tipo três `[claudinha-gestao-estrategica]`
   * definição: Resolver com precisão o problema errado: a resposta é tecnicamente certa para uma formulação que não é a do caso. O veredito recai sobre o investimento inteiro, não sobre a execução — quanto melhor a solução, maior o desperdício, porque a qualidade da resposta imuniza a formulação contra revisão.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dirty Rotten Strategies
      * Are Your Lights On?

* **esquema-de-organizacao** — Esquema de organização `[claudinha-produto]`
   * definição: Toda coleção exposta a busca se organiza por esquema exato (alfabético, cronológico, geográfico — uma resposta certa por item, exige que o usuário saiba o que procura) ou ambíguo (assunto, tarefa, público — agrupamento por julgamento, serve a quem não sabe nomear o que procura). O esquema escolhido decide se o usuário encontra sem dominar o vocabulário do sistema — e encontrar precede qualquer uso.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Information Architecture: For the Web and Beyond _(ocorre em estudos-ontologias)_
      * Designing Interfaces Patterns for Effective Interaction Design

* **estruturacao-de-problema** — Estruturação de problema `[claudinha-gestao-estrategica]`
   * definição: Produzir a formulação do problema — de quem é, que diferença entre estado percebido e estado desejado, sob qual leitura de mundo — antes de tratá-lo como escolha entre meios para um fim conhecido. A saída é um enunciado disputável, não uma solução; enquanto a formulação segue em disputa, otimizar alternativas responde a uma pergunta que ninguém validou.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Systems thinking, systems practice _(ocorre em arquiteturas)_
      * Are Your Lights On?
      * Dirty Rotten Strategies
      * Dilemmas in a General Theory of Planning

* **estruturacao-de-problema** — Estruturação de problema `[claudinho-arquiteto]`
   * definição: Produzir o enunciado do problema como artefato de trabalho — quem percebe, o que deseja, onde há conflito entre atores — antes de qualquer otimização; a escolha do enunciado predetermina o espaço de soluções, e a saída é uma formulação que sustenta acordo, não um ótimo. Decide contra a otimização (que exige enunciado dado) e contra product discovery (cujo objeto é a necessidade do usuário de um produto, não o enunciado disputado entre atores).
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Rational analysis for a problematic world revisited _(ocorre em gestao-organizacional)_
      * Redesigning the future _(ocorre em gestao-organizacional)_
      * Are Your Lights On?

* **fatiamento-por-jornada** — Fatiamento por jornada completa `[claudinha-produto]`
   * definição: Um release se recorta como fatia horizontal do fluxo narrativo: o menor conjunto que permite a um ator completar a jornada do gatilho até o objetivo entregue ou abandonado. Fatia que recorta por componente, camada ou dependência técnica não passa, porque nenhum ator completa nada com ela; a unidade de aceite é o comportamento de ponta a ponta, escrito antes da construção.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * User Story Mapping
      * WritingEffectiveUCs.book

* **outcome-sobre-output** — Outcome sobre output `[claudinha-produto]`
   * definição: A unidade de progresso de uma entrega é a mudança observável de comportamento humano que liga o artefato entregue ao resultado de negócio; a funcionalidade é meio, e uma entrega sem comportamento-alvo declarado não tem como ser julgada bem-sucedida. O teste é responder, antes de construir: que ator passa a fazer o quê de diferente, e como isso move o objetivo.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Outcomes Over Output
      * Impact Mapping

* **problema-perverso** — Problema perverso `[claudinha-gestao-estrategica]`
   * definição: Classe de problema sem formulação definitiva, sem regra de parada e sem teste de certo ou errado: cada intervenção é operação de um tiro que altera a situação, e a formulação escolhida já embute a solução preferida. Decide o formato do compromisso — o que é perverso não se planeja como projeto com fim declarado, se governa por intervenção assumida como irreversível.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dilemmas in a General Theory of Planning
      * Systems thinking, systems practice _(ocorre em arquiteturas)_

* **problema-perverso** — Problema perverso `[claudinho-arquiteto]`
   * definição: A formulação do problema não é dada, é escolhida — e cada formulação já embute uma classe de solução; não há teste objetivo de correção nem critério de parada, e o trabalho encerra por esgotamento de recurso ou decisão, não por "resolver". Decide contra o problema domado, que tem enunciado estável e teste de solução fixado ex ante.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Dilemmas in a General Theory of Planning
      * The Structure of Ill Structured Problems _(ocorre em gestao-organizacional)_

* **quatro-riscos-de-produto** — Quatro riscos de produto `[claudinha-produto]`
   * definição: Uma descoberta está completa quando há evidência coletada — não opinião de quem decide — contra quatro riscos distintos: o cliente escolhe usar (valor), o usuário consegue usar (usabilidade), dá para construir (viabilidade técnica) e funciona para o negócio (viabilidade de negócio). Endereçar um risco não endereça os outros; a régua reprova descoberta que só produziu evidência de valor.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Inspired
      * Empowered

* **teste-de-usabilidade-diy** — Teste de usabilidade faça-você-mesmo `[claudinha-produto]`
   * definição: Observação de poucos participantes (cerca de três) executando tarefas e pensando em voz alta, em cadência recorrente e barata, otimizando pelo número de problemas que a equipe consegue consertar até a rodada seguinte — não pela cobertura total de problemas existentes. O debrief fecha com o compromisso de correção dos mais graves; recrutamento é solto porque os problemas graves aparecem para quase qualquer participante.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * Rocket Surgery Made Easy: The Do-It-Yourself Guide to Finding and Fixing Usability Problems
      * Don't Make Me Think, Revisited

## seguranca-privacidade

* **abertura-por-padrao** — Abertura por padrão `[claudinho-arquiteto]`
   * definição: O regime fixa o acesso ao dado como presunção e a restrição como exceção enquadrada em categoria prévia; o ônus argumentativo é de quem restringe, e o rito de acesso é decidido pelo nível declarado ex ante, não por negociação bilateral caso a caso. Decide contra a classificação da informação (que atribui nível de sensibilidade sem fixar direção da presunção) e contra regimes de base legal, em que a presunção é inversa.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Decreto nº 8.777/2016 — Política de Dados Abertos do Poder Executivo federal _(ocorre em arquiteturas)_
      * Decreto nº 10.046/2019 — Governança no compartilhamento de dados na administração pública federal

* **acesso-delegado** — Acesso delegado `[claudinho-seguranca]` `balde A`
   * definição: Arranjo em que um terceiro obtém acesso limitado a um recurso em nome do dono sem receber a credencial do dono: uma autoridade separada media a aprovação e emite ao terceiro uma autorização própria, restrita em alcance e em prazo, revogável sem tocar na credencial original.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15)
      * Final: OpenID Connect Core 1.0 incorporating errata set 2 [snapshot 2026-08-01]
      * Model Context Protocol — Specification 2026-07-28 _(ocorre em ia)_

* **avaliacao-de-conformidade** — Avaliação de conformidade `[claudinho-seguranca]` `balde B`
   * definição: Regime em que três papéis são separados por desenho — o fornecedor declara e produz evidência, um laboratório acreditado ensaia contra requisito escrito de antemão, e uma autoridade emite ou nega a validação. O que o selo cobre é o objeto na configuração ensaiada contra aquele conjunto de requisitos, e nada além disso; a garantia não se estende ao produto que embute o objeto nem a versões posteriores.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Manual de Condutas Técnicas 11 — Volume I: requisitos, materiais e documentos técnicos para homologação de software de AC e AR no âmbito da ICP-Brasil
      * Manual de Condutas Técnicas 11 — Volume II: procedimentos de ensaios para avaliação de conformidade aos requisitos técnicos de softwares de AC e AR no âmbito da ICP-Brasil
      * CMVP Documentation Requirements: CMVP Validation Authority Updates to ISO/IEC 24759

* **avaliacao-de-impacto-a-privacidade** — Avaliação de impacto à privacidade `[claudinho-seguranca]` `balde A`
   * definição: Exame prévio de um tratamento novo ou alterado que descreve a operação, identifica os riscos que ela gera para os titulares e registra as medidas de mitigação adotadas. É obrigatório em hipóteses tipificadas — decisão automatizada com efeito jurídico, larga escala de dado sensível — e sua função é produzir o registro da decisão antes da operação, não depois.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * ABNT NBR ISO/IEC 27701:2019 — Técnicas de segurança — Extensão da ABNT NBR ISO/IEC 27001 e 27002 para gestão da privacidade da informação
      * Hipóteses legais de tratamento de dados pessoais - Legítimo Interesse
      * DPO Guide

* **base-legal-de-tratamento** — Base legal de tratamento `[claudinho-seguranca]` `balde B`
   * definição: A licitude de uma operação sobre dado pessoal não deriva da utilidade dela nem do cuidado técnico com que é feita: deriva de o agente enquadrá-la, antes de operar, em uma das hipóteses taxativas previstas para a categoria do dado. As hipóteses não são intercambiáveis depois do fato, e a que serve para um dado comum pode não servir para um dado sensível.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Hipóteses legais de tratamento de dados pessoais - Legítimo Interesse
      * LGPD - Saúde
      * Tratamento de dados pessoais pelo Poder Público: guia orientativo
      * Tratamento de dados pessoais para fins acadêmicos e para a realização de estudos e pesquisas — guia orientativo

* **comunicacao-de-incidente-ao-titular** — Comunicação de incidente ao titular `[claudinho-seguranca]` `balde A`
   * definição: Dever de comunicar à autoridade e às pessoas afetadas o incidente com dado pessoal que possa acarretar-lhes risco ou dano relevante, em prazo fixado e com conteúdo mínimo: natureza dos dados, titulares envolvidos, riscos, medidas de proteção existentes e medidas de reversão. O gatilho é o risco à pessoa, não a gravidade técnica do evento nem o sucesso da contenção.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Lei nº 13.709, de 14 de agosto de 2018 — Lei Geral de Proteção de Dados Pessoais (LGPD)
      * The EU General Data Protection Regulation (GDPR): A Practical Guide
      * DPO Guide

* **controlador-e-operador** — Controlador e operador `[claudinho-seguranca]` `balde A`
   * definição: Responde pelo tratamento quem determina a finalidade e os meios, não quem executa. Executar em nome de outro sob instrução documentada não transfere a responsabilidade; usar o dado para finalidade própria, fora da instrução, converte o executor em responsável por aquele tratamento.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * ABNT NBR ISO/IEC 27701:2019 — Técnicas de segurança — Extensão da ABNT NBR ISO/IEC 27001 e 27002 para gestão da privacidade da informação
      * Guidelines on shaping pseudonymisation according to GDPR provisions
      * Tratamento de dados pessoais pelo Poder Público: guia orientativo

* **credenciamento-de-seguranca** — Credenciamento de segurança `[claudinho-seguranca]` `balde A`
   * definição: Habilitação prévia e formal — de pessoa, órgão ou entidade privada — para tratar informação classificada em determinado grau, concedida por autoridade competente mediante requisitos verificados de idoneidade, qualificação técnica e designação de responsável nomeado. Sem a habilitação vigente não há tratamento lícito, ainda que haja necessidade e meio técnico.
   * natureza: processo
   * estatuto: instituido
   * âncoras:
      * Decreto nº 7.845, de 14 de novembro de 2012 — Credenciamento de segurança e tratamento de informação classificada
      * Instrução Normativa GSI/PR nº 2, de 5 de fevereiro de 2013 — Credenciamento de segurança para o tratamento de informação classificada
      * Norma Complementar 01/IN02/NSC/GSI/PR — disciplina o credenciamento de segurança de pessoas naturais, órgãos e entidades públicas e privadas para o tratamento de informações classificadas

* **criptoperiodo** — Criptoperíodo `[claudinho-seguranca]` `balde A`
   * definição: Intervalo durante o qual uma chave permanece autorizada para uso legítimo. É limitado para reduzir o material disponível à criptanálise, conter o alcance do comprometimento de uma única chave e não ultrapassar a vida útil estimada do algoritmo — e é ele, não a conveniência operacional, que fixa a cadência de rotação.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * nist.sp.800-57pt1r5
      * Transitioning the Use of Cryptographic Algorithms and Key Lengths
      * ISC2 CISSP Certified Information Systems Security Professional Official Study Guide

* **dano-de-privacidade-sem-incidente** — Dano de privacidade sem incidente de segurança `[claudinho-seguranca]` `balde B`
   * definição: O prejuízo ao indivíduo pode nascer de operação plenamente autorizada e conforme os controles de confidencialidade — agregação de fontes lícitas, identificação a partir de dado indireto, uso para finalidade diversa, exclusão do próprio titular da decisão que o afeta. Logo a ausência de acesso não autorizado não é evidência de ausência de dano, e o inventário de ameaças de segurança não enumera estas.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Threat Modeling: Designing for Security
      * NIST Privacy Framework: A Tool for Improving Privacy Through Enterprise Risk Management, Version 1.0
      * Understanding Privacy

* **delegado-confuso** — Delegado confuso `[claudinho-seguranca]` `balde B`
   * definição: Um intermediário autorizado a agir em nome de terceiros exerce a autoridade que ele próprio detém a pedido de quem não a detém, e o alvo não distingue as duas origens porque só vê a credencial do intermediário. A correção é vincular cada ato à parte pretendida — destinatário declarado na credencial, consentimento por ato, e proibição de repassar adiante a credencial recebida.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Model Context Protocol — Specification 2026-07-28 _(ocorre em ia)_
      * Resource Indicators for OAuth 2.0
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15)

* **exercicio-adversarial** — Exercício adversarial `[claudinho-seguranca]` `balde A`
   * definição: Exercício em que uma equipe age como adversário contra defensores que podem não saber do exercício, para medir a capacidade de detectar, escalar e responder. Distingue-se do teste de intrusão pelo objeto medido: lá se estabelece se a falha existe e é explorável; aqui se estabelece o que a defesa percebeu e o que fez a respeito.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * The Red Team Guide by Peerlyst
      * CompTIA CySA+ Cybersecurity Analyst Certification All-in-One Exam Guide (Exam CS0-002)

* **exercicio-de-plano** — Exercício de plano `[claudinho-seguranca]` `balde A`
   * definição: Simulação conduzida por cenário em que as pessoas com papel num plano discutem ou executam as ações que tomariam, para validar a viabilidade do plano. O objeto medido é o plano e o preparo de quem o executa — a saída útil é a lacuna descoberta —, e não a operabilidade do sistema, que é objeto de teste.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * nistspecialpublication800-84
      * CompTIA Security+ Certification Study Guide: Network Security Essentials

* **janela-de-exposicao** — Janela de exposição `[claudinho-seguranca]` `balde B`
   * definição: Entre o momento em que um defeito conhecido passa a ser explorável e o momento em que a correção está em produção, o risco corre. Todo controle de processo interposto nesse intervalo — teste, aprovação, janela de mudança — reduz o risco de a correção quebrar a operação e aumenta o risco de o defeito ser explorado; a decisão não é entre seguro e inseguro, é a escolha de qual dos dois riscos se prefere pagar.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-40 Rev.4 — Patch Management _(ocorre em engenharia-software)_
      * ISO/IEC 27002:2013 — Information technology — Security techniques — Code of practice for information security controls
      * ISC2 CISSP Certified Information Systems Security Professional Official Study Guide

* **linha-de-base-de-controles** — Linha de base de controles `[claudinho-seguranca]` `balde A`
   * definição: Conjunto de controles pré-selecionado para uma classe de sistema, que vigora por padrão sem escolha item a item. A adequação ao caso concreto se faz por ações de ajuste declaradas, e cada exceção exige motivo registrado, revisão e plano de eliminação — de modo que o desvio permaneça rastreável e a linha continue servindo de referência de auditoria.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-53 Rev.5 — Security and Privacy Controls
      * CIS VMware ESXi 8.0 Benchmark v1.3.0
      * CIS Linux Mint 22 Benchmark v1.0.0
      * CIS Critical Security Controls, Version 8.1

* **mediacao-do-loop-agentico** — Mediação do loop agêntico `[claudinho-IA]`
   * definição: Desenho do ponto em que a ação do agente é liberada: aprovação humana por ação, revisão automática por política, ou execução livre dentro de fronteira de isolamento previamente definida. A régua troca custo de mediação (fadiga de aprovação, latência, configuração) por raio de dano da ação não revisada — e prevê que mediação por ação degrada a própria vigilância que a justifica.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * Making Claude Code more secure and autonomous with sandboxing [snapshot 2026-08-01]
      * How we built Claude Code auto mode: a safer way to skip permissions [snapshot 2026-08-01]
      * Best practices for Claude Code - Claude Code Docs [snapshot 2026-08-01] _(ocorre em ia)_

* **modulo-criptografico** — Módulo criptográfico `[claudinho-seguranca]` `balde A`
   * definição: Conjunto de hardware, software ou firmware delimitado por uma fronteira declarada, dentro da qual residem as funções criptográficas aprovadas e os parâmetros críticos de segurança, e cujas interfaces, papéis, serviços, autotestes e proteções físicas são especificados por nível. A garantia se aplica ao que está dentro da fronteira, não ao produto que o contém.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Security Requirements for Cryptographic Modules
      * FIPS 140-3 Derived Test Requirements (DTR): CMVP Validation Authority Updates to ISO/IEC 24759
      * Instrução Normativa ITI nº 22, de 23 de março de 2022 — Padrões e algoritmos criptográficos da ICP-Brasil (DOC-ICP-01.01)

* **necessidade-de-conhecer** — Necessidade de conhecer `[claudinho-seguranca]` `balde A`
   * definição: Dois requisitos independentes governam o acesso a informação restrita: a habilitação, que fixa o teto do grau acessível, e a necessidade inerente ao exercício concreto de cargo, função ou atividade, que fixa o que dentro desse teto de fato se acessa. Ter o grau não confere acesso; a necessidade sem o grau tampouco.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Norma Complementar 01/IN02/NSC/GSI/PR — disciplina o credenciamento de segurança de pessoas naturais, órgãos e entidades públicas e privadas para o tratamento de informações classificadas
      * Coletânea de Normas de Segurança da Informação Classificada
      * Decreto nº 7.845, de 14 de novembro de 2012 — Credenciamento de segurança e tratamento de informação classificada

* **negar-por-padrao** — Negar por padrão `[claudinho-seguranca]` `balde A`
   * definição: Postura em que o sistema recusa tudo o que não estiver explicitamente permitido, de modo que a lista mantida é a de exceções autorizadas e o esquecimento produz recusa em vez de permissão. Distingue-se de menor privilégio: lá se decide o tamanho da permissão concedida; aqui se decide o que acontece quando não há decisão nenhuma.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-53 Rev.5 — Security and Privacy Controls
      * Guidelines on Firewalls and Firewall Policy
      * CIS Linux Mint 22 Benchmark v1.0.0

* **padrao-como-politica** — Padrão como decisão de política `[claudinho-seguranca]` `balde B`
   * definição: Em sistema configurável, o valor pré-selecionado é o que vigora para a maioria dos afetados, porque a maioria não intervém. Logo a escolha do valor de fábrica é a política efetiva do sistema, e oferecer a opção contrária não a corrige — só transfere ao afetado o ônus de descobrir e exercer a opção.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Guidelines 4/2019 on Article 25 — Data Protection by Design and by Default, Version 2.0
      * DPO Guide
      * CISSP All-in-One Exam Guide

* **politica-de-seguranca-institucional** — Política de segurança institucional `[claudinho-seguranca]` `balde A`
   * definição: Instrumento formal aprovado pela autoridade máxima da organização que fixa diretrizes, nomeia os papéis responsáveis — gestor, comitê, equipe de tratamento de incidentes — e obriga a organização inteira. Medida declarada obrigatória de que se abre mão exige motivação registrada em análise de risco, e é esse registro que a distingue de declaração de intenção.
   * natureza: modelo
   * estatuto: instituido
   * âncoras:
      * Instrução Normativa GSI/PR nº 1, de 27 de maio de 2020 — Estrutura de Gestão da Segurança da Informação na administração pública federal
      * Portaria SGD/MGI nº 852/2023 — Programa de Privacidade e Segurança da Informação (PPSI)
      * Política de Segurança da Informação e Comunicação do Laboratório Nacional de Computação Científica

* **prova-de-identidade** — Prova de identidade `[claudinho-seguranca]` `balde A`
   * definição: Ato anterior ao cadastro em que se coleta evidência sobre uma identidade do mundo real, se valida a autenticidade dessa evidência e se verifica que o requerente é a pessoa a quem ela se refere. Distingue-se da autenticação: aqui se estabelece o vínculo pela primeira vez; lá se reconhece um vínculo já estabelecido.
   * natureza: processo
   * estatuto: doutrinario
   * âncoras:
      * NIST SP 800-63A-4 — Identity Proofing
      * NIST SP 800-63-4 — Digital Identity Guidelines
      * Digital Identity Guidelines

* **regras-de-engajamento** — Regras de engajamento `[claudinho-seguranca]` `balde A`
   * definição: Autorização escrita, anterior à atividade intrusiva, que delimita alvos incluídos e explicitamente excluídos, período, técnicas permitidas e proibidas, e quem aprova o desvio. É ela que separa o teste do ataque: fora do que ela cobre, a mesma ação técnica deixa de ser autorizada.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * nistspecialpublication800-115
      * The Red Team Guide by Peerlyst

* **requisito-verificavel** — Requisito verificável `[claudinho-seguranca]` `balde B`
   * definição: Um enunciado prescritivo só governa quando vem acompanhado de (a) um procedimento de verificação que produz veredito binário sobre um objeto concreto e (b) um procedimento de correção do objeto que reprovou. Sem os dois, o enunciado é intenção declarada: não distingue quem cumpre de quem não cumpre, e por isso não se audita nem se delega.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * CIS Apache HTTP Server 2.4 Benchmark v2.3.0
      * Manual de Condutas Técnicas 11 — Volume II: procedimentos de ensaios para avaliação de conformidade aos requisitos técnicos de softwares de AC e AR no âmbito da ICP-Brasil
      * OWASP SAMM v2.2.0

* **token-portador** — Token portador `[claudinho-seguranca]` `balde A`
   * definição: Credencial cuja simples apresentação basta para o uso: quem a detém exerce tudo o que qualquer outro detentor exerceria, sem provar posse de chave associada. Toda a proteção colapsa no sigilo do armazenamento e do transporte, e o contraste é a credencial de prova de posse, que exige demonstrar controle de uma chave a cada uso.
   * natureza: modelo
   * estatuto: doutrinario
   * âncoras:
      * The OAuth 2.1 Authorization Framework (draft-ietf-oauth-v2-1-15)
      * JSON Web Token Best Current Practices
      * Resource Indicators for OAuth 2.0

* **transparencia-de-composicao** — Transparência de composição `[claudinho-seguranca]` `balde B`
   * definição: Propriedade de um artefato entregue cuja árvore de constituintes — fornecedor, nome, versão, identificador e relação de dependência, inclusive as transitivas — é declarada pelo produtor em forma legível por máquina, de modo que quem apenas opera o artefato responda "isto contém o componente X na versão Y?" sem consultar o produtor. O que a declaração não alcança é declarado como tal, em vez de omitido.
   * natureza: disposicao
   * estatuto: doutrinario
   * âncoras:
      * The Minimum Elements For a Software Bill of Materials (SBOM) _(ocorre em engenharia-software)_
      * Strategies for the Integration of Software Supply Chain Security in DevSecOps CI/CD Pipelines _(ocorre em engenharia-software)_
      * Software Supply Chain Security

* **vida-util-do-sigilo** — Vida útil do sigilo `[claudinho-seguranca]` `balde B`
   * definição: Toda informação protegida tem um prazo pelo qual precisa permanecer inacessível ao adversário. Somado ao tempo de migrar a proteção, esse prazo se compara ao tempo estimado até a quebra do mecanismo em uso: se a soma o excede, o dado já está comprometido no instante em que é transmitido ou armazenado, ainda que a proteção de hoje seja íntegra e o adversário só o abra depois.
   * natureza: fenomeno
   * estatuto: doutrinario
   * âncoras:
      * Transição Brasileira para a Prontidão Pós-Quântica (PQC) e Soberania Digital
      * Relatório executivo: estratégia de transição PQC e soberania digital do Brasil
      * Transitioning the Use of Cryptographic Algorithms and Key Lengths

