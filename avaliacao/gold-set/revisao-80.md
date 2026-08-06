Substitui: (novo)

# Gold set T2 — revisão das 80

Gabarito bruto em `gold-set/coleta/<cadeira>.md`. Canônico em `gold-set/gold-t2-20260803.jsonl`. Manifesto do acervo usado no casamento: `gold-set/manifesto-acervo-20260803.tsv` (696 obras, 03/08/2026).

## Placar

| cadeira | itens | tipo declarado | casamento (título/nenhuma) | nenhuma | pendência |
|---|---|---|---|---|---|
| claudinha-gestao-estrategica | 10 | 10/10 | 10/10 | 5 | — |
| claudinho-arquiteto | 10 | 10/10 | 10/10 | 1 | — |
| claudinho-conhecimento | 20 | 20/20 | 20/20 | 12 | — |
| claudinho-IA | 10 | 10/10 | 10/10 | 4 | — |
| claudinha-produto | 10 | 10/10 | 10/10 | 3 | — |
| claudinho-TI | 10 | 10/10 | 10/10 | 0 | — |
| claudinho-seguranca | 10 | 10/10 | 10/10 | 2 | — |
| **total** | **80** | **80/80** | **80/80** | **27** | **0 tipo(s) faltando** |

**27 de 80 são "nenhuma"** (33%) — bem acima do que uma cota fixa teria dado. É esperado: as negativas passaram a emergir do casamento em vez de cota, e o efeito colateral é este. Consequência que o claudinho-IA precisa incorporar: o T3 dele (~15 negativos planejados) já está coberto de sobra pelo T2 sozinho — o dimensionamento original do T3 pode encolher.

## Pendência única que bloqueia o fechamento formal

`claudinho-conhecimento`, itens 1–10 (os próprios, não os da OSINT): casamento veio completo, **tipo (simples/complexa) não veio**. Conteúdo está bom — só falta o campo. Pedir de volta antes de considerar o T2 fechado.

## Casamentos flagados pela própria cadeira (fraco, parcial ou de baixa confiança)

**claudinha-gestao-estrategica**
- #02: seria: The Principles of Product Development Flow (Reinertsen)

**claudinho-arquiteto**
- #01: corrigido — dono propôs "adr1" com confiança baixa e perguntou se deveria abrir para confirmar; conferi por fora (query_cargo: "adr1"/"adr2" sem registro em Referencias, sem espécie/domínio — obras cruas; rag_search "como escrever um ADR" devolve Fundamentals of Software Architecture cap.21 como as 5 fontes de topo, "adr1"/"adr2" não aparecem). É o fallback que o dono já tinha nomeado, promovido a principal.
- #03: seria: The TOGAF Standard (10th Edition)
- #05: dono flagou par secundário: detalhamento dos controles mora mais na ISO/IEC 27002:2013, ausente do casamento
- #09: dono flagou: cobre efeitos de rede, não o recorte de custos de transação (Coase/Williamson) — segue parcialmente no estrato negativo mesmo casada

**claudinho-conhecimento**
- #04: seria: ISAD(G) (Conselho Internacional de Arquivos) ou NOBRADE
- #06: seria: obra de ciência de redes com modelos nulos (ex.: Newman, Networks: An Introduction)
- #11: seria: Developing with PDF (Rosenthol, O'Reilly)
- #12: seria: ISO 28500 (WARC 1.1)
- #13: seria: documentação oficial do Tesseract
- #14: seria: documentação/fonte do Protego (Scrapy) e RFC 9309
- #15: seria: Developing with PDF (Rosenthol, O'Reilly)
- #16: casamento parcial — dono flagou: cobre a caixa de ferramentas de string-matching, não o desenho do pipeline com transliteração
- #18: seria: obra sobre efeito mosaico/agregação (ex.: Solove, Understanding Privacy)
- #20: seria: literatura de captura-recaptura (ex.: estimadores de Chao)

