# Carimbo — G0 geração, claude (sonnet)

Rodada: 2026-08-07T01:37:22.976331Z · arm oficial, decisao do dono
em 2026-08-06.

Executor: tooling/rodar-firmabot-claude.py — uma chamada `claude -p` isolada
por sonda (--no-session-persistence, --tools "").

    modelo (alias)     sonnet
    modelos no usage   claude-haiku-4-5-20251001, claude-sonnet-5
    num_ctx            n/a (API, nao GPU local)
    amostragem         padrao da CLI — sem flag de temperature exposta
    custo total        US$ 2.5648

Unico dos quatro arms que roda via API, nao GPU local — diferenca a declarar
em qualquer leitura comparada com G0-gemma4-12b / G0-granite4 / G0-qwen3.5-9b.
