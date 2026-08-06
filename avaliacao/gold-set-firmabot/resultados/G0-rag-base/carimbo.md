# Carimbo — G0 recuperação pura

Rodada: 2026-08-06T22:45Z · 34 sondas · executor `t0_sonda_34.py`

## Ambiente servido

    container      rag-extractor-api
    imagem         sha256:02c72acd6fae
    iniciado em    2026-08-06T21:18:51Z
    codigo         platafirma-conhecimento @ fc4e5f2 (build 2026-08-06 18:17 -03:00)
    acervo_sha     24ed2cbf607e73ab1e8ab79c0d286bf2996b5751db4e63cfb97c2f313dfc25c7

## Configuração do pipeline

    EMBED_MODEL    Qwen/Qwen3-Embedding-0.6B
    EMBED_BACKEND  torch
    EMBED_DEVICE   cuda
    RERANK_MODEL   BAAI/bge-reranker-v2-m3   (ativo em 34/34 sondas)
    GPU            exposta ao container via cdi nvidia.com/gpu=all

## Parâmetros congelados

    texto          secao
    k              8
    filtros        nenhum (dominio, subdominio, frente, colecao vazios)
    persona        nao declarada

## Sem gerador

Esta rodada mede recuperação pura. Nenhum modelo de geração participou.

## Resultado

    cobertura boa    25/34
    cobertura fraca   9/34
    sondas vazias     0/34
    top-1 nulo        1  (#20 opportunity solution tree)

## Latência

Mediana de 1.000 ms em amostra de 5 sondas (622 / 930 / 1000 / 1074 / 1503 ms), medida
separadamente após a rodada, com o mesmo container.

## Não comparável com

Rodadas anteriores a 2026-08-06 18:18. Duas execuções do dia foram descartadas por não
terem registro de qual código as serviu.
