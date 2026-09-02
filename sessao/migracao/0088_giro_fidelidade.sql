-- 0088 — sessao.giro.fidelidade: cliente-fiel × auto-relato (arq:0093 §5, #2945).
--
-- O QUE FAZ:
--   Coluna fidelidade em sessao.giro. arq:0093 §5 é explícita: "fidelidade é
--   coluna, não nota" — 'cliente-fiel' (Code: o adaptador copia o JSONL do giro
--   antes da purga) ou 'auto-relato' (claude.ai: só o encerrar alcança o turno,
--   relatado por quem fecha a fita). SEM DEFAULT de propósito — "indefinido não
--   vira auto-relato por default" (arq:0093 §5): quem grava declara a fidelidade,
--   nunca o schema assume por eles.
--
-- Idempotente: 2a passada devolve NOTICE/no-op, exit 0.
--
-- Ref.: platafirma-arquitetura/macro-global/decisions/0093 §5.

BEGIN;

ALTER TABLE sessao.giro
    ADD COLUMN IF NOT EXISTS fidelidade text
        CHECK (fidelidade IN ('cliente-fiel', 'auto-relato'));

COMMENT ON COLUMN sessao.giro.fidelidade IS
  'Proveniência do conteúdo do giro (arq:0093 §5): cliente-fiel (Code, JSONL copiado antes da purga) ou auto-relato (claude.ai, via /sessao/encerrar). Sem default — indefinido nunca vira auto-relato por inferência.';

COMMIT;
