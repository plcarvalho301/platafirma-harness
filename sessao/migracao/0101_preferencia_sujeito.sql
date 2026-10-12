-- 0101 — sessao.preferencia_sujeito: a preferência de cada pessoa, que sobrevive à sessão (#3449).
--
-- Fonte: decisão do arquiteto no #2143 do #3449 (verbo `preferencia`, entidade `tema`, o
-- sujeito nunca é argumento) e de ti no #2172 do #3449 (banco e schema `sessao`, tabela
-- chaveada por sujeito, sem coluna de sessão, sem FK). A coluna `preferencia` leva o slug
-- do que se prefere porque `acervo.entidade` já existe (dados, no #3449).
-- Quem lê e grava: `bin/preferencia` (atos ler e escrever), o único escritor.
--
-- Aplicação: `release migrar aplicar sessao` com este arquivo no stdin. Aditiva: tabela
-- nova, nada do que está no ar a lê ainda. Antes do código que a usa. Idempotente.
--
-- Rollback:
--   DROP TABLE IF EXISTS sessao.preferencia_sujeito;

CREATE TABLE IF NOT EXISTS sessao.preferencia_sujeito (
    sujeito       text        NOT NULL,
    preferencia   text        NOT NULL,
    valor         text        NOT NULL,
    atualizado_em timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (sujeito, preferencia)
);

COMMENT ON TABLE sessao.preferencia_sujeito IS
  'Preferência de uma pessoa (hoje só o tema da tela), uma linha por sujeito e preferência. Sobrevive à sessão. Sem linha quer dizer que a pessoa nunca escolheu. 0101.';
COMMENT ON COLUMN sessao.preferencia_sujeito.sujeito IS
  'sub do token OAuth (PF_SUJEITO que a porta injeta), em texto. Referência lógica, sem FK. 0101.';
COMMENT ON COLUMN sessao.preferencia_sujeito.preferencia IS
  'Slug do que se prefere (hoje só tema). Vocabulário aberto no banco; o verbo bin/preferencia o fecha. 0101.';
COMMENT ON COLUMN sessao.preferencia_sujeito.valor IS
  'Valor escolhido. O vocabulário de cada preferência mora no verbo, sem CHECK: o contrato vale enquanto bin/preferencia for o único escritor. 0101.';
COMMENT ON COLUMN sessao.preferencia_sujeito.atualizado_em IS
  'Instante da última escrita da preferência. 0101.';

DO $$
DECLARE n int;
BEGIN
  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'sessao' AND table_name = 'preferencia_sujeito'
     AND column_name IN ('sujeito', 'preferencia', 'valor', 'atualizado_em');
  IF n <> 4 THEN
    RAISE EXCEPTION '0101: sessao.preferencia_sujeito sem as quatro colunas (achou %)', n;
  END IF;
  SELECT count(*) INTO n FROM pg_constraint
   WHERE conrelid = 'sessao.preferencia_sujeito'::regclass AND contype = 'p';
  IF n <> 1 THEN
    RAISE EXCEPTION '0101: sessao.preferencia_sujeito sem chave primária (sujeito, preferencia)';
  END IF;
  RAISE NOTICE '0101 aceite: sessao.preferencia_sujeito existe, 4 colunas, chave (sujeito, preferencia)';
END $$;
