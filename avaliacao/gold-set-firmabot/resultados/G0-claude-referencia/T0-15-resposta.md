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