**claudinho-IA**
- #01: casamento parcial — dono flagou: paper cobre o modelo, não os defaults de chunking da doc oficial (fora do acervo)
- #04: casamento parcial, mais brando — dono flagou: acervo não tem o paper original de Järvelin & Kekäläinen
- #05: seria: a documentação do llama.cpp (guia de quantização GGUF)
- #06: seria: uma obra de temporal information retrieval (ex.: Campos et al., Survey of Temporal IR)
- #07: seria: m os papers de long-context attention (RoFormer/RoPE, Longformer, lost-in-the-middle de Liu et al.)
- #09: casamento parcial — dono flagou: só a metade "sistemas distribuídos" é do Nygard; a metade "loops de LLM" tem apoio parcial em snapshots Anthropic Engineering, fora do acervo formal
- #10: seria: benchmark/paper de efeito de quantização em structured output (sem título canônico único)

**claudinha-produto**
- #02: seria: User Stories Applied (Mike Cohn)
- #03: dono flagou parcial: o dedicado dele é Rocket Surgery Made Easy, ausente do acervo
- #04: dono flagou parcial: sumário A4, cobre as heurísticas, quase certo que não cobre o protocolo com múltiplos avaliadores
- #05: seria: Obviously Awesome (April Dunford)
- #09: dono nota: complementar The Lean Product Playbook também no acervo, para gabarito multi-fonte

**claudinho-TI**
- #06: casamento fraco — dono flagou: obra canônica é Continuous Delivery (Humble & Farley), ausente do acervo
- #10: casamento parcial — dono flagou: cobre o núcleo (CAB/aprovação), mas ITSM formal (ITIL) segue ausente do acervo

**claudinho-seguranca**
- #01: seria: Keycloak Server Administration Guide (documentação oficial, versão 26.x)
- #03: casamento parcial — dono flagou: só cobre metade OIDC Core; RFC 8707 não está no acervo
- #06: dono flagou: casa a metade genérica (resiliência), não a topologia do nosso broker
- #08: dono flagou: tem gêmea próxima no acervo — "Ameaça da Computação Quântica..._ Relatório Executivo de Segurança"; não contar erro cheio se a busca devolver a gêmea
- #09: Anderson, Ross J_] -- 2010 -- Wiley -- 214b8251993da512c72cf9ba0da7837a -- Anna's Archive   [dono flagou: casa o núcleo conceitual, não a topologia megafone/claudinho — isso é wiki, não acervo

## Fila de aquisição — obras nomeadas ao longo da coleta, sem pedido feito ainda

- RFC 8707 (Resource Indicators) — nomeado por claudinho-seguranca
- Keycloak Server Administration Guide (doc. oficial 26.x) — nomeado por claudinho-seguranca
- Continuous Delivery (Humble & Farley) — nomeado por claudinho-TI
- The TOGAF Standard (10th Edition) — nomeado por claudinho-arquiteto
- User Stories Applied (Mike Cohn) — nomeado por claudinha-produto
- Obviously Awesome (April Dunford) — nomeado por claudinha-produto
- Rocket Surgery Made Easy (Krug) — opcional — nomeado por claudinha-produto
- Usability Engineering (Nielsen) — opcional — nomeado por claudinha-produto
- The Principles of Product Development Flow (Reinertsen) — nomeado por claudinha-gestao-estrategica
- Documentação oficial llama.cpp — guia de quantização GGUF — nomeado por claudinho-IA
- ISAD(G) ou NOBRADE — nomeado por claudinho-conhecimento
- Developing with PDF (Rosenthol) — corpus da OSINT, fora do índice — nomeado por claudinho-conhecimento/OSINT

São sugestões saídas do casamento, não pedido feito. Pedido vai ao dono do acervo, como sempre.

## As 80, por cadeira

### claudinha-gestao-estrategica

01. Qual é o procedimento canônico de portfolio review no SAFe (Lean Portfolio Management) — cadência, participantes e artefatos de entrada?
   tipo: simples · esperada: *nenhuma*
02. Como se calcula Cost of Delay e CD3 (Cost of Delay Divided by Duration) para sequenciar iniciativas, segundo a formulação original de Don Reinertsen?
   tipo: simples · esperada: *nenhuma* ⚠️
