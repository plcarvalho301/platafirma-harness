1. Qual é a sequência de passos que o Nygard prescreve para escrever um ADR — campos obrigatórios, ordem e critério de quando um registro merece existir?
   tipo: simples
   esperada: Fundamentals of Software Architecture (2025)   [corrigido — dono propôs "adr1" com confiança baixa e perguntou se deveria abrir para confirmar; conferi por fora (query_cargo: "adr1"/"adr2" sem registro em Referencias, sem espécie/domínio — obras cruas; rag_search "como escrever um ADR" devolve Fundamentals of Software Architecture cap.21 como as 5 fontes de topo, "adr1"/"adr2" não aparecem). É o fallback que o dono já tinha nomeado, promovido a principal.]

2. Quais são os quatro tipos de topologia de time definidos em Team Topologies e os três modos de interação permitidos entre eles?
   tipo: simples
   esperada: Team Topologies_ Organizing Business and Technology for Fast -- Matthew Skelton, Manuel Pais -- 2, 2025 -- IT Revolution -- isbn13 9781966280002 -- 224c48d665a00d96c55fe8fb334039c3 -- Anna's Archive

3. Que critérios o TOGAF estabelece para separar arquitetura de negócio, de dados, de aplicação e de tecnologia — e onde cada artefato mora no ADM?
   tipo: simples
   esperada: nenhuma — seria The TOGAF Standard (10th Edition)

4. Quais são os padrões estratégicos de integração entre bounded contexts que o Evans cataloga (customer-supplier, conformist, anticorruption layer etc.) e a definição precisa de cada um?
   tipo: simples
   esperada: Domain-Driven Design

5. Que requisitos uma norma de gestão de ativos de informação (tipo ISO 27001 anexo A) impõe sobre classificação e inventário de dados?
   tipo: simples
   esperada: ISO/IEC 27001:2022   [dono flagou par secundário: detalhamento dos controles mora mais na ISO/IEC 27002:2013, ausente do casamento]

6. Nosso modelo de personas com cadeiras funcionais mapeia melhor para stream-aligned teams ou para times complicated-subsystem — e o que a fricção observada na fila de mensagens diz sobre a carga cognitiva que a topologia atual impõe?
   tipo: complexa
   esperada: Team Topologies_ Organizing Business and Technology for Fast -- Matthew Skelton, Manuel Pais -- 2, 2025 -- IT Revolution -- isbn13 9781966280002 -- 224c48d665a00d96c55fe8fb334039c3 -- Anna's Archive

7. A decisão de manter o modelo ontológico no Knowledge e materializar artefato read-only no Core é um caso de published language, de open-host service, ou de nenhum dos dois — e que consequências o padrão escolhido impõe sobre versionamento do artefato?
   tipo: complexa
   esperada: Domain-Driven Design

8. Onde a fronteira entre governança de dados (plano diretor, meu recorte) e engenharia de dados (pipeline, recorte alheio) passa quando o mesmo artefato — índice vetorial — é simultaneamente produto de pipeline e objeto de política de acesso?
   tipo: complexa
   esperada: DMBOK

9. O princípio de não-reciprocidade de esforço (absorver O(N) para dar O(1) ao integrador) tem paralelo em alguma teoria econômica de plataforma — custos de transação, efeitos de rede — que permita prever quando ele deixa de compensar?
   tipo: complexa
   esperada: Platform Scale   [dono flagou: cobre efeitos de rede, não o recorte de custos de transação (Coase/Williamson) — segue parcialmente no estrato negativo mesmo casada]

10. Se o critério de identidade é conteúdo (hash) e não nome, que implicações isso tem sobre a modelagem de agregados: o objeto digital é entidade ou value object, e o que a resposta muda no desenho do repositório?
    tipo: complexa
    esperada: Implementing Domain-Driven Design

# nenhuma: 1 (item 3) — sugestão de aquisição do dono: The TOGAF Standard (10th Edition)
