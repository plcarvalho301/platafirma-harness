# Consolidado T0 — recuperação + geração (claude-sonnet-5)

Gerado por `tooling/consolidar-firmabot.py`. Junta `G0-rag-base` (o que o
rag_search devolveu) com `G0-claude-referencia` (o que o gerador respondeu
em cima disso). Lista de obras é só o que apareceu nas fontes — não é
julgamento de qual é "a" fonte certa, isso é da claudinho-IA.

---

## 01. o que é um conceito e qual seu critério de identidade?  
*(bloco A)*

**Obras na recuperação:** Tractatus Logico-Philosophicus; Teoria dos Direitos Fundamentais; Evaluating ontological decisions with OntoClean; Atividade de inteligência nacional brasileira — doutrina; WonderWeb Deliverable D18: Ontology Library (final); Lei nº 6.880/1980 — Estatuto dos Militares; How We Think

**Resposta (claude-sonnet-5):**

Nenhuma das fontes que chegaram cobre, com matéria de fato, o par "conceito + critério de identidade" enquanto par definido — o que existe é aproximação temática incompleta ou trechos sem conteúdo. Vou mostrar o que cada fonte tem e onde ela para.

**A fonte mais próxima do tema, mas cortada antes do ponto**

[3] (503124-503150-2002, "Evaluating Ontological Decisions with OntoClean") é o único material que trata de metodologia para caracterizar conceitos/classes numa ontologia por meio de "metaproperties" formais (transcrito: *"we use these notions to define a set of metaproperties which, in turn, are used to characterize relevant aspects of the intended meaning of the properties, classes, and relations that make up an ontology"*). O trecho anuncia a primeira noção formal a ser discutida — *"Essence and Rigidity"* — e é cortado exatamente aí. Não chega ao ponto em que a metodologia trata de identidade (que no OntoClean é metapropriedade própria, distinta de Rigidez). Então não posso te dar, a partir desta fonte, a definição de critério de identidade — só o entorno metodológico dela.

**Fonte adjacente, sem prosa explicativa**

[5] (D18, "KIF version of DOLCE-Lite+") tem uma definição formal em lógica: `(DEFCONCEPT UNIVERSAL (?SELF)) :=> (CONCEPT ?SELF)`, isto é, CONCEPT como especialização de UNIVERSAL dentro do módulo TOP do DOLCE. É transcrição de axioma, não explicação em prosa do que é um conceito nem de critério de identidade — não dá para derivar definição substantiva daí sem forçar.

**Fontes sem matéria para o pedido**

- [6] (NC20 IN01/DSIC-GSIPR) é só o título "3 Conceitos e Definições" — cabeçalho de seção, sem corpo. Não sustenta afirmação.
- [4] (Doutrina da Atividade de Inteligência) é ficha catalográfica e sumário — não sustenta.
- [1] (Tractatus) é introdução do tradutor sobre a recepção do livro, não trata do conceito de "conceito".
- [7] (Alexy) menciona de passagem "jurisprudência dos conceitos" como momento histórico da Ciência do Direito, sem defini-lo.
- [8] (Dewey, *How We Think*) tem um capítulo chamado "Meaning: or Conceptions and Understanding" que seria pertinente, mas o que chegou é só o sumário do livro — sem conteúdo de matéria.

**Resposta possível, marcada como leitura minha, sem fonte no que chegou**

Como você parece estar perguntando no registro de engenharia ontológica (o que o corpus sugere, dado que a fonte mais próxima é OntoClean): um conceito, nesse campo, é uma categoria/classe usada para agrupar entidades por uma propriedade comum. Critério de identidade é a condição que permite dizer, para qualquer par de instâncias dessa categoria, se são a mesma instância ou instâncias distintas — é o que resolve a pergunta "isto e aquilo são o mesmo X?". No método OntoClean especificamente, ele é uma das metapropriedades formais (ao lado de rigidez, unidade e dependência) usadas para testar se uma classe está bem colocada na hierarquia de subsunção de uma ontologia — mas essa formulação específica não está no trecho que chegou, é conhecimento meu, não das fontes fornecidas.

Se você tiver o trecho do OntoClean que segue depois de "Essence and Rigidity" (a seção de Identity propriamente), me traga que aí cito com breadcrumb e transcrição.

---

## 02. o que distingue um tipo de um papel?  
*(bloco A)*

**Obras na recuperação:** Digital Forensics Processing and Procedures: Meeting the Requirements of ISO 17020, ISO 17025, ISO 27001 and Best Practice Requirements; Teoria dos Direitos Fundamentais

**Resposta (claude-sonnet-5):**

As fontes que chegaram não cobrem o conceito perguntado.

O que temos são trechos de duas obras — uma sobre forense digital (fonte [1], que é só um cabeçalho de apêndice sem matéria) e outra sobre teoria dos direitos fundamentais de Robert Alexy (fontes [2]–[7], tratando de sopesamento, regras/princípios, restrições a direitos fundamentais, igualdade e direitos subjetivos/competências). Nenhuma delas nomeia ou desenvolve a distinção conceitual entre "tipo" e "papel" — nem no sentido de modelagem de dados/domínio, nem em teoria jurídica de "tipo penal" vs. "papel processual", nem em nenhum outro domínio identificável nos breadcrumbs.

Como não há fonte cujo breadcrumb nomeie esse conceito exato, não vou forçar nenhum dos trechos acima a responder por ele — seriam vizinhos semânticos na melhor das hipóteses (ex.: [4] fala de restrição a direito fundamental, [6] fala de competência/sujeição de Hohfeld, mas nenhum define "tipo" vs. "papel" como par conceitual).

Se quiser, posso responder com leitura minha, sem fonte no que chegou — mas aí é conhecimento geral meu, não algo que o acervo sustente. Quer que eu faça isso, e se sim, em que domínio você está pensando (modelagem de dados, RBAC/controle de acesso, teoria jurídica, ontologia)? A distinção muda de conteúdo dependendo do domínio, e não quero adivinhar o seu.

---

## 03. o que é arquitetura de software?  
*(bloco A)*

**Obras na recuperação:** Fundamentals of Software Architecture (2025); [sem obra] Software-Architecture-in-Practice-Bass-Clements-Kazman.pdf; Continuous Architecture in Practice

**Resposta (claude-sonnet-5):**

**Definição**

A arquitetura de software é o conjunto de estruturas necessárias para raciocinar sobre um sistema, compreendendo os elementos de software, as relações entre eles e as propriedades de ambos.

*(Transcrito da fonte [2] — Software Architecture in Practice, Bass/Clements/Kazman, seção "1.1 What Software Architecture Is and What It Isn't")*

O trecho é explícito ao contrastar essa definição com outras que falam em decisões de design "iniciais" ou "principais": os autores argumentam que nem toda decisão arquitetural é tomada cedo (especialmente em projetos ágeis) e que nem toda decisão tomada cedo é arquitetural — por isso preferem ancorar a definição em *estruturas*, que são mais fáceis de identificar no software. A fonte acrescenta que arquitetura é um conjunto de estruturas de software: uma estrutura é um conjunto de elementos unidos por uma relação, e nenhuma estrutura isolada é "a" arquitetura — existem três categorias de estruturas arquiteturais (o trecho recebido corta antes de listá-las).

**Definições complementares**

A fonte [3] (Continuous Architecture in Practice, Erder/Pureur — seção "What Do We Mean by Architecture?") traz duas outras definições formais, também transcritas dela:

- Do IFIP Working Group 2.10: "Software architecture refers to the fundamental structures of a software system and the discipline of creating such structures and systems. Each structure comprises software elements, relations among them, and properties of both elements and relations." Essa mesma fonte acrescenta a metáfora de que a arquitetura funciona como planta (blueprint) do sistema e do projeto, e que arquitetura trata de escolhas estruturais fundamentais e custosas de mudar depois de implementadas.
- Da ISO/IEEE, o trecho começa a ser citado ("Architecture: Fundamental concept...") mas é cortado no material recebido — não dá para transcrever a definição completa dessa norma.

**O que não sustenta resposta aqui**

As fontes [1], [5], [6], [7] e [8] são sumário, ISBN, perguntas de discussão de capítulo ou prefácio/escopo de livro — não contêm definição do conceito e não foram usadas para sustentar a resposta. A fonte [4] é a introdução de uma parte do livro (roteiro do que os capítulos vão tratar), também sem definição direta, por isso não citada como fonte da definição em si.

---

## 04. o que é arquitetura de dados?  
*(bloco A)*

**Obras na recuperação:** Fundamentals of Data Engineering; Data Governance (2nd); Continuous Architecture in Practice

**Resposta (claude-sonnet-5):**

**Definição**

Arquitetura de dados é o conjunto de blueprints/modelos mestres que identificam as necessidades de dados de uma organização e orientam como esses dados são integrados, controlados e alinhados à estratégia de negócio. Ela representa o estado atual e futuro dos sistemas de dados que sustentam as necessidades de longo prazo de uma organização.

Há mais de uma formulação nas fontes que chegaram, e vale mostrar as três porque se complementam:

1. **Definição da DAMA (DMBOK)** — transcrita da fonte [3]:
> "Identifying the data needs of the enterprise (regardless of structure) and designing and maintaining the master blueprints to meet those needs. Using master blueprints to guide data integration, control data assets, and align data investments with business strategy."

Fonte: *Fundamentals of Data Engineering* (Reis & Housley), Capítulo 3 — Designing Good Data Architecture › DAMA's definition.

2. **Versão simplificada, de outro acervo** — transcrita da fonte [2], que primeiro resume a definição do DMBOK (mestre de modelos de dados e abordagens de design, a coluna "data" do Zachman Framework, ou a infraestrutura tecnológica física) e depois oferece a que o autor prefere usar em contexto de negócio:
> "Data architecture is a representation of the DM environment, its components, and their interactions. This picture, or abstraction, interrelates the framework, people, processes, projects, policies, technologies, and procedures to manage and use valuable enterprise information assets."

Fonte: *Data Governance* — Data literacy and concepts › Data architecture.

3. **Formulação de Reis & Housley** — transcrita da fonte [5]:
> "A data architecture reflects the current and future state of data systems that support an organization's long-term data needs and strategy."

Fonte: *Fundamentals of Data Engineering*, Capítulo 2 — The Data Engineering Lifecycle › Data Architecture. O mesmo trecho situa arquitetura de dados como "undercurrent" (corrente subjacente) do ciclo de vida de engenharia de dados, e distingue o papel de engenheiro de dados do de arquiteto de dados (são papéis tipicamente separados).

**Observação derivada** (não transcrita, mas ligando as três): as três definições convergem num ponto — arquitetura de dados não é a implementação em si, é a representação/blueprint que orienta decisões sobre dados (modelagem, integração, governança, trade-offs) em nível organizacional, distinta da execução tática do dia a dia.

**Fora do escopo da pergunta, deixado de lado**: as fontes [1], [4] e [7] tocam em arquitetura de dados mas não a definem no trecho que chegou — [1] é a introdução do capítulo que *antecede* as definições (o trecho corta antes de mostrar as definições em si), [4] fala de tipos/exemplos, e [7] fala de critérios de escolha de tecnologia. As fontes [6] e [8], de *Continuous Architecture in Practice*, tratam "dados" como preocupação arquitetural dentro da arquitetura de software geral, não definem "arquitetura de dados" como disciplina — não usei o conteúdo delas como definição por esse motivo.

---

## 05. o que é governança de dados?  
*(bloco A)*

**Obras na recuperação:** Cartilha de Governança de Dados — Volume I: Conceitos Iniciais; Cartilha de Governança de Dados — Volume III: Papéis e Responsabilidades de Governança de Dados no Poder Executivo Federal; Modelo de Maturidade de Dados (MMD) — Poder Executivo Federal, Versão 1.2; Cartilha do Catálogo Nacional de Dados; Apresentação do PowerPoint; Decreto nº 10.046/2019 — Governança no compartilhamento de dados na administração pública federal

**Resposta (claude-sonnet-5):**

Nenhuma das fontes que chegaram traz uma seção cujo breadcrumb nomeie diretamente "o que é governança de dados" como definição de conceito — mesmo a Cartilha de Governança de Dados Vol. I, que se chama "Conceitos Iniciais", veio com um trecho de capa/composição de comitê, sem matéria (não sustenta afirmação), e a Vol. III veio com a Apresentação, que fala do papel da governança, não de sua definição formal.

Diante disso, o mais próximo que consigo oferecer, marcado como **derivado** (não transcrição de definição), vem da Apresentação da *Cartilha de Governança de Dados — Volume III* (Papéis e Responsabilidades de Governança de Dados no Poder Executivo Federal):

