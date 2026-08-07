## Continuant e Occurrent

**Continuant** — definição: uma entidade que persiste, perdura ou continua a existir através do tempo mantendo sua identidade.
*(Transcrito da fonte [1], BFO2-Reference.docx › Specification › Continuant, Elucidation [008-002].)*

**Occurrent** — definição: uma entidade que se desdobra no tempo, ou é a fronteira instantânea de uma entidade desse tipo (por exemplo um começo ou um fim), ou é uma região temporal/espaço-temporal que tal entidade ocupa (occupies_temporal_region / occupies_spatiotemporal_region).
*(Transcrito da fonte [2], BFO2-Reference.docx › Specification › Occurrent, Elucidation [077-002].)*

### A dicotomia entre os dois

A distinção é o eixo organizador central do BFO e deriva de Zemach: continuants só podem ser "fatiados" ao longo da dimensão espacial (por exemplo, as partes de uma mesa — pernas, tampo), mas não da dimensão temporal; occurrents (que Zemach chama de "eventos") podem ser fatiados tanto no espaço quanto no tempo.
*(Transcrito/derivado da fonte [3], BFO2-Reference.docx › The dichotomy of 'continuant' and 'occurrent'.)*

Complementando, a fonte [1] traz a mesma ideia do lado dos continuants: se um occurrent ocupa uma região temporal de 2 minutos, ele é a soma de duas partes temporais não sobrepostas de 1 minuto cada; **continuants não têm partes temporais nesse sentido** — eles preservam identidade mesmo ganhando e perdendo partes materiais, enquanto occurrents se desdobram em partes ou fases temporais sucessivas.
*(Transcrito da fonte [1].)*

### Observação sobre parthood

As duas famílias de entidades têm relações de parte-todo tratadas separadamente no BFO: `continuant_part_of` (com sufixo `at t`, já que a composição de um continuant pode variar no tempo) versus `occurrent_part_of` (sem esse sufixo, pois um occurrent não muda quem são suas partes ao longo do tempo da mesma forma).
*(Transcrito/derivado das fontes [4] e [6].)*

Não usei a fonte [5] para sustentar conteúdo — é uma entrada de sumário (número de seção e página), sem matéria substantiva.