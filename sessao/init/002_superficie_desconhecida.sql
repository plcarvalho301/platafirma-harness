-- Superfície declarada: quando quem abre a fita não diz de onde, o banco registra
-- 'desconhecida' em vez de escolher uma. Declarar ausência é mais barato que um dado
-- plausível e errado — e é o que permite medir depois quem não está declarando.
ALTER TABLE sessao.fita DROP CONSTRAINT fita_superficie_check;
ALTER TABLE sessao.fita ADD CONSTRAINT fita_superficie_check
  CHECK (superficie IN ('claude.ai', 'chat', 'code', 'desconhecida'));
