# Consolidado T0 — recuperação + geração — 3 arms, mesmo prompt

Gerado por `tooling/consolidar-firmabot.py`. `G0-rag-base` (o que o
rag_search devolveu) + o(s) gerador(es) respondendo em cima do mesmo
`contexto` congelado, com `prompt-firmabot.md` como sistema. Lista de
obras é só o que apareceu nas fontes — não é julgamento de qual é "a"
fonte certa, isso é da claudinho-IA.

---

## 01. o que é um conceito e qual seu critério de identidade?  
*(bloco A)*

**Obras na recuperação:** Tractatus Logico-Philosophicus; Teoria dos Direitos Fundamentais; Evaluating ontological decisions with OntoClean; Atividade de inteligência nacional brasileira — doutrina; WonderWeb Deliverable D18: Ontology Library (final); Lei nº 6.880/1980 — Estatuto dos Militares; How We Think

**Resposta (claude-sonnet-5):**

O acervo não cobre o conceito exato perguntado.

Nenhuma das fontes apresentadas define de forma explícita "o que é um conceito" e "qual seu critério de identidade" como par de noções articuladas. A fonte [3] trata da metodologia OntoClean e menciona "Essence and Rigidity" como notion formal, mas o trecho fornecido não chega a definir "conceito" nem "critério de identidade" — apenas introduz o tema sem desenvolvê-lo [3]. A fonte [5] apresenta uma definição formal de CONCEPT em código KIF (DEFCONCEPT), mas é uma declaração lógico-formal, não uma explicação do que é conceito nem de seu critério de identidade [5]. A fonte [6] traz apenas o título "Conceitos e Definições", sem conteúdo desenvolvido [6]. As demais fontes ([1], [2], [4], [7], [8]) tratam de outros temas (Tractatus, direitos fundamentais, doutrina de inteligência, pensamento em Dewey) e não abordam o critério de identidade de conceitos.

Não respondo pela vizinha nem completo com conhecimento próprio, conforme a regra.

**Resposta (gemma4:12b):**

O acervo não cobre.

**Resposta (qwen3.5:9b):**

As fontes fornecidas não cobrem o conceito exato de "o que é um conceito e qual seu critério de identidade". [6] menciona apenas o título do capítulo sobre conceitos, sem desenvolver a definição ou o critério. [3] trata de ontologias e metapropriedades como essência e rigidez em contextos específicos de engenharia de conhecimento, não definindo universalmente "conceito" para fins gerais. [4], [7] e [8] tratam de fundamentos da atividade de inteligência, teoria dos direitos fundamentais e treinamento do pensamento (pensamento), respectivamente, sem abordar a definição filosófica ou lógica geral de conceito e seu critério de identidade.

---

## 02. o que distingue um tipo de um papel?  
*(bloco A)*

**Obras na recuperação:** Digital Forensics Processing and Procedures: Meeting the Requirements of ISO 17020, ISO 17025, ISO 27001 and Best Practice Requirements; Teoria dos Direitos Fundamentais

**Resposta (claude-sonnet-5):**

O acervo não cobre o conceito exato perguntado. As fontes fornecidas tratam de sopesamento e princípios [2], restrições a direitos fundamentais [4], direito geral de igualdade [5][7], direitos subjetivos e competência [6], objeto de uma teoria dos direitos fundamentais [3], e um relatório de seguro em perícia forense [1] — nenhuma delas aborda a distinção entre "tipo" e "papel" enquanto conceitos.

**Resposta (gemma4:12b):**

O acervo não cobre.

**Resposta (qwen3.5:9b):**

Não há informação nas fontes fornecidas sobre o que distingue um tipo de papel. [1]

---

## 03. o que é arquitetura de software?  
*(bloco A)*

**Obras na recuperação:** Fundamentals of Software Architecture (2025); [sem obra] Software-Architecture-in-Practice-Bass-Clements-Kazman.pdf; Continuous Architecture in Practice

**Resposta (claude-sonnet-5):**

Arquitetura de software é o conjunto de estruturas necessárias para raciocinar sobre um sistema, composto por elementos de software, relações entre eles e propriedades de ambos [2]. Essa definição se opõe a outras que falam em decisões "iniciais" ou "principais" de projeto — muitas decisões arquiteturais não são tomadas cedo, e nem toda decisão tomada cedo é arquitetural [2]. Estruturas são fáceis de identificar em software e formam uma ferramenta poderosa para o design de sistemas; um sistema é composto de várias estruturas, e nenhuma estrutura isolada é "a arquitetura" [2].

Sob outra fonte, a definição do IFIP Working Group 2.10 complementa: arquitetura de software refere-se às estruturas fundamentais de um sistema de software e à disciplina de criar tais estruturas e sistemas, cada estrutura compreendendo elementos de software, relações entre eles e propriedades de elementos e relações [3]. Essa fonte acrescenta que a arquitetura é uma metáfora análoga à arquitetura de edifícios, funcionando como planta (blueprint) para o sistema e o projeto de desenvolvimento, delineando as tarefas a serem executadas pelas equipes de design [3]. Arquitetura de software trata de fazer escolhas estruturais fundamentais que são custosas de mudar depois de implementadas [3]. Documentar a arquitetura de software facilita a comunicação entre stakeholders, captura decisões iniciais sobre o design de alto nível, e permite reuso de componentes de design entre projetos [3].

O acervo também traz a norma ISO/IEEE, mas o trecho fornecido corta antes de apresentar a definição completa, então não é possível citá-la com segurança [3].

**Resposta (gemma4:12b):**

A arquitetura de software pode ser definida como o conjunto de estruturas necessárias para raciocinar sobre o sistema, as quais compreendem elementos de software, as relações entre eles e as propriedades de ambos [2].

Outras definições incluem:
*   Refere-se às estruturas fundamentais de um sistema de software e à disciplina de criar tais estruturas e sistemas [3]. Cada estrutura é composta por elementos de software, relações entre eles e propriedades de ambos os elementos e relações [3].
*   Funciona como uma planta (blueprint) para o sistema e para o projeto de desenvolvimento, delineando as tarefas necessárias a serem executadas pelas equipes de design [3].
*   Trata de fazer escolhas estruturais fundamentais que são caras para alterar após a implementação [3].

**Resposta (qwen3.5:9b):**

Arquitetura de software é o conjunto de estruturas necessárias para raciocinar sobre um sistema, que compreende elementos de software, relações entre eles e propriedades tanto dos elementos quanto das relações [2]. Ela refere-se às estruturas fundamentais de um sistema de software e à disciplina de criar tais estruturas e sistemas; cada estrutura consiste em elementos de software, suas relações e as propriedades desses elementos e relações [3].

---

## 04. o que é arquitetura de dados?  
*(bloco A)*

**Obras na recuperação:** Fundamentals of Data Engineering; Data Governance (2nd); Continuous Architecture in Practice

**Resposta (claude-sonnet-5):**

Arquitetura de dados é um subconjunto da arquitetura corporativa (enterprise architecture), herdando dela processos, estratégia, gestão de mudança e avaliação de trade-offs [1].

Segundo a definição do DAMA DMBOK, citada em [3], trata-se de "identificar as necessidades de dados da empresa (independente da estrutura) e projetar e manter os blueprints mestres para atender a essas necessidades, usando esses blueprints para guiar a integração de dados, controlar ativos de dados e alinhar investimentos de dados com a estratégia de negócio" [3].

Outra formulação, também baseada no DMBOK mas simplificada, define arquitetura de dados como "uma representação do ambiente de gestão de dados (DM), seus componentes e suas interações — uma figura, ou abstração, que interrelaciona framework, pessoas, processos, projetos, políticas, tecnologias e procedimentos para gerenciar e usar os ativos de informação valiosos da empresa" [2].

Em termos operacionais, uma arquitetura de dados reflete o estado atual e futuro dos sistemas de dados que sustentam as necessidades e a estratégia de dados de longo prazo de uma organização [5]. Ela é descrita como uma corrente subjacente (undercurrent) ao longo de todo o ciclo de vida da engenharia de dados, e cabe ao engenheiro de dados entender as necessidades do negócio e traduzi-las em formas de capturar e servir dados, balanceando custo e simplicidade operacional [5].

Por ser uma disciplina abstrata, a arquitetura de dados é mais bem compreendida por exemplos e padrões (como data warehouse e data lake), já que não existe um único modelo universal aplicável a todos os casos de uso [4].

Do ponto de vista de boa prática, uma boa arquitetura de dados significa avaliar trade-offs e escolher as melhores ferramentas para o trabalho, mantendo as decisões reversíveis, evitando lock-in desnecessário, garantindo interoperabilidade e produzindo alto ROI [7].

Do ponto de vista de arquitetura de software mais ampla, o foco em dados como preocupação arquitetural cresceu nos últimos anos: antes, arquitetura de dados era domínio restrito a modeladores e arquitetos de dados voltados a relatórios (data warehouses, data marts); hoje, com sistemas cada vez mais distribuídos, dados tornaram-se uma preocupação arquitetural central [8]. Considerações fundamentais incluem como os dados são geridos (propriedade e metadados), compartilhados (integração) e evoluem no tempo (evolução de esquema) [8].

**Resposta (gemma4:12b):**

A arquitetura de dados pode ser definida de diversas formas dependendo do contexto:

*   É um subconjunto da arquitetura corporativa, herdando propriedades como processos, estratégia, gestão de mudanças e avaliação de compensações (trade-offs) [1].
*   É uma representação do ambiente de gerenciamento de dados (DM), seus componentes e suas interações, relacionando o framework, pessoas, processos, projetos, políticas, tecnologias e procedimentos para gerenciar e usar ativos de informação valiosos da empresa [2].
*   Segundo a definição do DAMA, é identificar as necessidades de dados da empresa (independentemente da estrutura) e projetar e manter os modelos mestres (master blueprints) para atender a essas necessidades, servindo para guiar a integração de dados, controlar ativos de dados e alinhar investimentos em dados com a estratégia de negócios [3].
*   Reflete o estado atual e futuro dos sistemas de dados que apoiam as necessidades e estratégias de longo prazo de uma organização [5].

**Resposta (qwen3.5:9b):**

Arquitetura de dados é um subconjunto da arquitetura empresarial que herda propriedades como processos, estratégia e gestão de mudanças [1]. Ela pode ser definida como a identificação das necessidades de dados da empresa (independentemente da estrutura) e o desenho e manutenção dos planos mestres para atender a essas necessidades [3]. Também representa o ambiente de gerenciamento de dados (DM), seus componentes e suas interações, relacionando framework, pessoas, processos, projetos, políticas, tecnologias e procedimentos para gerenciar ativos de informação empresarial valiosos [2]. Além disso, reflete o estado atual e futuro dos sistemas de dados que suportam as necessidades e a estratégia de longo prazo da organização em relação aos seus requisitos de dados [5].

---

## 05. o que é governança de dados?  
*(bloco A)*

**Obras na recuperação:** Cartilha de Governança de Dados — Volume I: Conceitos Iniciais; Cartilha de Governança de Dados — Volume III: Papéis e Responsabilidades de Governança de Dados no Poder Executivo Federal; Modelo de Maturidade de Dados (MMD) — Poder Executivo Federal, Versão 1.2; Cartilha do Catálogo Nacional de Dados; Apresentação do PowerPoint; Decreto nº 10.046/2019 — Governança no compartilhamento de dados na administração pública federal

**Resposta (claude-sonnet-5):**

O acervo não traz uma definição direta e explícita do conceito "governança de dados" [2]. As fontes disponíveis tratam de aspectos correlatos — estrutura organizacional [3], papéis e responsabilidades [5], riscos da não implementação [4], regulação de compartilhamento [7][8] — mas não uma definição conceitual do termo em si.

O que mais se aproxima é a apresentação da Cartilha vol. III, que descreve o papel da governança e gestão de dados como algo que "desempenha um papel basilar na implementação da estratégia de transformação digital do Estado para melhoria dos serviços e das políticas públicas, em que as organizações buscam extrair valor e evidências de seus ativos de dados, garantir a conformidade e segurança, facilitar a tomada de decisões embasadas, promover a cultura de dados, estabelecer responsabilidade e prestação de contas" [2]. Isso caracteriza a função da governança de dados, não uma definição formal do termo.

Se você quer uma definição formal e fechada do conceito, o acervo não cobre esse ponto exato.

**Resposta (gemma4:12b):**

A governança de dados desempenha um papel basilar na implementação da estratégia de transformação digital do Estado para melhoria dos serviços e das políticas públicas, permitindo que as organizações extraiam valor e evidências de seus ativos de dados, garantam a conformidade e segurança, facilitem a tomada de decisões embasadas, promovam a cultura de dados, estabeleçam responsabilidade e prestação de contas [2]. Além disso, ela é utilizada para integrar e convergir os esforços das diversas unidades, impactando diretamente nas entregas de produtos de dados para a sociedade [6].

**Resposta (qwen3.5:9b):**

Governança de Dados é um conjunto de normas, diretrizes e mecanismos estabelecidos para garantir o compartilhamento adequado entre órgãos da administração pública federal, visando simplificar serviços públicos, orientar políticas públicas e melhorar a qualidade dos dados [8]. Ela também envolve a definição de papéis, responsabilidades e estruturas organizacionais formais que garantem conformidade legal, segurança e uso estratégico dos dados como ativo [2][3]. Além disso, sua implementação mitiga riscos relacionados à não conformidade com leis de privacidade e sigilo, além de promover uma cultura de dados baseada em evidências para a sociedade [4][6].

---

## 06. o que é um domínio em gestão do conhecimento?  
*(bloco A)*

**Obras na recuperação:** Learning Domain-Driven Design; WonderWeb Deliverable D18: Ontology Library (final); Fundamentals of Data Engineering; Domain-Driven Design

**Resposta (claude-sonnet-5):**

O acervo não cobre especificamente "domínio" no contexto de **gestão do conhecimento** como disciplina. As fontes disponíveis tratam do conceito de domínio no contexto de **Domain-Driven Design (DDD)** e **arquitetura de dados**, que são áreas correlatas mas não idênticas à pergunta feita.

Pelo que as fontes cobrem sobre o conceito de domínio (em engenharia de software/dados):

Domínio é definido como "uma esfera de conhecimento, influência ou atividade. A área de assunto à qual o usuário aplica um programa é o domínio do software" [5]. Um domínio pode conter múltiplos serviços — por exemplo, um domínio de vendas pode conter serviços de pedidos, faturamento e produtos [5].

Na perspectiva de Eric Evans, "toda área de assunto à qual o usuário aplica o programa é o domínio do software" [6], e alguns domínios envolvem o mundo físico, como o domínio de um programa de reservas de companhia aérea [6].

Se a pergunta é sobre gestão do conhecimento como disciplina (KM), com seus próprios frameworks de "domínio de conhecimento", o acervo não cobre esse conceito exato — as fontes [3], [4] e [8] tratam de "conhecimento de domínio" (domain knowledge) dentro do DDD, que é sobre descobrir e modelar lógica de negócio, não sobre domínios como categoria estrutural em KM.

**Resposta (gemma4:12b):**

Um domínio é definido como uma esfera de conhecimento, influência ou atividade [5]. É o campo de assunto do mundo real para o qual se está projetando uma arquitetura [5] e representa a área de interesse ou atividade à qual o usuário aplica o programa [6]. Além disso, um domínio pode conter múltiplos serviços, que são conjuntos de funcionalidades com o objetivo de realizar tarefas específicas [5].