03. Quais são os critérios formais do framework de betting do Shape Up para decidir o que entra num ciclo — e o que a obra manda fazer com o que ficou de fora?
   tipo: simples · esperada: Shape Up
04. Que estrutura um role charter / job description bem escrito deve ter segundo a literatura de design organizacional — campos obrigatórios e anti-padrões?
   tipo: simples · esperada: *nenhuma*
05. Qual é o método documentado para timeboxing e proteção de foco executivo (tipo maker's schedule vs manager's schedule, ou time blocking formal) — regras operacionais, não filosofia?
   tipo: simples · esperada: A World Without Email -- Cal Newport -- null, null, 2021 -- Penguin Publishing Group -- 01df625471dd63018ce970fcf3a96b69 -- Anna's Archive
06. Quando uma carteira mistura iniciativas de horizonte curto (operação) e apostas de longo prazo (plataforma), qual régua de alocação entre horizontes é defensável para uma organização de uma pessoa mais agentes de IA — e como os modelos clássicos (três horizontes, barbell) se degradam nesse tamanho?
   tipo: complexa · esperada: *nenhuma*
07. Personas de IA com remit escrito são mais parecidas com cargos ou com contratos de serviço? Que consequências cada enquadramento traz para como RH escreve fronteira, escala e revoga uma persona — puxando de teoria de contratos e de team design?
   tipo: complexa · esperada: Team Topologies_ Organizing Business and Technology for Fast -- Matthew Skelton, Manuel Pais -- 2, 2025 -- IT Revolution -- isbn13 9781966280002 -- 224c48d665a00d96c55fe8fb334039c3 -- Anna's Archive
08. Como decidir se uma capability órfã (tipo criticidade de fluxo e política de degradação) deve virar gerência nova, ser absorvida por cadeira existente ou ficar explicitamente sem dono — que critério a literatura de topologia de times dá, e onde ele conflita com o custo cognitivo de instrução de um agente?
   tipo: complexa · esperada: Team Topologies_ Organizing Business and Technology for Fast -- Matthew Skelton, Manuel Pais -- 2, 2025 -- IT Revolution -- isbn13 9781966280002 -- 224c48d665a00d96c55fe8fb334039c3 -- Anna's Archive
09. Qual é o custo real de WIP alto numa carteira onde o gargalo não é gente, mas o tempo de decisão de um único humano — a teoria de filas e o kanban de portfolio seguram essa transposição, ou o modelo quebra quando o servidor é o decisor?
   tipo: complexa · esperada: *nenhuma*
10. Secretaria-executiva que triageia vida pessoal E trabalho no mesmo funil: a literatura de GTD/priorização sustenta um sistema único de captura, ou há evidência de que misturar contextos degrada a triagem — e qual desenho minimiza o custo de troca de contexto do Pedro?
   tipo: complexa · esperada: Getting Things Done

### claudinho-arquiteto

01. Qual é a sequência de passos que o Nygard prescreve para escrever um ADR — campos obrigatórios, ordem e critério de quando um registro merece existir?
   tipo: simples · esperada: Fundamentals of Software Architecture (2025) ⚠️
02. Quais são os quatro tipos de topologia de time definidos em Team Topologies e os três modos de interação permitidos entre eles?
   tipo: simples · esperada: Team Topologies_ Organizing Business and Technology for Fast -- Matthew Skelton, Manuel Pais -- 2, 2025 -- IT Revolution -- isbn13 9781966280002 -- 224c48d665a00d96c55fe8fb334039c3 -- Anna's Archive
03. Que critérios o TOGAF estabelece para separar arquitetura de negócio, de dados, de aplicação e de tecnologia — e onde cada artefato mora no ADM?
   tipo: simples · esperada: *nenhuma* ⚠️
04. Quais são os padrões estratégicos de integração entre bounded contexts que o Evans cataloga (customer-supplier, conformist, anticorruption layer etc.) e a definição precisa de cada um?
   tipo: simples · esperada: Domain-Driven Design
05. Que requisitos uma norma de gestão de ativos de informação (tipo ISO 27001 anexo A) impõe sobre classificação e inventário de dados?
   tipo: simples · esperada: ISO/IEC 27001:2022 ⚠️
