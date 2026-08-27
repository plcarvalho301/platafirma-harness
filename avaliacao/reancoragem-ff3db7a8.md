# Re-ancoragem do gold ao acervo servido — versao sha_acervo=ff3db7a8a59e

Ato do P0 (#2894, Fase D do epico #283), fita claudinho-dados 27/08/2026. Valida cada
alvo do `gabarito.jsonl` contra o corpus SERVIDO hoje (781 obras). Roda no container
(`rag-extractor-api`), casa contra `acervo.trecho.section_id` e `acervo.impressao` servindo.
Script: `var/tmp/reancora_valida.py` (+ `resolve2.py` para o diagnostico das pendencias).

## Resultado

| estrato | ancoradas / total | observacao |
|---|---|---|
| T1-deterministico | 116 / 118 | 2 pendencias (abaixo) |
| T2-cadeiras | 80 / 80 | 52 com obra + 27 negativas + 1 indeterminada; 0 orfa |
| T3-multistep | 30 / 30 | sem alvo por desenho (julgamento) |

- **Obras-alvo orfas: 0.** Os 176 `alvo_obra_ids` referenciados estao todos servindo.
  O expurgo/dedup das ondas anteriores NAO invalidou nenhum alvo do gold.
- **section_id nao mudou de esquema global.** O prefixo e por-obra (umas slug legivel
  `cmmi-1994#...`, outras short_id `d4ccae6a#...`); o gold ja bate com o servido em 116/118.

## Duas pendencias — re-julgamento, nao descarte

Ambas as obras seguem servindo; o que quebrou foi a ANCORA, re-slugificada na re-extracao
de estrutural (rotulo) para semantica (titulo da secao):

- **det-annex-014** — *Guia ANPD Legitimo Interesse 2024* (viva). Gold aponta `#annex-i`;
  hoje as ancoras sao semanticas (`#legitimo-interesse`, `#modelo-de-teste-simplificado`,
  `#sintese-legitimo-interesse`, ...). Nao ha `#annex-i`.
- **det-clause_decimal-015** — *Manual Operacional SIAPE Saude - Perfil Administrativo*
  (viva, 81d20863). Gold aponta `#7`; hoje as ancoras sao semanticas/figuras. Nao ha `#7`.

Qual secao semantica equivale a "Anexo I" / "clausula 7" e JULGAMENTO, nao determinismo.
As 2 estao marcadas no gabarito com `ancoragem_invalida: true` + motivo; saem do
denominador deterministico ate re-julgar, e sao candidatas naturais ao pooling
(`avaliacao.julgamento`, origem_run_id preenchido).

## Causa e regra para o futuro

T1 foi auto-rotulado assumindo ancora ESTRUTURAL (annex/numero). A re-extracao passou a
ancora SEMANTICA. Regra: T1 deve ser re-rotulado a partir do `section_id` SERVIDO, nunca
de um rotulo estrutural presumido — senao toda re-extracao que renomeia ancora quebra alvo
em silencio. As 116 que sobreviveram tinham ancora que o re-chunk preservou (AnnexA, numeros
que viraram slug identico).

## Registro

Esta versao esta carimbada em `avaliacao.gabarito_versao` (motor-pg): `sha_acervo=ff3db7a8a59e`
+ `sha_git` do commit que marcou as 2 pendencias. Toda `run` de baseline referencia esta versao.
