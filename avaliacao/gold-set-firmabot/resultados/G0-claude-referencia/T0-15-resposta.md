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