Governança de dados, nesse texto, é descrita por seu papel: instrumento pelo qual organizações **buscam extrair valor e evidências de seus ativos de dados, garantir conformidade e segurança, facilitar a tomada de decisões embasadas, promover a cultura de dados, e estabelecer responsabilidade e prestação de contas**. A mesma Apresentação cita a OCDE (2023) para situar a governança de dados como prioridade no setor público, tratando dados como ativo estratégico, com funções de liderança dedicadas, arranjos de governança e instrumentos estratégicos.

Isso é descrição de finalidade/papel, não definição de conceito — não encontrei nas fontes uma frase do tipo "governança de dados é...". As demais fontes tratam de aspectos correlatos mas não definem o termo:
- [3] e [6] (Modelo de Maturidade de Dados) tratam de **estrutura organizacional** e de **dados como pilar de entregas**, pressupondo o conceito já conhecido;
- [4] trata dos **riscos da não implementação**, também pressupondo a definição;
- [7] e [8] tratam de **governança no compartilhamento de dados** (inclusive o Decreto nº 10.046/2019, que regula especificamente esse recorte), o que é mais estreito que "governança de dados" em geral — não devo equiparar os dois;
- [5] é sumário, sem matéria.

Se quiser, uma leitura minha sem fonte no que chegou: governança de dados costuma ser descrita, na literatura de gestão pública e privada, como o conjunto de políticas, papéis, processos e padrões que definem como os dados de uma organização são criados, geridos, protegidos e usados ao longo do ciclo de vida — mas isso não está transcrito em nenhuma das fontes enviadas neste turno, e marco como conhecimento geral, não como corpus do acervo.

---

## 06. o que é um domínio em gestão do conhecimento?  
*(bloco A)*

**Obras na recuperação:** Learning Domain-Driven Design; WonderWeb Deliverable D18: Ontology Library (final); Fundamentals of Data Engineering; Domain-Driven Design

**Resposta (claude-sonnet-5):**

As fontes que chegaram não tratam de "domínio" como conceito de Gestão do Conhecimento (KM) enquanto disciplina — nenhum breadcrumb nomeia esse conceito exato. O que chegou usa "domínio" no sentido de Domain-Driven Design (DDD) e arquitetura de software/dados, que é um vizinho semântico, não a mesma coisa.

Dentro do que chegou, a definição mais próxima e citável é a transcrita em [5], que por sua vez cita Eric Evans:

> "Domain: A sphere of knowledge, influence, or activity. The subject area to which the user applies a program is the domain of the software."

— transcrito de *Fundamentals of Data Engineering* (Reis & Housley), Capítulo 3: Designing Good Data Architecture › Domains and Services, citando Eric Evans.

A obra original de Evans, em [6], traz a mesma ideia com outras palavras:

> "That subject area to which the user applies the program is the domain of the software."

— transcrito de *Domain-Driven Design* (Eric Evans), Part I: Putting the Domain Model to Work.

Nesses dois casos, "domínio" é definido como a área de conhecimento, influência ou atividade à qual um software (ou um sistema de conhecimento, por extensão) se aplica — o assunto/esfera que delimita o que está dentro e fora do escopo de modelagem. Isso é transcrito da fonte, não é uma definição de KM propriamente dita.

As demais fontes de DDD ([1], [3], [4], [7], [8]) tratam de *domain knowledge* (conhecimento de domínio) — como descobri-lo, comunicá-lo via linguagem ubíqua, e como ele evolui — o que é adjacente mas não é a definição de "domínio" em si nem pertence ao vocabulário de KM.

A fonte [2] é um artefato técnico de alinhamento ontológico WordNet-DOLCE em formato KIF/Lisp; não contém prosa definindo "domínio" e não sustenta afirmação sobre o conceito perguntado — deixo de fora por não ter matéria aplicável.

**Sobre "domínio" especificamente em Gestão do Conhecimento** (como área de expertise reconhecida, comunidade de prática, taxonomia de conhecimento organizacional): as fontes não cobrem esse enquadramento. Se você quiser, posso responder com o que sei sobre isso — mas seria leitura minha, sem fonte no que chegou.

---

## 07. o que é inteligência?  
*(bloco A)*

**Obras na recuperação:** Referencial de análise (Abin) — coletânea de artigos; Atividade de inteligência nacional brasileira — doutrina; Lei nº 9.883/1999 — Lei da Agência Brasileira de Inteligência; Decreto nº 8.793/2016 — Política Nacional de Inteligência

**Resposta (claude-sonnet-5):**

## O que é inteligência?

Não há uma definição única — as fontes trazem duas camadas distintas: uma conceitual/acadêmica sobre o termo em geral, e uma legal, sobre a "Atividade de Inteligência" no ordenamento brasileiro.

**1. Duas acepções do termo (leitura conceitual)**

Segundo a fonte [1], há dois usos principais do termo fora das ciências cognitivas:

- **Definição ampla**: "inteligência é toda informação coletada, organizada ou analisada para atender a demanda de um tomador de decisões." Nessa acepção, inteligência equivale a conhecimento ou informação em geral — usada correntemente em governos, empresas e organizações sociais.
- **Definição restrita**: "inteligência é a coleta de informações sem o consentimento, a cooperação ou mesmo o conhecimento por parte dos alvos da ação." Nessa acepção, inteligência equivale a segredo ou informação secreta.

O próprio texto declara adotar a definição restrita como ancoragem da análise, por ser esta que torna a atividade "problemática" — trecho transcrito da fonte [1] (*01_Abin_Referencial_de_análise-(artigos).pdf*, seção "1 - O que é inteligência?").

**2. Definição legal brasileira**

A Lei nº 9.883/1999, no art. 1º, §2º, formaliza: "entende-se como inteligência a atividade que objetiva a obtenção, análise e disseminação de conhecimentos dentro e fora do território nacional sobre fatos e situações de imediata ou potencial influência sobre o processo decisório e a ação governamental e sobre a salvaguarda e a segurança da sociedade e do Estado." Trecho transcrito da fonte [7] (*L9883.pdf*, art. 1º).

**3. Complemento sobre a atividade no contexto brasileiro**

A fonte [6] (*01_Abin_Referencial_de_análise-(artigos).pdf*, seção "Introdução") cita, referenciando BRASIL, 2016, que a Atividade de Inteligência brasileira "é caracterizada pela produção de conhecimentos com a finalidade de apontar oportunidades e ameaças à consecução dos objetivos nacionais" — trecho transcrito, mas note que aqui é a fonte citando outra fonte (BRASIL, 2016), não uma definição de primeira mão do documento.

---

**Observação sobre as demais fontes**: a fonte [3] traz o breadcrumb "Inteligência e Políticas Públicas", mas o trecho recuperado é um anexo com fases do ciclo de políticas públicas — não define o conceito e por isso não foi usado. A fonte [5] veio apenas com ficha catalográfica e sumário (sem matéria) e a fonte [8] trata de uma característica da atividade (sigilo/especialização), não do conceito geral — também não sustentam a definição pedida.

---

## 08. o que é criptografia pós-quântica?  
*(bloco A)*

**Obras na recuperação:** Ameaça da computação quântica e a transição para a criptografia pós-quântica: relatório executivo de segurança; Consolidação de Matrizes PQC; Transição Brasileira para a Prontidão Pós-Quântica (PQC) e Soberania Digital; OSIC 15/2024 — Normatização e regulação de tecnologias emergentes no contexto da cibersegurança; Relatório executivo: a transição para a criptografia pós-quântica (PQC) e a proteção das infraestruturas críticas no Brasil; Uma Extensão Pós-Quântica Híbrida para o Protocolo Matrix: Avaliação Experimental e Impacto Sistêmico

**Resposta (claude-sonnet-5):**

**Definição**

Criptografia Pós-Quântica (PQC) é a defesa primária contra a ameaça representada pela computação quântica: ela usa algoritmos matemáticos que se acredita serem seguros mesmo contra o poder de processamento de computadores quânticos. *(Transcrito de [1] — Ameaça da Computação Quântica e a Transição para a Criptografia Pós-Quântica: Relatório Executivo de Segurança › Criptografia Pós-Quântica (PQC) e Mitigação.)*

**Por que ela existe (a ameaça que motiva)**

Algoritmos quânticos como o de Shor conseguem quebrar a maioria dos sistemas de criptografia assimétrica usados hoje (RSA, ECC), que dependem da dificuldade de fatorar números grandes ou resolver o problema do logaritmo discreto — problemas que um computador quântico resolve de forma eficiente. Já o algoritmo de Grover afeta a criptografia simétrica, exigindo o dobro do tamanho de chave (ex.: AES-256) para manter o nível de segurança atual. *(Transcrito/derivado de [4] — OSIC 15/2024 › 3.2 Desafios da Computação Quântica › 3.2.1 Quebra da criptografia assimétrica; e de [8] — Relatório Executivo PQC e Infraestruturas Críticas › 1. Ameaça e Contexto Estratégico.)*

Essa urgência é reforçada pela ameaça "Harvest Now, Decrypt Later" (HNDL/SNDL): adversários já interceptam e armazenam hoje dados cifrados classicamente para descriptografá-los assim que dispuserem de computação quântica capaz disso. *(Transcrito de [8].)*

**Como ela é construída, tecnicamente**

As soluções emergentes de PQC incluem, entre outras, criptografia baseada em reticulados (lattice-based) e assinaturas hash-based (stateless e stateful); o NIST já publicou padrões nessas famílias. *(Transcrito de [4].)*

**Distinção importante**

PQC não é o mesmo que "criptografia quântica": PQC é a solução de curto prazo baseada em algoritmos matemáticos clássicos resistentes a ataque quântico; já a distribuição quântica de chaves (QKD) — uma técnica de criptografia quântica propriamente dita, que usa fenômenos físicos para gerar/compartilhar chaves — é tratada como solução de mais longo prazo. *(Transcrito de [6] — OSIC 15/2024 › 3.4 Conclusões.)*

**Modelo de adoção recomendado nas fontes**

As fontes de contexto brasileiro recomendam uma transição em modelo híbrido — combinando criptografia clássica com PQC ("Quantum-Safe-by-Design") — para mitigar o risco de descriptografia retrospectiva, em vez de substituição abrupta. *(Transcrito/derivado de [3] e [5].)*

**Exemplo de aplicação prática**

Um estudo técnico (SBRC 2026) avaliou a integração híbrida do algoritmo CRYSTALS-Kyber (PQC baseado em reticulados) ao protocolo Matrix, medindo overhead de banda (+548% no setup, +252% nas rotações de chave) com impacto desprezível em CPU/latência — ilustrando o custo de engenharia real de adotar PQC em um sistema de mensageria. *(Transcrito de [7]; nota: o abstract da fonte veio em inglês, mas há resumo equivalente em português no próprio trecho, por isso não deixei a fonte de fora.)*

---
Observação: a fonte [2] (Consolidação de Matrizes PQC.xlsx) trata de algoritmos *simétricos clássicos* (AES, ChaCha, SM4 etc.), não de algoritmos pós-quânticos propriamente ditos no trecho que chegou — por isso não a usei para sustentar a definição de PQC, ela não é o vizinho semântico correto aqui.

---

## 09. o que é uma decisão arquitetural e quando se registra?  
*(bloco A)*

**Obras na recuperação:** Fundamentals of Software Architecture (2025); Documenting Architecture Decisions; Continuous Architecture in Practice; Ontology of architectural design decisions in software-intensive systems; Software Architecture Knowledge Management: Theory and Practice

**Resposta (claude-sonnet-5):**

## O que é uma decisão arquitetural

Uma decisão arquitetural é a decisão que estrutura a aplicação ou sistema — e pode incluir decisões de tecnologia quando elas afetam características arquiteturais (os "-ilities": performance, disponibilidade, etc.). Não é qualquer escolha técnica; é a que orienta os times de desenvolvimento nas escolhas técnicas certas.

> "Architectural decisions usually involve the structure of the application or system, but they may involve technology decisions as well, particularly when those technology decisions impact architectural characteristics. [...] a good architectural decision is one that helps guide development teams in making the right technical choices."

— transcrito de *Fundamentals of Software Architecture* (Richards & Ford), Chapter 20: Architectural Patterns › Architectural Decisions.

Duas fontes complementam esse conceito colocando a decisão como **unidade de trabalho da atividade arquitetural**, não como artefato acessório:

> "Drive architectural decisions, which are the primary unit of work of architectural activities."