**Resposta (qwen3.5:9b):**

Um domínio é uma esfera de conhecimento, influência ou atividade [5]. Também pode ser definido como o assunto real para o qual você está arquitetando um sistema [5] e a área de interesse do usuário à qual ele aplica o programa [6]. Em termos mais amplos, refere-se ao modelo da realidade que abstrai aspectos relevantes para resolver um problema específico [6].

---

## 07. o que é inteligência?  
*(bloco A)*

**Obras na recuperação:** Referencial de análise (Abin) — coletânea de artigos; Atividade de inteligência nacional brasileira — doutrina; Lei nº 9.883/1999 — Lei da Agência Brasileira de Inteligência; Decreto nº 8.793/2016 — Política Nacional de Inteligência

**Resposta (claude-sonnet-5):**

Há mais de uma definição de inteligência conforme o acervo.

Em sentido amplo, inteligência é toda informação coletada, organizada ou analisada para atender à demanda de um tomador de decisões — nessa acepção, equivale a conhecimento ou informação [1]. Essa definição ampla é atribuída a Jennifer Sims, que caracteriza inteligência como "informação para tomadores de decisão" [2].

Em sentido restrito, inteligência é a coleta de informações sem o consentimento, a cooperação ou mesmo o conhecimento por parte dos alvos da ação — nessa acepção, equivale a segredo ou informação secreta [1].

No plano legal brasileiro, a Lei nº 9.883/1999 define inteligência como "a atividade que objetiva a obtenção, análise e disseminação de conhecimentos dentro e fora do território nacional sobre fatos e situações de imediata ou potencial influência sobre o processo decisório e a ação governamental e sobre a salvaguarda e a segurança da sociedade e do Estado" [7].

A Doutrina Nacional de Inteligência (D8793/2016) caracteriza a Inteligência como atividade especializada, alicerçada em um conjunto sólido de valores profissionais e doutrina comum, que emprega meios sigilosos para obter dados indispensáveis ao processo decisório, indisponíveis por coleta ordinária [8].

No contexto da Atividade de Inteligência brasileira, ela é caracterizada pela produção de conhecimentos com a finalidade de apontar oportunidades e ameaças à consecução dos objetivos nacionais [6].

**Resposta (gemma4:12b):**

Existem diferentes definições para o termo inteligência conforme as fontes:

*   **Definição Ampla:** É toda informação coletada, organizada ou analisada para atender à demanda de um tomador de decisões [1]. Nesta acepção, é equivalente a conhecimento ou informação [1, 2].
*   **Definição Restrita:** É a coleta de informações sem o consentimento, cooperação ou conhecimento por parte dos alvos da ação; nesta acepção, é equivalente a segredo ou informação secreta [1].
*   **Atividade Especializada:** É uma atividade especializada que exige o emprego de meios sigilosos para preservar ações, métodos, processos, profissionais e fontes. Ela desenvolve ações de caráter sigiloso para obter dados indispensáveis ao processo decisório que estão indisponíveis para coleta ordinária devido ao acesso negado por seus detentores [8].
*   **Definição Legal (Brasil):** É a atividade que objetiva a obtenção, análise e disseminação de conhecimentos dentro e fora do território nacional sobre fatos e situações de imediata ou potencial influência sobre o processo decisório e a ação governamental e sobre a salvaguarda e a segurança da sociedade e do Estado [7].
*   **Produção de Conhecimento:** É caracterizada pela produção de conhecimentos com a finalidade de apontar oportunidades e ameaças à consecução dos objetivos nacionais [6].

**Resposta (qwen3.5:9b):**

Segundo as fontes fornecidas, o termo inteligência possui dois usos principais fora das ciências cognitivas: uma definição ampla e uma restrita [1]. Na acepção ampla, inteligência é toda informação coletada, organizada ou analisada para atender a demanda de um tomador de decisões, sendo neste caso equivalente a conhecimento ou informação [2][3]. Já na definição mais restrita, que as fontes indicam como ancoragem forte para o estudo dos serviços governamentais, inteligência refere-se à coleta de informações sem consentimento, cooperação ou conhecimento por parte dos alvos da ação, sendo nesta acepção sinônimo de segredo ou informação secreta [1][2]. A Lei nº 9.883/1999 define a atividade de inteligência como aquela que objetiva a obtenção, análise e disseminação de conhecimentos sobre fatos e situações com influência no processo decisório e na segurança da sociedade e do Estado [7]. Além disso, a doutrina caracteriza a inteligência como uma atividade especializada que emprega meios sigilosos para obter dados indispensáveis ao processo decisório que não estão disponíveis para coleta ordinária devido à negação de acesso por seus detentores [8].

---

## 08. o que é criptografia pós-quântica?  
*(bloco A)*

**Obras na recuperação:** Ameaça da computação quântica e a transição para a criptografia pós-quântica: relatório executivo de segurança; Consolidação de Matrizes PQC; Transição Brasileira para a Prontidão Pós-Quântica (PQC) e Soberania Digital; OSIC 15/2024 — Normatização e regulação de tecnologias emergentes no contexto da cibersegurança; Relatório executivo: a transição para a criptografia pós-quântica (PQC) e a proteção das infraestruturas críticas no Brasil; Uma Extensão Pós-Quântica Híbrida para o Protocolo Matrix: Avaliação Experimental e Impacto Sistêmico

**Resposta (claude-sonnet-5):**

Criptografia pós-quântica (PQC) é o conjunto de algoritmos matemáticos desenvolvidos para permanecer seguros mesmo diante do poder de processamento de computadores quânticos, funcionando como defesa primária contra a ameaça quântica [1].

Sua necessidade surge porque algoritmos quânticos — como o Algoritmo de Shor — conseguem quebrar sistemas de criptografia assimétrica atuais (RSA e ECC), que dependem da dificuldade de fatoração de grandes números ou do logaritmo discreto [4][8]. Já o Algoritmo de Grover impacta a criptografia simétrica, exigindo o dobro do tamanho de chaves (ex.: AES-256) para manter o nível de segurança [8].

Entre as abordagens técnicas de PQC estão a criptografia baseada em reticulados (lattice-based) e as assinaturas baseadas em hash (hash-based), sendo que o NIST divulgou padrões nessas categorias [4]. Um exemplo prático dessa família é o CRYSTALS-Kyber, algoritmo lattice-based avaliado em integração híbrida com o protocolo Matrix para acordo de chaves [7].

A urgência da adoção é reforçada pela ameaça "Harvest Now, Decrypt Later" (HNDL/SNDL) — ou descriptografia retrospectiva —, em que adversários armazenam hoje dados cifrados classicamente para descriptografá-los assim que dispuserem de computação quântica capaz disso [8].

A estratégia recomendada não é a substituição pura, mas a criptografia híbrida, combinando segurança clássica com PQC, para mitigar esse risco de descriptografia futura [5]. No caso brasileiro, essa transição é tratada como imperativo de soberania digital e de financiamento contínuo de Defesa, sob uma abordagem "Quantum-Safe-by-Design" [3].

Por fim, distingue-se da criptografia quântica propriamente dita (como a distribuição quântica de chaves, QKD): a PQC é apontada como solução necessária de curto prazo, enquanto a QKD é vista como tecnologia de mais longo prazo [6].

**Resposta (gemma4:12b):**

A criptografia pós-quântica (PQC) é definida como o uso de algoritmos matemáticos que são considerados seguros mesmo contra o poder de processamento de computadores quânticos [1]. Ela é apresentada como uma solução necessária para proteger informações no futuro quântico e como a defesa primária contra as ameaças geradas pela computação quântica [1, 6]. A PQC envolve o desenvolvimento de novos algoritmos resistentes a ataques quânticos, tais como a criptografia baseada em reticulados (lattice-based cryptography) e assinaturas hash-based [4].

**Resposta (qwen3.5:9b):**

Criptografia Pós-Quântica (PQC) é definida como o uso de novos algoritmos matemáticos desenvolvidos para serem seguros mesmo contra o poder de processamento de computadores quânticos [1]. Ela consiste no desenvolvimento desses novos algoritmos resistentes a ataques quânticos, que podem incluir criptografia baseada em reticulados e assinaturas hash-based [4]. A PQC surge como solução necessária para proteger informações diante da ameaça representada pela computação quântica, especialmente contra o Algoritmo de Shor, capaz de quebrar sistemas clássicos assimétricos [8].

---

## 09. o que é uma decisão arquitetural e quando se registra?  
*(bloco A)*

**Obras na recuperação:** Fundamentals of Software Architecture (2025); Documenting Architecture Decisions; Continuous Architecture in Practice; Ontology of architectural design decisions in software-intensive systems; Software Architecture Knowledge Management: Theory and Practice

**Resposta (claude-sonnet-5):**

Uma decisão arquitetural é, segundo [1], aquela que geralmente envolve a estrutura da aplicação ou do sistema, podendo também abranger decisões de tecnologia quando estas impactam características arquiteturais; uma boa decisão orienta os times de desenvolvimento nas escolhas técnicas corretas [1]. Complementarmente, [3] define a decisão arquitetural como a unidade primária de trabalho das atividades arquiteturais, e [4] reforça essa visão ao descrever a arquitetura como um "fluxo de decisões".

Do ponto de vista estrutural, uma decisão de design arquitetural possui atributos formais: epítome (o enunciado curto da decisão), rationale (a justificativa do porquê) e escopo (limites em tempo, organização ou implementação) [6], [5]. Kruchten também descreve estados possíveis de uma decisão ao longo do tempo — decided, approved, challenged, rejected, obsolesced — indicando que o registro não é estático, mas acompanha o ciclo de vida da decisão [5].

Quanto ao "quando se registra": [1] indica que o processo de decisão arquitetural inclui, entre suas etapas, reunir informação relevante, justificar, documentar e comunicar a decisão aos stakeholders certos — ou seja, a documentação é parte constitutiva do próprio ato de decidir, não uma etapa posterior opcional [1].

Segundo [2], em projetos ágeis nem todas as decisões são tomadas de uma vez nem no início do projeto; o registro deve ocorrer de forma contínua, em documentos pequenos e modulares, justamente porque documentos grandes não são mantidos atualizados nem lidos. A motivação por trás de uma decisão é um dos aspectos mais difíceis de rastrear ao longo da vida do projeto, o que justifica registrar no momento em que a decisão é tomada [2].

[4] detalha um mecanismo prático: um quadro kanban de decisões arquiteturais, com colunas como Backlog, In Progress, Ready for Decision e Decision Made, recomendando não apenas documentar as decisões mas também definir antecipadamente quais decisões precisam ser tomadas e suas dependências.

Por fim, [3] e [8] justificam a necessidade do registro: sem capturar as decisões arquiteturais, perde-se o conhecimento dos tradeoffs feitos em determinado contexto, o que impede a equipe de sustentar a evolução de longo prazo do produto [3]. [8] descreve o risco do registro ausente — decisões implícitas (o arquiteto nem percebe que decidiu) ou explícitas mas não documentadas (decididas por razão específica, mas sem registro da razão) tendem a se perder com o tempo, dificultando o rastreio posterior, especialmente durante a evolução do sistema [8].

**Resposta (gemma4:12b):**

Uma decisão arquitetural é uma das principais expectativas de um arquiteto e envolve a estrutura do aplicativo ou sistema, podendo também envolver decisões tecnológicas quando estas impactam as características arquiteturais [1]. Elas são consideradas a unidade básica de trabalho das atividades de arquitetura [3, 4] e, se não forem compreendidas e capturadas, resultam na perda do conhecimento sobre as trocas (*trade-offs*) feitas em um contexto específico [3].

O registro (documentação) dessas decisões deve ocorrer para garantir que a justificativa e o raciocínio por trás das escolhas não sejam perdidos ao longo do tempo, permitindo que a equipe suporte a evolução de longo prazo do produto [3, 8]. O processo de decisão envolve coletar informações relevantes, justificar a escolha, documentá-la e comunicá-la aos stakeholders adequados [1]. Recomenda-se não apenas documentar as decisões, mas também defini-las antecipadamente e identificar suas dependências [4].

**Resposta (qwen3.5:9b):**

Uma decisão arquitetural é uma escolha que envolve a estrutura da aplicação ou sistema e pode incluir decisões de tecnologia quando estas impactam características arquiteturais [1]. Ela serve para guiar as equipes de desenvolvimento na tomada das escolhas técnicas corretas, exigindo coleta de informações relevantes, justificativa, documentação e comunicação eficaz com os stakeholders adequados [1].

A decisão arquitetural deve ser documentada porque sem capturar essas decisões perde-se o conhecimento sobre as concessões feitas em um contexto específico; sem esse conhecimento, a equipe fica impedida de suportar a evolução de longo prazo do produto de software [3]. A documentação é essencial para evitar que o raciocínio por trás das soluções se torne conhecimento tácito perdido na cabeça de poucas pessoas e não seja explicitamente capturado, facilitando futuras manutenções ou evoluções [8].

---

## 10. o que é curadoria de acervo?  
*(bloco A)*

**Obras na recuperação:** NOBRADE: Norma brasileira de descrição arquivística; Cartilha de Governança de Dados — Volume III: Papéis e Responsabilidades de Governança de Dados no Poder Executivo Federal; Cartilha de Governança de Dados — Volume I: Conceitos Iniciais; Cartilha do Catálogo Nacional de Dados; Estudo Técnico Preliminar 3/2026 e anexos — Central de Atendimento Multimeios (Contact Center Omnichannel); Decreto nº 4.073/2002 — Regulamentação da Lei nº 8.159/1991 (política nacional de arquivos públicos e privados); ISAD(G): Norma geral internacional de descrição arquivística — Segunda Edição

**Resposta (claude-sonnet-5):**

O acervo não cobre o conceito exato de "curadoria de acervo". As fontes disponíveis tratam de conceitos próximos, mas não do termo composto perguntado:

- A fonte [1] define apenas "acervo" isoladamente, como "totalidade de documentos de uma entidade custodiadora" [1], sem tratar de curadoria.
- A fonte [4] menciona "Curador" como papel na estrutura do Catálogo Nacional de Dados, mas não define "curadoria de acervo" [4].
- A fonte [3] cita "curador do dado" en passant, no contexto de riscos de governança, sem definir o conceito [3].
- A fonte [5] trata de "Curadoria e Gestão de Conteúdos e Processos", mas refere-se a ciclos de atendimento (scripts, roteiros), não a curadoria de acervo documental/arquivístico [5].

Nenhuma fonte define ou trata especificamente do conceito "curadoria de acervo". Não posso completar essa lacuna com conhecimento próprio.

**Resposta (gemma4:12b):**

O acervo não cobre.

**Resposta (qwen3.5:9b):**

O conceito exato de "curadoria de acervo" não é definido nas fontes fornecidas. As fontes tratam de termos relacionados a arquivos (como [1], [8]), governança de dados e curadores de dados ([3], [4]), ou gestão de conteúdos em atendimento ao cliente ([5]), mas nenhuma delas define especificamente o que é "curadoria de acervo". Portanto, com base estrita nas fontes fornecidas, não há resposta para a pergunta.

---

## 11. DDD  
*(bloco B)*