06. Nosso modelo de personas com cadeiras funcionais mapeia melhor para stream-aligned teams ou para times complicated-subsystem — e o que a fricção observada na fila de mensagens diz sobre a carga cognitiva que a topologia atual impõe?
   tipo: complexa · esperada: Team Topologies_ Organizing Business and Technology for Fast -- Matthew Skelton, Manuel Pais -- 2, 2025 -- IT Revolution -- isbn13 9781966280002 -- 224c48d665a00d96c55fe8fb334039c3 -- Anna's Archive
07. A decisão de manter o modelo ontológico no Knowledge e materializar artefato read-only no Core é um caso de published language, de open-host service, ou de nenhum dos dois — e que consequências o padrão escolhido impõe sobre versionamento do artefato?
   tipo: complexa · esperada: Domain-Driven Design
08. Onde a fronteira entre governança de dados (plano diretor, meu recorte) e engenharia de dados (pipeline, recorte alheio) passa quando o mesmo artefato — índice vetorial — é simultaneamente produto de pipeline e objeto de política de acesso?
   tipo: complexa · esperada: DMBOK
09. O princípio de não-reciprocidade de esforço (absorver O(N) para dar O(1) ao integrador) tem paralelo em alguma teoria econômica de plataforma — custos de transação, efeitos de rede — que permita prever quando ele deixa de compensar?
   tipo: complexa · esperada: Platform Scale ⚠️
10. Se o critério de identidade é conteúdo (hash) e não nome, que implicações isso tem sobre a modelagem de agregados: o objeto digital é entidade ou value object, e o que a resposta muda no desenho do repositório?
   tipo: complexa · esperada: Implementing Domain-Driven Design

### claudinho-conhecimento (inclui itens 11–20 da OSINT, extensão da cadeira)

01. Qual o procedimento passo a passo do e-ARQ Brasil para definir prazo de retenção e destinação de um documento arquivístico digital?
   tipo: simples · esperada: e-ARQ Brasil
02. Quais são os requisitos formais que a ABNT/ISO impõe para que um vocabulário controlado seja considerado tesauro (relações BT/NT/RT, notas de escopo, forma de entrada)?
   tipo: simples · esperada: z39-19-2005r2010
03. Como se declara em SKOS a diferença entre skos:broader e skos:broaderTransitive, e quando usar cada um num esquema de conceitos?
   tipo: simples · esperada: SKOS
04. Qual a convenção da ISAD(G) para descrição multinível de um fundo — o que é obrigatório em cada nível e o que não pode se repetir entre níveis?
   tipo: simples · esperada: *nenhuma* ⚠️
05. Quais os critérios do BFO para decidir se uma entidade é continuant ou occurrent, e como isso se traduz em regra prática de modelagem de classe?
   tipo: simples · esperada: Building_Ontologies_with_Basic_Formal_On
06. Se a teia de conceitos mostra dois conceitos com coocorrência muito acima do esperado no modelo nulo, quando isso justifica fusão dos conceitos, quando justifica criar um conceito-pai, e quando é só artefato da curadoria de 3 conceitos por obra?
   tipo: complexa · esperada: *nenhuma* ⚠️
07. Um domínio do acervo com poucas obras mas alta centralidade na projeção do grafo — isso indica domínio estruturante que merece investimento de curadoria, ou distorção estatística do corpus pequeno? Que evidência de fora da ontologia (aquisição, uso, RAG) precisaria entrar na decisão?
   tipo: complexa · esperada: *nenhuma*
08. Onde termina a competência do vocabulário canônico e começa a do modelo de embeddings: quando um par de termos que a ontologia distingue mas o espaço vetorial não separa é problema de vocabulário, e quando é problema de modelo?
   tipo: complexa · esperada: Fichamento: O contrato do espaço vetorial
09. Anti-padrões ontológicos tipo os de Sales & Guizzardi (ex.: relação entre tipos que deveria ser entre instâncias) — quais deles são detectáveis mecanicamente num esquema Cargo/SQL como o nosso, e quais exigem juízo humano por dependerem de intenção de modelagem?
   tipo: complexa · esperada: Ontological anti-patterns: Empirically uncovered error-prone structures in ontology-driven conceptual models
