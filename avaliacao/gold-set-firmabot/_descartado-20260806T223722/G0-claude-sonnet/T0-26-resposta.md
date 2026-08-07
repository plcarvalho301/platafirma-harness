## Definição

Trunk-based development é a prática de todo mundo integrar (check in) no mesmo "tronco" (trunk) do controle de versão, evitando branches de longa duração para features. Para não impactar os demais enquanto um trabalho está incompleto, usam-se técnicas como feature flags para "esconder" código ainda não pronto.

*(Transcrito — Sam Newman, "Building Microservices" (2nd ed.), Chapter 7. Build › A Brief Introduction to Continuous Integration › Branching Models)*

## Critérios que caracterizam a prática

Segundo o livro *Accelerate* (Cap. 10 — Trunk-Based Development), as equipes que fazem trunk-based development com bons resultados apresentam:

- menos de três branches ativas a qualquer momento;
- branches com vida muito curta (menos de um dia) antes do merge no trunk;
- ausência de períodos de "code freeze" ou estabilização.

*(Transcrito — Accelerate: The Science of Lean Software and DevOps, Chapter 10, seção Trunk-Based Development)*

O State of DevOps Report 2017 traz os mesmos critérios de forma quase idêntica: merge no trunk pelo menos diariamente, branches com menos de um dia de vida, menos de três branches ativas, e ausência de "code lock periods".

*(Transcrito — 2017 State of DevOps Report, seção practices › Trunk-based development)*

## Relação com desempenho de entrega

*Accelerate* afirma que desenvolver a partir do trunk/master, em vez de branches de longa duração, está correlacionado com desempenho de entrega mais alto, e que esse resultado é independente do tamanho da equipe, do tamanho da organização ou da indústria.

*(Transcrito — Accelerate, Cap. 10, mesma seção)*

O DORA Report 2021 lista trunk-based development como uma das capacidades técnicas de DevOps medidas, ao lado de arquitetura fracamente acoplada, integração contínua e testes contínuos.

*(Transcrito/derivado — 2021 DORA Accelerate State of DevOps Report, Chapter 3 › Technical DevOps capabilities)*

## Nuance sobre experiência da equipe

O DORA Report 2022 observa que o benefício da prática depende de disciplina: equipes sem regras rigorosas contra deixar o trunk quebrado, ou sem branches com gate e rollback automático quando o trunk quebra, sofrem. O relatório também associa mais anos de experiência dos profissionais a melhores resultados com a prática; equipes com menos experiência tendem a ver *queda* no desempenho de entrega ao tentar aplicá-la.

*(Transcrito — 2022 DORA Accelerate State of DevOps Report, seção 05 Surprises › Trunk-based development)*

## Observação sobre uma fonte

A fonte [1] (2023 DORA Report) chegou apenas como repetição de títulos de seção ("• Trunk-based development" listado várias vezes) sem trecho de conteúdo substantivo — não sustenta nenhuma afirmação e foi deixada de fora.

A fonte [3] (Shifting Left, 2016 State of DevOps Report) trata de um conceito vizinho (qualidade construída cedo no ciclo), não de trunk-based development, e por isso não foi usada aqui. A fonte [4] é introdução genérica de "Technical Practices" sem tratar do conceito específico, também deixada de fora.