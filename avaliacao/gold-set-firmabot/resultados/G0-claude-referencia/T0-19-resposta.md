## Quantização de modelo

**Definição** — Quantização é o processo de representar os pesos e ativações de uma rede neural usando tipos de dados de precisão mais baixa. No contexto de LLMs, o foco principal é reduzir a precisão dos pesos (e ativações) do modelo. Por padrão, pesos são armazenados em ponto flutuante de 16 ou 32 bits (FP16/FP32), formato de alta precisão mas com custo elevado de memória e computação; quantizar reduz esse footprint de memória e acelera a inferência.

*(Transcrito/derivado de: LLM Engineer's Handbook — Paul Iusztin, Maxime Labonne — seção "Model quantization" [3])*

Um achado notável registrado na mesma fonte: modelos maiores (acima de 30B parâmetros), quando quantizados para 2 ou 3 bits, podem superar em qualidade modelos menores (7B–13B) rodando em precisão mais alta, mantendo footprint de memória comparável. *(transcrito de [3])*

---

### Técnicas específicas cobertas nas fontes

**GGUF + llama.cpp** — formato de quantização do projeto llama.cpp (biblioteca C++ de inferência, criada por Georgi Gerganov), pensado para rodar em hardware amplo (CPU, Android, com offload de camadas para GPU), sem depender de bibliotecas fechadas como CUDA. GGUF armazena tensores e metadados em variantes de 1 a 8 bits (ex.: IQ1_S/M, Q2_K, Q4_K_S/M, Q6_K, Q8_0, entre outras). *(transcrito de [1], LLM Engineer's Handbook — "Quantization with GGUF and llama.cpp")*

A especificação formal do formato reforça: GGUF é um formato binário sucessor de GGML/GGMF/GGJT, desenhado para carregamento/salvamento rápido, autocontido (toda informação necessária para carregar o modelo) e extensível sem quebrar compatibilidade. *(transcrito de [4], recorte do repositório ggml-org/llama.cpp, commit 39eab74 — nota: a fonte identifica-se como rendição textual de um recorte específico, e o restante do arquivo original, por ser código, não entrou no trecho recebido)*

**GPTQ e EXL2** — formatos dedicados a GPU, mais rápidos que llama.cpp na inferência; EXL2 tem o maior throughput via ExLlamaV2. Ambos baseiam-se no algoritmo GPTQ (Frantar et al., 2023), que refina o Optimal Brain Quantization (OBQ) com decomposição de Cholesky da Hessiana inversa e atualização de pesos em lote (lazy batch updates). GPTQ limita-se a 4 bits; EXL2 permite taxas de bits fracionárias e mistas por camada (entre 2 e 8 bits), priorizando pesos mais importantes com maior precisão — na prática permitindo rodar um modelo de 70B numa única GPU de 24GB a ~2,55 bits. *(transcrito de [2])*

**AWQ, QuIP# e HQQ** — AWQ (Lin et al., 2023) protege os pesos mais importantes com base na magnitude de ativação (não do peso), aplicando escala por canal sem backprop; é próximo de GPTQ/EXL2 em resultado, um pouco mais lento, e integrado a TGI, vLLM, TensorRT-LLM. QuIP# e HQQ visam quantização extrema (1–2 bits) preservando melhor a qualidade do modelo original, tendência especialmente relevante para modelos grandes (>30B). *(transcrito de [7])*

---

### Estudos empíricos sobre efeito da quantização

As fontes [5] e [8] são artigos que investigam empiricamente o impacto da quantização, mas em recortes mais específicos que a pergunta não delimitou — não tratam do conceito em si, então trago apenas o que o trecho recebido permite dizer, sem completar com o restante do artigo:

- [5] (Afrin et al., "Quantize with Confidence?") investiga como GPTQ, AWQ, QuIP#, AQLM, BitsAndBytes e GGUF afetam a correção funcional e qualidade de código gerado por modelos de código (Qwen2.5-Coder, CodeLlama), usando os benchmarks McEval e CoderEval. O trecho recebido é a abertura do abstract; não chegou o resultado quantitativo.
- [8] (Dong et al., "Can Compressed LLMs Truly Act?") aponta que compressão pós-treino (poda e quantização) reduz custo computacional/de memória em até 4×, mas benchmarks existentes focam em perplexidade e NLU, ignorando capacidades agênticas (workflow, uso de ferramentas, contexto longo). O trecho recebido é o abstract/introdução; não traz os resultados do benchmark ACBench.

---

**Fora do escopo desta resposta**: a fonte [6] trata de *embeddings*, não de quantização de modelo — vizinho semântico que não sustenta a pergunta feita, por isso não foi usada.
