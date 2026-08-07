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