**Obras na recuperação:** Implementing Domain-Driven Design; Domain-Driven Design in Software Development: A Systematic Literature Review on Implementation, Challenges, and Effectiveness

**Resposta (claude-sonnet-5):**

**DDD (Domain-Driven Design)** é uma abordagem de desenvolvimento de software voltada para produzir modelos de software de alta qualidade que expressem explicitamente o objetivo de negócio pretendido [6]. Quando implementado corretamente, o DDD leva o design a refletir exatamente como o software funciona [6].

**Objetivo central**

O propósito do DDD é ajudar equipes a alcançar sucesso na criação de designs de modelos de software de alta qualidade [6].

**Estrutura do livro/tema**

O capítulo introdutório cobre: se o projeto "merece" o investimento em DDD, os motivos para adotá-lo, os alternativos comuns e por que costumam gerar problemas, os fundamentos do DDD, os primeiros passos práticos, e como "vender" DDD para gestão, especialistas de domínio e equipe técnica [6][7]. Um estudo de caso fictício de uma empresa SaaS multitenant, desenvolvendo uma aplicação de gestão de projetos baseada em Scrum, ilustra erros comuns na adoção do DDD e descobertas que ajudam a corrigir o rumo [6].

**Por que fazer DDD**

Colocar especialistas de domínio e desenvolvedores em pé de igualdade produz software que faz sentido para o negócio, não apenas para os programadores — isso significa formar uma equipe coesa, não apenas tolerar o outro grupo [4]. Isso representa investir no negócio, aproximando o software do que os líderes de negócio criariam se fossem eles os programadores [4]. O DDD também ensina mais sobre o próprio negócio à organização, já que ninguém conhece tudo sobre ele — é um processo constante de descoberta, e com DDD todos aprendem porque todos contribuem para as discussões [4]. Centralizar o conhecimento é fundamental para que o entendimento do software não fique preso em "conhecimento tribal", disponível apenas a poucos desenvolvedores [4]. A meta é chegar a zero traduções entre especialistas de domínio, desenvolvedores e o software, por meio de uma linguagem comum e compartilhada [4].

**Valor de negócio (lista enumerada no acervo)**

O capítulo elenca oito pontos de valor de negócio do DDD: 1) a organização ganha um modelo útil de seu domínio; 2) desenvolve-se uma definição refinada e precisa do negócio; 3) especialistas de domínio contribuem para o design do software; 4) obtém-se uma melhor experiência de usuário; 5) fronteiras limpas são colocadas ao redor de modelos puros; 6) a arquitetura corporativa fica melhor organizada; 7) usa-se modelagem ágil, iterativa e contínua; 8) empregam-se novas ferramentas, tanto estratégicas quanto táticas [7].

**Desafios de aplicar DDD**

Os desafios mais comuns são: permitir o tempo e esforço necessários para criar uma Linguagem Ubíqua; envolver especialistas de domínio desde o início e continuamente no projeto; e mudar a forma como os desenvolvedores pensam sobre soluções em seu domínio [8]. Um dos maiores desafios é o tempo e esforço exigidos para pensar sobre o domínio de negócio, pesquisar conceitos e terminologia, e conversar com especialistas para descobrir e aprimorar a Linguagem Ubíqua, em vez de codificar em "tecno-babble" [8]. Também é desafiador obter o envolvimento necessário dos especialistas de domínio — sem o comprometimento de ao menos um especialista real, não se descobre o conhecimento profundo do domínio [8].

**Estrutura tática/estratégica do livro**

Após o capítulo introdutório, os dois capítulos seguintes tratam de design estratégico, seguidos por um capítulo sobre arquiteturas de software com DDD, conteúdo considerado essencial antes de avançar para os capítulos de modelagem tática [5]. Há também um capítulo específico (Chapter 14) sobre a camada de Application, cobrindo renderização de objetos de domínio, DTOs a partir de instâncias de Aggregate, uso de mediador para publicar estado interno de Aggregate, consultas otimizadas de repositório para casos de uso, e lidar com múltiplos clientes distintos [1].

**Pesquisa acadêmica sobre DDD**

Uma revisão sistemática de literatura (SLR) sobre DDD no desenvolvimento de software aponta que há interesse e adoção crescentes de DDD no contexto de microsserviços desde 2017, embora mais pesquisa empírica seja necessária para entender plenamente benefícios e desafios em diferentes cenários [3]. O estudo revela variações na implementação e avaliação dos princípios de DDD entre os trabalhos incluídos [3]. Para melhorar a qualidade da pesquisa em DDD, estudos futuros deveriam focar em uso consistente dos princípios, metodologias de avaliação robustas e discussão aberta de vantagens e limitações [3]. A implementação de DDD depende significativamente da expertise dos stakeholders — desenvolvedores experientes e especialistas de domínio são cruciais para aplicar efetivamente os conceitos e práticas de DDD [3].

**Resposta (gemma4:12b):**

O Design-Driven Domain (DDD) é uma abordagem de desenvolvimento de software que visa ajudar a alcançar modelos de software de alta qualidade, onde o design do software reflete exatamente como ele funciona e expressa a solução para o objetivo de negócio [1].

As principais características e benefícios do DDD incluem:
*   **Alinhamento com o Negócio:** O DDD coloca especialistas de domínio e desenvolvedores em um mesmo nível, criando uma equipe coesa que produz software que faz sentido para o negócio, não apenas para os programadores [4]. Isso elimina a necessidade de traduções entre especialistas, desenvolvedores e o software através do desenvolvimento de uma linguagem compartilhada [4].
*   **Descoberta e Conhecimento:** O processo permite que todos aprendam sobre o negócio por meio de discussões de descoberta, centralizando o conhecimento e evitando que ele fique restrito apenas aos desenvolvedores ("conhecimento tribal") [4].
*   **Valor Organizacional:** A implementação do DDD proporciona à organização um modelo útil de seu domínio, desenvolve uma definição precisa do negócio, permite a contribuição de especialistas no design do software e resulta em melhores experiências para o usuário [7].
*   **Complexidade e Desafios:** O uso de DDD ajuda as equipes a lidarem com a complexidade do domínio [5, 6]. No entanto, exige esforço considerável para criar uma Linguagem Ubíqua (Ubiquitous Language), envolver especialistas continuamente e mudar a forma como os desenvolvedores pensam sobre as soluções no domínio [8].
*   **Contexto de Microserviços:** Há um interesse e adoção crescente do DDD no contexto de microserviços desde 2017 [3].

**Resposta (qwen3.5:9b):**

O acervo não cobre o conceito exato perguntado (DDD), pois as fontes fornecidas tratam de Domain-Driven Design, e não do código postal DDD ou outros significados comuns da sigla. [1][2][3][4][5][6][7][8]

---

## 12. convergência sociotécnica  
*(bloco B)*

**Obras na recuperação:** Architecture Modernization; Sociomateriality: Challenging the Separation of Technology, Work and Organization; Adoção de Tecnologia: Um estudo sobre o uso de software livre nas empresas

**Resposta (claude-sonnet-5):**

O acervo não cobre o conceito exato de "convergência sociotécnica". As fontes [2][4][7] tratam de **sociomaterialidade** — a fusão entre técnico e social como inseparabilidade ontológica — que é um conceito próximo, mas não o mesmo termo nem a mesma formulação teórica de "convergência sociotécnica" [2]. Por regra, não posso usar fonte vizinha para responder pergunta sobre conceito diferente.

Se a pergunta for sobre sociomaterialidade, posso responder com base nessas fontes — só precisa confirmar o redirecionamento.

**Resposta (gemma4:12b):**

O acervo não cobre o conceito exato "convergência sociotécnica". As fontes tratam de "sociomaterialidade" [2], que aborda a fusão e a inseparabilidade entre o técnico e o social [2, 4].

**Resposta (qwen3.5:9b):**

O conceito exato "convergência sociotécnica" não é coberto pelas fontes fornecidas; as fontes tratam do termo relacionado "sociomateriality", que define a inseparabilidade inerente entre o técnico e o social, mas não utiliza especificamente a expressão "convergência sociotécnica". [2]

---

## 13. arquitetura de negócios  
*(bloco B)*

**Obras na recuperação:** BIZBOK Guide; The TOGAF Standard, Version 9.2; Architecture Modernization

**Resposta (claude-sonnet-5):**

Arquitetura de negócios, conforme o acervo, é estruturada em blueprints fundamentais e estendidos: os fundamentais — capability, organization, value e information — são visões relativamente estáveis que formam a essência do negócio; os estendidos — strategy, initiatives, products, stakeholders e policy — são mais dinâmicos e se relacionam com os fundamentais [2].

Essa arquitetura de negócios se articula com modelos de negócio: um business model descreve a lógica de como uma organização cria, entrega e captura valor, e pode ser usado em conjunto com os blueprints de arquitetura de negócios para orientar inovação e resultados organizacionais, com frameworks de modelo de negócio e de arquitetura de negócios alinhados para dar estrutura e linguagem comuns [6].

Do ponto de vista de valor para a organização, a introdução da arquitetura de negócios costuma ser justificada por problemas concretos — falha de comunicação de requisitos entre executivos e times de solução, desalinhamento de terminologia entre stakeholders, informações conflitantes entre unidades de negócio, e dificuldade de sincronizar dados por vocabulário divergente — e o caso de negócio deve manter o foco no valor de negócio ligado às estratégias e prioridades executivas [8].

Quanto ao papel de quem executa essa disciplina, o Business Architecture Practitioner é definido como aquele que aplica arquitetura de negócios para resolver problemas de negócio e entregar valor de negócio [1].

O acervo não cobre, de forma direta e específica, uma definição unificada e completa do conceito "arquitetura de negócios" além do que está fragmentado nessas fontes — não há uma fonte única que sintetize definição, escopo e propósito num só lugar.

**Resposta (gemma4:12b):**

A arquitetura de negócios é composta por visões fundamentais (que incluem capacidade, organização, valor, informação e são consideradas estáveis) e visões estendidas (que incluem estratégia, iniciativas, produtos, partes interessadas e política, sendo mais dinâmicas) [2]. A arquitetura de negócios serve como a base sobre a qual diversas práticas e cenários de arquitetura de negócios são fundamentados [2].

**Resposta (qwen3.5:9b):**

O conceito de arquitetura de negócios é definido como a aplicação da arquitetura de negócios para resolver problemas de negócios e entregar valor [1]. A Parte 2 do guia estabelece o que pode ser chamado de "arquitetura de negócios fundamental", fornecendo princípios, diretrizes e cenários de uso para estabelecer e mapear visões fundamentais e estendidas dos negócios [2]. As visões fundamentais incluem capacidade, organização, valor e informação, enquanto as visões estendidas incluem estratégia, iniciativas, produtos, partes interessadas e política [2]. A arquitetura de negócios pode ser usada em conjunto com modelos de negócios para impulsionar inovação e apoiar resultados organizacionais específicos [6].

---

## 14. vocabulário controlado  
*(bloco B)*

**Obras na recuperação:** ANSI/NISO Z39.19-2005 (R2010), Guidelines for the Construction, Format, and Management of Monolingual Controlled Vocabularies

**Resposta (claude-sonnet-5):**

Vocabulário controlado é usado para melhorar a efetividade de sistemas de armazenamento e recuperação de informação, sistemas de navegação web e outros ambientes que buscam identificar e localizar conteúdo desejado por meio de descrição em linguagem [3]. O propósito primário é alcançar consistência na descrição de objetos de conteúdo e facilitar a recuperação [3][5].

O controle de vocabulário é alcançado por três métodos principais: definir o escopo/significado dos termos; usar a relação de equivalência para ligar termos sinônimos ou quase sinônimos; e distinguir entre homógrafos [2][5].

Há quatro princípios importantes que orientam o design e desenvolvimento do vocabulário controlado: eliminar ambiguidade; controlar sinônimos; estabelecer relações entre termos onde apropriado; e testar e validar termos [6]. Um objetivo central é assegurar que cada conceito distinto seja descrito por uma única forma linguística — se existirem múltiplas formas, elas devem ser controladas ou regularizadas para que o conteúdo não fique disperso sob múltiplos pontos de acesso, mas reunido em um só lugar [6].

Para os fins da norma, "termo" é definido como uma ou mais palavras usadas para representar um conceito, selecionadas da linguagem natural para inclusão em um vocabulário controlado; o termo pode se referir tanto a "termos preferidos" quanto a "termos de entrada" (não-preferidos) [8].

**Resposta (gemma4:12b):**

O objetivo principal do controle de vocabulário é alcançar a consistência na descrição de objetos de conteúdo e facilitar a recuperação [3, 5]. O controle de vocabulário é alcançado por três métodos principais: definir o escopo ou significado dos termos; usar a relação de equivalência para ligar termos sinônimos ou quase sinônimos; e distinguir entre homógrafos [2, 5].

Existem quatro princípios importantes do controle de vocabulário que orientam seu design e desenvolvimento: eliminar ambiguidades, controlar sinônimos, estabelecer relações entre termos quando apropriado e realizar testes e validação de termos [6]. Um objetivo principal é garantir que cada conceito distinto seja descrito por uma única forma linguística; se existirem múltiplas formas, estas devem ser controladas ou regularizadas para que o conteúdo não fique espalhado pelo sistema sob múltiplos pontos de acesso, mas seja reunido em um só lugar [6]. A eliminação de ambiguidades e a compensação da sinonímia garantem que cada termo tenha apenas um significado e que apenas um termo possa ser usado para representar um determinado conceito ou entidade [6].

Vocabulários controlados são geralmente usados para descrever conteúdo atribuindo termos para representar metadados associados a objetos de conteúdo, organizar conteúdos em sites e atividades semelhantes [8]. Para fins deste padrão, um termo é definido como uma ou mais palavras usadas para representar um conceito [8].

**Resposta (qwen3.5:9b):**

O vocabulário controlado é utilizado para melhorar a eficácia de sistemas de armazenamento e recuperação de informações [3]. Seu propósito primário é alcançar consistência na descrição de objetos de conteúdo e facilitar a recuperação [5]. O controle do vocabulário é realizado por três métodos principais: definir o escopo ou significado dos termos; usar as relações de equivalência para vincular termos sinônimos e quase sinônimos; e distinguir entre homógrafos [2][5]. Existem quatro princípios importantes que orientam o design e o desenvolvimento, incluindo eliminar ambiguidade, controlar sinônimos, estabelecer relacionamentos apropriados entre termos e testar/validar termos [6].

---

## 15. continuant e occurrent  
*(bloco B)*

**Obras na recuperação:** Basic Formal Ontology 2.0 — Specification and User's Guide

**Resposta (claude-sonnet-5):**

**Continuant**

Continuant é uma entidade que persiste, perdura ou continua a existir através do tempo mantendo sua identidade [1]. O ramo continuant do BFO 2.0 incorpora continuantes materiais e imateriais, estendidos e potencialmente móveis no espaço, além das regiões espaciais onde se localizam e pelas quais se movem, e suas fronteiras espaciais associadas [1]. Entidades materiais continuant podem preservar sua identidade mesmo ganhando e perdendo partes materiais [1]. Continuants não têm partes temporais no sentido em que occurrents têm — se um occurrent ocupa uma região temporal de 2 minutos, ele é a soma de duas partes temporais não sobrepostas, cada uma de 1 minuto; continuants não se dividem dessa forma [1].

