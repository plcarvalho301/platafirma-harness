-- 0097 — Caderno por entrada: sessao.caderno_entrada passa de projeção a fonte, com evento,
-- uso de aresta e legado (#3218).
--
-- Fonte: arq:0120 §2, §5, §6 e §7 (quatro categorias com campo obrigatório, uma linha por
-- entrada com evento, estados, nada se apaga); parecer 2026-10-01-caderno, seções 3 a 5 e 7; a
-- forma da aresta fixada por dados na #3218 (fila 20261001T163717-dados, resposta à gestão).
-- Desenho: dados (arq:0120 §5.5). Quem lê: o verbo `mesa` (escrever, caderno, colheita e os atos
-- de estado); a abertura, pela peça `cadernos`; a varredura da #3219.
--
-- O que muda: a sessao.caderno_entrada de sessao/init/001 era projeção vazia, uma linha por
-- caderno inteiro (PK cadeira, chapeu), sem leitor. Sai e volta por entrada. A troca só acontece
-- com a tabela velha vazia; com linha, a migração aborta e nada se grava.
--
-- Aplicação: `migrar aplicar sessao` com este arquivo no stdin, da bancada, antes do merge. É
-- aditiva para o que está no ar: nenhum código lê a projeção. Depois de 0094. Antes do
-- `bin/mesa` que grava por entrada. Idempotente.
--
-- Rollback (só com as tabelas vazias; com entrada, a volta é migração nova que preserva):
--   DROP TABLE IF EXISTS sessao.caderno_aresta_uso, sessao.caderno_evento,
--     sessao.caderno_legado, sessao.caderno_entrada;
--   DROP FUNCTION IF EXISTS sessao.caderno_nada_se_apaga();
--   e o CREATE TABLE sessao.caderno_entrada de sessao/init/001_sessao.sql.

-- 1. A projeção de 001 sai, só vazia.
DO $$
DECLARE n bigint;
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_schema = 'sessao' AND table_name = 'caderno_entrada'
                AND column_name = 'blob_sha') THEN
    EXECUTE 'SELECT count(*) FROM sessao.caderno_entrada' INTO n;
    IF n > 0 THEN
      RAISE EXCEPTION '0097: sessao.caderno_entrada (projeção de 001) tem % linha(s); nada se apaga, a troca para aqui', n;
    END IF;
    DROP TABLE sessao.caderno_entrada;
  END IF;
END $$;

-- 2. A entrada.
CREATE TABLE IF NOT EXISTS sessao.caderno_entrada (
  id              bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cadeira         text        NOT NULL CHECK (length(btrim(cadeira)) > 0),
  chapeu          text        NOT NULL CHECK (chapeu ~ '^[a-z0-9][a-z0-9-]{0,40}$'),
  categoria       text        NOT NULL
                              CHECK (categoria IN ('licao', 'preferencia', 'premissa', 'aresta')),
  estado          text        NOT NULL DEFAULT 'vigente'
                              CHECK (estado IN ('vigente', 'substituida', 'tombada', 'retirada')),
  texto           text        NOT NULL
                              CHECK (length(btrim(texto)) > 0 AND char_length(texto) <= 600),
  caso            text,
  dito_em         date,
  dito_onde       text,
  vale_ate        date,
  ate_que         text,
  de_ponta        text,
  para_ponta      text,
  em_tombamento   boolean     NOT NULL DEFAULT false,
  candidata       text,
  destino         text,
  motivo          text,
  substituida_por bigint      REFERENCES sessao.caderno_entrada(id),
  criada_em       timestamptz NOT NULL DEFAULT now(),
  confirmada_em   timestamptz NOT NULL DEFAULT now(),
  criada_por      text,
  CONSTRAINT caderno_licao_tem_caso CHECK (
    categoria <> 'licao' OR (caso IS NOT NULL AND length(btrim(caso)) > 0)),
  CONSTRAINT caderno_preferencia_tem_palavra CHECK (
    categoria <> 'preferencia'
    OR (dito_em IS NOT NULL AND dito_onde IS NOT NULL AND length(btrim(dito_onde)) > 0)),
  CONSTRAINT caderno_premissa_tem_validade CHECK (
    categoria <> 'premissa'
    OR ((vale_ate IS NOT NULL) <> (ate_que IS NOT NULL AND length(btrim(ate_que)) > 0))),
  CONSTRAINT caderno_premissa_ate_60_dias CHECK (
    vale_ate IS NULL OR vale_ate <= (confirmada_em AT TIME ZONE 'America/Sao_Paulo')::date + 60),
  CONSTRAINT caderno_aresta_tem_pontas CHECK (
    categoria <> 'aresta'
    OR (de_ponta IS NOT NULL AND para_ponta IS NOT NULL
        AND de_ponta ~ '^(conceito|termo):.+' AND para_ponta ~ '^(conceito|obra|casa|chapeu):.+')),
  CONSTRAINT caderno_tombada_tem_destino CHECK (
    (estado <> 'tombada' AND NOT em_tombamento)
    OR (destino IS NOT NULL AND length(btrim(destino)) > 0)),
  CONSTRAINT caderno_retirada_tem_motivo CHECK (
    estado <> 'retirada' OR (motivo IS NOT NULL AND length(btrim(motivo)) > 0)),
  CONSTRAINT caderno_substituida_aponta CHECK (
    estado <> 'substituida' OR substituida_por IS NOT NULL)
);

