# caderno dados/ontologia

## Régua

- **Campo que depende da espécie só se cobra onde é identidade para a espécie inteira.** «Depende da obra» é comporta, não exige; quem decide é a curadoria, não o detector. Juízo instituído pelo dono (vinculação, aplicabilidade) não vira número a perseguir em lista de verificação.
- **Antes de propor escopo a um card em lapidação, medir; card não lapidado não sabe o tamanho do buraco.** Feature que cresce na lapidação não pede feature irmã.

## Diário de bordo

2026-09-27 — `lint rodar --help` → exit 1 «sem bancada '--help'»; `lint prosa <caminho>` → exit 4 «nome de repo invalido»; `lint prosa platafirma-casa` → exit 5 «lista de verificacao 'styleguide-da-wiki' nao encontrada no acervo». — contorno encontrado NA DATA 2026-09-27 foi nenhum; lista publicada sem passada do lint de prosa.

2026-09-27 — `repo procurar <repo> "<regex>"` → exit 2 «--termo obrigatório»; com `--termo` → exit 1 «sem bancada aberta para <repo>». — contorno NA DATA 2026-09-27 foi `repo abrir <repo> --slug <s>` e `procurar <repo> --termo <literal>`.

2026-09-27 — `acervo listar casa adr --sobre serie ont` → exit 2 «classe 'serie' nao e referente de Sobre:». — contorno NA DATA 2026-09-27 foi `repo listar platafirma-casa adr/ont` para achar o próximo número de ADR.

2026-09-27 — `descobrir "<termo>"` → «fonte-nao-indexada, falta concessao para acervo:*». — contorno NA DATA 2026-09-27 foi `motor rag buscar obra|casa`.

2026-09-27 — `mesa caderno ontologia` com stdin só lê; `--anexa` não existe. — contorno NA DATA 2026-09-27 foi `mesa escrever ontologia` com o caderno inteiro no stdin.
