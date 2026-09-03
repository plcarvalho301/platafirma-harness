-- 0087 — sessao.sessao: a entidade que dá nome ao schema (arq:0093 passo zero, #2945).
--
-- O QUE FAZ:
--   Cria sessao.sessao (PK sessao_id uuid) — a shadow session da arq:0091, cunhada
--   por monta_sessao na primeira abertura de uma conversa e durável através de
--   múltiplas aberturas (troca de chapéu, retomada). O schema `sessao` hoje tem
--   fita/giro/pacote/peca_servida/mesa_item/mesa_legado/caderno_entrada mas não a
--   entidade-mãe que os contém — este é o furo que a 0093 §Consequências fecha.
--
--   Par sessão↔fita: coluna sessao_id em sessao.fita (FK, nullable — uma sessão
--   tem N fitas no tempo, 1 viva; o FK vive no lado N, não o inverso). Não é
--   sessao.sessao que aponta para a fita corrente: quem lê "a fita desta sessão"
--   consulta sessao.fita WHERE sessao_id = ... ORDER BY aberta_em DESC.
--
-- Idempotente: 2a passada devolve NOTICE/no-op, exit 0.
--
-- Ref.: platafirma-arquitetura/macro-global/decisions/0091 (sessao_id),
-- 0093 (camada analítica, passo zero), platafirma-arquitetura/docs/
-- modelo-dados-sessao-reforco.md §3.1.

BEGIN;

CREATE TABLE IF NOT EXISTS sessao.sessao (
  sessao_id  uuid        PRIMARY KEY,
  cadeira    text,
  chapeu     text,
  superficie text        CHECK (superficie IN ('claude.ai', 'chat', 'code', 'desconhecida')),
  aberta_em  timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE sessao.sessao IS
  'Entidade-mãe da conversa (arq:0061 L3, arq:0091). PK sessao_id = UUIDv4 shadow, cunhado por monta_sessao. Nunca reflexo do session-id do fornecedor (arq:0091 §2).';
COMMENT ON COLUMN sessao.sessao.sessao_id IS
  'UUIDv4 RFC-4122 (36 chars, com hífen), gerado na borda por lib nativa — sem gerador central (arq:0091 §4).';

ALTER TABLE sessao.fita
  ADD COLUMN IF NOT EXISTS sessao_id uuid REFERENCES sessao.sessao(sessao_id);

COMMENT ON COLUMN sessao.fita.sessao_id IS
  'Par sessão↔fita (arq:0093 passo zero): a sessão a que esta fita pertence. Uma sessão tem N fitas no tempo, 1 viva (arq:0093 §7) — o FK vive na fita, não o inverso.';

CREATE INDEX IF NOT EXISTS fita_sessao_idx ON sessao.fita (sessao_id);

COMMIT;
