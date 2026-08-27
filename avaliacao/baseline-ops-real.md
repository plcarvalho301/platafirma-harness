# Baseline exploratoria — prompts reais (ops), sem alvo pontual

P0 (#2894, Fase D do epico #283), fita claudinho-dados 27/08/2026. Primeira medicao de
recuperacao sobre PROMPT REAL colhido de fonte (nao gold sintetico). Vinculada a
`avaliacao.gabarito_versao` 6d523c55 (sha_acervo ff3db7a8a59e). Run: `avaliacao.run` c68a5e07.

## Procedencia e curadoria

Fonte: `candidatos-prompts-reais.jsonl` do jaiminho (fabrica), 498 candidatos. Auditados e
CORTADOS por dados (fabrica e fonte nao-verificada):

- **264 `ops`** (buscas reais contra o RAG) = o unico trigo. Diversos (9/264 no cluster
  TOGAF), mediana 76 chars.
- Descartados: **200 `synapse`** (chit-chat de sala: "fala aranha", "Zerar") e **29 `typed`**
  (meta-operacional de bootstrap 01/08: "puxa sua fila", "como abro sessao na CLI").
- Rotulos do jaiminho `tipo` e `ja_no_gold` sao NAO-CONFIAVEIS (486 "ordem-operacional"
  incluindo "fala aranha"; ja_no_gold todos false sem conferir). Descartados.

**Bug de extracao do jaiminho:** muitos "ops" eram CACOS de frase explodida em tokens
("the","user","query","embedding","similarity","route"...). Duas passadas de limpeza
(meta + fragmento, protegendo interrogativas) baixaram 264 -> **200 buscas reais**.

## Numeros (k=8)

| metrica | valor |
|---|---|
| N | 200 |
| cobertura boa | 164 (82,0%) |
| cobertura fraca | 36 (18,0%) |
| abstencao (fraca+nenhuma) | 18,0% |
| similaridade mediana | 0,671 |
| latencia p50 | 52 ms |
| latencia p95 | 109 ms |

Sem alvo pontual declarado, isto mede cobertura/abstencao/latencia — **nao recall**. Recall
entra quando dono/pooling der alvo (`avaliacao.julgamento`). As 36 de baixa cobertura sao
candidatas a negativa ou a lacuna de acervo (ex.: MIREOT, constante k=60 da fusao, Manual Pix).

## Debitos abertos

- **stack_sha do rag servido nao e auto-legivel** (run gravado com "rag-servido-desconhecido").
  Sem ele o delta entre stacks — a regra de sign-off do #2894 — nao fecha. Falta `/version`
  na API ou marcador no container. Debito de TI/IA.
- Conjunto curado: `candidatos-ops-real-200.jsonl`. Falta alvo por pergunta (julgamento).