-- Uma aresta vigente por cadeira, chapéu e par de pontas: a marcação seguinte conta na mesma.
CREATE UNIQUE INDEX IF NOT EXISTS caderno_aresta_vigente_uq
  ON sessao.caderno_entrada (cadeira, chapeu, de_ponta, para_ponta)
  WHERE categoria = 'aresta' AND estado = 'vigente';
CREATE INDEX IF NOT EXISTS caderno_entrada_chapeu_idx
  ON sessao.caderno_entrada (cadeira, chapeu, estado);

COMMENT ON TABLE sessao.caderno_entrada IS
  'Caderno de chapéu, uma linha por entrada (arq:0120 §5). Fonte, não projeção: não se exporta ao git. Sai por estado; nenhuma linha se apaga. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.cadeira IS
  'Slug canônico da cadeira dona do caderno (o mesmo de sessao.mesa_item.cadeira). Referência lógica, sem FK. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.chapeu IS
  'Slug do chapéu (abertura/<cadeira>/<chapeu>/chapeu.md). 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.categoria IS
  'licao, preferencia (do dono), premissa ou aresta (arq:0120 §2). Cada uma tem o seu campo obrigatório. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.estado IS
  'vigente (servida), substituida, tombada (virou norma; destino), retirada (motivo; volta por restaurar). 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.texto IS
  'A entrada, até 600 caracteres. Na aresta, o primeiro para quê. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.caso IS
  'Lição: o caso que a ensinou (card, fita ou data). 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.dito_em IS
  'Preferência do dono: a data em que ele disse. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.dito_onde IS
  'Preferência do dono: onde ele disse (fita, card, mensagem). 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.vale_ate IS
  'Premissa: até quando vale, no máximo 60 dias depois da escrita ou da reconfirmação. Exclusivo com ate_que. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.ate_que IS
  'Premissa: o evento que se confere e a derruba. Exclusivo com vale_ate. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.de_ponta IS
  'Aresta: o conceito da pergunta, conceito:<slug> ou termo:<texto> (forma de #3218). 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.para_ponta IS
  'Aresta: o que se puxou de fora da cadeira, conceito:<slug>, obra:<uuid>, casa:<especie>/<chave> ou chapeu:<cadeira>/<slug>. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.em_tombamento IS
  'Marca da vigente: tombamento pedido, à espera de o destino publicar (arq:0120 §6). 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.candidata IS
  'Marca da vigente: por que a varredura a apontou (duplicata, fora de categoria, referência morta, órfã, tombamento). Null = não apontada. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.destino IS
  'Tombada ou em tombamento: a chave do destino (chapéu, documento de casa, ADR, conceito, aresta da teia). 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.motivo IS
  'Retirada: por quê; duplicata leva a chave do cânone. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.substituida_por IS
  'Substituída: a entrada que a trocou, no mesmo ato. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.criada_em IS
  'Quando a entrada nasceu. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.confirmada_em IS
  'Última escrita ou reconfirmação: a lição vence 90 dias depois («a revisar»); a premissa conta os 60 dias daqui. 0097.';
COMMENT ON COLUMN sessao.caderno_entrada.criada_por IS
  'Sessão ou fita que escreveu (PF_FITA, ou PF_SESSAO na porta). 0097.';

