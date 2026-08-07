## Definição

**Chunking** (ou *data splitting*) é o processo de quebrar textos longos em segmentos gerenciáveis, dentro do pipeline de indexação de um sistema RAG.

*Transcrito de* [1] *A Simple Guide to Retrieval Augmented Generation* — 3 Indexing pipeline: Creating a knowledge base for RAG › 3.2 Data splitting (chunking): "Breaking down long pieces of text to manageable segments is called data splitting or chunking."

## Por que chunking existe

*Transcrito de* [5] (mesma obra, seção Summary): chunking endereça os limites de janela de contexto dos LLMs, mitiga o problema de "lost-in-the-middle" em prompts longos, e viabiliza busca e recuperação mais eficazes.

## O processo de chunking

*Transcrito de* [4] *A Simple Guide to Retrieval Augmented Generation* — 3.2.2 Chunking process › Figure 3.2, o processo tem três etapas:
1. dividir o texto longo em unidades compactas e significativas (frases ou parágrafos);
2. mesclar essas unidades pequenas em chunks maiores até atingir um tamanho-alvo, tratando cada chunk resultante como um segmento independente;
3. ao criar um novo chunk, incluir parte do chunk anterior no início — o *overlap* — para preservar continuidade contextual.

## Métodos de chunking

*Transcrito/derivado de* [6] (3.2.3 Chunking methods): métodos vão de simples a sofisticados —
- métodos simples predeterminam o tamanho do chunk e dividem por caractere (ou, de forma mais refinada, por token);
- métodos especializados são mais adequados a formatos de dado específicos;
- **semantic chunking** é um método experimental que, em vez de tamanho fixo, agrupa por similaridade semântica entre frases — proposto por Greg Kamradt, questionando por que usar tamanho fixo predefinido e por que ignorar o significado real do conteúdo;
- **agentic chunking** é citado como outra técnica experimental na fronteira do tema.

*Transcrito de* [5] (Summary): "Chunking can be fixed size, specialized (or adaptive), or semantic."

## Como escolher a estratégia

*Transcrito de* [3], [7], [8] *A Simple Guide to Retrieval Augmented Generation* — 3.2.4 Choosing a chunking strategy: não há regras fixas ("There are no guidelines or rules to answer this question"), mas certas características da aplicação orientam a escolha:

- **Natureza do caso de uso** ([3]): para question-answering direto, chunks curtos costumam dar resultados mais precisos; para sumarização, chunks mais longos fazem mais sentido. Se a saída alimenta outra aplicação downstream, isso também pesa na escolha.
- **Complexidade e tamanho esperado da query do usuário** ([8]): queries curtas e diretas pedem um tamanho de chunk diferente de queries longas e complexas; casar query longa com chunk curto tende a ser ineficiente, e query curta com chunk grande pode trazer resultados parcialmente irrelevantes.
- **Modelo de embeddings usado** ([7]): certos modelos de embedding performam melhor com chunks de tamanhos específicos.

*Transcrito de* [5] (Summary): "A chunking strategy can include multiple methods" — ou seja, é legítimo combinar mais de um método de chunking na mesma estratégia.

## Observação sobre as fontes

A fonte [2] (Chip Huyen, *AI Engineering*, seção Introduction) trata de embeddings, não de chunking — é vizinho semântico dentro do mesmo pipeline de RAG, mas não responde pela estratégia de chunking em si, então não a usei aqui.