Há axiomas formais: se b é continuant e, para algum t, c é continuant_part de b em t, então c é continuant [1]; e reciprocamente, se b é continuant e, para algum t, c has_continuant_part b em t, então c é continuant [1].

**Occurrent**

Occurrent é uma entidade que se desdobra a si mesma no tempo, ou é a fronteira instantânea de tal entidade (por exemplo um começo ou um fim), ou é uma região temporal ou espaço-temporal que tal entidade ocupa (occupies_temporal_region ou occupies_spatiotemporal_region) [2]. O domínio dos occurrents tem menos unidades naturais que o dos continuants independentes — não há um contraparte natural de "objeto" nesse domínio; em BFO 1.0 "processo" cumpria esse papel, mas em BFO 2.0 "processo" é o contraparte occurrent de "entidade material" [2]. Unidades naturais em occurrents (vidas, jogos de futebol, reações químicas) são tipicamente parasitárias das unidades do lado continuant, ou são fiat [2].

**A dicotomia continuant/occurrent**

Essa dicotomia é o eixo organizador central da ontologia BFO [3]. Deriva em parte de Zemach, que distingue entidades não-continuant ("eventos"), definidas por poderem ser fatiadas ao longo de qualquer dimensão espacial e temporal para gerar partes (por exemplo o primeiro ano da vida de uma mesa) [3]. Já entidades continuant só podem ser fatiadas para gerar partes ao longo da dimensão espacial — por exemplo as pernas, o tampo e os pregos de uma mesa; em relação ao tempo, porém, a coisa é continuant [3]. Um exemplo de instanciação: "2012" instance_of temporal region, e "o nascimento de John" instance_of process (isto é, occurrent) [3].

**Parthood diferenciada por tipo**

O BFO distingue parthood entre continuants e occurrents usando relações explícitas: continuant_part_of (com sufixo "at t", pois a parte pode variar no tempo) versus occurrent_part_of (sem esse sufixo) [4]. Dessa distinção derivam relações inversas e de parte própria: proper_continuant_part_of e has_continuant_part (com "at t") para continuants; proper_occurrent_part_of e has_occurrent_part para occurrents [6].

**Processos não mudam (occurrent)**

Um ponto específico sobre occurrents: processos não mudam, porque processos SÃO mudanças — são as mudanças que ocorrem nos continuants que deles participam [8]. Isso contrasta com continuants (como John e sua qualidade de peso), que podem mudar permanecendo o mesmo objeto ao longo do tempo [8].

**Resposta (gemma4:12b):**

Um continuant é uma entidade que persiste, perdura ou continua a existir através do tempo enquanto mantém sua identidade [1]. Eles podem incluir regiões espaciais e não possuem partes temporais no sentido de serem divididos em fases sucessivas [1].

Um occurrent é uma entidade que se desenrola no tempo, ou é o limite instantâneo de tal entidade (como um início ou fim), ou é uma região temporal ou espaço-temporal que tal entidade ocupa [2]. Diferente dos continuants, os occurrents são contrastados por se desenrolarem em partes ou fases temporais sucessivas [1].

**Resposta (qwen3.5:9b):**

Um *continuant* é uma entidade que persiste, dura ou continua a existir através do tempo enquanto mantém sua identidade [1]. Em contraste com os *occurrents*, que se desdobram em partes temporais sucessivas ou fases, os continuants não possuem partes temporais nesse sentido; por exemplo, um occurrent pode ocupar uma região temporal de 2 minutos e ser composto por duas partes temporais sobrepostas de 1 minuto cada, enquanto os continuants não têm essa estrutura [1]. Os *occurrents* são entidades que se desdobram no tempo ou representam a fronteira instantânea de tal entidade (como um início ou fim), bem como regiões temporais ou espaço-temporais ocupadas por tais entidades [2]. A dicotomia entre ontologias continuant e occurrent forma o eixo organizador central da ontologia BFO, onde os eventos (*occurrents*) podem ser fatiados ao longo de qualquer dimensão espacial e temporal para produzir partes, enquanto as entidades continuant só podem ser fatiadas apenas na dimensão espacial [3].

---

## 16. proveniência arquivística  
*(bloco B)*

**Obras na recuperação:** ISAD(G): Norma geral internacional de descrição arquivística — Segunda Edição; NOBRADE: Norma brasileira de descrição arquivística

**Resposta (claude-sonnet-5):**

O acervo não traz uma definição autônoma e completa de "proveniência arquivística" como verbete específico, mas o conceito aparece em pontos correlatos:

O termo é usado para definir **fundo**: "Conjunto de documentos de uma mesma proveniência. Termo que equivale a arquivo" [7]. Em contraste, **coleção** é definida como "uma reunião artificial de documentos acumulados com base em alguma característica comum, sem atentar para a sua proveniência" [1] — ou seja, a proveniência é justamente o critério que distingue fundo de coleção.

O elemento "Unidades de descrição relacionadas" da ISAD(G) também toca no conceito, ao orientar que se registre "informação sobre unidades de descrição existentes na mesma instituição custodiadora ou em qualquer outro lugar que sejam relacionadas por proveniência ou outra(s) associação(ões)" [8].

Atenção: não confunda com **Procedência**, que é elemento distinto na ISAD(G) e trata da "origem imediata de aquisição ou transferência da unidade de descrição" [6] — é a última fonte de custódia antes da entrada no arquivo, não o produtor original. O elemento "História arquivística" também é próximo, mas cobre as sucessivas transferências de propriedade, custódia e responsabilidade, não a proveniência em si [3][4].

Não há, nas fontes fornecidas, um verbete de glossário que defina "proveniência" isoladamente com esse rótulo exato — apenas seu uso funcional nas definições acima.

**Resposta (gemma4:12b):**

O acervo não cobre o conceito exato de "proveniência arquivística". As fontes tratam de "Procedência" [4], [6] e mencionam "proveniência" como critério para a formação de um fundo [7] ou para identificar unidades relacionadas [8], mas não definem explicitamente o termo "proveniência arquivística".

**Resposta (qwen3.5:9b):**

Proveniência é a origem imediata de aquisição ou transferência da unidade de descrição [6]. O termo também se refere ao conjunto de documentos que compartilham essa mesma origem [7]. Para unidades adquiridas diretamente do produtor, não deve ser registrada história arquivística, mas sim informação sobre procedência (proveniência) [4].

---

## 17. fusão recíproca de rankings  
*(bloco B)*

**Obras na recuperação:** Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods; AI Engineering (for True Epub); Structured Analytic Techniques for Intelligence Analysis; Pretrained Transformers for Text Ranking: BERT and Beyond; Red-Blooded Risk: The Secret History of Wall Street

**Resposta (claude-sonnet-5):**

Fusão recíproca de rankings — Reciprocal Rank Fusion (RRF) — é um método simples para combinar rankings de documentos vindos de múltiplos sistemas de RI, que consistentemente produz resultados melhores do que qualquer sistema individual e melhores do que o método padrão Condorcet Fuse [1]. O RRF ordena os documentos segundo uma fórmula de escore ingênua baseada no rank recíproco, usando uma constante k que mitiga o impacto de rankings altos por sistemas outliers, evitando que a contribuição de documentos ranqueados mais abaixo desapareça como aconteceria com uma função exponencial [1].

O método foi criado como baseline para busca não supervisionada, atraente por não exigir exemplos de treino [2]. Em experimentos combinando resultados de quatro conjuntos de submissões ao TREC, o RRF superou o Condorcet Fuse em MAP em todos os casos e o CombMNZ em todos exceto um caso, além de superar o melhor ranking individual em quase todos os experimentos, exceto naquele em que o melhor ranking envolvia humano no loop [2].

O RRF é apontado como mais simples e mais eficaz que o Condorcet Fuse, mantendo a propriedade valiosa de combinar ranks sem depender dos escores arbitrários retornados por métodos de ranking específicos [4]. Diferente do Condorcet, no qual uma maioria simples de preferências fracas pode sobrepor-se a preferências mais fortes, o RRF consegue capturar melhor a diversidade dentro de rankings individuais, permitindo que um ou dois sistemas que ranqueiem um documento muito bem melhorem substancialmente sua posição relativa [4]. O RRF também não exige algoritmo especial de votação nem informação global, podendo ter ranks computados e somados um sistema por vez, sem necessidade de manter todos os rankings em memória simultaneamente [4].

**Resposta (gemma4:12b):**

A fusão recíproca de rankings, conhecida como Reciprocal Rank Fusion (RRF), é um método simples para combinar os rankings de múltiplos sistemas de recuperação de informação [1]. O RRF é utilizado como uma base por não exigir exemplos de treinamento e costuma melhorar os resultados em comparação aos melhores sistemas individuais combinados [2]. Além disso, o RRF é considerado mais simples e eficaz do que o Condorcet Fuse, pois combina rankings sem considerar as pontuações arbitrárias retornadas por métodos específicos de ranking [4].

**Resposta (qwen3.5:9b):**

A fusão recíproca de rankings (Reciprocal Rank Fusion - RRF) é um método simples para combinar os rankings de documentos vindos de múltiplos sistemas de recuperação de informação, que consistentemente produz melhores resultados do que qualquer sistema individual ou métodos padrão como Condorcet Fuse [1]. O método ordena os documentos baseando-se em uma fórmula de pontuação ingênua e não requer algoritmos especiais de votação nem informações globais; os rankings podem ser computados e somados um por um, evitando a necessidade de manter todos os rankings na memória [4].

---

## 18. estratégia de chunking  
*(bloco B)*

**Obras na recuperação:** A Simple Guide to Retrieval Augmented Generation; AI Engineering (for True Epub)

**Resposta (claude-sonnet-5):**

A estratégia de chunking (divisão de dados/data splitting) é o processo de quebrar textos longos em segmentos gerenciáveis [1]. Ela é necessária porque endereça os limites de janela de contexto dos LLMs, mitiga o problema de "lost-in-the-middle" em prompts longos e facilita busca e recuperação [5].

**Processo de chunking**, em três etapas: dividir o texto longo em unidades compactas e significativas (frases ou parágrafos); mesclar essas unidades menores em chunks maiores até atingir um tamanho específico, tratando cada chunk resultante como um segmento independente; e, ao criar um novo chunk, incluir parte do chunk anterior no início, para preservar continuidade contextual (overlap) [4] [5].

**Métodos de chunking**: métodos simples predeterminam o tamanho dos chunks e dividem por caracteres; uma técnica um pouco mais refinada divide por tokens; métodos especializados são mais adequados a formatos de dados diferentes; e técnicas experimentais como chunking semântico e chunking agentic estão à frente dos avanços na área [6]. O chunking semântico, proposto por Greg Kamradt, questiona por que ter um tamanho fixo predefinido de chunks e por que os métodos não consideram o significado real do conteúdo — ele analisa a similaridade semântica entre frases para formar grupos [6]. De forma geral, o chunking pode ser fixed size, especializado (ou adaptativo) ou semântico [5].

**Escolha da estratégia**: não há regras fixas para decidir qual método usar (único ou múltiplos), mas certas características da aplicação orientam a escolha [3] [7] [8]:
- Natureza do caso de uso: para sistemas de pergunta-resposta direta, chunks mais curtos tendem a gerar resultados mais precisos; para tarefas de sumarização, chunks mais longos podem fazer mais sentido; se a saída alimenta outra aplicação downstream, isso também influencia a escolha [3].
- Complexidade e tamanho esperado da query do usuário: queries curtas e diretas pedem chunks de tamanho diferente de queries longas e complexas — casar query longa com chunk curto pode ser ineficiente, e query curta com chunk grande pode trazer resultados parcialmente irrelevantes [8].
- Modelo de embeddings: certos modelos de embeddings performam melhor com chunks de tamanhos específicos [7].

Uma estratégia de chunking pode combinar múltiplos métodos, e a escolha deve ser avaliada e ajustada conforme os resultados observados — não é uma tarefa excessivamente complicada, e a maioria dos métodos funciona [5] [7].

**Resposta (gemma4:12b):**

A escolha de uma estratégia de chunking (ou divisão de dados) não possui regras ou diretrizes fixas, mas pode ser guiada por características específicas da aplicação em desenvolvimento [3], [7]. A seleção da estratégia deve basear-se na natureza do conteúdo, no comprimento e complexidade esperados das consultas dos usuários, nos requisitos de caso de uso da aplicação e no modelo de embeddings utilizado [5].

A natureza do caso de uso influencia a escolha: sistemas de perguntas e respostas diretas tendem a utilizar fragmentos (chunks) menores para resultados precisos, enquanto tarefas de sumarização podem se beneficiar de fragmentos maiores [3]. Além disso, o tipo de consulta recebido pelo sistema RAG também determina a estratégia; por exemplo, consultas curtas e diretas exigem tamanhos de fragmentos diferentes de consultas longas e complexas, pois combinar consultas longas com fragmentos curtos ou consultas curtas com fragmentos grandes pode ser ineficiente ou gerar resultados parcialmente irrelevantes [8].

Existem diversos métodos disponíveis, que variam desde técnicas simples (tamanho fixo por caracteres) até métodos mais sofisticados como a divisão por tokens, métodos especializados para diferentes formatos de dados e técnicas experimentais como o "semantic chunking" e "agentic chunking" [6]. Uma estratégia de chunking pode incluir múltiplos métodos [5].

**Resposta (qwen3.5:9b):**

A estratégia de chunking (ou *data splitting*) consiste em dividir textos longos em segmentos gerenciáveis para superar os limites da janela de contexto dos LLMs e mitigar o problema "lost-in-the-middle" [5]. O processo envolve três etapas principais: dividir o texto longo em unidades compactas e significativas (como frases ou parágrafos), fundir essas unidades menores até atingir um tamanho específico, e incluir uma parte do chunk anterior no início de cada novo chunk para preservar a continuidade contextual [4][5]. Existem diferentes métodos disponíveis, incluindo *fixed size* (tamanho fixo), especializado (*specialized*), semântico (*semantic*) e agêntico (*agentic*). A escolha da estratégia deve considerar a natureza do conteúdo, o comprimento esperado e a complexidade das consultas dos usuários, os requisitos de uso do aplicativo e o modelo de embeddings utilizado [5][8]. Para sistemas de resposta direta a perguntas, chunks menores são preferíveis para resultados precisos, enquanto tarefas de sumarização podem se beneficiar de chunks maiores [3].

---

## 19. quantização de modelo  
*(bloco B)*

**Obras na recuperação:** LLM Engineer’s Handbook; llama.cpp — formato GGUF e quantização; Quantize with Confidence? An Empirical Study of Quantization for Code Generation; AI Engineering (for True Epub); Can Compressed LLMs Truly Act? An Empirical Evaluation of Agentic Capabilities in LLM Compression

**Resposta (claude-sonnet-5):**

Quantização de modelo é o processo de representar pesos e ativações de uma rede neural usando tipos de dados de menor precisão [3]. Por padrão, os pesos costumam ser armazenados em ponto flutuante de 16 ou 32 bits (FP16/FP32), formato de alta precisão mas com maior custo de memória e computação; a quantização reduz essa pegada de memória e acelera a inferência [3]. Um efeito notável é que modelos maiores (acima de 30 bilhões de parâmetros), quando quantizados para 2 ou 3 bits, podem superar em qualidade modelos menores (7B–13B) mantendo uma pegada de memória comparável [3].