-- 3. O evento: quem, quando, de que estado, para que estado, por quê (arq:0120 §5.1).
CREATE TABLE IF NOT EXISTS sessao.caderno_evento (
  id          bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  entrada_id  bigint      NOT NULL REFERENCES sessao.caderno_entrada(id),
  ato         text        NOT NULL CHECK (ato IN ('escrever', 'substituir', 'confirmar', 'retirar',
                                                  'restaurar', 'tombar', 'apontar', 'aresta',
                                                  'veredito')),
  de_estado   text        CHECK (de_estado IN ('vigente', 'substituida', 'tombada', 'retirada')),
  para_estado text        NOT NULL
                          CHECK (para_estado IN ('vigente', 'substituida', 'tombada', 'retirada')),
  por         text        NOT NULL CHECK (length(btrim(por)) > 0),
  sessao      text,
  porque      text,
  em          timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS caderno_evento_entrada_idx ON sessao.caderno_evento (entrada_id, em);

COMMENT ON TABLE sessao.caderno_evento IS
  'Histórico por entrada do caderno: todo ato do verbo mesa que nasce, marca ou muda uma entrada grava uma linha. Nada se apaga. 0097.';
COMMENT ON COLUMN sessao.caderno_evento.ato IS
  'O ato do verbo mesa que gerou o evento. 0097.';
COMMENT ON COLUMN sessao.caderno_evento.de_estado IS
  'Estado antes do ato; null no nascimento. 0097.';
COMMENT ON COLUMN sessao.caderno_evento.para_estado IS
  'Estado depois do ato; marca que não muda estado (apontar, em tombamento, uso de aresta) repete o estado. 0097.';
COMMENT ON COLUMN sessao.caderno_evento.por IS
  'Cadeira que fez o ato (slug canônico); no veredito, a curadoria. 0097.';
COMMENT ON COLUMN sessao.caderno_evento.sessao IS
  'Fita ou sessão do ato (PF_FITA, ou PF_SESSAO na porta). 0097.';
COMMENT ON COLUMN sessao.caderno_evento.porque IS
  'O motivo, o destino ou a marca, em texto. 0097.';
COMMENT ON COLUMN sessao.caderno_evento.em IS
  'Quando. 0097.';

-- 4. O uso da aresta: uma linha por fita, e a fita conta uma vez (arq:0120 §2).
CREATE TABLE IF NOT EXISTS sessao.caderno_aresta_uso (
  entrada_id bigint      NOT NULL REFERENCES sessao.caderno_entrada(id),
  fita       text        NOT NULL CHECK (length(btrim(fita)) > 0),
  para_que   text        NOT NULL
                         CHECK (length(btrim(para_que)) > 0 AND char_length(para_que) <= 600),
  quem       text        NOT NULL CHECK (quem IN ('dono', 'cadeira')),
  declarada  boolean     NOT NULL,
  em         timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (entrada_id, fita)
);
CREATE INDEX IF NOT EXISTS caderno_aresta_uso_em_idx ON sessao.caderno_aresta_uso (em);

COMMENT ON TABLE sessao.caderno_aresta_uso IS
  'Prova de uso de uma aresta do caderno: a fita que puxou a matéria e a usou na resposta. A colheita conta fitas e cadeiras distintas por par de pontas (#3218). 0097.';
COMMENT ON COLUMN sessao.caderno_aresta_uso.fita IS
  'PF_FITA, ou PF_SESSAO onde a porta não injeta fita. Chave da contagem: uma vez por fita. 0097.';
COMMENT ON COLUMN sessao.caderno_aresta_uso.para_que IS
  'Uma linha: a relação que a cadeira viu ao usar. 0097.';
COMMENT ON COLUMN sessao.caderno_aresta_uso.quem IS
  'Quem puxou: dono (pediu) ou cadeira (foi buscar). 0097.';
COMMENT ON COLUMN sessao.caderno_aresta_uso.declarada IS
  'Se o destino já está na consulta dirigida (seção c) do chapéu. 0097.';
COMMENT ON COLUMN sessao.caderno_aresta_uso.em IS
  'Quando a fita marcou. 0097.';

-- 5. O legado: os cadernos em arquivo, capturados para a cadeira triar (arq:0120 §11).
CREATE TABLE IF NOT EXISTS sessao.caderno_legado (
  chave_origem text        PRIMARY KEY,
  cadeira      text        NOT NULL,
  chapeu       text        NOT NULL,
  texto        text        NOT NULL,
  bytes        integer     NOT NULL CHECK (bytes > 0),
  sha256       text        NOT NULL,
  capturado_em timestamptz NOT NULL DEFAULT now(),
  triado_em    timestamptz
);
CREATE INDEX IF NOT EXISTS caderno_legado_pendente_idx ON sessao.caderno_legado (cadeira, chapeu)
  WHERE triado_em IS NULL;

COMMENT ON TABLE sessao.caderno_legado IS
  'Os cadernos em arquivo (abertura/<cadeira>/<chapeu>/caderno.md), capturados por `mesa legado --caderno --capturar` para a cadeira triar pela arq:0120. Servido no corpo do chapéu até triado. 0097.';
COMMENT ON COLUMN sessao.caderno_legado.chave_origem IS
  'O caminho do arquivo capturado, relativo à árvore da abertura. 0097.';
COMMENT ON COLUMN sessao.caderno_legado.sha256 IS
  'Digest do texto capturado: a recaptura só troca o texto quando o arquivo mudou e a triagem não fechou. 0097.';
COMMENT ON COLUMN sessao.caderno_legado.triado_em IS
  'Quando a cadeira terminou de triar o legado do chapéu; daí em diante ele não se serve. 0097.';

-- 6. Nada se apaga (arq:0120 §6): DELETE e TRUNCATE recusados nas quatro tabelas.
CREATE OR REPLACE FUNCTION sessao.caderno_nada_se_apaga() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'caderno: nada se apaga (arq:0120 §6); a saída é mudança de estado'
    USING ERRCODE = 'restrict_violation';
END $$;

COMMENT ON FUNCTION sessao.caderno_nada_se_apaga() IS
  'Recusa DELETE e TRUNCATE nas tabelas do caderno (arq:0120 §6). 0097.';

DROP TRIGGER IF EXISTS caderno_entrada_nada_se_apaga ON sessao.caderno_entrada;
CREATE TRIGGER caderno_entrada_nada_se_apaga BEFORE DELETE ON sessao.caderno_entrada
  FOR EACH ROW EXECUTE FUNCTION sessao.caderno_nada_se_apaga();
DROP TRIGGER IF EXISTS caderno_entrada_nada_se_trunca ON sessao.caderno_entrada;
CREATE TRIGGER caderno_entrada_nada_se_trunca BEFORE TRUNCATE ON sessao.caderno_entrada
  FOR EACH STATEMENT EXECUTE FUNCTION sessao.caderno_nada_se_apaga();

DROP TRIGGER IF EXISTS caderno_evento_nada_se_apaga ON sessao.caderno_evento;
CREATE TRIGGER caderno_evento_nada_se_apaga BEFORE DELETE ON sessao.caderno_evento
  FOR EACH ROW EXECUTE FUNCTION sessao.caderno_nada_se_apaga();
DROP TRIGGER IF EXISTS caderno_evento_nada_se_trunca ON sessao.caderno_evento;
CREATE TRIGGER caderno_evento_nada_se_trunca BEFORE TRUNCATE ON sessao.caderno_evento
  FOR EACH STATEMENT EXECUTE FUNCTION sessao.caderno_nada_se_apaga();

DROP TRIGGER IF EXISTS caderno_aresta_uso_nada_se_apaga ON sessao.caderno_aresta_uso;
CREATE TRIGGER caderno_aresta_uso_nada_se_apaga BEFORE DELETE ON sessao.caderno_aresta_uso
  FOR EACH ROW EXECUTE FUNCTION sessao.caderno_nada_se_apaga();
DROP TRIGGER IF EXISTS caderno_aresta_uso_nada_se_trunca ON sessao.caderno_aresta_uso;
CREATE TRIGGER caderno_aresta_uso_nada_se_trunca BEFORE TRUNCATE ON sessao.caderno_aresta_uso
  FOR EACH STATEMENT EXECUTE FUNCTION sessao.caderno_nada_se_apaga();

DROP TRIGGER IF EXISTS caderno_legado_nada_se_apaga ON sessao.caderno_legado;
CREATE TRIGGER caderno_legado_nada_se_apaga BEFORE DELETE ON sessao.caderno_legado
  FOR EACH ROW EXECUTE FUNCTION sessao.caderno_nada_se_apaga();
DROP TRIGGER IF EXISTS caderno_legado_nada_se_trunca ON sessao.caderno_legado;
CREATE TRIGGER caderno_legado_nada_se_trunca BEFORE TRUNCATE ON sessao.caderno_legado
  FOR EACH STATEMENT EXECUTE FUNCTION sessao.caderno_nada_se_apaga();

-- 7. Aceite: a forma e as recusas, provadas sem gravar nada do próprio aceite.
DO $$
DECLARE
  n     bigint;
  falta text;
BEGIN
  SELECT string_agg(t, ', ' ORDER BY t) INTO falta
    FROM unnest(array['caderno_entrada', 'caderno_evento', 'caderno_aresta_uso',
                      'caderno_legado']) t
   WHERE NOT EXISTS (SELECT 1 FROM information_schema.tables
                      WHERE table_schema = 'sessao' AND table_name = t);
  IF falta IS NOT NULL THEN
    RAISE EXCEPTION '0097: faltam tabelas: %', falta;
  END IF;

  SELECT count(*) INTO n FROM information_schema.columns
   WHERE table_schema = 'sessao' AND table_name = 'caderno_entrada'
     AND column_name IN ('id', 'cadeira', 'chapeu', 'categoria', 'estado', 'texto', 'caso',
                         'dito_em', 'dito_onde', 'vale_ate', 'ate_que', 'de_ponta', 'para_ponta',
                         'em_tombamento', 'candidata', 'destino', 'motivo', 'substituida_por',
                         'criada_em', 'confirmada_em', 'criada_por');
  IF n <> 21 THEN
    RAISE EXCEPTION '0097: sessao.caderno_entrada tem % das 21 colunas', n;
  END IF;
  IF EXISTS (SELECT 1 FROM information_schema.columns
              WHERE table_schema = 'sessao' AND table_name = 'caderno_entrada'
                AND column_name = 'blob_sha') THEN
    RAISE EXCEPTION '0097: a projeção de 001 continua no lugar';
  END IF;

  -- As recusas da arq:0120 §5.3 que cabem no banco. Cada INSERT tem de cair em check_violation;
  -- o que entrar aborta a migração inteira.
  BEGIN
    INSERT INTO sessao.caderno_entrada (cadeira, chapeu, categoria, texto)
    VALUES ('aceite-0097', 'aceite', 'licao', 'lição sem o caso');
    RAISE EXCEPTION '0097: lição sem caso entrou';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO sessao.caderno_entrada (cadeira, chapeu, categoria, texto, dito_em)
    VALUES ('aceite-0097', 'aceite', 'preferencia', 'preferência sem onde', current_date);
    RAISE EXCEPTION '0097: preferência sem onde entrou';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO sessao.caderno_entrada (cadeira, chapeu, categoria, texto)
    VALUES ('aceite-0097', 'aceite', 'premissa', 'premissa sem validade');
    RAISE EXCEPTION '0097: premissa sem validade entrou';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO sessao.caderno_entrada (cadeira, chapeu, categoria, texto, vale_ate)
    VALUES ('aceite-0097', 'aceite', 'premissa', 'premissa de 61 dias', current_date + 61);
    RAISE EXCEPTION '0097: premissa além de 60 dias entrou';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO sessao.caderno_entrada (cadeira, chapeu, categoria, texto, de_ponta)
    VALUES ('aceite-0097', 'aceite', 'aresta', 'aresta sem o para', 'conceito:x');
    RAISE EXCEPTION '0097: aresta sem uma das pontas entrou';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO sessao.caderno_entrada (cadeira, chapeu, categoria, texto, caso)
    VALUES ('aceite-0097', 'aceite', 'licao', repeat('x', 601), '#3218');
    RAISE EXCEPTION '0097: entrada de 601 caracteres entrou';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO sessao.caderno_entrada (cadeira, chapeu, categoria, texto)
    VALUES ('aceite-0097', 'aceite', 'diario', 'categoria fora das quatro');
    RAISE EXCEPTION '0097: categoria fora das quatro entrou';
  EXCEPTION WHEN check_violation THEN NULL;
  END;

  -- Nada se apaga: uma entrada válida entra, o DELETE dela é recusado, e o bloco se desfaz.
  BEGIN
    INSERT INTO sessao.caderno_entrada (cadeira, chapeu, categoria, texto, caso)
    VALUES ('aceite-0097', 'aceite', 'licao', 'lição válida do aceite', '#3218')
    RETURNING id INTO n;
    BEGIN
      DELETE FROM sessao.caderno_entrada WHERE id = n;
      RAISE EXCEPTION '0097: DELETE passou no caderno';
    EXCEPTION WHEN restrict_violation THEN NULL;
    END;
    RAISE EXCEPTION USING ERRCODE = 'PF997', MESSAGE = '0097: desfaz a linha do aceite';
  EXCEPTION WHEN SQLSTATE 'PF997' THEN NULL;
  END;

  SELECT count(*) INTO n FROM sessao.caderno_entrada WHERE cadeira = 'aceite-0097';
  IF n <> 0 THEN
    RAISE EXCEPTION '0097: o aceite deixou % linha(s)', n;
  END IF;

  RAISE NOTICE '0097 aceite: 4 tabelas, 21 colunas na entrada, 7 recusas no banco e o DELETE barrado; nada do aceite gravado';
END $$;
