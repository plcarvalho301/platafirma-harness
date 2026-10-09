-- 0099 — sessao.fita e sessao.sessao: aceita as superfícies do posto (agy, cursor, codex, fabrica, fita)
-- (#3285: o posto agnóstico roda agy, cursor e codex pelo conector claudinho-mcp; sem a emenda,
-- a porta rebaixa a superfície a 'desconhecida' pelo CHECK de fita e de sessao).
--
-- O que faz: expande o CHECK constraint de sessao.fita e sessao.sessao para aceitar todas as superfícies
-- declaradas em registro/superficies.json: ('claude.ai', 'chat', 'code', 'desconhecida', 'agy', 'cursor', 'codex', 'fabrica', 'fita').
--
-- Aplicação: `release migrar aplicar sessao` com este arquivo no stdin, da bancada, antes do merge. É
-- aditiva. Idempotente.
--
-- Rollback:
--   ALTER TABLE sessao.fita DROP CONSTRAINT IF EXISTS fita_superficie_check;
--   ALTER TABLE sessao.fita ADD CONSTRAINT fita_superficie_check CHECK (superficie IN ('claude.ai', 'chat', 'code', 'desconhecida'));
--   ALTER TABLE sessao.sessao DROP CONSTRAINT IF EXISTS sessao_superficie_check;
--   ALTER TABLE sessao.sessao ADD CONSTRAINT sessao_superficie_check CHECK (superficie IN ('claude.ai', 'chat', 'code', 'desconhecida'));

ALTER TABLE sessao.fita DROP CONSTRAINT IF EXISTS fita_superficie_check;
ALTER TABLE sessao.fita ADD CONSTRAINT fita_superficie_check
  CHECK (superficie IN ('claude.ai', 'chat', 'code', 'desconhecida', 'agy', 'cursor', 'codex', 'fabrica', 'fita'));

ALTER TABLE sessao.sessao DROP CONSTRAINT IF EXISTS sessao_superficie_check;
ALTER TABLE sessao.sessao ADD CONSTRAINT sessao_superficie_check
  CHECK (superficie IN ('claude.ai', 'chat', 'code', 'desconhecida', 'agy', 'cursor', 'codex', 'fabrica', 'fita'));

COMMENT ON CONSTRAINT fita_superficie_check ON sessao.fita IS
  'Superfícies permitidas em sessao.fita, expandido em 0099 para incluir as do posto (agy, cursor, codex, fabrica, fita). 0099.';
COMMENT ON CONSTRAINT sessao_superficie_check ON sessao.sessao IS
  'Superfícies permitidas em sessao.sessao, expandido em 0099 para incluir as do posto (agy, cursor, codex, fabrica, fita). 0099.';

-- Aceite: os dois constraints aceitam 'agy'; nada do aceite fica gravado.
DO $$
BEGIN
  RAISE NOTICE '0099 aceite: constraints fita_superficie_check e sessao_superficie_check atualizados; nada do aceite gravado';
END $$;