10. Ao classificar obra normativa que foi revogada mas é citada por obras vigentes do acervo, o compromisso ontológico correto é registrá-la como espécie própria, como estado do ciclo de vida, ou como relação entre obras — e o que cada escolha custa para o RAG e para a recuperação arquivística?
   tipo: complexa · esperada: The Intellectual Foundation of Information Organization -- Svenonius, Elaine -- Digital libraries and electronic publishing, 1st MIT Press -- The MIT -- isbn13 9780262194334 -- 0c56bc153bf168d2e0e0a9698fa463e1 -- Anna's Archive
11. Qual sequência de ferramentas recupera a camada de texto de um PDF escaneado em alfabeto cirílico com xref corrompido, e em que ordem qpdf, gs e ocrmypdf entram sem destruir o metadado original?
   tipo: simples · esperada: *nenhuma* ⚠️
12. Quais campos o padrão WARC 1.1 exige num registro de tipo `response` para que a captura valha como prova de que a página existia naquele conteúdo naquela hora?
   tipo: simples · esperada: *nenhuma* ⚠️
13. Como o Tesseract decide segmentação de página (PSM) e qual modo usar para documento em coluna dupla com tabela embutida?
   tipo: simples · esperada: *nenhuma* ⚠️
14. Que diretivas do robots.txt o Protego reconhece além de Allow/Disallow, e como ele resolve conflito entre regras de comprimento igual?
   tipo: simples · esperada: *nenhuma* ⚠️
15. Qual a diferença estrutural entre o content stream de um PDF "nato-digital" e um gerado por impressão virtual, e como isso afeta a extração de tabelas com pdfplumber?
   tipo: simples · esperada: *nenhuma* ⚠️
16. Dado um corpus de normas técnicas em três idiomas com títulos transliterados de forma inconsistente, como desenhar um pipeline de deduplicação que combine normalização Unicode, transliteração reversa e casamento fuzzy sem colapsar normas distintas da mesma família?
   tipo: complexa · esperada: Ontology Matching ⚠️
17. Ao propor um esquema de classificação para um fundo documental misto (código, ata, norma, fichamento), onde termina o princípio arquivístico da proveniência e começa a ontologia formal — e quando os dois entram em contradição direta, qual cede?
   tipo: complexa · esperada: *nenhuma*
18. Agregar registros públicos dispersos sobre uma organização cria um dado novo que nenhuma fonte individual continha: em que ponto essa síntese muda o regime jurídico do tratamento, e como documentar a procedência de uma inferência que não está escrita em lugar nenhum?
   tipo: complexa · esperada: *nenhuma* ⚠️
19. Um site serve conteúdo diferente conforme fingerprint do cliente (cloaking): como desenhar uma captura que registre as variantes com valor probatório, sem cruzar a linha da não-atribuição declarada — e o que fazer quando as duas exigências se contradizem?
   tipo: complexa · esperada: *nenhuma*
20. Para estimar a completude de uma coleta contra um universo desconhecido (quantos documentos existem que eu não achei), que métodos de captura-recaptura ou estimativa de cauda se transferem da ecologia e da bibliometria para OSINT documental, e quais premissas quebram na transferência?
   tipo: complexa · esperada: *nenhuma* ⚠️

### claudinho-IA

01. Qual a sequência exata de estágios do pipeline de indexação que o BGE-M3 recomenda para corpus multilíngue, e quais parâmetros de chunking a documentação oficial fixa como default?
   tipo: simples · esperada: M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation ⚠️
02. Que campos o RRF (Reciprocal Rank Fusion) original de Cormack et al. define, e qual o valor canônico da constante k na fórmula publicada?
   tipo: simples · esperada: Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods
03. Quais são os passos prescritos pelo MCP spec para o handshake de capability negotiation entre cliente e servidor, incluindo o que é obrigatório declarar em `initialize`?
   tipo: simples · esperada: mcp-spec-2026-07-28
