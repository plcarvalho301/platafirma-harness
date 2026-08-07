# Carimbo — G0 geração local, qwen3.5:9b

Rodada: 2026-08-06T21:13–21:27Z (aprox.) · 34 sondas · executor `g0_geracao.py`

## Ambiente servido

    modelo          qwen3.5:9b
    digest          6488c96fa5fa
    parametros      9.7B
    quantizacao     Q4_K_M
    PROCESSOR       100% GPU (ollama ps no momento da rodada)

## Parâmetros congelados

    sistema         avaliacao/gold-set-firmabot/prompt-firmabot.md — IDÊNTICO
                    ao usado em G0-claude-referencia desde 2026-08-06
    formato usuário PERGUNTA: <pergunta>\n\nFONTES:\n<contexto>
    temperature     0
    seed            42
    num_ctx         16384
    num_predict     900
    contexto        campo `contexto` congelado de G0-rag-base (não re-recuperado)

## Agregados (aritmética simples sobre `_resumo.json`, sem julgamento de cobertura)

    declarou_nao_cobertura   7/34
    taxa_citação média       0.85
    latência média           3432 ms
    tok/s médio              69.9

Classificação de cobertura (boa/fraca) não entra aqui — é da claudinho-IA,
mesma régua do carimbo de G0-rag-base.

## Autoria

Script `g0_geracao.py`, sentado sem commit na pasta do harness antes desta
rodada de consolidação. Autoria não confirmada por mensagem de fila; o dono
declarou ter sido ele mesmo, sessão não lembrada. Script agora commitado.