— transcrito de *Continuous Architecture in Practice* (Erder & Pureur), Chapter 2 › Drive architectural decisions...

E na mesma obra, a ideia de que a arquitetura *é* esse fluxo de decisões:

> "the key unit of work of architecture is an architectural decision [...] architecture is just a flow of decisions."

— transcrito de *Continuous Architecture in Practice*, Chapter 2 › Architecture as a Flow of Decisions.

Um terceiro ângulo, mais estrutural, descreve a decisão pelos seus atributos mínimos — pelo menos um enunciado curto (epítome) e a justificativa (rationale):

> "Epitome (or the Decision itself). This is a short textual statement of the design decision [...] Rationale. This is a textual explanation of the 'why' of the decision, its justification."

— transcrito de *Software Architecture Knowledge Management* (Babar et al.), Chapter 3.4.1 What Is an Architectural Design Decision?, citando o framework de Kruchten.

## Quando se registra

Aqui as fontes não dão uma regra de "quando" no sentido de gatilho temporal explícito, mas dão dois elementos que, juntos, permitem responder por derivação:

**1. Registrar é parte constitutiva do ato de decidir, não uma etapa posterior facultativa.** Fundamentals of Software Architecture lista documentar e comunicar como parte do mesmo processo de "fazer" a decisão, junto com reunir informação e justificar — transcrito acima, mesmo trecho de [1].

**2. O registro deve ser modular e feito no momento em que a decisão é tomada, não como documentação monolítica ao final.** Michael Nygard argumenta que projetos ágeis não fazem todas as decisões de uma vez nem no início, e que documentos pequenos e modulares têm chance real de se manter atualizados — ao contrário de documentos grandes:

> "Not all decisions will be made at once, nor will all of them be done when the project begins. [...] Documents that assist the team itself can have value, but only if they are kept up to date. Large documents are never kept up to date. Small, modular documents have at least a chance at being updated."

— transcrito de adr2.pdf (Michael Nygard, "Documenting Architecture Decisions", 2011).

*Continuous Architecture in Practice* propõe operacionalizar isso com um quadro Kanban de decisões (Backlog → In Progress → Ready for Decision → Decision Made), recomendando identificar de antemão quais decisões serão necessárias e suas dependências, e tratar a documentação como parte do fluxo até o estado "Decision Made" — transcrito de [4], mesma seção citada acima.

**Derivado dessas duas fontes:** o registro acontece no momento em que a decisão é tomada (não antes, especulativamente, nem muito depois, de memória), e como artefato pequeno e específico daquela decisão — não como capítulo de um documento de especificação geral.

Como reforço do porquê disso importa, *Software Architecture Knowledge Management* descreve o custo de não registrar no momento certo — decisão implícita (o arquiteto nem percebe que decidiu) ou explícita mas não documentada (decidida por um motivo específico, mas a razão não é escrita e se perde com o tempo):

> "The design decision is explicit but undocumented: the architect takes a decision for a very specific reason [...] The reasoning is not documented, and thus is likely to vaporize over time."

— transcrito de [8], Chapter 1.2.2.1 Architecture as a Set of Design Decisions.

Nenhuma das fontes que chegaram detalha um gatilho formal (ex.: "toda decisão acima de X impacto" ou "em toda reunião de arquitetura") — se você precisa desse critério operacional específico, as fontes não cobrem esse nível.

---

## 10. o que é curadoria de acervo?  
*(bloco A)*

**Obras na recuperação:** NOBRADE: Norma brasileira de descrição arquivística; Cartilha de Governança de Dados — Volume III: Papéis e Responsabilidades de Governança de Dados no Poder Executivo Federal; Cartilha de Governança de Dados — Volume I: Conceitos Iniciais; Cartilha do Catálogo Nacional de Dados; Estudo Técnico Preliminar 3/2026 e anexos — Central de Atendimento Multimeios (Contact Center Omnichannel); Decreto nº 4.073/2002 — Regulamentação da Lei nº 8.159/1991 (política nacional de arquivos públicos e privados); ISAD(G): Norma geral internacional de descrição arquivística — Segunda Edição

**Resposta (claude-sonnet-5):**

Nenhuma das fontes que chegaram traz uma entrada de glossário para "curadoria de acervo" como conceito unificado — o que existe são fontes vizinhas, e vale separar o que cada uma diz.

**O que as fontes cobrem:**

- **Acervo** (transcrito da fonte [1], NOBRADE/CONARQ 2006, Glossário): "Totalidade de documentos de uma entidade custodiadora." A norma define quem responde pelo acervo — a "entidade custodiadora", "responsável pela custódia e acesso a um acervo" (fonte [8]) — mas não usa nem define o termo "curadoria".

- **Curador**, como papel, aparece em dois contextos diferentes das fontes, nenhum deles definindo "curadoria de acervo":
  - Na Cartilha de Governança de Dados vol. 1 (fonte [3], seção 5.2), "curador do dado" aparece de passagem, ligado a risco de desconhecimento de normas de privacidade — não há definição do papel nem do processo de curadoria ali, só a menção.
  - Na Cartilha do Catálogo Nacional de Dados (fonte [4]), "Curador" é apenas uma entrada de sumário (seção 1.8.3) — trecho sem matéria, não sustenta definição.

- **"Curadoria e Gestão de Conteúdos e Processos"** aparece definida na fonte [5] (apêndices de um TR), mas é outro conceito: ali descreve o ciclo de obtenção, roteirização e manutenção de scripts de atendimento (central de atendimento do MEC), não curadoria de acervo documental/arquivístico. Não uso essa definição para responder sua pergunta porque o breadcrumb e o conteúdo tratam de fluxo de atendimento, não de acervo.

**Conclusão:** as fontes não cobrem "curadoria de acervo" como conceito próprio. Vou responder com leitura minha, sem fonte no que chegou:

Curadoria de acervo é, de modo geral, o conjunto de decisões e atividades técnicas responsáveis por selecionar, organizar, descrever, preservar e dar acesso aos documentos que compõem um acervo — decidindo o que entra, como é classificado e descrito, e como se mantém íntegro e recuperável ao longo do tempo. Isso costuma incluir avaliação (o que guardar e por quanto tempo), arranjo, descrição normalizada e política de acesso. Essa leitura é minha, sem respaldo nas fontes fornecidas — as fontes que chegaram definem "acervo" e "entidade custodiadora" (arquivística) e citam "curador" só de passagem (governança de dados), mas nenhuma define o processo de curadoria em si.

---

## 11. DDD  
*(bloco B)*

**Obras na recuperação:** Implementing Domain-Driven Design; Domain-Driven Design in Software Development: A Systematic Literature Review on Implementation, Challenges, and Effectiveness

**Resposta (claude-sonnet-5):**

**Domain-Driven Design (DDD)** é a abordagem de desenvolvimento de software que existe para ajudar equipes a alcançar modelos de software de alta qualidade — modelos que expressam explicitamente o objetivo de negócio pretendido. Quando implementado corretamente, o design passa a ser exatamente como o software funciona: não só livre de defeitos, mas fiel ao domínio do negócio.

Isso é **transcrito** de: *Implementing Domain-Driven Design* (Vaughn Vernon) — Chapter 1: Getting Started with DDD [1].

Complementando, ainda **transcrito** do mesmo capítulo, seção *Why You Should Do DDD* [4], o valor prático de DDD inclui:
- colocar especialistas de domínio e desenvolvedores em pé de igualdade, produzindo software que faz sentido para o negócio, não só para quem programa;
- eliminar traduções entre a linguagem dos especialistas de domínio e a do código, via uma linguagem comum e compartilhada (a Ubiquitous Language);
- centralizar o conhecimento do domínio em vez de deixá-lo como "conhecimento tribal" restrito a poucos desenvolvedores.

O mesmo capítulo (seção *The Challenges of Applying DDD* [8]) também registra, **transcrito**, os principais desafios de aplicar DDD: o tempo e esforço para construir a Ubiquitous Language, a necessidade de envolvimento contínuo de especialistas de domínio desde o início, e a mudança na forma como desenvolvedores pensam soluções dentro do domínio.

Uma nota à parte: as fontes [2] e [3] vêm de um artigo de revisão sistemática de literatura sobre DDD, mas os trechos que chegaram tratam da metodologia da revisão (extração de dados, síntese narrativa) e dos highlights do estudo — não trazem uma definição própria do conceito, então não sustentam afirmação sobre "o que é DDD" e ficaram de fora da definição acima.

---

## 12. convergência sociotécnica  
*(bloco B)*

**Obras na recuperação:** Architecture Modernization; Sociomateriality: Challenging the Separation of Technology, Work and Organization; Adoção de Tecnologia: Um estudo sobre o uso de software livre nas empresas

**Resposta (claude-sonnet-5):**

As fontes que chegaram não cobrem "convergência sociotécnica" como conceito nomeado. O que existe no lote é vizinho semântico, não o mesmo conceito, e por isso não sustenta a definição:

- As fontes [2] e [4] (Orlikowski & Scott, *Sociomateriality: Challenging the Separation of Technology, Work and Organization* — seção que introduz o termo guarda-chuva e a seção "Moving Forward: Beyond Separation and Towards Fusion") tratam de **sociomaterialidade**: a tese de que técnico e social são *inseparáveis* — não duas coisas que convergem, mas uma coisa só, indivisível desde o início. É uma postura ontológica diferente da ideia de convergência (que pressupõe duas coisas distintas se alinhando).
- A fonte [1] (*Architecture Modernization*, capítulo 15, estudo de caso da telco europeia) descreve um episódio de reorganização sociotécnica (NetCo/ServCo, mudança de modelo operacional para acelerar entrega), mas não nomeia nem define "convergência sociotécnica" — é relato de caso, não definição de conceito.
- A fonte [8] veio só com folha de rosto e agradecimentos da dissertação sobre adoção de software livre; não há matéria no trecho para sustentar nada.

Dado isso, respondo com leitura minha, sem fonte no que chegou: **convergência sociotécnica** (*socio-technical congruence*), na literatura de engenharia de software (linha que remonta a Conway e foi operacionalizada por Cataldo, Herbsleb e colegas), é o grau de alinhamento entre as dependências técnicas de um sistema (quem precisa coordenar com quem por causa do código) e a estrutura social real de coordenação entre as pessoas que o desenvolvem (quem de fato se comunica, em que frequência). Baixa congruência — dependência técnica sem coordenação social correspondente — é associada a mais defeitos e atraso; é a base empírica por trás de heurísticas como "a arquitetura do software espelha o organograma que a produziu" (Lei de Conway) e de práticas de desenho de equipe como as do *Team Topologies*.

Isso é leitura minha, não derivado de nenhuma fonte deste lote — nenhuma delas define ou nomeia esse conceito específico.

---

## 13. arquitetura de negócios  
*(bloco B)*

**Obras na recuperação:** BIZBOK Guide; The TOGAF Standard, Version 9.2; Architecture Modernization

**Resposta (claude-sonnet-5):**

Não há, entre as fontes que chegaram, nenhuma que traga a definição do conceito "arquitetura de negócios" (business architecture) em si — todas tratam de assuntos vizinhos: o profissional que a aplica [1], a traits do arquiteto [4], sua relação com business model canvas [6], como comunicar seu valor [8], um trecho de mindset de modernização [7], e uma lista de figuras do TOGAF que não tem matéria de conteúdo [5]. Nenhuma delas nomeia e define o conceito central.

A que mais se aproxima é [2] (BIZBOK_Guide_v11 · PART 2: BUSINESS ARCHITECTURE BLUEPRINTS), mas ela não define "arquitetura de negócios" isoladamente — ela descreve a estrutura da Parte 2 do BIZBOK, dizendo que essa parte estabelece a "arquitetura de negócios fundacional" (foundational business architecture) e organiza as visões do negócio em dois grupos:

- **Visões fundacionais** (relativamente estáveis, essência do negócio): capability, organization, value, information.
- **Visões estendidas** (mais dinâmicas): strategy, initiatives, products, stakeholders, policy.

Isso é transcrito/derivado diretamente de [2]: "Foundational views of business architecture include capability, organization, value, and information [...] The extended business architecture includes strategy, initiatives, products, stakeholders, and policy."

Isso me dá o *escopo* que o BIZBOK atribui à arquitetura de negócios (suas visões constituintes), mas não a definição formal do termo (algo como "blueprint da empresa que orienta decisão estratégica" — essa formulação não aparece em nenhum trecho recebido).