**Técnicas principais**

- **GGUF e llama.cpp**: llama.cpp é uma biblioteca open-source em C++ criada por Georgi Gerganov para inferência de LLMs, sendo a técnica de quantização mais popular, com muitos modelos quantizados disponíveis no Hugging Face Hub [1]. Ao contrário de bibliotecas que dependem de bibliotecas fechadas específicas de hardware como CUDA, llama.cpp roda em uma gama maior de hardware, incluindo CPUs e dispositivos Android, podendo também descarregar camadas para a GPU [1]. O projeto tem seu próprio formato de quantização, o GGUF, que armazena tensores e metadados suportando formatos de 1 a 8 bits de precisão, com convenção de nomenclatura como IQ1_S/IQ1_M (1-bit), IQ2/Q2_K (2-bit), IQ3/Q3_K (3-bit), IQ4/Q4_K (4-bit), Q5_K/Q5_0/1 (5-bit), Q6_K (6-bit) e Q8_0 (8-bit) [1]. O formato GGUF em si é um formato binário projetado para carregamento e salvamento rápidos de modelos, sucessor do GGML, GGMF e GGJT, desenhado para ser inequívoco e extensível [4].

- **GPTQ e EXL2**: são formatos de quantização dedicados a GPUs, sendo mais rápidos que llama.cpp na inferência; EXL2 oferece o maior throughput com sua biblioteca dedicada ExLlamaV2 [2]. Ambos se baseiam no algoritmo GPTQ, que otimiza a quantização de pesos refinando a abordagem Optimal Brain Quantization (OBQ), usando decomposição de Cholesky da inversa da Hessiana para estabilidade numérica e processamento em lotes (lazy batch updates) [2]. Enquanto GPTQ é limitado a precisão de 4 bits, EXL2 oferece mais flexibilidade, permitindo bitrates precisos entre 2 e 8 bits por peso e aplicando múltiplos níveis de quantização por camada linear, priorizando pesos mais importantes com bits mais altos — na prática, isso permite rodar modelos de 70B em uma única GPU de 24GB com precisão de 2,55 bits [2].

- **Outras técnicas**: AWQ (Activate-aware Weight Quantization), introduzida por Lin et al. (2023), identifica e protege os pesos mais importantes com base na magnitude de ativação (não de peso), aplicando escalonamento ótimo por canal sem depender de backpropagation, e é bem suportada por engines como TGI, vLLM e TensorRT-LLM [7]. Há também uma tendência de quantização extrema para 1 ou 2 bits; enquanto formatos como EXL2 permitem isso, a qualidade costuma sofrer significativamente, mas algoritmos recentes como QuIP# (Quantization with Incoherence Processing) e HQQ (Half-Quadratic Quantization) preservam melhor o desempenho, especialmente em modelos grandes (acima de 30B) [7].

**Avaliação empírica**

Um estudo empírico investiga o impacto de métodos de quantização de última geração — incluindo GPTQ, AWQ, QuIP#, AQLM, BitsAndBytes e GGUF — sobre a correção funcional e qualidade de código gerado por famílias de modelos de código como Qwen2.5-Coder e CodeLlama, usando os benchmarks McEval e CoderEval, no contexto de frameworks de inferência local como Ollama em hardware com recursos limitados [5]. Outro trabalho aponta que a compressão pós-treinamento (incluindo quantização) reduz custo computacional e de memória em até 4x preservando desempenho em benchmarks padrão como perplexidade, mas destaca que benchmarks existentes ignoram capacidades agênticas (workflow, uso de ferramentas, compreensão de contexto longo), propondo o ACBench como benchmark abrangente para avaliar esse impacto [8].

**Resposta (gemma4:12b):**

Quantização refere-se ao processo de representar os pesos e ativações de uma rede neural utilizando tipos de dados de menor precisão [3]. No contexto de modelos de linguagem de grande escala (LLMs), a quantização foca principalmente em reduzir a precisão dos pesos e ativações para diminuir o uso de memória e acelerar a inferência [3].

Existem diversos formatos e técnicas de quantização:
*   **GGUF:** Um formato de arquivo projetado para carregamento rápido e simplificado, que suporta diversas precisões, desde 1-bit até 8-bit [1]. É utilizado com o projeto llama.cpp, que permite inferência em uma ampla gama de hardwares, incluindo CPUs e dispositivos Android [1].
*   **GPTQ:** Um algoritmo que otimiza a quantização de pesos para LLMs através da refinação da abordagem Optimal Brain Quantization (OBQ) para lidar com matrizes extensas [2]. O GPTQ é limitado à precisão de 4 bits [2].
*   **EXL2:** Um formato dedicado a GPUs que oferece alta taxa de transferência e permite uma precisão altamente customizável, podendo misturar diferentes níveis entre 2 e 8 bits por peso [2].
*   **AWQ (Activation-aware Weight Quantization):** Identifica e protege os pesos mais importantes com base na magnitude da ativação em vez da magnitude do peso [7].
*   **QuIP# e HQQ:** Técnicas de quantização extrema que visam preservar o desempenho de modelos originais, especialmente em regimes de 1 ou 2 bits [7].

A quantização é considerada uma técnica essencial para permitir a implantação prática de modelos em hardwares com recursos limitados [5]. Modelos maiores (acima de 30 bilhões de parâmetros) podem superar modelos menores quando quantizados para 2 ou 3 bits, mantendo um uso de memória comparável enquanto entregam maior qualidade [3, 7]. Além disso, técnicas de compressão pós-treinamento, como a quantização, podem reduzir o tamanho do modelo em até 4 vezes preservando o desempenho em tarefas padrão [8].

**Resposta (qwen3.5:9b):**

Quantização refere-se ao processo de representar os pesos e ativações de uma rede neural usando tipos de dados de menor precisão [3]. No contexto de Grandes Modelos de Linguagem (LLMs), a quantização foca principalmente na redução da precisão dos pesos e das ativações do modelo [3]. Por padrão, os pesos são armazenados em formatos de ponto flutuante de 16 ou 32 bits (FP16 ou FP32), o que oferece alta precisão mas aumenta o uso de memória e a complexidade computacional; a quantização é uma solução para reduzir o footprint de memória e acelerar a inferência [3].

---

## 20. opportunity solution tree  
*(bloco B)*

**Obras na recuperação:** [sem obra] Continuous-Discovery-Habits-Torres.epub; Empowered; Cracking the PM Career; Structured Analytic Techniques for Intelligence Analysis; Measuring and Managing Information Risk; User Story Mapping

**Resposta (claude-sonnet-5):**

Opportunity Solution Tree é uma técnica de descoberta de produto, criada pela coach Teresa Torres, usada para identificar e avaliar múltiplas abordagens de solução para um problema importante [2].

O acervo contém a obra "Continuous Discovery Habits", de Teresa Torres, autora da técnica, mas o sumário disponível [1] não expõe o conteúdo detalhado do conceito — apenas mostra que o capítulo "Mapping the Opportunity Space" faz parte do livro, sem descrever a árvore em si.

Não uso as fontes sobre "opportunity backlog" e discussões de go/no-go de Jeff Patton [6][7][8], pois tratam de um conceito vizinho (backlog de oportunidades em User Story Mapping), não da Opportunity Solution Tree especificamente.

**Resposta (gemma4:12b):**

A "Opportunity Solution Tree" é uma técnica útil para identificar e avaliar múltiplos caminhos (abordagens) para resolver um problema importante [2].

**Resposta (qwen3.5:9b):**

O conceito de "Opportunity Solution Tree" é uma técnica inventada pela coach de descoberta Teresa Torres, utilizada para identificar e avaliar múltiplas abordagens na resolução de um problema importante [2].

---

## 21. posicionamento de produto  
*(bloco B)*

**Obras na recuperação:** Obviously Awesome: How to Nail Product Positioning so Customers Get It, Buy It, Love It

**Resposta (claude-sonnet-5):**

Posicionamento de produto é o processo deliberado de definir o contexto de mercado em que um produto compete, de forma a evidenciar seus benefícios óbvios sobre alternativas [1]. A ideia central é que a maioria dos produtos pode ser posicionada em múltiplos mercados diferentes — o produto não está fadado a permanecer em um mercado onde ninguém reconhece seu valor [6].

**Posicionamento como contexto.** Posicionar um produto funciona como a cena de abertura de um filme: dá ao público as informações básicas para entender o que está diante dele [5]. Sem esse trabalho deliberado, equipes caem em duas armadilhas: ficar presa à ideia original do que o produto deveria ser sem perceber que ele virou outra coisa, ou manter um posicionamento que já foi correto mas que o mercado ao redor mudou [3] [5].

**Vocabulário comum.** Para reposicionar um produto, a equipe precisa abandonar noções pré-concebidas e construir um vocabulário de posicionamento compartilhado, já que o mesmo produto pode ser "muitas coisas para muitos tipos de compradores" [1].

**Dos atributos ao valor.** O processo envolve agrupar atributos e recursos em "temas" de valor, sempre pela perspectiva do cliente — o exercício não é listar cada funcionalidade, mas destacar o que é mais crítico e diferenciado, trazendo esse valor único para o centro [2].

**Categoria e tendências.** Posicionar o produto dentro de uma categoria de mercado estabelecida ajuda o cliente a entender rapidamente do que se trata e se deve considerá-lo; de forma opcional, apoiar-se em tendências relevantes do setor pode reforçar por que o produto importa agora [4].

**Registro e compartilhamento.** Por fim, o posicionamento só é útil se for compartilhado na organização, com aceite de todos, para orientar branding, marketing, vendas, produto e sucesso do cliente — daí a recomendação de documentá-lo, inclusive num "canvas de posicionamento" que relaciona categoria de mercado, alternativas competitivas, atributos, valor e segmentos de cliente [7].

Em suma: bom posicionamento não acontece por padrão — exige deliberação, teste, falha e nova tentativa [6], e a introdução do próprio material reconhece que, apesar de não ser um tema "moderno", ainda é mal compreendido e mal executado por muita gente [8].

**Resposta (gemma4:12b):**

O posicionamento de produto consiste em colocar o produto no contexto de um mercado onde ele possa vencer facilmente por possuir benefícios óbvios sobre as alternativas [1]. O processo envolve identificar os elementos mais críticos que tornam o produto especial e valioso, trazendo esse valor único para o primeiro plano [2].

O posicionamento funciona como a definição de um contexto (semelhante à cena de abertura de um filme) que permite às pessoas entenderem o que é importante [5]. Ele deve ser feito de forma deliberada para evitar que a empresa fique presa em uma única visão limitada do produto, já que a maioria dos produtos pode ser posicionada em múltiplos mercados diferentes [1, 5, 6].

Os principais aspectos do posicionamento incluem:
*   **Contexto de Mercado:** Posicionar o produto em uma categoria estabelecida ajuda os clientes a entenderem rapidamente se devem considerar a compra [4]. O posicionamento deve refletir o contexto atual do mercado, que muda constantemente devido a tecnologias e preferências dos consumidores [3].
*   **Valor para o Cliente:** Em vez de destacar cada pequena característica, o posicionamento foca em agrupar atributos em "temas" de valor que façam sentido para o cliente [2].
*   **Estratégia de Comunicação:** Um bom posicionamento deve ser compartilhado por toda a organização para informar branding, marketing, vendas e decisões de produto [7].

**Resposta (qwen3.5:9b):**

O posicionamento de produto é definido como o ato de colocar uma oferta dentro de uma categoria de mercado que coloca as forças da mesma no seu melhor contexto [4]. Ele funciona como um estabelecimento de contexto, semelhante à abertura de um filme, onde se responde a perguntas básicas para dar sentido ao produto e ajudar os clientes a entenderem rapidamente em qual categoria ele opera [5], [8]. O objetivo é encontrar a posição ideal que coloque o produto no contexto de um mercado onde possa vencer facilmente devido aos benefícios óbvios sobre as alternativas existentes [1]. Além disso, envolve identificar tendências relevantes da indústria para ajudar os clientes a compreenderem por que devem considerar o produto naquele momento específico [4].

---

## 22. avaliação heurística  
*(bloco B)*

**Obras na recuperação:** Information Architecture: For the Web and Beyond; Human Problem Solving: The State of the Theory in 1970; Lei nº 6.880/1980 — Estatuto dos Militares; Threat Modeling: Designing for Security; ABNT NBR ISO/IEC 27701:2019 — Técnicas de segurança — Extensão da ABNT NBR ISO/IEC 27001 e 27002 para gestão da privacidade da informação; Guia de Elaboração de PDTIC do SISP, versão 2.1; Learning Domain-Driven Design

**Resposta (claude-sonnet-5):**

O acervo não cobre o conceito de "avaliação heurística" como método específico (ex.: avaliação de usabilidade por heurísticas, à la Nielsen/Molich).

As fontes disponíveis tratam de temas vizinhos, mas não do conceito exato:
- [1] trata de definição de arquitetura da informação, não de avaliação heurística.
- [2] discute heurísticas de resolução de problemas em cryptarithmetic (Simon), não avaliação heurística como técnica de avaliação.
- [3], [5], [6] tratam de "avaliação" em contextos normativos (segurança, PDTIC, SGPI), sem menção a método heurístico.
- [4] aborda heurísticas para análise de "ceremony" em modelagem de ameaças de segurança, não avaliação heurística de usabilidade/UX.
- [7] e [8] definem heurística no contexto de Domain-Driven Design (regras práticas de decisão arquitetural), não avaliação heurística como técnica formal de avaliação.

Nenhuma dessas fontes cobre o conceito exato perguntado; não vou completar com a fonte vizinha nem com conhecimento próprio.

**Resposta (gemma4:12b):**

O acervo não cobre o conceito de "avaliação heurística". As fontes mencionam apenas o termo "heurística" como uma regra prática para resolução de problemas [7] ou "heurísticas de design" para decisões de software [8], e tratam de "avaliação" em contextos de implementação [3], desempenho [5] ou planejamento de TIC [6].

**Resposta (qwen3.5:9b):**

O conceito de "avaliação heurística" não é coberto pelas fontes fornecidas [1], [2], [3], [4], [5], [6], [7] ou [8]. As fontes tratam de arquitetura da informação, resolução de problemas humanos, modelagem de ameaças com heurísticas específicas (como "Ceremony Analysis"), requisitos de segurança e definições gerais de heurística como regras práticas, mas não descrevem o processo específico chamado de "avaliação heurística".

---

## 23. gestão de incidente  
*(bloco B)*

**Obras na recuperação:** Tecnologia da informação — Técnicas de segurança — Código de prática para a gestão da segurança da informação; Decreto nº 10.748/2021 — Rede Federal de Gestão de Incidentes Cibernéticos; Política de Segurança da Informação e Comunicação do Laboratório Nacional de Computação Científica; Norma Complementar nº 08/IN01/DSIC/GSIPR; Norma Complementar 21/IN01/DSIC/GSIPR

**Resposta (claude-sonnet-5):**

Gestão de incidente aparece no acervo sob duas óticas complementares: a norma de segurança da informação e o arcabouço normativo federal brasileiro.

