-- 0086 — conteúdo do giro: prompt do dono e resposta do modelo, crus.
-- #2945: a fonte do voto é a próxima mensagem do dono (reforco §5). Persistir o
-- texto do turno no Postgres da fita permite ancorar reacao_texto ao evento de
-- recuperação por (fita_id, seq) sem batch/heurística — disparo async de dentro
-- da sessão grava cada lado no momento em que existe.
-- Nullable de propósito: o giro pode existir antes de a resposta fechar, e o
-- disparo async pode falhar sem derrubar o turno (degrada declarado, não bloqueia).

ALTER TABLE sessao.giro
  ADD COLUMN IF NOT EXISTS prompt_texto   text,
  ADD COLUMN IF NOT EXISTS resposta_texto text;

COMMENT ON COLUMN sessao.giro.prompt_texto   IS 'fala crua do dono no giro (fonte do voto: reacao ao giro anterior). #2945';
COMMENT ON COLUMN sessao.giro.resposta_texto IS 'resposta crua do modelo no giro. #2945';
