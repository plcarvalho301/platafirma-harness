# Carimbo — G0 geração local, qwen3.5:9b

Não executado.

## Candidato congelado

    modelo         qwen3.5:9b
    digest         6488c96fa5fa
    disco          6,6 GB
    residente      6,2 GB com num_ctx=16384
    PROCESSOR      100% GPU

O mais folgado dos candidatos: deixa ~3,8 GB livres com o RAG residente, e é o único que
comporta subir o `num_ctx` acima de 16k sem offload.