Se quiser, posso responder com uma definição de leitura minha, sem fonte no que chegou: arquitetura de negócios é a disciplina que modela e organiza os elementos estruturais de uma organização — capacidades, estrutura organizacional, geração de valor, informação, estratégia — para alinhar decisão estratégica e execução operacional. Isso não vem de nenhuma das fontes fornecidas; é conhecimento geral meu, marcado como tal.

---

## 14. vocabulário controlado  
*(bloco B)*

**Obras na recuperação:** ANSI/NISO Z39.19-2005 (R2010), Guidelines for the Construction, Format, and Management of Monolingual Controlled Vocabularies

**Resposta (claude-sonnet-5):**

**Vocabulário controlado**

**Definição (derivada das fontes, composta a partir de trechos que não trazem — no recorte recebido — uma entrada de glossário fechada para o termo exato "controlled vocabulary")**

Um vocabulário controlado é um conjunto de termos selecionados da linguagem natural para representar conceitos e descrever objetos de conteúdo — usado para indexação, organização de sites e sistemas de recuperação de informação (derivado de [8], *5.2.1 Terms*, e do resumo em [5]). O controle sobre esses termos é alcançado por três métodos:

> "Vocabulary control is achieved by three principal methods: Defining the scope, or meaning, of terms; Using the equivalence relationship to link synonymous and nearly synonymous terms; and Distinguishing among homographs."
— transcrito de [2] (*1 Introduction › 1.2 How Vocabulary Control is Achieved*)

**Propósito** — transcrito de [3] (*1 Introduction*):
> "Vocabulary control is used to improve the effectiveness of information storage and retrieval systems, Web navigation systems, and other environments that seek to both identify and locate desired content via some sort of description using language. The primary purpose of vocabulary control is to achieve consistency in the description of content objects and to facilitate retrieval."

**Princípios que orientam o desenho** — transcrito de [6] (*5 Controlled Vocabularies – Purpose, Concepts, Principles, and Structure › 5.3 Principles*): eliminar ambiguidade, controlar sinônimos, estabelecer relações entre termos quando pertinente, e testar/validar os termos. A mesma fonte acrescenta: "A major goal of vocabulary control is to ensure that each distinct concept is described by a single linguistic form."

**Escopo da obra** — derivado do resumo em [5] (*ISBN: 1-880124-65-3*): o standard cobre vocabulários controlados monolíngues nas formas de listas, synonym rings, taxonomias e tesauros.

---

Observações sobre as fontes:
- [4] (*4.1 Definitions*) é a seção de glossário formal do padrão, mas o trecho recebido cobre apenas as entradas de "associative relationship" até "category" (ordem alfabética) — a entrada para "controlled vocabulary" em si não veio no recorte, então não posso transcrever uma definição de dicionário formal do termo.
- [1] e [7] são, respectivamente, um título de seção (5) e o sumário do documento — não têm matéria própria para sustentar afirmação, por isso não foram usados como base de conteúdo.

---

## 15. continuant e occurrent  
*(bloco B)*

**Obras na recuperação:** Basic Formal Ontology 2.0 — Specification and User's Guide

**Resposta (claude-sonnet-5):**

## Continuant

**Definição (transcrito da fonte [1], elucidação formal do BFO):**
"A continuant is an entity that persists, endures, or continues to exist through time while maintaining its identity."

A fonte [1] complementa (transcrito): continuants incluem também regiões espaciais, e "material entities (continuants) can preserve their identity even while gaining and losing material parts." Além disso, dois axiomas são dados (transcritos):
- "if b is a continuant and if, for some t, c is continuant_part of b at t, then c is a continuant."
- "if b is a continuant and if, for some t, c has_continuant_part b at t, then c is a continuant."

Um ponto central (transcrito): "Continuants have no temporal parts in this sense" — ao contrário dos occurrents, que se decompõem em partes temporais sucessivas.

**De onde sai:** BFO2-Reference.docx, seção *Specification › Continuant*.

## Occurrent

**Definição (transcrito da fonte [2], elucidação formal do BFO):**
"An occurrent is an entity that unfolds itself in time or it is the instantaneous boundary of such an entity (for example a beginning or an ending) or it is a temporal or spatiotemporal region which such an entity occupies_temporal_region or occupies_spatiotemporal_region."

A fonte [2] observa ainda (transcrito) que o domínio dos occurrents tem poucas "unidades naturais" comparado ao dos continuants — não há um contraparte natural de "objeto"; em BFO 2.0, "process" é o contraparte ocorrente de "material entity". Unidades identificáveis (vidas, jogos de futebol, reações químicas) são ou parasitárias da existência de unidades no lado continuant, ou de natureza *fiat*.

**De onde sai:** BFO2-Reference.docx, seção *Specification › Occurrent*.

## A dicotomia entre os dois

A fonte [3] (seção *The dichotomy of 'continuant' and 'occurrent'*) traz o pano de fundo teórico, transcrito: essa dicotomia "forms the central organizing axis of the BFO ontology" e deriva em parte de Zemach [60]. Segundo essa origem:

- **Occurrents** (chamados "events" por Zemach) podem ser fatiados em qualquer dimensão, espacial e temporal, para gerar partes.
- **Continuants**, por contraste, só podem ser fatiados ao longo da dimensão espacial — cita o exemplo da mesa: "'My desk stretches from the window to the door. It has spatial parts, and can be sliced (in space) in two. With respect to time, however, a thing is a continuant.'"

Isso é coerente com o que a fonte [1] afirma sobre ausência de partes temporais nos continuants, e com a nota (derivado da fonte [1], que cita [60]) de que continuants "are contrasted with occurrents, which unfold themselves in successive temporal parts or phases."

**Observação sobre parthood:** a fonte [4] (transcrito) mostra que o BFO distingue formalmente parthood entre os dois ramos com relações próprias — `continuant_part_of` (com sufixo `at t`, pois a composição de um continuant pode mudar no tempo) versus `occurrent_part_of` (sem sufixo temporal, pois um occurrent já é definido pela sua extensão temporal). A fonte [6] detalha as relações derivadas (`proper_continuant_part_of`, `has_continuant_part`, `proper_occurrent_part_of`, `has_occurrent_part`), reforçando que os dois ramos não compartilham a mesma mereologia.

---

## 16. proveniência arquivística  
*(bloco B)*

**Obras na recuperação:** ISAD(G): Norma geral internacional de descrição arquivística — Segunda Edição; NOBRADE: Norma brasileira de descrição arquivística

**Resposta (claude-sonnet-5):**

As fontes que chegaram não têm uma entrada dedicada ao conceito "proveniência arquivística" enquanto princípio nomeado. O que chegou trata de dois conceitos vizinhos, e nenhum deles é esse:

**1. "Procedência" (elemento descritivo, não o princípio)**
Na ISAD-G, "Procedência" é elemento 3.2.4, com objetivo de "identificar a origem imediata de aquisição ou transferência da unidade de descrição" — registra de quem/quando o acervo foi adquirido (doação, compra, depósito etc.) [3][6, transcrito]. Isso é procedência no sentido de cadeia de custódia/aquisição, distinto do princípio de proveniência.

**2. Menção de passagem em "fundo"**
O glossário do NOBRADE define fundo como "Conjunto de documentos de uma mesma proveniência. Termo que equivale a arquivo." [7, transcrito]. A palavra "proveniência" aparece aqui, mas a entrada não é sobre proveniência — é sobre fundo, e não define o termo.

O glossário geral da ISAD-G [1] também não chega à letra "P" no trecho que veio (para em "Controle de autoridade"), então não hedge nenhuma definição formal ali tampouco.

**Conclusão sobre a cobertura:** nenhuma fonte define o princípio da proveniência (respect des fonds) — a regra segundo a qual documentos de uma mesma origem/produtor devem ser mantidos juntos e não misturados com os de outra proveniência, preservando a ordem original quando existir. Isso é leitura minha, sem fonte no que chegou, e fica marcado como tal.

Se sua pergunta era sobre o elemento "Procedência" da ISAD-G (3.2.4) em vez do princípio, essa parte eu tenho transcrita das fontes [3]/[6] acima — me diga se é esse o recorte que você quer aprofundar.

---

## 17. fusão recíproca de rankings  
*(bloco B)*

**Obras na recuperação:** Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods; AI Engineering (for True Epub); Structured Analytic Techniques for Intelligence Analysis; Pretrained Transformers for Text Ranking: BERT and Beyond; Red-Blooded Risk: The Secret History of Wall Street

**Resposta (claude-sonnet-5):**

**Fusão recíproca de rankings (Reciprocal Rank Fusion — RRF)**

RRF é um método não supervisionado e simples para combinar os rankings de documentos produzidos por múltiplos sistemas de recuperação de informação (RI), pontuando cada documento pela soma dos recíprocos de sua posição em cada ranking de entrada (com uma constante `k` que amortece o impacto de posições muito altas dadas por sistemas discrepantes/outliers). — transcrito e derivado de [1] e [2] (*cormack-rrf-sigir2009* › ABSTRACT e RECIPROCAL RANK FUSION).

Pontos que as fontes sustentam:

- **Objetivo**: servir como baseline não supervisionado — "não requer exemplos de treino" — para combinar resultados de múltiplos sistemas de IR (incluindo métodos de learning-to-rank). Transcrito de [2].
- **Resultado empírico**: RRF "quase invariavelmente melhora sobre o melhor dos resultados combinados" e igualou ou superou consistentemente outros métodos de metaranking, como Condorcet Fuse e CombMNZ, em experimentos com quatro conjuntos de submissões ao TREC. O MAP do RRF superou o Condorcet Fuse em todos os casos, e o CombMNZ em quase todos. Transcrito de [2].
- **Comparação com Condorcet Fuse**: Condorcet Fuse combina rankings ordenando documentos por relação de pares determinada por voto majoritário entre os rankings de entrada — e pode ser dominado por uma maioria de preferências fracas que anula preferências individuais mais fortes. RRF, ao contrário, soma ranks sem olhar para os scores arbitrários de cada método, permite que um ou dois sistemas que rankeiam um documento muito bem melhorem substancialmente sua posição relativa aos documentos "populares", e não exige algoritmo de votação especial nem manter todos os rankings em memória simultaneamente (ranks podem ser somados um sistema por vez). Transcrito/derivado de [4] (seção References, que traz também texto de discussão) e [1] (ABSTRACT, fórmula de comparação com CombMNZ).
- **CombMNZ**, citado como outro método comparado, usa para cada ranking uma função de scoring `s_r: D → R` e um corte de rank `c`, combinando pela soma dos scores multiplicada pela contagem de rankings em que o documento aparece dentro do corte. Transcrito de [1].

Onde sai: *Reciprocal Rank Fusion (RRF)*, artigo de Cormack, seções ABSTRACT, RECIPROCAL RANK FUSION e References (SIGIR 2009).

As demais fontes do turno ([3], [5], [6], [7], [8]) não tratam de fusão recíproca de rankings — [6] e [8] cobrem ranking de texto em geral (arquitetura multi-estágio, avaliação Cranfield), o que é vizinho semântico mas não o conceito exato; [3] é sobre embeddings; [5] e [7] são de domínios completamente distintos (análise de inteligência e risco financeiro).

---

## 18. estratégia de chunking  
*(bloco B)*

**Obras na recuperação:** A Simple Guide to Retrieval Augmented Generation; AI Engineering (for True Epub)

**Resposta (claude-sonnet-5):**

# Estratégia de chunking

**Definição.** Chunking (também chamado *data splitting*) é o processo de quebrar textos longos em segmentos menores e manejáveis, necessário porque os textos-fonte de um sistema RAG costumam ser longos demais para caber inteiros na janela de contexto de um LLM. *(Transcrito da fonte [1], breadcrumb "3.2 Data splitting (chunking)".)*

Segundo o resumo do capítulo (fonte [5]), chunking resolve três problemas práticos: limites de janela de contexto do LLM, o problema de "lost-in-the-middle" em prompts longos, e facilita busca e recuperação. *(Transcrito.)*

## O processo (3 etapas)

De acordo com a fonte [4] (Figura 3.2 — Data-chunking process), o processo tem três passos:
1. Dividir o texto longo em unidades compactas e com sentido próprio (frases ou parágrafos);
2. Mesclar essas unidades menores em chunks maiores até atingir um tamanho-alvo, tratando cada chunk resultante como um segmento independente;
3. Ao criar um novo chunk, incluir parte do chunk anterior no início, para preservar continuidade contextual (overlap).
*(Transcrito.)*

## Métodos de chunking

