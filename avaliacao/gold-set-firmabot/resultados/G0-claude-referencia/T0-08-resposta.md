**Definição**

Criptografia Pós-Quântica (PQC) é a defesa primária contra a ameaça representada pela computação quântica: ela usa algoritmos matemáticos que se acredita serem seguros mesmo contra o poder de processamento de computadores quânticos. *(Transcrito de [1] — Ameaça da Computação Quântica e a Transição para a Criptografia Pós-Quântica: Relatório Executivo de Segurança › Criptografia Pós-Quântica (PQC) e Mitigação.)*

**Por que ela existe (a ameaça que motiva)**

Algoritmos quânticos como o de Shor conseguem quebrar a maioria dos sistemas de criptografia assimétrica usados hoje (RSA, ECC), que dependem da dificuldade de fatorar números grandes ou resolver o problema do logaritmo discreto — problemas que um computador quântico resolve de forma eficiente. Já o algoritmo de Grover afeta a criptografia simétrica, exigindo o dobro do tamanho de chave (ex.: AES-256) para manter o nível de segurança atual. *(Transcrito/derivado de [4] — OSIC 15/2024 › 3.2 Desafios da Computação Quântica › 3.2.1 Quebra da criptografia assimétrica; e de [8] — Relatório Executivo PQC e Infraestruturas Críticas › 1. Ameaça e Contexto Estratégico.)*

Essa urgência é reforçada pela ameaça "Harvest Now, Decrypt Later" (HNDL/SNDL): adversários já interceptam e armazenam hoje dados cifrados classicamente para descriptografá-los assim que dispuserem de computação quântica capaz disso. *(Transcrito de [8].)*

**Como ela é construída, tecnicamente**

As soluções emergentes de PQC incluem, entre outras, criptografia baseada em reticulados (lattice-based) e assinaturas hash-based (stateless e stateful); o NIST já publicou padrões nessas famílias. *(Transcrito de [4].)*

**Distinção importante**

PQC não é o mesmo que "criptografia quântica": PQC é a solução de curto prazo baseada em algoritmos matemáticos clássicos resistentes a ataque quântico; já a distribuição quântica de chaves (QKD) — uma técnica de criptografia quântica propriamente dita, que usa fenômenos físicos para gerar/compartilhar chaves — é tratada como solução de mais longo prazo. *(Transcrito de [6] — OSIC 15/2024 › 3.4 Conclusões.)*

**Modelo de adoção recomendado nas fontes**

As fontes de contexto brasileiro recomendam uma transição em modelo híbrido — combinando criptografia clássica com PQC ("Quantum-Safe-by-Design") — para mitigar o risco de descriptografia retrospectiva, em vez de substituição abrupta. *(Transcrito/derivado de [3] e [5].)*

**Exemplo de aplicação prática**

Um estudo técnico (SBRC 2026) avaliou a integração híbrida do algoritmo CRYSTALS-Kyber (PQC baseado em reticulados) ao protocolo Matrix, medindo overhead de banda (+548% no setup, +252% nas rotações de chave) com impacto desprezível em CPU/latência — ilustrando o custo de engenharia real de adotar PQC em um sistema de mensageria. *(Transcrito de [7]; nota: o abstract da fonte veio em inglês, mas há resumo equivalente em português no próprio trecho, por isso não deixei a fonte de fora.)*

---
Observação: a fonte [2] (Consolidação de Matrizes PQC.xlsx) trata de algoritmos *simétricos clássicos* (AES, ChaCha, SM4 etc.), não de algoritmos pós-quânticos propriamente ditos no trecho que chegou — por isso não a usei para sustentar a definição de PQC, ela não é o vizinho semântico correto aqui.