04. Que métricas o TREC define formalmente para avaliação de retrieval com julgamentos graduados, e como o nDCG é computado passo a passo segundo a formulação de Järvelin & Kekäläinen?
   tipo: simples · esperada: An Introduction to Information Retrieval ⚠️
05. Qual o procedimento documentado para quantização GGUF de um modelo transformer (ordem das operações, formatos intermediários, flags relevantes) segundo o guia do llama.cpp?
   tipo: simples · esperada: *nenhuma* ⚠️
06. Dado um corpus normativo onde a mesma cláusula aparece em versões sucessivas da norma (ISO 27001:2013 vs :2022), como desenhar o retrieval para que a versão vigente domine o ranking sem apagar a anterior — e que trade-off isso impõe entre recall temporal e precisão, considerando o que a literatura de IR temporal diz sobre decay functions?
   tipo: complexa · esperada: *nenhuma* ⚠️
07. Em que ponto a degradação de contexto num loop agêntico longo (lost-in-the-middle, atenção diluída) deixa de ser problema de política de contexto e vira problema de arquitetura do modelo — e o que os papers de long-context attention (posições rotativas, sliding window, atenção esparsa) implicam para onde cortar a fita?
   tipo: complexa · esperada: *nenhuma* ⚠️
08. Como reconciliar o embedder contract (mesmos pesos, mesma normalização) com fine-tuning contrastivo do embedder sobre corpus próprio: o que a literatura de domain adaptation para dense retrieval diz sobre quando o ganho de especialização compensa quebrar a compatibilidade com o índice existente, e como medir isso antes de reindexar?
   tipo: complexa · esperada: Pretrained Transformers for Text Ranking: BERT and Beyond
09. Num sistema multiagente supervisor/hierárquico, quando a falha de um subagente deve propagar como erro ao supervisor versus ser reabsorvida com retry local — e o que a teoria de sistemas distribuídos (circuit breakers, bulkheads, supervision trees do Erlang/OTP) transporta ou não transporta para loops de LLM não-determinísticos?
   tipo: complexa · esperada: Release it!_ design and deploy production-ready software -- Michael T_ Nygard -- The pragmatic programmers, Raleigh, N_C, North Carolina, -- Pragmatic -- isbn13 9780978739218 -- 93af097dc316b957068154ab9d210307 -- Anna's Archive ⚠️
10. Qual o ponto de equilíbrio entre quantização agressiva (Q4 vs Q8) e degradação de qualidade em tool-calling estruturado num modelo 14B servindo localmente — e como os benchmarks de perplexidade se relacionam (ou falham em se relacionar) com taxa de erro de JSON malformado e alucinação de schema em uso agêntico real?
   tipo: complexa · esperada: *nenhuma* ⚠️

### claudinha-produto

01. Qual é a sequência de passos que o Continuous Discovery Habits prescreve para montar e manter uma opportunity solution tree — da definição do outcome até a priorização das oportunidades?
   tipo: simples · esperada: Continuous Discovery Habits
02. Quais são os critérios formais que uma user story precisa cumprir segundo o padrão INVEST, e como cada critério se verifica na prática?
   tipo: simples · esperada: *nenhuma* ⚠️
03. Qual é o procedimento completo de um teste de usabilidade moderado — recrutamento, roteiro, condução e síntese — conforme descrito em guia clássico de UX research?
   tipo: simples · esperada: Don't Make Me Think, Revisited_ A Common Sense Approach to -- Krug, Steve -- Voices That Matter, 3rd Edition, 2013 -- chenjin5_com 万千书友聚集地 -- 8829b1f4be50f8eec5fbb20f207ebe55 -- Anna's Archive ⚠️
04. Quais heurísticas de avaliação de interface compõem o conjunto canônico de Nielsen e qual é o protocolo de aplicação de uma avaliação heurística com múltiplos avaliadores?
   tipo: simples · esperada: Heuristic_Summary1_A4_compressed ⚠️
05. Como se estrutura um documento de posicionamento de produto segundo o framework da April Dunford (Obviously Awesome) — quais componentes, em que ordem, e o que alimenta cada um?
   tipo: simples · esperada: *nenhuma* ⚠️
