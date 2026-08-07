## Fusão recíproca de rankings (Reciprocal Rank Fusion — RRF)

**Definição** (derivada de [1] e [4], obra *Reciprocal Rank Fusion* de Cormack, SIGIR 2009): RRF é um método não supervisionado — não exige exemplos de treino — para combinar os rankings de documentos produzidos por múltiplos sistemas de recuperação de informação. Ele funde os rankings usando apenas a **posição** (rank) de cada documento em cada lista de entrada, e não os *scores* brutos de cada sistema — o que evita o problema de scores de sistemas diferentes serem incomparáveis entre si. Isso permite que os ranks sejam "computados e somados um sistema por vez", sem precisar manter todos os rankings em memória simultaneamente (transcrito de [4], *References*/discussão final).

**De onde sai**: cormack-rrf-sigir2009.pdf, seção *RECIPROCAL RANK FUSION* [2], com complementos do *ABSTRACT* [1] e da seção final ligada às *References* [4].

**Detalhes que as fontes dão**:
- Transcrito de [1] (*ABSTRACT*): existe uma constante *k* na fórmula de pontuação, cuja função é mitigar o impacto de sistemas que colocam um documento em posição muito alta de forma atípica ("outlier systems"); ao contrário de uma função exponencial, a contribuição de documentos ranqueados mais abaixo "não desaparece".
- Transcrito de [1]: nos experimentos-piloto (30 configurações do Wumpus Search em quatro coleções TREC), *k = 60* mostrou-se próximo do ótimo, mas a escolha não é crítica.
- Transcrito de [2]: RRF "quase invariavelmente melhora sobre o melhor dos resultados combinados", e igualou ou superou Condorcet Fuse e CombMNZ nos testes reportados; em experimentos com submissões reais ao TREC, o MAP de RRF excedeu o de Condorcet Fuse em todos os casos e o de CombMNZ em todos menos um.
- Transcrito de [4]: a vantagem conjecturada de RRF sobre Condorcet Fuse é que RRF "consegue aproveitar melhor a diversidade dentro de rankings individuais" — um ou dois sistemas que ranqueiam um documento muito bem já melhoram substancialmente sua posição relativa, enquanto no Condorcet uma maioria simples de preferências fracas pode sobrepor-se a preferências muito mais fortes.

**Lacuna nas fontes**: o trecho recebido de [2] corta exatamente onde a fórmula de pontuação da RRF seria apresentada ("RRF simply sorts the documents according to a naive scoring formu[la]..."), então **não tenho, nas fontes que chegaram, a expressão matemática exata** (o formato usual $1/(k+\text{rank})$ é conhecimento meu, fora do que as fontes trouxeram — não vou afirmá-lo como vindo do acervo).

As demais fontes do turno ([3] embeddings, [5] análise de inteligência, [6]/[8] arquiteturas de reranking em texto, [7] risco financeiro) não tratam de fusão de rankings e ficaram de fora por não serem pertinentes ao conceito perguntado.