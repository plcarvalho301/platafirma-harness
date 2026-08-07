# Carimbo — G0 geração local, granite4:latest (piso de controle)

Rodada: 2026-08-06T21:13–21:27Z (aprox.) · 34 sondas · executor `g0_geracao.py`

Entra como piso de controle, não como concorrente — não faz parte da comparação
dos 3 (claude-sonnet-5, gemma4:12b, qwen3.5:9b). Consolidado em arquivo
separado: `consolidado-granite4-piso.md`.

## Ambiente servido

    modelo          granite4:latest
    digest          4235724a127c
    parametros      3.4B
    quantizacao     Q4_K_M
    PROCESSOR       100% GPU (ollama ps no momento da rodada)

## Parâmetros congelados

    sistema         avaliacao/gold-set-firmabot/prompt-firmabot.md — mesmo
                    texto dos outros 3 arms
    formato usuário PERGUNTA: <pergunta>\n\nFONTES:\n<contexto>
    temperature     0
    seed            42
    num_ctx         16384
    num_predict     900
    contexto        campo `contexto` congelado de G0-rag-base (não re-recuperado)

## Agregados (aritmética simples sobre `_resumo.json`, sem julgamento de cobertura)

    declarou_nao_cobertura   4/34
    taxa_citação média       0.23
    latência média           3225 ms
    tok/s médio              132.2

Classificação de cobertura (boa/fraca) não entra aqui — é da claudinho-IA.

## Autoria

Script `g0_geracao.py`, mesma rodada dos outros dois locais. Autoria não
confirmada por mensagem de fila; o dono declarou ter sido ele mesmo, sessão
não lembrada.