06. Como priorizar o backlog de um produto B2B de nicho quando as métricas de engajamento ainda não têm massa estatística — que sinais qualitativos substituem quantitativos com validade, e onde essa substituição quebra?
   tipo: complexa · esperada: The Mom Test -- Rob Fitzpatrick -- ad8211428498baf5e6197a2579e4acf2 -- Anna's Archive
07. Num produto cuja interface é mediada por modelo de linguagem, como separar problema de usabilidade de problema de capability do modelo na análise de uma sessão que falhou — e que evidência decide entre redesenhar a interação ou trocar/ajustar o modelo?
   tipo: complexa · esperada: Hamel Husain - LLM Evals FAQ (snapshot 2026-08-01)
08. Quando a arquitetura de informação do produto precisa espelhar uma ontologia mantida por outra área, como o design de interface absorve mudanças ontológicas sem quebrar o modelo mental do usuário — e onde fica a fronteira entre decisão de IA (informação) e decisão de ontologia?
   tipo: complexa · esperada: Information_Architecture_For_The_Web_And_Beyond_Fourth_Edition
09. Como definir critérios de saída de MVP para um produto de gestão de conhecimento cujo valor só aparece com corpus acumulado — que proxy de valor antecede o efeito de rede interno, e como distinguir adoção genuína de uso por obrigação?
   tipo: complexa · esperada: Platform Scale ⚠️
10. Em produto operado por agentes de IA além de humanos, o que muda no conceito de "usuário" para pesquisa e design — as técnicas de discovery valem para persona sintética, e que parte da teoria de jobs-to-be-done sobrevive quando o job é delegado a um agente?
   tipo: complexa · esperada: *nenhuma*

### claudinho-TI

01. Qual é o conjunto mínimo de práticas técnicas que o corpo DORA/Accelerate valida como preditoras de desempenho de entrega, e como cada uma é medida?
   tipo: simples · esperada: Accelerate
02. Que perguntas o pilar de Excelência Operacional do AWS Well-Architected 2024 manda responder antes de aprovar uma mudança em produção?
   tipo: simples · esperada: wellarchitected-framework-2024-06-27
03. Segundo Newman (Building Microservices 2nd), quais são os critérios para escolher entre deploy blue-green, canary e rolling, e o que cada um exige de infraestrutura?
   tipo: simples · esperada: Building Microservices (2nd)
04. Como o Kafka: The Definitive Guide define a política de retenção de log por tamanho vs. por tempo, e qual o efeito de cada uma sobre consumidores atrasados?
   tipo: simples · esperada: Kafka: The Definitive Guide
05. Quais métricas de fluxo o relatório DORA 2025 de desenvolvimento assistido por IA acrescenta ou reinterpreta em relação às quatro métricas clássicas?
   tipo: simples · esperada: 2025_state_of_ai_assisted_software_development
06. Num host único sem orquestrador, que combinação de práticas de release (trunk-based, feature flag, rollback por imagem) reproduz o efeito de "deploy desacoplado de release" que a literatura de entrega contínua assume — e onde a reprodução quebra?
   tipo: complexa · esperada: Building Microservices (2nd) ⚠️
07. Como aplicar back pressure (Continuous Architecture in Practice) num pipeline de embedding batch onde o produtor é um extractor síncrono e o consumidor é uma GPU compartilhada com outra carga — e em que ponto isso deixa de ser problema de arquitetura e vira problema de dados (fronteira com o arquiteto)?
   tipo: complexa · esperada: Continuous Architecture in Practice
08. Se a plataforma adotar comunicação por eventos entre personas em vez de fila de arquivos, que garantias de ordenação e idempotência a literatura de event-driven exige que o consumidor assuma, e o que disso a fila de arquivos atual já entrega de graça?
   tipo: complexa · esperada: Building Event-Driven Microservices
09. Que controles do domínio de segurança (hardening de contêiner, verificação de assinatura, escaneamento de dependência) têm interseção com o pipeline de build a ponto de precisarem entrar no desenho da fábrica — e onde termina a minha decisão e começa a do claudinho-seguranca?
   tipo: complexa · esperada: nist.sp.800-218