A fonte [6] classifica os métodos em ordem crescente de sofisticação:
- **Fixed-size / simples**: tamanho de chunk predeterminado, dividindo por caracteres ou, de forma mais refinada, por tokens;
- **Especializado (specialized/adaptive)**: mais adequado a formatos de dado diferentes (ex.: código, tabelas, markdown);
- **Semântico**: proposto por Greg Kamradt, questiona a necessidade de tamanho fixo e propõe agrupar por similaridade semântica entre frases, olhando o significado real do conteúdo.

O resumo (fonte [5]) reforça essa mesma tripartição: "fixed size, specialized (or adaptive), or semantic", e adiciona que "newer chunking methods are constantly being introduced" e que "a chunking strategy can include multiple methods" — ou seja, não é obrigatório escolher um único método. *(Transcrito.)*

## Critérios para escolher a estratégia

As fontes [3], [7] e [8] são o mesmo trecho-pai (seção "3.2.4 Choosing a chunking strategy") subdividido, e afirmam explicitamente que **não há regras ou diretrizes fixas** para essa escolha — apenas features da aplicação que orientam a decisão:

- **Natureza do caso de uso** (fonte [3]): pergunta-resposta direta pede chunks curtos, para precisão; sumarização tende a se beneficiar de chunks mais longos; se a saída alimenta outra aplicação downstream, isso também influencia a escolha.
- **Modelo de embeddings** (fonte [7]): certos modelos de embedding performam melhor com chunks de tamanhos específicos.
- **Extensão e complexidade esperada da query do usuário** (fonte [8]): queries curtas e diretas pedem chunks de tamanho diferente de queries longas e complexas — casar query longa com chunk curto tende a ser ineficiente, e query curta com chunk grande pode trazer resultados parcialmente irrelevantes.

A fonte [7] fecha dizendo que chunking "não é uma tarefa complicada demais" e que a maioria dos métodos funciona — mas exige avaliação e ajuste conforme os resultados observados. *(Transcrito.)*

---

**Nota sobre as fontes**: a fonte [2] trata de *embeddings* (representação vetorial de texto), que é um conceito vizinho de chunking mas não o mesmo — chunking acontece antes da geração de embeddings, na etapa de divisão do texto. Por isso deixei-a de fora da resposta sobre estratégia de chunking em si; ela seria pertinente a uma pergunta sobre embeddings.

Todas as demais fontes vêm do mesmo livro (Kimothi, *A Simple Guide to Retrieval Augmented Generation*, capítulo 3, seção 3.2), então a resposta reflete a cobertura de uma única obra sobre o tema.

---

## 19. quantização de modelo  
*(bloco B)*

**Obras na recuperação:** LLM Engineer’s Handbook; llama.cpp — formato GGUF e quantização; Quantize with Confidence? An Empirical Study of Quantization for Code Generation; AI Engineering (for True Epub); Can Compressed LLMs Truly Act? An Empirical Evaluation of Agentic Capabilities in LLM Compression

**Resposta (claude-sonnet-5):**

## Quantização de modelo

**Definição** — Quantização é o processo de representar os pesos e ativações de uma rede neural usando tipos de dados de precisão mais baixa. No contexto de LLMs, o foco principal é reduzir a precisão dos pesos (e ativações) do modelo. Por padrão, pesos são armazenados em ponto flutuante de 16 ou 32 bits (FP16/FP32), formato de alta precisão mas com custo elevado de memória e computação; quantizar reduz esse footprint de memória e acelera a inferência.

