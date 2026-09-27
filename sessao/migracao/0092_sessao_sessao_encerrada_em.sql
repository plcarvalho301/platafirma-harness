-- 0092 — sessao.sessao.encerrada_em: a marca de fechamento que faltava (card #3145,
-- Onda 1 Frente E, decisão do planejador sobre o item 5 do relato).
--
-- O QUE FAZ:
--   A 0087 criou sessao.sessao (sessao_id, cadeira, chapeu, superficie, aberta_em) sem
--   coluna de fechamento. Sem ela, a reidratação de `sessao:{id}` a partir do durável
--   (bin/_sessao/reidratar.py, card #3145 decisão 1) não conseguia distinguir uma
--   sessão encerrada de propósito (`sessao encerrar`/`sessao limpar`) de uma ainda
--   aberta — as duas colapsavam no mesmo "existe e está dentro do TTL". Esta coluna
--   fecha o furo: `bin/sessao::ato_encerrar`/`ato_limpar` gravam `encerrada_em = now()`
--   na linha durável além do DEL de sempre no msg-mem; `reidratar()` não reidrata
--   linha com `encerrada_em` preenchida.
--
-- Aditiva e nullable de propósito: linha sem fechamento (aberta, ou encerrada antes
-- desta migração — histórico não se reescreve) fica com `encerrada_em IS NULL`, o
-- mesmo estado de "ainda pode reidratar" que já valia. Idempotente: 2a passada
-- devolve NOTICE/no-op, exit 0.
--
-- Ref.: platafirma-arquitetura/macro-global/decisions/0091 (sessao_id, ciclo de vida),
-- sessao/migracao/0087_sessao_sessao.sql (tabela-mãe), sessao/migracao/0089_fita_sessao_id.sql
-- (mesmo molde de ALTER TABLE aditivo).

BEGIN;

ALTER TABLE sessao.sessao
  ADD COLUMN IF NOT EXISTS encerrada_em timestamptz;

COMMENT ON COLUMN sessao.sessao.encerrada_em IS
  'Fechamento deliberado (sessao encerrar|limpar, bin/sessao). NULL = nunca encerrada (ou encerrada antes desta migração). Preenchida: bin/_sessao/reidratar.py não reidrata a linha, mesmo dentro do TTL (card #3145).';

COMMIT;