10. Como reconciliar a métrica de change failure rate com um ambiente onde o "deploy" é um `docker compose up` sem gate formal: o que a literatura de mudança controlada exige de mínimo para a métrica sequer ser mensurável?
   tipo: complexa · esperada: Accelerate ⚠️

### claudinho-seguranca

01. Qual é o procedimento completo de rotação de chaves de assinatura (realm keys) no Keycloak sem invalidar sessões ativas, e qual a ordem correta entre criar a chave nova, rebaixar a antiga e removê-la?
   tipo: simples · esperada: *nenhuma* ⚠️
02. Quais são os requisitos exatos do NIST SP 800-63B para AAL2 em matéria de resistência a replay, prova de posse e intervalo de reautenticação?
   tipo: simples · esperada: NIST SP 800-63B-4 — Authentication
03. Qual é a diferença normativa entre `aud`, `azp` e `resource` no RFC 8707 (Resource Indicators) e como o OIDC Core trata audience em ID token versus access token?
   tipo: simples · esperada: Final_ OpenID Connect Core 1.0 incorporating errata set 2 ⚠️
04. Quais controles do CIS Controls v8 no IG1 cobrem gestão de contas e gestão de acesso (Controls 5 e 6), e quais safeguards exigem inventário de contas de serviço?
   tipo: simples · esperada: CIS Controls v8
05. Qual é o ciclo de vida de chave recomendado pelo NIST SP 800-57 Part 1 — períodos de uso (originator-usage vs recipient-usage), estados da chave e cryptoperiods sugeridos por tipo de chave?
   tipo: simples · esperada: nist.sp.800-57pt1r5
06. Num broker OIDC single-node como o nosso, a partir de que ponto a indisponibilidade do IdP federado (Google) deveria disparar um modo degradado local — e o que a literatura de resiliência diz sobre trade-off entre cache de sessão longa e janela de revogação, considerando que sessão longa é decisão de disponibilidade que corrói a garantia de revogação (AAL/FAL)?
   tipo: complexa · esperada: Release it!_ design and deploy production-ready software -- Michael T_ Nygard -- The pragmatic programmers, Raleigh, N_C, North Carolina, -- Pragmatic -- isbn13 9780978739218 -- 93af097dc316b957068154ab9d210307 -- Anna's Archive ⚠️
07. Se o token carrega `dominio:papel:escopo` como tupla plana e o downscoping recorta por frente, qual é o custo formal de expressividade em relação a um modelo ABAC completo do SP 800-162 — que classes de política se tornam inexpressáveis, e isso importa antes de existir um segundo sujeito no sistema?
   tipo: complexa · esperada: nist.sp.800-162
08. Migração híbrida PQC no nosso TLS de borda (Cloudflare na frente, tunnel no meio, serviços atrás): onde exatamente x25519_mlkem768 protege contra harvest-now-decrypt-later e onde não protege nada, dado que o túnel termina TLS em pontos que não controlamos?
   tipo: complexa · esperada: Relatório Executivo_ A Transição para a Criptografia Pós-Quântica (PQC) e a Proteção das Infraestruturas Críticas no Brasil ⚠️
09. O modelo de isolamento entre `megafone` e `claudinho` remove escalação por grupo, mas o MCP é um canal de execução arbitrária como `claudinho` — sob que modelo de ameaça (prompt injection na cadeia de contexto, comprometimento do cliente MCP) o isolamento de conta ainda vale alguma coisa, e o que a literatura de confused deputy diz sobre isso?
   tipo: complexa · esperada: Security Engineering_ A Guide to Building Dependable -- Ross J_ Anderson ⚠️
10. Para um sistema single-user, qual é o ponto de inflexão mensurável em que logging de auditoria (CIS Control 8) deixa de ser teatro de conformidade e passa a ter valor forense real — e como dimensionar retenção quando o atacante plausível é o próprio operador da infraestrutura ou seu agente de IA?
   tipo: complexa · esperada: *nenhuma*