*(Transcrito/derivado de: LLM Engineer's Handbook — Paul Iusztin, Maxime Labonne — seção "Model quantization" [3])*

Um achado notável registrado na mesma fonte: modelos maiores (acima de 30B parâmetros), quando quantizados para 2 ou 3 bits, podem superar em qualidade modelos menores (7B–13B) rodando em precisão mais alta, mantendo footprint de memória comparável. *(transcrito de [3])*

---

### Técnicas específicas cobertas nas fontes

**GGUF + llama.cpp** — formato de quantização do projeto llama.cpp (biblioteca C++ de inferência, criada por Georgi Gerganov), pensado para rodar em hardware amplo (CPU, Android, com offload de camadas para GPU), sem depender de bibliotecas fechadas como CUDA. GGUF armazena tensores e metadados em variantes de 1 a 8 bits (ex.: IQ1_S/M, Q2_K, Q4_K_S/M, Q6_K, Q8_0, entre outras). *(transcrito de [1], LLM Engineer's Handbook — "Quantization with GGUF and llama.cpp")*

A especificação formal do formato reforça: GGUF é um formato binário sucessor de GGML/GGMF/GGJT, desenhado para carregamento/salvamento rápido, autocontido (toda informação necessária para carregar o modelo) e extensível sem quebrar compatibilidade. *(transcrito de [4], recorte do repositório ggml-org/llama.cpp, commit 39eab74 — nota: a fonte identifica-se como rendição textual de um recorte específico, e o restante do arquivo original, por ser código, não entrou no trecho recebido)*

**GPTQ e EXL2** — formatos dedicados a GPU, mais rápidos que llama.cpp na inferência; EXL2 tem o maior throughput via ExLlamaV2. Ambos baseiam-se no algoritmo GPTQ (Frantar et al., 2023), que refina o Optimal Brain Quantization (OBQ) com decomposição de Cholesky da Hessiana inversa e atualização de pesos em lote (lazy batch updates). GPTQ limita-se a 4 bits; EXL2 permite taxas de bits fracionárias e mistas por camada (entre 2 e 8 bits), priorizando pesos mais importantes com maior precisão — na prática permitindo rodar um modelo de 70B numa única GPU de 24GB a ~2,55 bits. *(transcrito de [2])*

**AWQ, QuIP# e HQQ** — AWQ (Lin et al., 2023) protege os pesos mais importantes com base na magnitude de ativação (não do peso), aplicando escala por canal sem backprop; é próximo de GPTQ/EXL2 em resultado, um pouco mais lento, e integrado a TGI, vLLM, TensorRT-LLM. QuIP# e HQQ visam quantização extrema (1–2 bits) preservando melhor a qualidade do modelo original, tendência especialmente relevante para modelos grandes (>30B). *(transcrito de [7])*

---

### Estudos empíricos sobre efeito da quantização

As fontes [5] e [8] são artigos que investigam empiricamente o impacto da quantização, mas em recortes mais específicos que a pergunta não delimitou — não tratam do conceito em si, então trago apenas o que o trecho recebido permite dizer, sem completar com o restante do artigo:

- [5] (Afrin et al., "Quantize with Confidence?") investiga como GPTQ, AWQ, QuIP#, AQLM, BitsAndBytes e GGUF afetam a correção funcional e qualidade de código gerado por modelos de código (Qwen2.5-Coder, CodeLlama), usando os benchmarks McEval e CoderEval. O trecho recebido é a abertura do abstract; não chegou o resultado quantitativo.
- [8] (Dong et al., "Can Compressed LLMs Truly Act?") aponta que compressão pós-treino (poda e quantização) reduz custo computacional/de memória em até 4×, mas benchmarks existentes focam em perplexidade e NLU, ignorando capacidades agênticas (workflow, uso de ferramentas, contexto longo). O trecho recebido é o abstract/introdução; não traz os resultados do benchmark ACBench.

---

**Fora do escopo desta resposta**: a fonte [6] trata de *embeddings*, não de quantização de modelo — vizinho semântico que não sustenta a pergunta feita, por isso não foi usada.

---

## 20. opportunity solution tree  
*(bloco B)*

**Obras na recuperação:** [sem obra] Continuous-Discovery-Habits-Torres.epub; Empowered; Cracking the PM Career; Structured Analytic Techniques for Intelligence Analysis; Measuring and Managing Information Risk; User Story Mapping

**Resposta (claude-sonnet-5):**

**Definição** (transcrita da fonte [2], nota de rodapé em *Empowered: Ordinary People, Extraordinary Products*, seção "Team Objectives"): Opportunity Solution Tree é uma técnica, criada pela coach de discovery Teresa Torres, útil para identificar e avaliar múltiplas abordagens de solução para um problema importante e crítico.

**Sobre as demais fontes:**

- A fonte [1] é do próprio livro de Teresa Torres, *Continuous Discovery Habits*, mas o trecho que chegou é a página de copyright e o sumário (índice de capítulos). Ele mostra que existe um capítulo "Mapping the Opportunity Space" dentro da Parte 2 ("Discovering Opportunities"), o que é consistente com o tema, mas não traz conteúdo que defina a árvore em si — é sumário, não sustenta afirmação sobre o conceito.

- A fonte [4] está em russo e ficou de fora por não ser um idioma que leio com segurança.

- A fonte [5] (FAIR) usa "opportunities" no sentido de "oportunidades de melhoria" em contexto de GRC/compliance — vizinho semântico, não é o mesmo conceito.

- As fontes [6], [7] e [8], de Jeff Patton (*User Story Mapping*), tratam de "opportunities" e "opportunity backlog" como conceito próprio do story mapping (decisão go/no-go sobre ideias de feature), com raiz conceitual distinta da Opportunity Solution Tree de Torres — não uso esse material para definir a árvore, para não confundir os dois vocabulários.

- A fonte [3] não menciona o conceito.

Se quiser a estrutura detalhada da árvore (outcome no topo, oportunidades, soluções, experimentos), as fontes que chegaram não cobrem isso com matéria suficiente — isso ficaria como leitura minha, sem fonte no que chegou, e prefiro não misturar sem sinalizar. Posso trazer se você confirmar que quer essa parte marcada como leitura livre.

---

## 21. posicionamento de produto  
*(bloco B)*

**Obras na recuperação:** Obviously Awesome: How to Nail Product Positioning so Customers Get It, Buy It, Love It

**Resposta (claude-sonnet-5):**

## Posicionamento de produto

**Definição** (transcrito de [5], seção *POSITIONING AS CONTEXT*, obra *Obviously Awesome: How to Nail Product Positioning*, de April Dunford):

> "Context enables people to figure out what's important. Positioning products is a lot like context setting in the opening of a movie."

Ou seja: posicionamento é o trabalho de dar contexto a um produto — do mesmo jeito que a cena de abertura de um filme ajuda o espectador a responder rapidamente "onde estamos, quem são esses personagens, devo torcer por eles ou contra eles, isso é triste ou é engraçado". Sem esse contexto deliberado, o comprador não sabe onde encaixar o produto na cabeça dele.

A mesma fonte descreve uma armadilha comum (derivado de [5]): produtos criadores tendem a achar que só existe uma forma de posicionar uma oferta, presos à ideia original de "o que eu construí" (ex.: "sobremesa" ou "e-mail"), quando na verdade o mesmo produto poderia ser reposicionado em outro mercado (ex.: "lanche" ou "chat") — e isso não é acidente, é escolha deliberada.

**O objetivo do processo** (transcrito de [1], *STEP 3 — Align Your Positioning Vocabulary*):

> "The goal of the 10-Step Positioning Process is to find the best position for a product, one that puts the product in the context of a market where it can easily win because the product has obvious benefits over alternatives."

A mesma fonte observa (derivado de [1]) que a maioria dos produtos pode ser "muitas coisas para muitos tipos de compradores" — por isso é preciso um vocabulário comum de equipe antes de tentar reposicionar, largando bagagem de posicionamento anterior.

**Risco de desatualização** (transcrito/derivado de [3], *POSITIONING AS CONTEXT › The Two Traps › Trap 2*): um posicionamento pode ficar ruim não porque o produto mudou, mas porque o mercado ao redor dele mudou — a fonte ilustra com o caso do "diet muffin" que virou irrelevante quando o mesmo produto, com os mesmos ingredientes, passou a ser vendido como "gluten-free paleo snack" pela concorrência.

**Componentes e captura**: as fontes [4] e [7] cobrem partes específicas do processo — [4] fala de um dos "5 (mais 1) componentes" (tendências relevantes como elemento opcional de contexto) e [7] descreve o *Step 10*, a captura do posicionamento em documento e em um "positioning canvas" (nome do produto, categoria de mercado, alternativas competitivas, atributos, valor e segmentos de cliente) para que o posicionamento tenha adesão da empresa e informe marca, marketing, vendas e produto — isso é transcrito de [7].

**Conclusão do livro** (transcrito de [6]): "Any product can be positioned in multiple markets" e "Great positioning rarely comes by default" — reforça que posicionamento é resultado de trabalho deliberado (testar, falhar, tentar de novo), não algo que acontece sozinho.

As fontes [2] (Step 6, sobre agrupar valor em "temas") não tratam do conceito geral de posicionamento em si, mas de uma etapa específica do processo de dez passos — deixei fora da definição central porque o breadcrumb aponta para uma técnica intermediária, não para o conceito.

---

## 22. avaliação heurística  
*(bloco B)*

**Obras na recuperação:** Information Architecture: For the Web and Beyond; Human Problem Solving: The State of the Theory in 1970; Lei nº 6.880/1980 — Estatuto dos Militares; Threat Modeling: Designing for Security; ABNT NBR ISO/IEC 27701:2019 — Técnicas de segurança — Extensão da ABNT NBR ISO/IEC 27001 e 27002 para gestão da privacidade da informação; Guia de Elaboração de PDTIC do SISP, versão 2.1; Learning Domain-Driven Design

**Resposta (claude-sonnet-5):**

As fontes que chegaram não cobrem "avaliação heurística" no sentido em que o termo é normalmente usado — método de inspeção de usabilidade (um pequeno grupo de avaliadores examina uma interface contra um conjunto de heurísticas, como o de Nielsen, para achar problemas de usabilidade sem precisar de usuários reais).

O que chegou fala de heurística em outros sentidos, nenhum deles o conceito perguntado:

- [7] (*Learning Domain-Driven Design*, Cap. 9, seção "Heuristic") traz uma definição genérica do termo "heurística" — transcrito: "não é uma regra rígida garantida e matematicamente provada correta em 100% dos casos [...] é uma regra de ouro: não garantida como perfeita, mas suficiente para os objetivos imediatos". É definição de heurística como categoria de raciocínio, não do método "avaliação heurística".
- [8], mesma obra, seção "Design Heuristics" — heurísticas para decisões de design de software orientado a domínio (DDD), assunto distinto.
- [4] (*Threat Modeling*, Adam Shostack) — "Ceremony Analysis Heuristics", heurísticas para achar ameaças em modelagem de segurança, também não é o conceito perguntado.
- [2] (Simon, 1970) — heurísticas de resolução de problemas (ex.: colunas mais restritas primeiro em criptoaritmética), tema de psicologia cognitiva, sem relação com avaliação de interface.
- [3], [5], [6] trazem só o título/breadcrumb de seções chamadas "Avaliação" (implementação de segurança, desempenho de SGPI, PDTIC) sem trecho de matéria que defina algo — não sustentam nenhuma afirmação sobre o conceito.
- [1] (*Information Architecture*) não fala de avaliação heurística; trata de "Defining the damned thing", debate sobre definir IA.

Como nenhuma fonte cobre o conceito exato, respondo com o que sei, marcado como **leitura minha, sem fonte no que chegou**:

Avaliação heurística é um método de inspeção de usabilidade, proposto por Jakob Nielsen e Rolf Molich no fim dos anos 1980/início dos 1990, em que um pequeno número de avaliadores (tipicamente 3 a 5) examina uma interface de forma independente e a julga contra um conjunto de princípios de usabilidade reconhecidos — as "heurísticas" (por exemplo, visibilidade do estado do sistema, correspondência entre sistema e mundo real, prevenção de erros, consistência e padrões, entre outras do conjunto clássico de Nielsen). Cada avaliador lista os problemas encontrados, tipicamente com uma severidade estimada, e os achados são depois consolidados. É um método de custo relativamente baixo, não requer usuários reais e é usado sobretudo em fases iniciais de design para captar problemas óbvios antes de testes de usabilidade mais caros.

---

## 23. gestão de incidente  
*(bloco B)*

**Obras na recuperação:** Tecnologia da informação — Técnicas de segurança — Código de prática para a gestão da segurança da informação; Decreto nº 10.748/2021 — Rede Federal de Gestão de Incidentes Cibernéticos; Política de Segurança da Informação e Comunicação do Laboratório Nacional de Computação Científica; Norma Complementar nº 08/IN01/DSIC/GSIPR; Norma Complementar 21/IN01/DSIC/GSIPR

**Resposta (claude-sonnet-5):**

**Definição** (transcrita da ABNT NBR ISO/IEC 27002, seção 13.2 [2]): gestão de incidentes de segurança da informação é o conjunto de responsabilidades e procedimentos definidos para o manuseio efetivo de eventos de segurança da informação e fragilidades, uma vez que estes tenham sido notificados, com o objetivo de assegurar um enfoque consistente e efetivo — e sobre o qual convém aplicar um processo de melhoria contínua às respostas, ao monitoramento, à avaliação e à gestão total dos incidentes.

**Objetivo declarado dos procedimentos** (transcrito de 13.2.1 [1]): assegurar respostas rápidas, efetivas e ordenadas a incidentes. A norma detalha que os procedimentos precisam cobrir:
- tipos de incidente a tratar — falhas de sistema e perda de serviços, código malicioso, negação de serviço, erros por dados incompletos/inconsistentes, violações de confidencialidade e integridade, uso impróprio de sistemas;
- etapas do tratamento — análise e identificação da causa, retenção, planejamento/implementação de ação corretiva para prevenir repetição, comunicação com afetados e envolvidos na recuperação, notificação à autoridade apropriada, e coleta e proteção de trilhas de auditoria e evidências similares.

**No âmbito da administração pública federal brasileira**, duas fontes normativas tratam do mesmo conceito com recorte institucional:
- NC21/GSIPR [8] — dentro do processo de Gestão da Segurança da Informação e Comunicações, a gestão de incidentes abrange registro de eventos, coleta e preservação de evidências, identificação de causas e tratamento dos incidentes (transcrito).
- NC08/GSIPR [7] — trata do gerenciamento de incidentes de segurança em redes de computadores na APF, estruturado por ETIRs que trocam informação com a CGTIR (Coordenação Geral de Tratamento de Incidentes de Segurança em Redes de Computadores), viabilizando intercâmbio técnico, apoio no tratamento, monitoramento/métricas, avaliação de danos e capacitação (transcrito).
- Decreto 10.748/2021 [3] institui a Rede Federal de Gestão de Incidentes Cibernéticos, de participação obrigatória para órgãos/entidades da administração federal direta e adesão voluntária para empresas públicas e sociedades de economia mista — é estrutura institucional de coordenação, não uma definição do conceito em si (derivado do trecho).

**Fora do escopo desta resposta**: a fonte POSIC LNCC [5] trata de segmentação de rede e controle de acesso — vizinho semântico de segurança da rede, mas não aborda gestão de incidentes, então não a usei para sustentar nada aqui. As fontes [4] e [6] são cabeçalho de capítulo e página de copyright/sumário, respectivamente — sem matéria para embasar afirmação.

---

## 24. gestão de mudança  
*(bloco B)*

**Obras na recuperação:** ISO 31000:2018 — Risk management — Guidelines; Guia Livre: Referência de Migração para Software Livre do Governo Federal, Versão 1.0; Tecnologia da informação — Técnicas de segurança — Código de prática para a gestão da segurança da informação; DAMA-DMBOK: Data Management Body of Knowledge; Data Governance (2nd); CompTIA Security+ Certification Study Guide: Network Security Essentials

**Resposta (claude-sonnet-5):**

## Gestão de mudança

**Definição** (transcrita de [7], Security+ – Ahmed Sheikh, Capítulo 5 "Risk Management and Disaster Recovery" › "Why Change Management?"):

> "Change management is a structured approach for performing and recording changes during software development and system operation" — em tradução livre: gestão de mudança é uma abordagem estruturada para executar e registrar mudanças durante o desenvolvimento de software e a operação de sistemas.

A mesma fonte acrescenta que a gestão de mudança é parte essencial da estrutura de governança e controle, e crítica para conformidade com a Sarbanes–Oxley Act (transcrito).

**A norma ABNT NBR ISO/IEC 27002** trata do mesmo conceito em termos operacionais, em 10.1.2 "Gestão de mudanças" [3]. Transcrito da fonte, os elementos que convém considerar são:

- identificação e registro das mudanças significativas;
- planejamento e testes das mudanças;
- avaliação de impactos potenciais, incluindo impactos de segurança;
- procedimento formal de aprovação das mudanças propostas;
- comunicação dos detalhes às pessoas envolvidas;
- procedimentos de recuperação em caso de insucesso ou evento inesperado.

A norma justifica isso dizendo que "o controle inadequado de modificações nos sistemas e nos recursos de processamento da informação é uma causa comum de falhas de segurança ou de sistema" (transcrito), e recomenda manter registro de auditoria de toda mudança realizada.

**Caso específico de terceiros**, também na 27002, em 10.2.3 "Gerenciamento de mudanças para serviços terceirizados" [4]: o processo precisa levar em conta tanto mudanças feitas pela própria organização (melhorias de serviço, novas aplicações, novas políticas, novos controles) quanto mudanças do lado do fornecedor (novas tecnologias, novos produtos, mudanças de localização física ou de fornecedor) — sempre considerando a criticidade dos sistemas envolvidos e a reavaliação de riscos (transcrito).

**Complemento — a dimensão de pessoas**: a obra de governança de dados [8], na seção "Operation and change › Essential questions", trata gestão de mudança sob o ângulo comportamental: cita que as pessoas mudam menos por dados e fatos e mais por experiências que afetam suas emoções (citação de Kotter e Cohen, transcrita), e recomenda monitorar a efetividade dos processos de gestão de mudança por métricas frequentes. Essa fonte é sobre change management dentro de um programa de governança de dados especificamente, não uma definição geral do conceito.

**Fontes deixadas de fora por não tratarem do conceito exato** (vizinhos semânticos, não "gestão de mudança"):
- [1] ISO 31000, 5.7 "Melhoria/Adaptação" — fala de adaptação contínua da *estrutura de gestão de riscos*, não do processo de gestão de mudança em si.
- [2] Guia de migração para software livre — introdução geral do guia, sem definir o conceito.
- [5] DMBOK, 3.7 — menciona "organizational change" de passagem, ao tratar de modelo operacional de dados, sem defini-lo.
- [6] Data Governance, Cap. 4 overview — introduz um estudo de caso, não trata de change management.

---

## 25. observabilidade  
*(bloco B)*

**Obras na recuperação:** Observability Engineering; Building Microservices (2nd)

**Resposta (claude-sonnet-5):**

## Observabilidade

**Definição** (transcrita da fonte [3], *Observability Engineering*, Capítulo 22 — "Where to Go from Here", que retoma a definição dada no Capítulo 1):

> "Observability for software systems is a measure of how well you can understand and explain any state your system can get into, no matter how novel or bizarre. You must be able to comparatively debug that bizarre or novel state across all dimensions of system state data, and combinations of dimensions, in an ad hoc iterative investigation, without being required to define or predict those debugging needs in advance. If you can understand any bizarre or novel state without needing to ship new code, you have observability."

Em resumo (derivado da fonte): observabilidade é a capacidade de entender e explicar qualquer estado — inclusive estados nunca vistos antes — de um sistema em produção, fazendo perguntas ad hoc sobre os dados sem precisar prever essas perguntas com antecedência nem alterar o código para respondê-las.

### Origem do termo

Transcrito de [2] (Capítulo 1, "The Mathematical Definition of Observability"): o termo foi cunhado pelo engenheiro Rudolf E. Kálmán em 1960, na teoria de controle, onde observabilidade é "a measure of how well internal states of a system can be inferred from knowledge of its external outputs". A obra deixa claro que essa definição matemática original foi adaptada — de forma "radicalmente diferente" — para sistemas de software, e não é o enfoque do livro.

### Observabilidade vs. monitoramento

De [6] (*Building Microservices*, 2ª ed., Sam Newman, seção "Observability Versus Monitoring"), transcrito/próximo do original:

> "The observability of a system is the extent to which you can understand the internal state of the system from external outputs."

O mesmo trecho distingue: monitoramento é uma *atividade* (você monitora, observa o sistema), enquanto observabilidade é uma *propriedade* do sistema. Abordagens tradicionais de monitoramento exigem prever com antecedência o que pode dar errado e definir alertas para isso — o que se torna limitado à medida que o sistema cresce em complexidade (trecho cortado na fonte antes de concluir o raciocínio).

### Observabilidade como prática (não capacidade pontual)

Transcrito de [1] (Introdução, "Introducing Observability as a Practice"): assim como segurança ou testabilidade, observabilidade "is an ongoing practice that is a responsibility shared by anyone responsible for developing and running a production service" — não é algo que se "alcança" com uma checkbox técnica. A fonte marca dois planos: (1) capacidade técnica — o sistema pode ser observado?; e (2) prática sociotécnica — as equipes e o sistema operam bem juntos, já que "just because a system can be observed does not mean that it is being observed effectively."

### Pré-requisito técnico: o evento estruturado

Derivado de [4] (Capítulo 5, "Structured Events Are the Building Blocks of Observability"): para sustentar a definição acima, o livro aponta o **evento estruturado** como bloco de construção fundamental — telemetria coletada em resolução completa, no nível de request/serviço, preservando o contexto de captura, permitindo fatiar os dados em qualquer combinação de dimensões sem definição prévia. A fonte contrasta isso com métricas tradicionais, que exigem definição de antemão e perdem o contexto do evento.

### Debugging exploratório

De [8] ("Debugging with Observability"): a *explorability* de um sistema é medida por quão bem se pode fazer qualquer pergunta e inspecionar o estado interno correspondente — investigação iterativa e aberta, sem prever de antemão quais estados serão investigados.

---

**Nota sobre as fontes:** todos os trechos usados vêm de duas obras específicas do acervo — *Observability Engineering* (Majors, Fong-Jones, Miranda) e *Building Microservices* (Newman) — ambas com identificação completa (autor, ano, ISBN quando aplicável). Não há conflito entre elas: a segunda converge com a primeira na definição central (estado interno inferível a partir de saídas externas), acrescentando o contraste com monitoramento.

---

## 26. trunk-based development  
*(bloco B)*

**Obras na recuperação:** Accelerate: State of DevOps 2023; Accelerate: State of DevOps 2022; State of DevOps Report 2016; Accelerate: State of DevOps 2019; State of DevOps Report 2017; Building Microservices (2nd); Accelerate: The Science of Lean Software and DevOps; Accelerate: State of DevOps 2021

**Resposta (claude-sonnet-5):**

**Definição**

Trunk-based development é a prática de integrar código continuamente no "tronco" (trunk/master) em vez de manter branches de feature de vida longa. Para evitar que trabalho incompleto vaze para os demais, usa-se feature flags para "esconder" o que ainda não está pronto. É considerada complementar à integração contínua.
— Transcrito/derivado de *Building Microservices, 2nd ed.* (Sam Newman), Capítulo 7, seção "Branching Models": "The alternative approach is to have everyone check in to the same 'trunk' of source code. To keep changes from impacting other people, techniques like feature flags are used to 'hide' incomplete work. This technique of everyone working off the same trunk is called trunk-based development."

Convergindo com isso, o *2022 DORA Accelerate State of DevOps Report* (seção "Trunk-based development") transcreve: "the practice of continuously merging code into the trunk and avoiding long-lived feature branches [...] considered a complement to continuous integration."

**Critérios operacionais que caracterizam a prática (empíricos)**

Transcrito de *Accelerate: The Science of Lean Software and DevOps* (Cap. 10, seção "Trunk-based development") e do *2017 State of DevOps Report* (seção "Trunk-based development", que apresenta os mesmos critérios do ano anterior):
- Merge de código no trunk pelo menos uma vez ao dia.
- Branches (ou forks) com vida muito curta — menos de um dia antes de serem integradas.
- Menos de três branches ativas simultaneamente por equipe.
- Ausência de períodos de "code freeze" ou estabilização.

**Impacto associado (achado de pesquisa, não definição)**

Derivado das mesmas fontes DORA/Accelerate: equipes que seguem esses critérios apresentam maior desempenho de entrega de software (lead time, frequência de deploy, tempo de restauração) e menor taxa de falha em mudanças — resultado, segundo o relato, independente de tamanho de time, de organização ou de indústria (Accelerate, Cap. 10).

O *2022 DORA Report* (seção "Trunk-based development") acrescenta um recorte por experiência: profissionais com 16+ anos que praticam trunk-based development tendem a realizar os benefícios da prática (maior desempenho geral, menos trabalho não planejado, menor propensão a erro, menor change failure rate); já profissionais com menos experiência apresentam resultados menos positivos — atribuído, no texto, à ausência das práticas complementares necessárias (regras rígidas contra deixar o trunk quebrado, gated branches, auto-rollback).

**Ressalva sobre resistência à prática**

Transcrito do *2017 State of DevOps Report*: existe ceticismo de desenvolvedores acostumados ao fluxo recomendado pelo GitHub ("GitHub Flow"), que se apoia em desenvolvimento por branches com merges periódicos ao trunk — mas o relatório argumenta que esse fluxo, quando as branches são de fato curtas (menos de um dia), é compatível com os critérios de integração contínua acima.

**Fontes que apareceram mas não sustentam a definição**

- Fonte [8] (2021 DORA) apenas lista "Trunk-based development" como uma das capacidades técnicas medidas, sem defini-la no trecho — não usada para conceituar.
- Fonte [3] (2016 State of DevOps, "Shifting Left") e fonte [4] (2019 DORA, "Technical Practices") tratam de conceitos vizinhos (shift-left/qualidade, abordagem holística de práticas técnicas), não do conceito exato — deixadas de fora da definição.
- Fonte [1] (2023 DORA) trouxe só cabeçalhos repetidos de headings ("Trunk-based development") sem corpo de texto no trecho recebido — não sustenta afirmação, mera lista/sumário.

---

## 27. feature flag  
*(bloco B)*

**Obras na recuperação:** Building Microservices (2nd); AWS Well-Architected Framework; Architecture Modernization; Developing with PDF: Dive Into the Portable Document Format; Lean Inception; CIS Google Cloud Platform Foundation Benchmark; The Site Reliability Workbook

**Resposta (claude-sonnet-5):**

## Feature flag (feature toggle)

**Definição** — Mecanismo que esconde funcionalidade já implantada atrás de um controle (toggle) que liga ou desliga essa funcionalidade, ou alterna entre duas implementações diferentes de um mesmo comportamento, sem precisar de novo deploy. *(Transcrito/derivado de [1] e [2].)*

**De onde sai** — *Building Microservices: Designing Fine-Grained Systems*, 2ª ed., Sam Newman. A obra trata o conceito em dois lugares, cada um com um uso diferente:

- **Capítulo 8, Deployment › Progressive Delivery › Feature Toggles** [1]: aqui o foco é entrega progressiva. É o uso mais comum, associado a trunk-based development — funcionalidade incompleta é integrada e implantada, mas fica oculta do usuário final até estar pronta. Também serve para ligar uma feature em horário programado, desligar algo que está causando problema, ou dar tratamento granular por perfil de usuário (ex.: grupo beta vê a feature ligada, o resto vê desligada) — o que viabiliza canary rollout. O texto cita soluções gerenciadas (LaunchDarkly, Split), mas recomenda começar simples, até com um arquivo de configuração, e recomenda o artigo de Pete Hodgson, "Feature Toggles (aka Feature Flags)", para aprofundamento.

- **Capítulo 3, Splitting the Monolith › Useful Decompositional Patterns › Feature Toggle** [2]: aqui o uso é como padrão de decomposição durante migração para microsserviços. No contexto do strangler fig, o toggle permite alternar entre a funcionalidade que ainda vive no monolito e a nova implementação no microsserviço — por exemplo, implementado na camada de proxy HTTP do strangler fig.

**Observação sobre as demais fontes** — as fontes [3], [4], [5], [7] e [8] tratam de assuntos distintos (cultura organizacional, plataforma interna de desenvolvimento, campos de formulário em PDF, "database flag" do SQL Server no CIS Benchmark, e fundamentos de SRE) e não abordam feature flag/toggle como conceito — não as usei. A fonte [6] define "Feature" (não "feature flag") no glossário do *Lean Inception*, um conceito vizinho mas diferente, também deixada de fora por não nomear o conceito exato perguntado.

---

## 28. teste de contrato  
*(bloco B)*

**Obras na recuperação:** Instrução Normativa SGD/ME nº 94, de 23 de dezembro de 2022; INOVAÇÃO ABERTA E JUSTIÇA DIGITAL: transformação disruptiva do Judiciário por meio da colaboração com empresas startups; Análise dos modelos e contratos de desenvolvimento de software na administração direta do governo federal: a crise na produção de software e as alternativas à fábrica de software; Termo de Referência 32/2026; Estudo Técnico Preliminar da Contratação — registro de preços para licenças de aplicativos, softwares e sistemas operacionais Microsoft; Acórdão 2569/2018-TCU-Plenário — Relatório de Auditoria, SETIC (TC 030.236/2016-9)

**Resposta (claude-sonnet-5):**

Nenhuma das oito fontes que chegaram neste turno define um conceito, método ou critério identificável a partir de uma pergunta específica — o turno trouxe apenas "teste de contrato", sem uma pergunta de fato formulada.

Preciso que você me diga qual conceito, método ou critério quer que eu defina. As fontes que recebi cobrem temas variados (obrigações contratuais em TIC, Marco Legal das Startups, métricas de crise em modelos de desenvolvimento, licenciamento de software, entre outros) — mas sem saber qual deles é o alvo da sua pergunta, não consigo apontar a fonte certa pelo breadcrumb nem montar a resposta.

Pode reformular com a pergunta de conceito/método/critério que você quer que eu responda?

---

## 29. cryptoperiod  
*(bloco B)*

**Obras na recuperação:** nist.sp.800-57pt1r5; CISSP All-in-One Exam Guide; Serious Cryptography; ISC2 CISSP Certified Information Systems Security Professional Official Study Guide; ISO/IEC 27002:2013 — Information technology — Security techniques — Code of practice for information security controls; Transição Brasileira para a Prontidão Pós-Quântica (PQC) e Soberania Digital

**Resposta (claude-sonnet-5):**

Nenhuma das fontes que chegaram cobre o conceito exato de **cryptoperiod**.

A fonte que seria a referência canônica para esse termo é a NIST SP 800-57 Part 1 [1], mas o trecho que chegou dela é só o sumário (table of contents) da publicação — não tem matéria, é lista de números de seção sem texto. Não dá para sustentar uma definição a partir disso.

As fontes [2] e [4] tratam de **cryptographic life cycle** (ciclo de vida criptográfico) — o processo de identificar necessidade de criptografia, escolher algoritmo, provisionar e gerenciar chaves até que o sistema fique obsoleto e o ciclo recomece. É um conceito vizinho, mas não é o mesmo que cryptoperiod: o ciclo de vida trata da vida útil do *sistema/algoritmo* como um todo, enquanto cryptoperiod, no uso padrão de gestão de chaves (NIST SP 800-57), é o intervalo de tempo específico durante o qual uma *chave criptográfica particular* está autorizada para uso antes de ser trocada. São conceitos relacionados, mas não intercambiáveis, e por isso [2]/[4] não respondem pela pergunta.

Como leitura minha, sem fonte no que chegou: cryptoperiod costuma ser definido como o tempo de vida útil de uma chave específica, dimensionado a partir de fatores como volume de dados protegidos sob a mesma chave, sensibilidade da informação, exposição a ataque e custo operacional de rotação — mas essa definição não está sustentada por nenhuma das fontes que chegaram neste turno.

---

## 30. nível de garantia de autenticação  
*(bloco B)*

**Obras na recuperação:** NIST SP 800-63B-4 — Authentication; NIST SP 800-63-4 — Digital Identity Guidelines; Solving Identity Management in Modern Applications; NIST SP 800-63A-4 — Identity Proofing; Guia Livre: Referência de Migração para Software Livre do Governo Federal, Versão 1.0; Manual de Condutas Técnicas 11 — Volume II: procedimentos de ensaios para avaliação de conformidade aos requisitos técnicos de softwares de AC e AR no âmbito da ICP-Brasil

**Resposta (claude-sonnet-5):**

## Nível de garantia de autenticação

**Definição geral (derivada de [3]):** é o grau de confiança que um provedor de serviço tem de que o usuário autenticado numa sessão é de fato o dono legítimo da conta. Esse grau varia conforme a força do mecanismo usado — por exemplo, autenticar só com senha estática dá menos garantia do que autenticar também com um código de uso único gerado no celular do usuário, porque é mais difícil um impostor ter acesso ao segundo fator. Quando uma aplicação exige elevar essa garantia para liberar uma operação mais sensível, o mecanismo usado para isso é o *step-up authentication*.

Importante: a fonte [3] (*Solving Identity Management in Modern Applications*, cap. 12, seção "Step-Up Authentication") é explícita em dizer que os nomes e a numeração dos níveis ali ("nível um", "nível dois") são **exemplo arbitrário de ilustração** do autor, não uma escala normativa — isso está transcrito da fonte, não é uma taxonomia oficial.

**Como termo técnico formal (NIST):** a sigla AAL (*Authentication Assurance Level*) é conceito próprio do NIST SP 800-63B. O trecho recuperado dessa obra [1] confirma a existência do conceito — o Preface diz textualmente: *"This document, SP 800-63B, provides requirements to credential service providers (CSPs) for remote user authentication at each of three authentication assurance levels (AALs)"* — mas o breadcrumb desse trecho é "List of Figures/Preface", e o conteúdo que chegou não inclui a seção que de fato define e caracteriza AAL1, AAL2 e AAL3. Ou seja: **confirmo, transcrito da fonte, que existem três AALs definidos no SP 800-63B, mas as fontes que chegaram não cobrem o conteúdo de cada nível** — não tenho de onde tirar as características técnicas de cada AAL sem especular.

O companheiro [2] (SP 800-63-4, volume geral) também só trouxe List of Figures/Preface, sem detalhar AAL.

Se quiser, posso responder com a caracterização técnica de AAL1/AAL2/AAL3 (número de fatores exigidos, resistência a phishing, etc.) como **leitura minha sem fonte no que chegou** — mas nesse caso preciso que você autorize essa marcação explicitamente, já que não está lastreada em nenhuma das fontes recebidas neste turno.

---

## 31. gestão de acesso privilegiado  
*(bloco B)*

**Obras na recuperação:** Tecnologia da informação — Técnicas de segurança — Código de prática para a gestão da segurança da informação; ABNT NBR ISO/IEC 27701:2019 — Técnicas de segurança — Extensão da ABNT NBR ISO/IEC 27001 e 27002 para gestão da privacidade da informação; OSIC 15/2024 — Normatização e regulação de tecnologias emergentes no contexto da cibersegurança; ISO/IEC 27002:2013 — Information technology — Security techniques — Code of practice for information security controls; CompTIA Security+ Certification Study Guide: Network Security Essentials

**Resposta (claude-sonnet-5):**

**Definição** (transcrita da fonte [6], ABNT NBR ISO/IEC 27002:2005, seção 11.2.2 "Gerenciamento de privilégios"):

Gestão de acesso privilegiado é a disciplina que restringe e controla a concessão e o uso de privilégios — direitos de acesso que ultrapassam os de um usuário comum, como os de administrador de sistema, banco de dados ou aplicação. A norma prescreve, entre outros pontos:

- identificar o privilégio de acesso associado a cada produto de sistema (SO, SGBD, aplicação) e as categorias de usuário que dele precisam;
- conceder privilégios apenas conforme a necessidade de uso, com base em eventos e alinhados à política de controle de acesso — "requisitos mínimos para sua função somente quando necessário";
- manter um processo de autorização formal e um registro de todos os privilégios concedidos, sem liberá-los antes de esse processo estar concluído;
- incentivar rotinas e programas de sistema que dispensem a necessidade de conceder privilégios a usuários;
- atribuir os privilégios a um ID de usuário diferente do usado normalmente para atividades de negócio.

A fonte [6] também registra, em trecho cortado no fim do excerto, que "o uso inapropriado de privilégios de administrador de sistemas" é tratado como fator de risco relevante — mas o texto que chegou não continua além desse ponto, então não sei o que a norma diz na sequência.

**De onde sai**: ABNT NBR ISO/IEC 27002:2005, seção 11 "Controle de acessos" › 11.2 "Gerenciamento de acesso do usuário" › 11.2.2 "Gerenciamento de privilégios" (fonte [6]).

**Complementos do mesmo acervo**:

- A análise crítica periódica desses direitos é tratada à parte, na 11.2.4: "autorizações para direitos de acesso privilegiado especial (ver 11.2.2) sejam analisadas criticamente em intervalos mais frequentes, por exemplo, em um período de três meses" — mais curto que a revisão geral de acesso de usuários (seis meses) — transcrito da fonte [7], mesma norma, seção 11.2.4.
- A fonte [1] (seção 11.2, objetivo geral) situa isso dentro do ciclo de vida de acesso do usuário, com "atenção especial [...] para a necessidade de controlar a distribuição de direitos de acesso privilegiado que permitem os usuários mudar controles de sistemas" — transcrito.
- A fonte [2] (ABNT NBR ISO/IEC 27701:2019, 6.6.2.3, mesmo título "Gerenciamento de direitos de acesso privilegiado") apenas remete ao controle da ISO/IEC 27002:2013, 9.2.3, sem trazer conteúdo próprio no trecho recebido — não sustenta afirmação adicional.
- A fonte [3] (guia de gestão de identidades e acessos, não específico de privilégio) trata do tema mais amplo de IAM e do princípio do menor privilégio (PoLP) como resposta ao risco de "gestão inadequada de permissões" — é conceito vizinho (IAM geral), não o mesmo recorte de "gestão de acesso privilegiado" da 27002, mas ajuda a contextualizar o princípio que sustenta essa prática.

A fonte [5] (ISO/IEC 27002:2013 em inglês, seção 9.2) e a fonte [8] (resumo de capítulo de livro didático) não trazem, nos trechos recebidos, conteúdo específico sobre gestão de acesso privilegiado — [5] corta antes do item 9.2.3 (que seria o correspondente em inglês) e [8] é só um resumo sem definição.

---

## 32. cost of delay  
*(bloco B)*

**Obras na recuperação:** Accelerate: State of DevOps 2018; Investment Valuation; The Principles of Product Development Flow: Second Generation Lean Product Development; Escaping the Build Trap; Essential Kanban Condensed

**Resposta (claude-sonnet-5):**

## Cost of Delay

**Definição** (transcrito de [6]): Cost of Delay (COD) é o valor numérico que quantifica o impacto econômico do tempo sobre os objetivos de um projeto — combina urgência e valor para medir o custo de adiar uma entrega. Reinertsen a chama de "a chave de ouro que destrava muitas portas": é o que permite avaliar o custo de filas, o valor de capacidade excedente, o benefício de lotes menores e o valor da redução de variabilidade. Sem quantificar o COD, não é possível saber se vale a pena trocar dinheiro por tempo de ciclo (ex.: inserir uma margem de segurança no cronograma tem um custo, mas só se sabe se a troca compensa se o valor do tempo de ciclo estiver quantificado).

**Origem:** *The Principles of Product Development Flow* (Donald G. Reinertsen), seção "The Economic View › The Project Economic Framework › E3: The Principle of Quantified Cost of Delay: If you only quantify one thing, quantify the cost of delay." — o próprio nome do princípio é "se você só for quantificar uma coisa, quantifique o cost of delay" (transcrito).

**Complemento** (transcrito de [4], *Escaping the Build Trap*, seção "Prioritizing Work"): Melissa Perri cita esse mesmo conceito de Reinertsen como seu framework de priorização preferido — ao entender os outcomes estratégicos desejados, o COD ajuda a decidir o que entregar primeiro, pesando o valor capturado contra o tempo até o lançamento; atrasar demais por escopo excessivo custa receita perdida e pode abrir espaço para concorrentes.

**Nota:** as fontes [3] e [5], do mesmo livro de Reinertsen, tratam de conceito vizinho — filas, Little's Law e DIP (design-in-process inventory) — que fundamentam o raciocínio econômico por trás do COD, mas não definem o termo em si; não as usei para sustentar a definição. As fontes [1], [2] e [8] não tratam de cost of delay e ficaram de fora.

---

## 33. limite de WIP  
*(bloco B)*

**Obras na recuperação:** Essential Kanban Condensed; The Lean Product Playbook; The Principles of Product Development Flow: Second Generation Lean Product Development; Accelerate: The Science of Lean Software and DevOps

**Resposta (claude-sonnet-5):**

## Limite de WIP (work in progress)

**Definição.** Limite de WIP é a restrição imposta à quantidade de itens de trabalho que podem estar simultaneamente em andamento em um processo, com o objetivo de controlar o tempo de ciclo (cycle time) e o fluxo. Tecnicamente, corresponde a transformar um sistema de fila sem limite (M/M/1/∞) em um sistema com limite superior k (M/M/1/k): quando o WIP atinge esse teto, novas entradas de demanda são bloqueadas.

— *Transcrito/derivado* de **The Principles of Product Development Flow** (Reinertsen), seção *Applying WIP Constraints › The Economic Logic of WIP Control › W1: The Principle of WIP Constraints: Constrain WIP to control cycle time and flow* [6]. O texto afirma explicitamente: "When we set a limit on WIP, we create one positive effect and two negative ones. The positive effect is to reduce average cycle time." E localiza o mecanismo formal no modelo M/M/1/k, em oposição ao M/M/1/∞ sem limite.

**Mecanismo de enforcement.** A forma mais simples de operar um limite de WIP é bloquear toda demanda nova quando o teto é atingido — é exatamente o método usado no sistema kanban, e análogo a um sinal de "ocupado" em um sistema telefônico. O bloqueio pode ser feito ejetando o item que chega ou retendo-o numa fila anterior (esta segunda forma é a usada no Toyota Production System, que também aplica limites de WIP às filas upstream).

— *Transcrito* de **The Principles of Product Development Flow**, seção *Applying WIP Constraints › Reacting to Emergent Queues › W6: The Principle of Demand Blocking* [7].

**Limites diferenciados por categoria.** Como o fluxo de trabalho normalmente não é homogêneo, uma prática mais sofisticada consiste em subdividir o WIP em categorias por custo de atraso (alto, médio, baixo) e usar a Fórmula de Little para determinar um limite de WIP específico por categoria, alcançando tempos de fluxo diferenciados mesmo compartilhando o mesmo recurso.

— *Transcrito/derivado* de **The Principles of Product Development Flow**, seção *Applying WIP Constraints › WIP Constraints in Practice › W18: The Principle of Differential Service* [3].

**Como prática de gestão lean (Accelerate).** Limitar o WIP é listado como um dos três componentes das práticas de Lean Management aplicadas à entrega de software, ao lado de displays visuais e uso de dados de monitoramento. O achado empírico do livro é que o limite de WIP isolado não prediz fortemente a performance de entrega — o efeito forte aparece quando combinado com displays visuais e loop de feedback de produção.

— *Transcrito/derivado* de **Accelerate — The Science of Lean Software and DevOps**, seção *Software › Lean Management Practices* [5].

**Sobre o kanban de Olsen [2] e o resumo de kanban [1]:** o trecho de *The Lean Product Playbook* descreve o quadro kanban e suas colunas, e o *Essential Kanban Condensed* traz um foreword geral sobre o método — nenhum dos dois, no recorte que chegou, define ou explica o limite de WIP em si (o segundo é prefácio, sem matéria técnica sobre o conceito), então não os uso para sustentar a definição.

---

## 34. role charter  
*(bloco B)*

**Obras na recuperação:** Data Governance (2nd); User Stories Applied: For Agile Software Development; Basic Formal Ontology 2.0 — Specification and User's Guide; Server Administration Guide

**Resposta (claude-sonnet-5):**

As fontes que chegaram não cobrem "role charter" como conceito único e nomeado — nenhuma delas tem breadcrumb que trate exatamente disso. O que existe é matéria adjacente, mas nenhuma fecha a definição:

- [3], [4] e [5] tratam de **charter**, mas do *programa* de Data Governance (documento que define escopo, propósito, autoridade dos órgãos de governança, representação, subtimes) — é charter de um programa/estrutura, não de um papel (role).
- [6] e [8] tratam de **role** no sentido ontológico da BFO (entidade realizável dependente do portador, distinção entre "ter" um papel e "desempenhar" um papel) — é role, sem nenhuma noção de charter.
- [7] trata de **role** no sentido técnico de controle de acesso (Keycloak, operações de CLI sobre roles de um realm) — também sem charter.
- [2] trata de **user role** em user stories (papel de usuário do sistema, para fins de elicitação de requisitos) — sem charter.

Nenhuma fonte junta os dois termos. Por isso, não vou atribuir a nenhuma obra uma definição de "role charter" que ela não contém.

Como leitura minha, sem fonte no que chegou: "role charter" é um termo comum em desenho organizacional (às vezes ligado a RACI ou a frameworks de governança), que designa um documento curto descrevendo um papel específico — não uma pessoa nem um cargo formal — com propósito do papel, responsabilidades, autoridade/decisões que ele pode tomar, e a quem se reporta ou com quem interage. É o análogo, em escala de um único papel, do que [3]/[4]/[5] descrevem em escala de programa inteiro (propósito, responsabilidades, representação). Mas essa costura é minha, não das fontes.

Se o que você quer é o charter do *programa* de Data Governance, ou a definição ontológica/técnica de *role* isoladamente, tenho fonte pra cada um — me diga qual e eu respondo com base nelas.

---

