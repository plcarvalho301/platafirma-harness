**Fusão recíproca de rankings (Reciprocal Rank Fusion — RRF)**

RRF é um método não supervisionado e simples para combinar os rankings de documentos produzidos por múltiplos sistemas de recuperação de informação (RI), pontuando cada documento pela soma dos recíprocos de sua posição em cada ranking de entrada (com uma constante `k` que amortece o impacto de posições muito altas dadas por sistemas discrepantes/outliers). — transcrito e derivado de [1] e [2] (*cormack-rrf-sigir2009* › ABSTRACT e RECIPROCAL RANK FUSION).

Pontos que as fontes sustentam:

- **Objetivo**: servir como baseline não supervisionado — "não requer exemplos de treino" — para combinar resultados de múltiplos sistemas de IR (incluindo métodos de learning-to-rank). Transcrito de [2].
- **Resultado empírico**: RRF "quase invariavelmente melhora sobre o melhor dos resultados combinados" e igualou ou superou consistentemente outros métodos de metaranking, como Condorcet Fuse e CombMNZ, em experimentos com quatro conjuntos de submissões ao TREC. O MAP do RRF superou o Condorcet Fuse em todos os casos, e o CombMNZ em quase todos. Transcrito de [2].
- **Comparação com Condorcet Fuse**: Condorcet Fuse combina rankings ordenando documentos por relação de pares determinada por voto majoritário entre os rankings de entrada — e pode ser dominado por uma maioria de preferências fracas que anula preferências individuais mais fortes. RRF, ao contrário, soma ranks sem olhar para os scores arbitrários de cada método, permite que um ou dois sistemas que rankeiam um documento muito bem melhorem substancialmente sua posição relativa aos documentos "populares", e não exige algoritmo de votação especial nem manter todos os rankings em memória simultaneamente (ranks podem ser somados um sistema por vez). Transcrito/derivado de [4] (seção References, que traz também texto de discussão) e [1] (ABSTRACT, fórmula de comparação com CombMNZ).
- **CombMNZ**, citado como outro método comparado, usa para cada ranking uma função de scoring `s_r: D → R` e um corte de rank `c`, combinando pela soma dos scores multiplicada pela contagem de rankings em que o documento aparece dentro do corte. Transcrito de [1].

Onde sai: *Reciprocal Rank Fusion (RRF)*, artigo de Cormack, seções ABSTRACT, RECIPROCAL RANK FUSION e References (SIGIR 2009).

As demais fontes do turno ([3], [5], [6], [7], [8]) não tratam de fusão recíproca de rankings — [6] e [8] cobrem ranking de texto em geral (arquitetura multi-estágio, avaliação Cranfield), o que é vizinho semântico mas não o conceito exato; [3] é sobre embeddings; [5] e [7] são de domínios completamente distintos (análise de inteligência e risco financeiro).