Pela ABNT NBR ISO/IEC 27002, existe capítulo dedicado — "13 Gestão de incidentes de segurança da informação" [4]. O objetivo declarado é assegurar um enfoque consistente e efetivo à gestão de incidentes, com responsabilidades e procedimentos definidos para o manuseio efetivo de eventos e fragilidades notificados, além de processo de melhoria contínua aplicado às respostas, monitoramento, avaliação e gestão total dos incidentes [2]. Convém que evidências sejam coletadas quando exigidas, para assegurar conformidade legal [2].

O detalhamento de responsabilidades e procedimentos consta em 13.2.1: convém estabelecê-los para respostas rápidas, efetivas e ordenadas, usando notificação de eventos e monitoramento de sistemas/alertas/vulnerabilidades para detecção [1]. Os tipos de incidentes a manusear incluem falhas de sistemas e perda de serviços, código malicioso, negação de serviço (denial of service), erros por dados incompletos ou inconsistentes, violações de confidencialidade e integridade, e uso impróprio de sistemas [1]. Os procedimentos também devem considerar análise e identificação da causa, retenção, planejamento de ação corretiva, comunicação com afetados/envolvidos na recuperação, e notificação à autoridade apropriada, com trilhas de auditoria e evidências coletadas e protegidas [1].

No âmbito da administração pública federal brasileira, o Decreto nº 10.748/2021 institui a Rede Federal de Gestão de Incidentes Cibernéticos, de participação obrigatória para órgãos e entidades da administração direta, autárquica e fundacional, e voluntária para empresas públicas e sociedades de economia mista federais; a Secretaria de Governo Digital participa como órgão central do Sisp [3]. A finalidade da Rede é aprimorar e manter a coordenação entre órgãos para prevenção de incidentes [3].

Complementarmente, a Norma Complementar nº 08/GSIPR trata do gerenciamento de incidentes de segurança em redes de computadores como tema que requer atenção da alta administração dos órgãos e entidades da APF, com a troca de informações entre ETIR (Equipes de Tratamento e Resposta a Incidentes) e a CGTIR permitindo intercâmbio científico-tecnológico, apoio ao gerenciamento e tratamento de incidentes, monitoramento e análise técnica com criação de métricas/alertas, avaliação de danos e capacitação no tratamento de incidentes [7].

Já a Norma Complementar nº 21/GSIPR situa a gestão de incidentes dentro do processo mais amplo de Gestão da Segurança da Informação e Comunicações, que abrange registro de eventos, coleta e preservação de evidências de incidentes em redes computacionais, incluindo identificação das causas e o tratamento dos incidentes [8].

O acervo não cobre, dentro das fontes fornecidas, um procedimento operacional passo a passo de resposta a incidente (playbook) além do que está descrito nesses trechos.

**Resposta (gemma4:12b):**

A gestão de incidentes de segurança da informação deve contar com responsabilidades e procedimentos estabelecidos para garantir respostas rápidas, efetivas e ordenadas [1]. O objetivo é assegurar que um enfoque consistente e efetivo seja aplicado à gestão desses incidentes [2].

Os procedimentos de gestão devem ser estruturados para lidar com diversos tipos de incidentes, tais como: falhas de sistemas e perda de serviços; código malicioso; negação de serviço (denial of service); erros por dados incompletos ou inconsistentes; violações de confidencialidade e integridade; e uso impróprio de sistemas [1].

Além dos planos de contingência, os procedimentos devem considerar a análise e identificação da causa do incidente, retenção, planejamento e implementação de ações corretivas para evitar repetições, comunicação com afetados ou envolvidos na recuperação, e notificação à autoridade apropriada [1]. É necessário que evidências e trilhas de auditoria sejam coletadas e protegidas [1].

O processo de gestão também envolve o monitoramento de sistemas, alertas e vulnerabilidades para detecção de incidentes [1], além do registro de eventos, coleta e preservação de evidências (incluindo identificação de causas e tratamento) [8]. Deve-se aplicar um processo de melhoria contínua às respostas, ao monitoramento, à avaliação e à gestão total dos incidentes [2].

A troca de informações sobre o gerenciamento de incidentes em redes de computadores permite promover o intercâmbio científico-tecnológico, apoiar órgãos na gestão e tratamento, monitorar e analisar tecnicamente os incidentes para criação de métricas/alertas, implementar mecanismos de avaliação de danos e contribuir para a capacitação no tratamento desses incidentes [7].

**Resposta (qwen3.5:9b):**

A gestão de incidente envolve estabelecer responsabilidades e procedimentos para assegurar respostas rápidas, efetivas e ordenadas [1]. O processo abrange atividades como registro de eventos, coleta e preservação de evidências, identificação das causas e tratamento dos incidentes [8]. Além disso, deve-se considerar diretrizes que incluem análise da causa do incidente, retenção de informações, planejamento de ação corretiva para prevenir repetição e comunicação com os afetados ou envolvidos na recuperação [1]. A participação em redes federais de gestão pode ser obrigatória para órgãos públicos ou voluntária por adesão no caso de empresas públicas e sociedades de economia mista [3].

---

## 24. gestão de mudança  
*(bloco B)*

**Obras na recuperação:** ISO 31000:2018 — Risk management — Guidelines; Guia Livre: Referência de Migração para Software Livre do Governo Federal, Versão 1.0; Tecnologia da informação — Técnicas de segurança — Código de prática para a gestão da segurança da informação; DAMA-DMBOK: Data Management Body of Knowledge; Data Governance (2nd); CompTIA Security+ Certification Study Guide: Network Security Essentials

**Resposta (claude-sonnet-5):**

Gestão de mudança é um processo estruturado para executar e registrar alterações durante o desenvolvimento de software e a operação de sistemas [7]. Trata-se de parte essencial da criação de uma estrutura de governança e controle viável, com relevância para conformidade regulatória como a Lei Sarbanes-Oxley [7].

No contexto de segurança da informação, convém que modificações nos recursos de processamento da informação e sistemas sejam controladas, com sistemas operacionais e aplicativos sujeitos a rígido controle de gestão de mudanças [3]. Os itens que convém serem considerados incluem: identificação e registro das mudanças significativas; planejamento e testes das mudanças; avaliação de impactos potenciais, incluindo impactos de segurança; procedimento formal de aprovação das mudanças propostas; comunicação dos detalhes das mudanças para todas as pessoas envolvidas; e procedimentos de recuperação para casos de insucesso ou eventos inesperados [3]. Convém também que sejam estabelecidos procedimentos e responsabilidades gerenciais formais para garantir controle satisfatório de todas as mudanças em equipamentos, software ou procedimentos, mantendo-se registro de auditoria com as informações relevantes [3]. O controle inadequado de modificações é apontado como causa comum de falhas de segurança ou de sistema, especialmente na transferência de um sistema em desenvolvimento para o estágio operacional [3].

Para serviços terceirizados, o gerenciamento de mudanças precisa levar em conta tanto mudanças feitas pela organização (melhorias de serviços, novas aplicações, modificações de políticas, novos controles de segurança) quanto mudanças em serviços de terceiros (melhorias em redes, novas tecnologias, novos produtos, novas ferramentas e ambientes de desenvolvimento, mudanças de localização física e de fornecedores) [4]. Essa gestão deve levar em conta a criticidade dos sistemas e processos de negócio envolvidos e a reanálise/reavaliação de riscos [4].

Há também a dimensão humana da gestão de mudança: os itens de change management endereçam o aspecto das pessoas, e conseguir que elas lidem com o elemento emocional de adotar uma disciplina antes inexistente é central — mudanças de comportamento decorrem mais de experiências emocionalmente marcantes do que de fatos ou dados [8]. Recomenda-se seguir planos de treinamento e comunicação e monitorar continuamente a efetividade dos processos, com coleta frequente de métricas [8].

O acervo não cobre gestão de mudança como disciplina formal (frameworks como ADKAR, Kotter em detalhe, ou metodologias específicas de change management corporativo) além do que consta nessas quatro fontes.

**Resposta (gemma4:12b):**

A gestão de mudanças é definida como uma abordagem estruturada para realizar e registrar mudanças durante o desenvolvimento de software e a operação de sistemas [7]. Em ambientes baseados em tecnologia, ela envolve manter o registro dos detalhes do sistema [7] e é considerada essencial para criar uma estrutura de governança e controle viável, além de ser crítica para a conformidade com a Lei Sarbanes-Oxley [7].

No contexto de recursos de processamento de informação e sistemas, a gestão de mudanças deve garantir que modificações sejam controladas, incluindo:
*   Identificação e registro de mudanças significativas;
*   Planejamento e testes das mudanças;
*   Avaliação de impactos potenciais (incluindo segurança);
*   Procedimento formal de aprovação;
*   Comunicação dos detalhes para todos os envolvidos;
*   Procedimentos de recuperação em caso de insucesso ou eventos inesperados [3].

Para serviços terceirizados, a gestão de mudanças deve considerar a criticidade dos sistemas e processos de negócio, além da reanálise de riscos, abrangendo melhorias de serviços, desenvolvimento de novas aplicações, atualizações de políticas e adoção de novas tecnologias ou fornecedores [4].

Sob a perspectiva do fator humano, os itens de gestão de mudança abordam o aspecto das pessoas, focando em superar a resistência e lidar com o componente emocional da adoção de novas disciplinas [8].

**Resposta (qwen3.5:9b):**

A gestão de mudanças é uma abordagem estruturada para realizar e registrar alterações durante o desenvolvimento de software e a operação do sistema, sendo parte essencial da criação de uma estrutura viável de governança e controle [7]. Ela envolve manter um registro dos detalhes do sistema e considera aspectos como identificação e registro das mudanças significativas, planejamento e testes, avaliação de impactos potenciais (incluindo segurança), aprovação formal, comunicação para todas as pessoas envolvidas e procedimentos de recuperação em caso de insucesso ou eventos inesperados [3]. Para serviços terceirizados, o gerenciamento de mudanças deve levar em conta a criticidade dos sistemas e processos de negócio envolvidos, além da reanálise/reavaliação de riscos, abrangendo melhorias de serviços, desenvolvimento de novas aplicações, modificações de políticas e adoção de novas tecnologias ou produtos [4]. A organização também deve monitorar e adaptar continuamente sua estrutura de gestão para abordar mudanças externas e internas, considerando as capacidades e restrições dos recursos existentes [1].

---

## 25. observabilidade  
*(bloco B)*

**Obras na recuperação:** Observability Engineering; Building Microservices (2nd)

**Resposta (claude-sonnet-5):**

**Observabilidade** é um conceito que tem origem na engenharia de controle: o termo foi cunhado pelo engenheiro Rudolf E. Kálmán em 1960 para descrever sistemas de controle matemáticos, sendo definida como uma medida de quão bem os estados internos de um sistema podem ser inferidos a partir de seus outputs externos [2].

Ao ser adaptado para sistemas de software modernos, o conceito ganha uma definição própria: observabilidade é uma medida de quão bem você consegue entender e explicar qualquer estado em que seu sistema possa entrar, por mais novo ou bizarro que seja, sendo capaz de depurar comparativamente esse estado através de todas as dimensões dos dados de estado do sistema, em uma investigação iterativa e ad hoc, sem precisar definir ou prever essas necessidades de depuração com antecedência [3].

Um dos pilares técnicos dessa definição é o evento estruturado, considerado o bloco fundamental de construção da observabilidade: é preciso obter respostas para qualquer pergunta que se possa fazer, sem antecipar ou prever a necessidade de respondê-la com antecedência, o que exige telemetria coletada em resolução total, no nível de granularidade mais baixo possível, mantendo o contexto em que foi coletada [4].

A observabilidade não deve ser confundida com monitoramento: monitoramento é algo que se *faz* — você observa o sistema e, tradicionalmente, precisa pensar com antecedência no que pode dar errado para definir mecanismos de alerta. Já a observabilidade é uma característica *do* sistema — a extensão em que se pode entender o estado interno de um sistema a partir de seus outputs externos, exigindo uma compreensão mais holística do software como um todo, não como um conjunto de entidades separadas [6].

Essa distinção também é reforçada quanto ao uso indevido do termo: observabilidade tem sido erroneamente tratada como sinônimo de "monitoramento" ou "telemetria de sistema", quando na verdade é uma característica do software que só pode ser efetivamente utilizada em sistemas de produção quando as equipes adotam novas práticas que sustentam seu desenvolvimento contínuo — tornando sua introdução tanto um desafio técnico quanto cultural [7].

Do ponto de vista de debugging, ferramentas de observabilidade incentivam a coleta de telemetria rica para cada evento possível, com o contexto completo de cada requisição, permitindo interrogar os dados de forma arbitrária: você faz uma pergunta que não precisou prever de antemão, e a resposta leva à próxima pergunta, repetidamente, até encontrar a causa do problema. Essa capacidade é chamada de explorabilidade — a medida de quão bem se pode investigar iterativamente e entender qualquer estado do sistema, mesmo um nunca visto antes, sem prever esse estado com antecedência [8].

Por fim, observabilidade não é um estado que se "alcança" de uma vez, como um checkbox — assim como segurança ou testabilidade, é uma prática contínua e uma responsabilidade compartilhada por quem desenvolve e opera um serviço em produção. Sistemas de produção são sociotécnicos: primeiro a observabilidade existe como capacidade técnica mensurável (o sistema pode ou não ser observado); depois, o sucesso é medido por quão bem equipes e sistema operam juntos, já que ter a capacidade técnica não garante que o sistema esteja sendo observado de forma eficaz [1].

**Resposta (gemma4:12b):**

A observabilidade pode ser definida de diferentes formas dependendo do contexto:

*   **Em sistemas de controle (definição original):** É uma medida de quão bem os estados internos de um sistema podem ser inferidos a partir do conhecimento de suas saídas externas [2].
*   **Para sistemas de software:** É uma medida de quão bem você pode entender e explicar qualquer estado em que seu sistema possa entrar, independentemente de quão novo ou bizarro ele seja [3, 4]. Isso implica na capacidade de depurar esse estado através de diversas dimensões de dados de forma iterativa e ad hoc, sem a necessidade de prever ou definir essas necessidades de depuração antecipadamente [3, 4]. Se for possível entender qualquer estado incomum sem precisar enviar novos códigos, o sistema possui observabilidade [3].
*   **Como prática e característica:** A observabilidade é uma característica dos sistemas de software que, quando adotada como uma prática contínua (e não apenas um checklist técnico), permite que as equipes desenvolvam, operem, depurem e relatem seus sistemas de forma eficaz [1]. Ela envolve a capacidade de explorar o sistema de maneira aberta, permitindo responder a perguntas arbitrárias sobre seu comportamento [1, 8].
*   **Diferença entre Observabilidade e Monitoramento:** Enquanto o monitoramento é uma atividade que geralmente foca em prever o que pode dar errado e definir alertas para esses eventos específicos, a observabilidade foca na capacidade de entender o estado interno do sistema através de saídas externas para investigar problemas rapidamente [6]. A observabilidade não deve ser confundida com apenas "telemetria" ou "monitoramento", pois envolve desafios técnicos e culturais para que as equipes possam interrogar os dados de forma exploratória [7].

**Resposta (qwen3.5:9b):**

Observabilidade é uma medida de quão bem você pode entender e explicar qualquer estado em que seu sistema possa entrar, seja ele novo ou bizarro [3]. Ela permite investigar condições arbitrariamente sem precisar prever as necessidades de depuração com antecedência [4]. A observabilidade também se refere à capacidade de inferir o estado interno do sistema a partir das suas saídas externas [6].

