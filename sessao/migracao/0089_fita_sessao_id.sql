-- 0089 — sessao_id na fita: a âncora que o carregador de giro já esperava.
--
-- bin/_giro-carga.py resolve a fita por `SELECT id FROM sessao.fita WHERE
-- sessao_id = %s`, mas a coluna nunca existiu — a carga dos giros recusava com
-- "nenhuma fita casada". Ordem do dono (02/09): os 3 primeiros giros de cada
-- chat cravados no banco no encerrar/descansar. Esta coluna é o par que faltava.
--
-- Aditiva. NÃO cria sessao.sessao (arq:0093 passo zero, fronteira à parte): só a
-- coluna-âncora na fita, que monta_sessao passa a gravar na abertura. Nullable de
-- propósito — fita antiga (pré-0089) fica sem par, e o carregador simplesmente
-- não a encontra, sem quebrar.

ALTER TABLE sessao.fita
  ADD COLUMN IF NOT EXISTS sessao_id text;

CREATE INDEX IF NOT EXISTS fita_sessao_id_idx ON sessao.fita (sessao_id)
  WHERE sessao_id IS NOT NULL;

COMMENT ON COLUMN sessao.fita.sessao_id IS
  'UUIDv4 cunhado por monta_sessao (arq:0091), shadow. Âncora do carregador de giro (bin/_giro-carga.py) e do log de reforço. #2945';
