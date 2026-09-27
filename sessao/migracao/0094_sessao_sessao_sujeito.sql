-- 0094 — sessao.sessao.sujeito: o sujeito que abriu a sessão, disponível também para
-- quem reidrata (card #3145, defeito pós-fita: a porta só injetava PF_SUJEITO no
-- execve de `sessao abrir`; nos demais verbos — infra, migrar — a variável não
-- chegava, e a fita perdia a identidade de vez ao reidratar depois de uma promoção).
--
-- O QUE FAZ:
--   `sessao:{id}` (msg-mem) já grava `sujeito` desde a cunhagem (bin/sessao::ato_abrir).
--   O registro durável (sessao.sessao, migração 0087) nunca teve essa coluna: quando a
--   chave efêmera some do msg-mem (promoção da stack motor recria o msg-mem vazio,
--   card #3145 decisão 1) e a porta reidrata de `sessao.sessao`
--   (bin/_sessao/reidratar.py), o sujeito se perdia — mesmo a sessão continuando
--   válida, PF_SUJEITO deixava de chegar aos verbos que o exigem.
--
-- Aditiva e nullable de propósito: linha gravada antes desta migração fica com
-- `sujeito IS NULL` (reidrata cadeira normalmente, sem sujeito — mesmo regime de
-- degradação que `encerrada_em` já tem na 0092). Idempotente: 2a passada devolve
-- NOTICE/no-op, exit 0.
--
-- Ref.: sessao/migracao/0087_sessao_sessao.sql (tabela-mãe), sessao/migracao/0092_
-- sessao_sessao_encerrada_em.sql (mesmo molde de ALTER TABLE aditivo nullable),
-- bin/sessao::_registra_duravel (grava), bin/_sessao/reidratar.py::reidratar (lê).

BEGIN;

ALTER TABLE sessao.sessao
  ADD COLUMN IF NOT EXISTS sujeito text;

COMMENT ON COLUMN sessao.sessao.sujeito IS
  'sub do token OAuth que cunhou a sessão (PF_SUJEITO, bin/sessao::ato_abrir). NULL = gravada antes desta migração, ou sessão sem sujeito. bin/_sessao/reidratar.py devolve este campo quando presente, para a porta injetar PF_SUJEITO no execve do verbo mesmo após reidratação (card #3145).';

COMMIT;
