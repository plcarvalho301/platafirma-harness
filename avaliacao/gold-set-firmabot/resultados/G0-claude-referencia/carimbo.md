# Carimbo — G0 geração, claude (sonnet)

Rodada: 2026-08-07T02:16:38.053375Z

Executor: tooling/rodar-firmabot-claude.py — uma chamada `claude -p` isolada
por sonda (--no-session-persistence, --tools "", processo novo a cada sonda).

    modelo      sonnet
    num_ctx     n/a (API, nao GPU local)
    amostragem  nao exposta na CLI --print (sem temperature/seed/num_predict)
    sistema     avaliacao/gold-set-firmabot/prompt-firmabot.md — IDENTICO ao
                usado em G0-gemma4-12b e G0-qwen3.5-9b (g0_geracao.py)

Arm oficial (decisao do dono, 2026-08-06), papel de referência de teto —
não substitui G0-gemma4-12b / G0-qwen3.5-9b, que medem viabilidade local.
Prompt agora idêntico aos dois; amostragem não é controlável via --print.
