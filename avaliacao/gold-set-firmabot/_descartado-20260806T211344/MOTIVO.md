# Descartado — colisão de dois runners

Dois units rodaram a mesma série G0 em paralelo na mesma GPU e nos mesmos diretórios
de resultado: `g0-geracao.service` (21:06:22) e `goldset-g0.service` (21:08:41, via
`_run_arms.sh`). Consequência medida:

- `G0-granite4` — sondas 15–34 da série limpa (21:07:18–21:08:11) misturadas com
  01–14 reescritas pelo runner duplicado sob contenção (21:08:58–21:12:10).
  `_resumo.json` descreve a série limpa; os arquivos por sonda, não.
- `G0-qwen3.5-9b` — série inteira (21:08:42–21:11:00) concorrente com o duplicado.
- `G0-gemma4-12b` — parcial (6 sondas), concorrente.

Texto gerado não é afetado (`temperature=0`, `seed=42`, contexto congelado do
`G0-rag-base`); latência e tok/s são. Como o arm local se decide por custo, a série
foi refeita sozinha na GPU.
