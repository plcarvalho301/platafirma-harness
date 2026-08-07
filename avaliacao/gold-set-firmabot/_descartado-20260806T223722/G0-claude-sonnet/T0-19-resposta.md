## Quantização de modelo

**Definição** (transcrito de LLM Engineer's Handbook, seção *Model quantization*, fonte [3]):
Quantização é o processo de representar os pesos e as ativações de uma rede neural usando tipos de dado de menor precisão. Em LLMs, o foco principal é reduzir a precisão dos pesos e ativações do modelo. Por padrão, os pesos são armazenados em ponto flutuante de 16 ou 32 bits (FP16/FP32), formato de alta precisão mas com maior custo de memória e computação. A quantização reduz essa pegada de memória e acelera a inferência.

Um achado curioso citado na mesma fonte: modelos maiores (acima de 30B parâmetros), quando quantizados para 2 ou 3 bits, podem superar em qualidade modelos menores (7B–13B) mantendo pegada de memória comparável.

### Técnicas principais

**GGUF / llama.cpp** (transcrito de [1] e [4]): formato de arquivo próprio do projeto llama.cpp (biblioteca C++ open-source de Georgi Gerganov), pensado para carregar modelos de forma rápida e simples. Roda em hardware mais amplo que soluções dependentes de CUDA — inclusive CPU e Android — podendo também deslocar camadas para GPU. Suporta precisões de 1 a 8 bits, com convenção de nomes por variante (ex.: IQ1_S/M em 1 bit, qualidade muito baixa; Q4_K_S/M em 4 bits, boa qualidade e uso mais comum; Q8_0 em 8 bits, qualidade mais alta). A fonte [4], trecho da própria especificação do formato GGUF no repositório llama.cpp, confirma (transcrito): GGUF é formato binário sucessor de GGML/GGMF/GGJT, feito para autocontenção (toda informação para carregar o modelo já está no arquivo) e extensibilidade.

**GPTQ / EXL2** (transcrito de [2]): formatos dedicados a GPU, mais rápidos que llama.cpp na inferência — EXL2 com a maior vazão via biblioteca ExLlamaV2. Baseiam-se no algoritmo GPTQ (Frantar et al., 2023), que refina a Optimal Brain Quantization com decomposição de Cholesky da Hessiana inversa e atualização em lote (lazy batch updates). GPTQ limita-se a 4 bits; EXL2 permite taxas de bits fracionárias e mistas por camada (entre 2 e 8 bits), possibilitando, por exemplo, rodar um modelo de 70B em uma única GPU de 24 GB a 2.55 bits.

**Outras técnicas** (transcrito de [7]): AWQ (Activate-aware Weight Quantization, Lin et al., 2023) protege os pesos mais importantes com base na magnitude de ativação, sem backpropagation; é usado por TGI, vLLM e TensorRT-LLM. Para quantização extrema (1–2 bits), QuIP# e HQQ preservam melhor a performance do modelo original que abordagens como EXL2 nesse regime, sobretudo em modelos grandes (>30B).

### Avaliação empírica (sinalizado à parte, não é definição)

As fontes [5] e [8] são artigos de pesquisa que avaliam efeitos da quantização, não definem o conceito:
- [5] (Afrin et al.) investiga empiricamente o impacto de GPTQ, AWQ, QuIP#, AQLM, BitsAndBytes e GGUF sobre a correção funcional de código gerado por Qwen2.5-Coder e CodeLlama — o trecho recebido é abstract/cabeçalho, sem os resultados.
- [8] (Dong et al.) apresenta o ACBench, benchmark para avaliar como a compressão (poda e quantização) afeta capacidades agênticas de LLMs (uso de ferramentas, contexto longo), argumentando que benchmarks tradicionais (perplexidade, GLUE) não cobrem isso — também trecho de abertura, sem resultados no que chegou.

**Observação:** a fonte [6] (AI Engineering, Chip Huyen) trata de *embedding*, conceito vizinho mas distinto de quantização, e por isso não foi usada para sustentar nenhuma afirmação acima.