---

## 26. trunk-based development  
*(bloco B)*

**Obras na recuperação:** Accelerate: State of DevOps 2023; Accelerate: State of DevOps 2022; State of DevOps Report 2016; Accelerate: State of DevOps 2019; State of DevOps Report 2017; Building Microservices (2nd); Accelerate: The Science of Lean Software and DevOps; Accelerate: State of DevOps 2021

**Resposta (claude-sonnet-5):**

Trunk-based development é a prática de mesclar código continuamente no trunk (branch principal), evitando feature branches de vida longa [2][6]. É considerada complementar à integração contínua e demonstra, ao longo de anos de pesquisa, acelerar a velocidade de entrega de software [2].

**Definição e mecânica**

A prática consiste em todos os desenvolvedores fazerem check-in na mesma "trunk" do código-fonte; para evitar que mudanças incompletas afetem outros, usam-se técnicas como feature flags para "esconder" trabalho não finalizado [6]. Isso se opõe ao feature branching, em que o trabalho isolado em branches atrasa a integração e gera merges mais complexos quando finalmente ocorrem [6].

**Evidências de impacto no desempenho**

A pesquisa da Accelerate mostrou que desenvolver a partir do trunk/master, em vez de branches de longa duração, correlaciona-se com maior desempenho de entrega de software [7]. Times de melhor desempenho apresentavam: menos de três branches ativos a qualquer momento, branches com vida muito curta (menos de um dia) antes de serem mescladas ao trunk, e nunca tinham períodos de "code freeze" ou estabilização [7]. Esses resultados são independentes de tamanho de time, tamanho de organização ou indústria [7].

O relatório de 2017 confirma achados similares: mesclar código no trunk diariamente, branches ou forks com vida muito curta (menos de um dia), e menos de três branches ativos contribuem para maior desempenho de entrega [5]. Times sem períodos de "code lock" também apresentaram desempenho superior [5].

**Contraponto ao GitHub Flow**

Apesar das evidências, alguns desenvolvedores acostumados ao workflow recomendado pelo GitHub — que depende fortemente de desenvolvimento em branches com merges periódicos ao trunk — permanecem céticos [5][7]. A pesquisa argumenta que trabalhar em branches curtas, mescladas ao trunk pelo menos diariamente, é consistente com práticas de integração contínua amplamente aceitas [5][7].

**Papel da experiência (achado de 2022)**

O relatório de 2022 aponta que a experiência do profissional importa na implementação: indivíduos com 16+ anos de experiência que usam trunk-based development percebem os benefícios da prática — maior desempenho geral de entrega, menos trabalho não planejado, menos propensão a erros e menor taxa de falha em mudanças [2]. Já profissionais com menos experiência tendem a ver resultados menos positivos, incluindo desempenho geral de entrega reduzido [2]. Isso é atribuído às práticas adicionais necessárias para implementar a técnica com sucesso — como regras rigorosas contra deixar o trunk quebrado sem correção e uso de gated code branches com rollback automático quando o trunk quebra [2].

**Posição no conjunto de capacidades técnicas DevOps**

O relatório DORA de 2021 lista trunk-based development como uma das capacidades técnicas medidas, ao lado de arquitetura fracamente acoplada, testes contínuos e integração contínua [8].

**Resposta (gemma4:12b):**

Trunk-based development é a prática de integrar continuamente o código ao "trunk" (tronco) e evitar ramos de funcionalidades de longa duração (long-lived feature branches) [2]. Esta prática é considerada um complemento à integração contínua e tem sido demonstrada por anos como um fator que acelera a velocidade de entrega de software [2].

A técnica consiste em todos trabalharem a partir do mesmo "trunk" de código; para evitar que trabalhos incompletos impactem outros usuários, utilizam-se técnicas como *feature flags* [6]. O desenvolvimento baseado em trunk está correlacionado com melhor desempenho de entrega (como menor tempo de entrega e maior frequência de implantação) e menores taxas de falha de alteração [7].

As práticas que contribuem para um melhor desempenho na entrega de software incluem:
*   Mesclar código no tronco diariamente [5].
*   Ter ramos ou *forks* com vidas muito curtas (menos de um dia) [5].
*   Ter menos de três ramos ativos em qualquer momento [5, 7].

Equipes que utilizam trunk-based development e possuem mais experiência (16+ anos) tendem a perceber benefícios como aumento no desempenho da entrega, redução de trabalho não planejado, menor propensão a erros e menor taxa de falha de alteração [2]. Além disso, o uso desta prática é identificado como uma das capacidades técnicas do DevOps que prediz o sucesso da entrega contínua [8].

**Resposta (qwen3.5:9b):**

Trunk-based development é a prática de mesclar continuamente código no trunk e evitar branches de funcionalidade com longa duração [2]. Essa abordagem contribui para um aumento geral do desempenho da entrega de software, redução das quantidades de trabalho não planejado, diminuição da propensão a erros e redução da taxa de falha nas alterações [2]. Equipes que desenvolvem fora do trunk/master em vez de usar branches de funcionalidade com longa duração apresentam maior desempenho na entrega de software; essas equipes possuem menos de três branches ativas simultaneamente, suas branches têm vida muito curta (menos de um dia) antes de serem mescladas no trunk e nunca passam por períodos de "congelamento" ou estabilização do código [7].

---

## 27. feature flag  
*(bloco B)*

**Obras na recuperação:** Building Microservices (2nd); AWS Well-Architected Framework; Architecture Modernization; Developing with PDF: Dive Into the Portable Document Format; Lean Inception; CIS Google Cloud Platform Foundation Benchmark; The Site Reliability Workbook

**Resposta (claude-sonnet-5):**

Feature flag (também chamado feature toggle) é um mecanismo que permite esconder funcionalidade já implantada, ligando ou desligando o acesso a ela sem novo deploy [1]. É usado principalmente em trunk-based development, permitindo que código incompleto seja versionado e implantado mas mantido oculto dos usuários finais [1].

Além de ligar/desligar por completo, o flag pode ter granularidade fina, variando o estado conforme o usuário que faz a requisição — por exemplo, liberar a feature para um grupo de beta testers enquanto o restante ainda vê a feature desligada, o que ajuda a implementar um canary rollout [1]. Existem soluções gerenciadas como LaunchDarkly e Split, mas é possível começar com algo simples, como um arquivo de configuração, e evoluir depois [1].

No contexto de decomposição de monolito, o feature toggle também serve para alternar entre duas implementações de uma mesma funcionalidade — por exemplo, entre a versão que ainda vive no monolito e a nova versão extraída para um microsserviço, podendo ser implementado na camada de proxy do padrão strangler fig [2].

As demais fontes fornecidas não tratam do conceito de feature flag/toggle: [3] trata de cultura organizacional e patrocínio executivo, [4] trata de plataformas internas de desenvolvedor e golden paths, [5] trata de campos de texto rico em PDF, [6] define "feature" no sentido de funcionalidade de produto (não de flag), [7] trata de "trace flag" de banco de dados SQL Server, e [8] trata de fundamentos de SRE — nenhum cobre o conceito exato perguntado.

**Resposta (gemma4:12b):**

Feature flags (também conhecidas como feature toggles) são mecanismos que permitem ocultar funcionalidades implantadas atrás de um interruptor que pode ser usado para ligar ou desligar a funcionalidade [1]. Elas podem ser usadas para permitir que funcionalidades ainda não finalizadas sejam enviadas e implantadas, mas permanecendo ocultas para os usuários finais, sendo comumente utilizadas em desenvolvimento baseado em tronco (trunk-based development) [1]. Além disso, podem servir para ativar uma funcionalidade em um momento específico, desativar uma funcionalidade que esteja causando problemas ou permitir estados diferentes baseados no perfil do usuário, como em testes beta ou lançamentos canários [1].

Uma feature toggle também é definida como um mecanismo que permite alternar entre duas implementações diferentes de uma mesma funcionalidade [2]. Esse padrão é considerado útil para transições de microsserviços, permitindo a alternância entre a funcionalidade existente em um monólito e a nova versão em um microsserviço [2].

**Resposta (qwen3.5:9b):**

Feature flags, também conhecidos como feature toggles, são mecanismos que permitem ocultar funcionalidades implantadas atrás de um interruptor que pode ser usado para ligar ou desligar a funcionalidade [1]. Eles são frequentemente usados no desenvolvimento baseado em trunk (trunk-based development), onde funcionalidades não concluídas podem ser verificadas e implantadas, mas ainda ocultas dos usuários finais [1]. Além disso, feature toggles permitem alternar entre duas implementações diferentes de alguma funcionalidade ou desligar uma característica que está causando problemas [2].

---

## 28. teste de contrato  
*(bloco B)*

**Obras na recuperação:** Instrução Normativa SGD/ME nº 94, de 23 de dezembro de 2022; INOVAÇÃO ABERTA E JUSTIÇA DIGITAL: transformação disruptiva do Judiciário por meio da colaboração com empresas startups; Análise dos modelos e contratos de desenvolvimento de software na administração direta do governo federal: a crise na produção de software e as alternativas à fábrica de software; Termo de Referência 32/2026; Estudo Técnico Preliminar da Contratação — registro de preços para licenças de aplicativos, softwares e sistemas operacionais Microsoft; Acórdão 2569/2018-TCU-Plenário — Relatório de Auditoria, SETIC (TC 030.236/2016-9)

**Resposta (claude-sonnet-5):**

O acervo não cobre o conceito exato de "teste de contrato" (contract testing, no sentido de teste automatizado de integração entre serviços/APIs). As fontes fornecidas tratam de temas distintos: obrigações contratuais em contratações de TIC [1], marco legal de startups [2], métricas de gravidade de eventos em modelos de desenvolvimento [3], termo de referência para aquisição de software [4], comparação de modelos de licenciamento [5][6], entrevistas sobre modelos de contrato de desenvolvimento [5][7] e auditoria sobre práticas comerciais de licenciamento [8]. Nenhuma delas aborda teste de contrato como prática ou técnica de teste de software.

**Resposta (gemma4:12b):**

O processo de teste das soluções surgidas a partir de desafios abertos a startups deve ser padronizado e contar com métricas claras de sucesso ou falha de teste, além do prazo de duração do teste [2].

**Resposta (qwen3.5:9b):**

O acervo não cobre informações sobre testes de contrato.

---

## 29. cryptoperiod  
*(bloco B)*

**Obras na recuperação:** nist.sp.800-57pt1r5; CISSP All-in-One Exam Guide; Serious Cryptography; ISC2 CISSP Certified Information Systems Security Professional Official Study Guide; ISO/IEC 27002:2013 — Information technology — Security techniques — Code of practice for information security controls; Transição Brasileira para a Prontidão Pós-Quântica (PQC) e Soberania Digital

**Resposta (claude-sonnet-5):**

O acervo não cobre o conceito específico de cryptoperiod (período de tempo definido durante o qual uma chave criptográfica específica está autorizada para uso).

As fontes disponíveis tratam de temas correlatos, mas não do conceito exato:

- A fonte [1] é apenas um sumário/índice do NIST SP 800-57 Part 1 — publicação que trata de key management e teria a definição formal de cryptoperiod —, mas o conteúdo indexado não traz a definição em si, só títulos de seções [1].
- As fontes [2] e [4] tratam de "cryptographic life cycle" (ciclo de vida criptográfico), que é um conceito relacionado mas distinto de cryptoperiod — o ciclo de vida trata da obsolescência de algoritmos ao longo do tempo, não do período de validade de uma chave específica [2][4].
- As demais fontes ([3], [5], [6], [7], [8]) não abordam nem o conceito de cryptoperiod nem o de ciclo de vida criptográfico de forma direta.

Não é possível responder pela fonte vizinha (life cycle) como se fosse cryptoperiod — são conceitos diferentes no vocabulário técnico de gestão de chaves.

**Resposta (gemma4:12b):**

O acervo não cobre.

**Resposta (qwen3.5:9b):**

O acervo não cobre o conceito exato de "cryptoperiod". Nenhuma das fontes fornecidas define ou discute especificamente esse termo; as fontes tratam do ciclo de vida criptográfico [2], [4] e cronogramas de migração para pós-quântica, mas sem mencionar a duração específica da validade de uma chave (cryptoperiod).

---

## 30. nível de garantia de autenticação  
*(bloco B)*

**Obras na recuperação:** NIST SP 800-63B-4 — Authentication; NIST SP 800-63-4 — Digital Identity Guidelines; Solving Identity Management in Modern Applications; NIST SP 800-63A-4 — Identity Proofing; Guia Livre: Referência de Migração para Software Livre do Governo Federal, Versão 1.0; Manual de Condutas Técnicas 11 — Volume II: procedimentos de ensaios para avaliação de conformidade aos requisitos técnicos de softwares de AC e AR no âmbito da ICP-Brasil

**Resposta (claude-sonnet-5):**

O acervo cobre o conceito de "nível de garantia de autenticação" (Authentication Assurance Level).

O NIST SP 800-63B define que o documento "provides requirements to credential service providers (CSPs) for remote user authentication at each of three authentication assurance levels (AALs)" [1]. Ou seja, existem três níveis formais de garantia de autenticação (AALs) estabelecidos pela norma [1].

De forma complementar, há uma explicação ilustrativa do conceito: quando um usuário autentica, cria-se uma sessão autenticada com um certo nível de garantia de que o usuário é o legítimo dono da conta [3]. O exemplo dado mostra que login com senha estática pode ser considerado "nível um", enquanto autenticação subsequente com um fator mais forte, como senha de uso único gerada no celular, eleva a confiança para um "nível dois" — sendo esses nomes um exemplo arbitrário para fins de ilustração, não a nomenclatura formal do NIST [3]. Esse mesmo trecho descreve que autenticação step-up é o processo de autenticar com uma forma mais forte para elevar o nível de garantia de uma sessão já existente, e que políticas de autorização podem exigir um nível de garantia específico para liberar acesso a recursos ou transações de maior risco [3].

**Resposta (gemma4:12b):**

Quando um usuário se autentica, uma sessão autenticada é criada com um determinado nível de garantia de autenticação (authentication assurance) de que o usuário é o proprietário legítimo da conta [3]. Por exemplo, o uso de uma senha estática pode ser considerado como "nível um", enquanto a utilização de uma forma mais forte de autenticação, como uma senha de uso único (OTP), resulta em um nível de confiança muito maior, podendo ser considerado como "nível dois" [3]. O processo de autenticação progressiva (step-up authentication) é utilizado para elevar o nível de garantia de autenticação de uma sessão existente ao exigir formas mais fortes de autenticação para acessar recursos ou realizar transações que envolvam mais risco [3].

**Resposta (qwen3.5:9b):**

O acervo não cobre o conceito exato perguntado. As fontes fornecidas mencionam "níveis" de garantia (como AALs ou níveis arbitrários de exemplo) [3], mas nenhuma fonte define especificamente um valor numérico, escala padrão ou definição técnica para o "nível de garantia de autenticação".

---

## 31. gestão de acesso privilegiado  
*(bloco B)*

