# obs. do dono ao entregar: "Falando como head aqui — as perguntas cruzam as três gerências."

1. Qual a sequência exata de estágios do pipeline de indexação que o BGE-M3 recomenda para corpus multilíngue, e quais parâmetros de chunking a documentação oficial fixa como default?
   tipo: simples
   esperada: M3-Embedding: Multi-Linguality, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation   [casamento parcial — dono flagou: paper cobre o modelo, não os defaults de chunking da doc oficial (fora do acervo)]

2. Que campos o RRF (Reciprocal Rank Fusion) original de Cormack et al. define, e qual o valor canônico da constante k na fórmula publicada?
   tipo: simples
   esperada: Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods

3. Quais são os passos prescritos pelo MCP spec para o handshake de capability negotiation entre cliente e servidor, incluindo o que é obrigatório declarar em `initialize`?
   tipo: simples
   esperada: mcp-spec-2026-07-28

4. Que métricas o TREC define formalmente para avaliação de retrieval com julgamentos graduados, e como o nDCG é computado passo a passo segundo a formulação de Järvelin & Kekäläinen?
   tipo: simples
   esperada: An Introduction to Information Retrieval   [casamento parcial, mais brando — dono flagou: acervo não tem o paper original de Järvelin & Kekäläinen]

5. Qual o procedimento documentado para quantização GGUF de um modelo transformer (ordem das operações, formatos intermediários, flags relevantes) segundo o guia do llama.cpp?
   tipo: simples
   esperada: nenhuma — seria a documentação do llama.cpp (guia de quantização GGUF)

6. Dado um corpus normativo onde a mesma cláusula aparece em versões sucessivas da norma (ISO 27001:2013 vs :2022), como desenhar o retrieval para que a versão vigente domine o ranking sem apagar a anterior — e que trade-off isso impõe entre recall temporal e precisão, considerando o que a literatura de IR temporal diz sobre decay functions?
   tipo: complexa
   esperada: nenhuma — seria uma obra de temporal information retrieval (ex.: Campos et al., Survey of Temporal IR)

7. Em que ponto a degradação de contexto num loop agêntico longo (lost-in-the-middle, atenção diluída) deixa de ser problema de política de contexto e vira problema de arquitetura do modelo — e o que os papers de long-context attention (posições rotativas, sliding window, atenção esparsa) implicam para onde cortar a fita?
   tipo: complexa
   esperada: nenhuma — seriam os papers de long-context attention (RoFormer/RoPE, Longformer, lost-in-the-middle de Liu et al.)

8. Como reconciliar o embedder contract (mesmos pesos, mesma normalização) com fine-tuning contrastivo do embedder sobre corpus próprio: o que a literatura de domain adaptation para dense retrieval diz sobre quando o ganho de especialização compensa quebrar a compatibilidade com o índice existente, e como medir isso antes de reindexar?
   tipo: complexa
   esperada: Pretrained Transformers for Text Ranking: BERT and Beyond

9. Num sistema multiagente supervisor/hierárquico, quando a falha de um subagente deve propagar como erro ao supervisor versus ser reabsorvida com retry local — e o que a teoria de sistemas distribuídos (circuit breakers, bulkheads, supervision trees do Erlang/OTP) transporta ou não transporta para loops de LLM não-determinísticos?
   tipo: complexa
   esperada: Release it!_ design and deploy production-ready software -- Michael T_ Nygard -- The pragmatic programmers, Raleigh, N_C, North Carolina, -- Pragmatic -- isbn13 9780978739218 -- 93af097dc316b957068154ab9d210307 -- Anna's Archive   [casamento parcial — dono flagou: só a metade "sistemas distribuídos" é do Nygard; a metade "loops de LLM" tem apoio parcial em snapshots Anthropic Engineering, fora do acervo formal]

10. Qual o ponto de equilíbrio entre quantização agressiva (Q4 vs Q8) e degradação de qualidade em tool-calling estruturado num modelo 14B servindo localmente — e como os benchmarks de perplexidade se relacionam (ou falham em se relacionar) com taxa de erro de JSON malformado e alucinação de schema em uso agêntico real?
    tipo: complexa
    esperada: nenhuma — seria benchmark/paper de efeito de quantização em structured output (sem título canônico único)

# nenhuma: 4 (itens 5, 6, 7, 10) — item 10 sem candidato de aquisição por falta de título único
