# Baseline central do P0 (#2894) — gold re-ancorado (228)

Fita claudinho-dados 27/08/2026. Runner e2e contra a porta `/search` SERVIDA, em uma chamada
(`rodar-baseline.sh`). Gravado em `avaliacao.run` 8f9770e8 + 228 linhas em `avaliacao.resultado`,
vinculado a `gabarito_versao` 6d523c55 (sha_git 3284b46, sha_acervo ff3db7a8a59e).

## Números (k=8)

| estrato | avaliável | hit@8 | recall@8 médio |
|---|---|---|---|
| T1-determinístico | 118 | 94 (79,7%) | 0,398 |
| T2-cadeiras (positivas) | 52 | 33 (63,5%) | 0,629 |
| negativas | 27 | abstenção **7/27** | — |
| T3 + inválidas | 58 | **N/A** (NULL) | N/A |

Latência p50 **66 ms**, p95 **519 ms**. Régua N/A aplicada: 58 sem alvo gravam rank/hit/recall
= NULL; a média de recall (0,469 no geral válido) filtra NULL, nunca conta como 0.

## Três achados que a baseline expõe

1. **Abstenção quebrada — o modo de falha perigoso.** Só 7 das 27 negativas o sistema abstém;
   em **20/27** ele reporta cobertura boa onde deveria dizer "não sei". É o defeito mais grave
   (inventa cobertura). Candidato a prioridade da próxima onda (revisor como juiz, #2887).
2. **T1 acha a obra, erra a seção.** hit@8 79,7% mas recall@8 0,398: T1 tem alvo de seção +
   obra; a busca traz a obra certa e falha na seção exata. Recuperação grosseira no nível fino
   — casa com o P1.5 (ligar runtime à SEÇÃO, #2896).
3. **Cauda de latência.** p50 66 ms vs p95 519 ms — alguma classe de pergunta paga ~8x.

## Débito aberto

- **stack_sha do rag servido não é auto-legível** (run gravado com "rag-servido-desconhecido").
  A régua de sign-off do #2894 é delta ENTRE stacks; sem carimbo de stack o delta não fecha.
  Falta `/version` na API — matéria TI/IA.

## Como reproduzir (uma chamada)

```
bash platafirma-harness/avaliacao/rodar-baseline.sh [gold.jsonl] [rotulo]
```
Mede no container, grava run + resultados. Runner: `runner_gold_baseline.py`.
