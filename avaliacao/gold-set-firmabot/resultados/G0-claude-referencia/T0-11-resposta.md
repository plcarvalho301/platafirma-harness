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
