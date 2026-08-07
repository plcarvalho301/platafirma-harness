# Estratégia de chunking

**Definição.** Chunking (também chamado *data splitting*) é o processo de quebrar textos longos em segmentos menores e manejáveis, necessário porque os textos-fonte de um sistema RAG costumam ser longos demais para caber inteiros na janela de contexto de um LLM. *(Transcrito da fonte [1], breadcrumb "3.2 Data splitting (chunking)".)*

Segundo o resumo do capítulo (fonte [5]), chunking resolve três problemas práticos: limites de janela de contexto do LLM, o problema de "lost-in-the-middle" em prompts longos, e facilita busca e recuperação. *(Transcrito.)*

## O processo (3 etapas)

De acordo com a fonte [4] (Figura 3.2 — Data-chunking process), o processo tem três passos:
1. Dividir o texto longo em unidades compactas e com sentido próprio (frases ou parágrafos);
2. Mesclar essas unidades menores em chunks maiores até atingir um tamanho-alvo, tratando cada chunk resultante como um segmento independente;
3. Ao criar um novo chunk, incluir parte do chunk anterior no início, para preservar continuidade contextual (overlap).
*(Transcrito.)*

## Métodos de chunking

A fonte [6] classifica os métodos em ordem crescente de sofisticação:
- **Fixed-size / simples**: tamanho de chunk predeterminado, dividindo por caracteres ou, de forma mais refinada, por tokens;
- **Especializado (specialized/adaptive)**: mais adequado a formatos de dado diferentes (ex.: código, tabelas, markdown);
- **Semântico**: proposto por Greg Kamradt, questiona a necessidade de tamanho fixo e propõe agrupar por similaridade semântica entre frases, olhando o significado real do conteúdo.

O resumo (fonte [5]) reforça essa mesma tripartição: "fixed size, specialized (or adaptive), or semantic", e adiciona que "newer chunking methods are constantly being introduced" e que "a chunking strategy can include multiple methods" — ou seja, não é obrigatório escolher um único método. *(Transcrito.)*

## Critérios para escolher a estratégia

As fontes [3], [7] e [8] são o mesmo trecho-pai (seção "3.2.4 Choosing a chunking strategy") subdividido, e afirmam explicitamente que **não há regras ou diretrizes fixas** para essa escolha — apenas features da aplicação que orientam a decisão:

- **Natureza do caso de uso** (fonte [3]): pergunta-resposta direta pede chunks curtos, para precisão; sumarização tende a se beneficiar de chunks mais longos; se a saída alimenta outra aplicação downstream, isso também influencia a escolha.
- **Modelo de embeddings** (fonte [7]): certos modelos de embedding performam melhor com chunks de tamanhos específicos.
- **Extensão e complexidade esperada da query do usuário** (fonte [8]): queries curtas e diretas pedem chunks de tamanho diferente de queries longas e complexas — casar query longa com chunk curto tende a ser ineficiente, e query curta com chunk grande pode trazer resultados parcialmente irrelevantes.

A fonte [7] fecha dizendo que chunking "não é uma tarefa complicada demais" e que a maioria dos métodos funciona — mas exige avaliação e ajuste conforme os resultados observados. *(Transcrito.)*

---

**Nota sobre as fontes**: a fonte [2] trata de *embeddings* (representação vetorial de texto), que é um conceito vizinho de chunking mas não o mesmo — chunking acontece antes da geração de embeddings, na etapa de divisão do texto. Por isso deixei-a de fora da resposta sobre estratégia de chunking em si; ela seria pertinente a uma pergunta sobre embeddings.

Todas as demais fontes vêm do mesmo livro (Kimothi, *A Simple Guide to Retrieval Augmented Generation*, capítulo 3, seção 3.2), então a resposta reflete a cobertura de uma única obra sobre o tema.
