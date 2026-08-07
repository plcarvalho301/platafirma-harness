# Carimbo — G0 geração, claude (sonnet)

Rodada: 2026-08-07T01:46:58.397267Z

Executor: tooling/rodar-firmabot-claude.py — uma chamada `claude -p` isolada
por sonda (--no-session-persistence, --tools "", processo novo a cada sonda).

    modelo      sonnet
    num_ctx     n/a (API, nao GPU local)
    amostragem  padrao da CLI — sem flag de temperature exposta em --print

Arm oficial (decisao do dono, 2026-08-06), papel de referência de teto —
não substitui G0-gemma4-12b / G0-granite4 / G0-qwen3.5-9b, que medem
viabilidade local. Ver docstring do script para o motivo da distinção.
