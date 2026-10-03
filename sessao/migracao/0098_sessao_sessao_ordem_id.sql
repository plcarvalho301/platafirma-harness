-- 0098 — sessao.sessao.ordem_id: a ordem da última abertura, durável, para quem reidrata
-- (balde #2856, linha 152: `sessao limpar --rascunho` recusava «sem PF_ORDEM_ID valido ('-')»).
--
-- Fonte: bin/_sessao/reidratar.py gravava "ordem_id": "-" fixo ao refazer `sessao:{id}`, porque
-- sessao.sessao (0087) nunca teve a coluna. Toda promoção do harness reinicia a porta, o msg-mem
-- (Valkey) perde a chave, a sessão é reidratada e perde a ordem: PF_ORDEM_ID chega «-» a todo
-- verbo, e o que vive em <instancia>/var/tmp/<ordem_id> (rascunho da fita, sessao limpar
-- --rascunho, acervo ler biblioteca objeto --destino) some do alcance dela. Medido em 03/10/2026:
-- `sessao ver` da sessão da fita mostrava ordem_id «-» e origem «reidratada» depois de várias
-- promoções da fita.
--
-- O que faz: coluna nullable com a ordem da ÚLTIMA abertura (reabrir a mesma conversa troca a
-- ordem, bin/sessao::ato_abrir; o UPSERT acompanha). Linha gravada antes desta migração fica com
-- NULL e reidrata com «-», como antes: mesmo regime de degradação das 0092 e 0094.
--
-- Aplicação: `migrar aplicar sessao` com este arquivo no stdin, da bancada, antes do merge. É
-- aditiva: o código no ar não a lê nem escreve (bin/sessao e bin/_sessao/reidratar.py tentam a
-- forma nova e caem na antiga se a coluna faltar). Idempotente.
--
-- Rollback: ALTER TABLE sessao.sessao DROP COLUMN IF EXISTS ordem_id;

ALTER TABLE sessao.sessao
  ADD COLUMN IF NOT EXISTS ordem_id text;

COMMENT ON COLUMN sessao.sessao.ordem_id IS
  'Ordem da última abertura da sessão (o<UTC>-<6 hex>, bin/sessao::ato_abrir). NULL = gravada antes da 0098. bin/_sessao/reidratar.py a devolve para a porta injetar PF_ORDEM_ID depois que a chave viva some (promoção). 0098.';

-- Aceite: a coluna existe, é text e aceita NULL; nada do aceite fica gravado.
DO $$
DECLARE
  tipo text;
  anulavel text;
BEGIN
  SELECT data_type, is_nullable INTO tipo, anulavel
    FROM information_schema.columns
   WHERE table_schema = 'sessao' AND table_name = 'sessao' AND column_name = 'ordem_id';
  IF tipo IS NULL THEN
    RAISE EXCEPTION '0098: sessao.sessao.ordem_id nao existe';
  END IF;
  IF tipo <> 'text' OR anulavel <> 'YES' THEN
    RAISE EXCEPTION '0098: sessao.sessao.ordem_id deveria ser text nullable, e e % (anulavel: %)', tipo, anulavel;
  END IF;
  RAISE NOTICE '0098 aceite: sessao.sessao.ordem_id text nullable; nada do aceite gravado';
END $$;
