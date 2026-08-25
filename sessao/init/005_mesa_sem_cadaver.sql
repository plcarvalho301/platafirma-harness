-- 005 — mesa não retém cadáver: `mesa fez` passa a APAGAR, não a marcar.
--
-- Ordem do dono, 25/08 ("sem fóssil"). arq:0062 §4 (reescrita) e arq:0074: mesa é
-- cache efêmera, estado vivo sujeito a expurgo de fóssil. Reter item esvaziado "para
-- medição" era o cadáver que a 0074 proíbe; a medição vive fora da mesa (sessao.fita).
--
-- Some `esvaziado_em` e `esvaziado_por_fita`. Com o fez apagando, "pendente" deixa de
-- existir como distinção — toda linha viva É pendente. Antes de dropar a coluna, os
-- esvaziados que ainda estão na tabela (cadáveres pré-existentes) são deletados; senão
-- ressuscitariam como vivos ao sumir o filtro.

BEGIN;

-- 1. Expurga os cadáveres já acumulados (o que a regra antiga retinha "para medir").
DELETE FROM sessao.mesa_item WHERE esvaziado_em IS NOT NULL;

-- 2. Índice parcial dependia de esvaziado_em; cai junto.
DROP INDEX IF EXISTS sessao.mesa_item_pendente_idx;

-- 3. As colunas de cadáver saem.
ALTER TABLE sessao.mesa_item
  DROP COLUMN esvaziado_em,
  DROP COLUMN esvaziado_por_fita;

-- 4. Índice de leitura sem o filtro morto — toda linha é viva agora.
CREATE INDEX mesa_item_vivo_idx ON sessao.mesa_item (cadeira, chapeu, plantado_em);

COMMIT;