**Obras na recuperação:** Tecnologia da informação — Técnicas de segurança — Código de prática para a gestão da segurança da informação; ABNT NBR ISO/IEC 27701:2019 — Técnicas de segurança — Extensão da ABNT NBR ISO/IEC 27001 e 27002 para gestão da privacidade da informação; OSIC 15/2024 — Normatização e regulação de tecnologias emergentes no contexto da cibersegurança; ISO/IEC 27002:2013 — Information technology — Security techniques — Code of practice for information security controls; CompTIA Security+ Certification Study Guide: Network Security Essentials

**Resposta (claude-sonnet-5):**

Gestão de acesso privilegiado é tratada no acervo como parte do gerenciamento de acesso do usuário, com atenção especial à distribuição de direitos que permitem alterar controles de sistema [1].

**Controle específico de privilégios**: a concessão e o uso de privilégios devem ser restritos e controlados por processo de autorização formal, cobrindo identificação do privilégio por produto de sistema (SO, SGBD, aplicação), concessão conforme necessidade de uso e alinhada à política de controle de acesso, registro de todos os privilégios concedidos, e atribuição a um ID de usuário diferente do usado normalmente para os negócios [6]. O uso inapropriado de privilégios de administrador de sistemas é destacado como fator relevante de falhas de segurança [6].

**Análise crítica periódica**: autorizações para direitos de acesso privilegiado especial devem ser revisadas em intervalos mais frequentes que os direitos de acesso comuns — por exemplo, a cada três meses —, incluindo verificação de alocações de privilégios e registro de modificações em contas privilegiadas para análise crítica [7].

**Extensão para gestão de privacidade**: a ABNT NBR ISO/IEC 27701:2019 remete diretamente ao controle de gerenciamento de direitos de acesso privilegiado da ISO/IEC 27002:2013 (item 9.2.3), aplicando as mesmas diretrizes de implementação ao contexto de SGPI [2][4].

**Perspectiva de gestão pública brasileira**: o desafio apontado é que a gestão inadequada de permissões de usuários eleva o risco de invasão e comprometimento de dados; a solução recomendada é adotar o princípio do menor privilégio (PoLP), concedendo apenas as permissões necessárias pelo tempo necessário, combinado com need to know para informações classificadas, e integrar sistemas de IAM com políticas de auditoria e revisão contínua de acessos [3].

**Gestão de contas e permissões (Security+)**: o acervo cobre privilege management, políticas de senha e controles de segurança e permissões como parte da gestão eficaz de contas, mas a fonte apresentada é apenas o resumo do capítulo, sem detalhamento do conteúdo técnico [8].

**Resposta (gemma4:12b):**

Deve-se dar atenção especial à necessidade de controlar a distribuição de direitos de acesso privilegiado que permitem aos usuários mudar controles de sistemas [1]. O controle, as diretrizes para implementação e outras informações sobre o gerenciamento de direitos de acesso privilegiado seguem as orientações estabelecidas na ABNT NBR ISO/IEC 27002:2013, 9.2.3 [2]. As autorizações para direitos de acesso privilegiado especial devem ser analisadas criticamente em intervalos mais frequentes, por exemplo, em um período de três meses [7].

**Resposta (qwen3.5:9b):**

A gestão de acesso privilegiado envolve assegurar que a distribuição e o uso de privilégios sejam restritos e controlados, com concessão baseada na necessidade de uso [6]. É necessário realizar análise crítica dos direitos de acesso privilegiado em intervalos mais frequentes (por exemplo, a cada três meses) para garantir controle efetivo [7]. Os procedimentos devem cobrir todas as fases do ciclo de vida do usuário, incluindo o cancelamento final quando não houver mais necessidade de acesso [1].

---

## 32. cost of delay  
*(bloco B)*

**Obras na recuperação:** Accelerate: State of DevOps 2018; Investment Valuation; The Principles of Product Development Flow: Second Generation Lean Product Development; Escaping the Build Trap; Essential Kanban Condensed

**Resposta (claude-sonnet-5):**

Cost of Delay (CoD) é um valor numérico que descreve o impacto do tempo sobre os resultados que se deseja alcançar, combinando urgência e valor para medir impacto e priorizar o que deve ser feito primeiro [4].

**Origem e definição central**

Reinertsen chama CoD de "a única coisa" que deveria ser quantificada em desenvolvimento de produto [4]. Segundo o princípio E3 (Quantified Cost of Delay), se você só for quantificar uma coisa, quantifique o cost of delay [6]. Na teoria, seguindo o princípio E1, o CoD seria automaticamente quantificado nos projetos; na prática, 85% das empresas não o quantificam, por isso vale destacar essa sensibilidade específica — não faz sentido trocar dinheiro por tempo de ciclo sem saber o valor econômico desse tempo [6].

**Por que importa**

Nenhuma outra sensibilidade é tão reveladora quanto o CoD: a economia do fluxo é quase sempre dominada pelo custo das filas, e sem quantificar o custo de uma fila no caminho crítico não é possível quantificar o benefício de reduzi-la — e sem quantificar o benefício, não se consegue gerar apoio para mudanças relevantes [6]. O CoD é necessário para avaliar o custo das filas, o valor da capacidade excedente, o benefício de lotes menores e o valor da redução de variabilidade; é descrito como "a chave de ouro que abre muitas portas" [6].

Na conclusão da visão econômica, o CoD é apontado como a regra de decisão que mais transforma o raciocínio, justamente por estar ausente na maioria das empresas hoje — com ela, o custo oculto das filas fica exposto ao entendimento econômico [7].

**Aplicação em priorização de produto**

Melissa Perri trata CoD como seu framework preferido de priorização, à frente de benefits mapping e Kano models: entendendo os resultados estratégicos desejados, o CoD ajuda a determinar o que deve ser entregue mais cedo, combinando urgência e valor em uma medida de impacto [4]. Ela relaciona isso ao trade-off entre escopo e tempo de lançamento — esperar demais por overscoping tem custo de oportunidade (dinheiro que se deixou de ganhar) e risco competitivo [4].

**Relação com filas**

O conceito de CoD conecta-se diretamente ao problema de "cegueira a filas": poucos desenvolvedores percebem que filas são a causa mais importante do desempenho ruim em desenvolvimento de produto, gerando inventário em processo (DIP) alto e ciclos longos [5] — é exatamente esse custo de fila que o CoD permite quantificar [6].

**Resposta (gemma4:12b):**

O "Cost of Delay" (Custo do Atraso) é um valor numérico que descreve o impacto do tempo nos resultados que se deseja alcançar [4]. Ele combina urgência e valor para permitir a medição de impacto e a priorização do que deve ser feito primeiro [4].

O conceito é descrito como "a única coisa" que deve ser quantificada [4]. O Cost of Delay (COD) funciona como uma regra de decisão que permite trazer o custo oculto das filas para o entendimento econômico, permitindo quantificar o impacto econômico de produtos que ficam parados em filas [7]. Além disso, o COD é essencial para avaliar o custo de filas, o valor de capacidade excedente, o benefício de tamanhos de lote menores e o valor da redução de variabilidade [6]. Sem a quantificação do valor do tempo de ciclo (através do COD), não é possível saber se trocas entre tempo de ciclo e redução de incerteza são vantajosas [6].

**Resposta (qwen3.5:9b):**

O conceito de "cost of delay" (custo do atraso) é definido como um valor numérico que descreve o impacto do tempo sobre os resultados desejados, combinando urgência e valor para medir impacto e priorizar tarefas [4]. Ele representa a perda econômica decorrente da espera excessiva ou do ciclo longo de desenvolvimento, onde se troca dinheiro por tempo sem conhecer seu valor econômico [6]. O custo do atraso é considerado uma métrica fundamental no framework econômico de projetos que transforma variáveis proxy em lucros ao longo do ciclo de vida para permitir decisões econômicas sobre filas e capacidade excedente [7].

---

## 33. limite de WIP  
*(bloco B)*

**Obras na recuperação:** Essential Kanban Condensed; The Lean Product Playbook; The Principles of Product Development Flow: Second Generation Lean Product Development; Accelerate: The Science of Lean Software and DevOps

**Resposta (claude-sonnet-5):**

Limite de WIP (work in progress) é um mecanismo de controle de fluxo que restringe quantos itens podem estar em andamento simultaneamente no sistema [6].

**Fundamento quantitativo:** o limite de WIP transforma o sistema de fila de um modelo M/M/1/∞ (sem limite) em M/M/1/k, onde k é o teto máximo de itens permitidos [6]. Ao impor esse limite ocorre um efeito positivo — redução do tempo médio de ciclo — e dois efeitos negativos: rejeição permanente de demanda potencialmente valiosa e redução da utilização de capacidade, pois a demanda rejeitada durante períodos de congestionamento é perdida definitivamente [6]. Um limite relativamente leve, de duas vezes o WIP médio, já produz redução significativa de 28% no tempo de ciclo, com penalidade de apenas 1% em subutilização e custo de bloqueio [6].

**Como agir ao atingir o limite:** o método mais simples é bloquear toda a demanda quando o WIP atinge seu limite superior — é a técnica usada no próprio sistema kanban, análoga ao sinal de ocupado de um sistema telefônico [7]. Isso pode ser feito de duas formas: ejetar o trabalho que chega (impondo um teto rígido de WIP e tempo de ciclo global) ou reter o trabalho em uma fila anterior (o que não reduz a demanda, apenas desloca a localização da fila) — essa segunda abordagem é usada no Toyota Production System, que também aplica restrições de WIP às filas anteriores [7]. Além do bloqueio de demanda, existem outras oito táticas práticas para reagir a excursões de WIP, incluindo descarte de projetos de baixo valor quando o WIP está alto [7][8].

**Serviço diferenciado:** como o fluxo de trabalho em desenvolvimento de produto não é homogêneo — há itens com custos de atraso muito diferentes —, pode fazer sentido subdividir o fluxo em categorias (alto, médio, baixo custo de atraso) e usar a Fórmula de Little para determinar o limite de WIP de cada categoria, obtendo tempos de fluxo diferenciados mesmo compartilhando o mesmo recurso [3].

**No contexto de gestão Lean de software:** limitar o WIP é um dos três componentes centrais das práticas de gestão Lean aplicadas à entrega de software, usado para orientar melhoria de processo e aumentar throughput [5]. Isoladamente, porém, o limite de WIP não prediz fortemente o desempenho de entrega — o efeito forte só aparece quando combinado com painéis visuais e um loop de retroalimentação vindo do monitoramento de produção de volta para as equipes [5].

**No kanban como método:** o acervo trata do kanban de forma mais ampla, cobrindo entendimento compartilhado do trabalho, das regras de execução e de "quanto conseguimos lidar de cada vez" [1], e também descreve o quadro kanban com colunas representando estados do fluxo de trabalho, onde cartões sinalizam a puxada de novos itens [2] — mas nenhuma dessas duas fontes detalha o mecanismo numérico do limite de WIP em si, que está coberto pelas fontes [6][7][3] acima.

**Resposta (gemma4:12b):**

O limite de WIP (Work in Progress) é utilizado para controlar o tempo de ciclo e o fluxo [6]. Ao estabelecer um limite de WIP, cria-se um efeito positivo de redução do tempo médio de ciclo, mas também ocorrem dois efeitos negativos: a rejeição permanente de demandas potencialmente valiosas e a redução da utilização da capacidade devido à perda dessas demandas durante períodos de congestionamento [6].

O uso de limites de WIP serve para garantir que as equipes não fiquem sobrecarregadas (o que pode levar a tempos de entrega mais longos) e para expor obstáculos ao fluxo [5]. Quando combinados com exibições visuais, os limites de WIP ajudam a impulsionar a melhoria do processo e aumentar o rendimento (throughput) [5].

Existem diferentes formas de aplicar esses limites:
*   **Bloqueio de Demanda:** O método mais simples é bloquear toda a demanda quando o WIP atinge seu limite superior, como ocorre no sistema kanban [7]. Isso pode ser feito descartando o trabalho que chega ou retendo-o em uma fila anterior (upstream) [7].
*   **Purga de Projetos:** Quando o WIP está alto, projetos de baixo valor podem ser descartados [7].
*   **Segmentação por Custo de Atraso:** Para fluxos não homogêneos, é possível subdividir o trabalho em categorias e usar a Fórmula de Little para determinar limites de WIP específicos para cada categoria, permitindo diferentes tempos de fluxo para diferentes tipos de tarefas [3].

**Resposta (qwen3.5:9b):**

O limite de WIP (Work In Progress) é definido como o máximo permitido no número de itens em um sistema, onde atingir esse limite superior resulta na rejeição da demanda ou bloqueio de novas chegadas [6]. A aplicação desse limite visa reduzir o tempo médio do ciclo e controlar a fila, embora possa levar à subutilização da capacidade devido ao bloqueio permanente de demandas valiosas durante períodos de congestionamento [6]. O método mais simples para usar uma restrição de WIP é bloquear toda a demanda quando o WIP atinge seu limite superior, conforme utilizado no sistema Kanban e em sistemas telefônicos padrão [7].

---

## 34. role charter  
*(bloco B)*

**Obras na recuperação:** Data Governance (2nd); User Stories Applied: For Agile Software Development; Basic Formal Ontology 2.0 — Specification and User's Guide; Server Administration Guide

**Resposta (claude-sonnet-5):**

O acervo não cobre o conceito exato de "role charter" como unidade única.

Há fontes sobre "charter" de governança de dados (documento que estabelece propósito, escopo, responsabilidades e representação de um programa de DG) [3][4][5], e há fontes sobre "role" em sentidos distintos — papel como entidade realizável dependente de portador (BFO) [6][8], papel de usuário em user stories [2], e operações de papel/role no Keycloak (CLI) [7]. Nenhuma delas trata especificamente de um "role charter" (documento de charter definindo um papel/cargo específico dentro de uma estrutura de governança).

Se a pergunta for sobre o charter de um programa de DG que inclui seção de "Responsibilities" e "Representation" (papéis dos participantes), isso está coberto por [5], que lista essas seções no template de Appendix 3. Mas não há fonte que trate "role charter" como termo ou artefato específico e nomeado.

**Resposta (gemma4:12b):**

O charter é um documento crítico para um programa de governança de dados [3]. Ele possui diversos propósitos, incluindo: estabelecer o framework operacional; documentar o propósito e os objetivos do programa; identificar componentes como conselhos ou patrocinadores; estabelecer o nível de autoridade que os órgãos operacionais de governança terão; identificar o tipo de federação; e identificar os nomes dos participantes [3]. O charter é considerado um documento vivo, que deve se adaptar ao crescimento e às mudanças na governança de dados conforme o programa evolui [3]. Além disso, o propósito do charter pode enfatizar o escopo, descrever se haverá um escritório de governança de dados ou uma estrutura operacional virtual informal, e definir se ele descreve todas as áreas de governança ou apenas uma área específica [4].

**Resposta (qwen3.5:9b):**

O documento de carta (charter) é um documento crítico para um programa de governança de dados que tem como propósitos definir o quadro operacional, documentar os objetivos e identificar componentes como conselhos ou patrocinadores [3]. Ele também estabelece o nível de autoridade dos órgãos operacionais da DG e identifica os tipos de federação e participantes [3]. Em organizações maiores, pode ser necessário uma carta separada para cada "camada" do quadro operacional, incluindo cartas específicas para patrocinadores, conselhos e fóruns [3].

---

