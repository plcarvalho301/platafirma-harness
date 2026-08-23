-- Entidades operacionais da montagem de sessão.
-- capacidade: memoria · dono: claudinho-TI (substrato) · modelo: claudinho-dados
-- Fonte do modelo: platafirma-arquitetura/docs/spec_montagem-de-sessao.md §3, card #189 fase 6.
--
-- Raiz do agregado é a FITA. Tudo aqui muda por fita, não por decisão: o que muda por
-- decisão é o CATÁLOGO, que é canônico em git e não mora neste banco (spec §3).
--
-- Referência que cruza fronteira de componente é LÓGICA, sem FK, por arq:0046:
--   fita.persona        -> identidade.identidade (instância do core, 5435)
--   peca_servida.peca   -> arvore abertura/**/*.md + PECAS_VERBO no montador (#262)
--   mesa_item.chapeu    -> abertura/<cadeira>/<slug>/chapeu.md
-- Sem FK possível entre instâncias, e é por isso que não há JOIN acidental a lembrar.

CREATE SCHEMA IF NOT EXISTS sessao;

-- ---------------------------------------------------------------- fita
-- Uma linha por fita aberta em qualquer superfície. O `id` é o mesmo que hoje viaja
-- na chave de fita corrente do Valkey (card 449) — não se inventa id novo aqui.
CREATE TABLE sessao.fita (
  id            text        PRIMARY KEY,
  persona       text        NOT NULL,
  superficie    text        NOT NULL CHECK (superficie IN ('claude.ai', 'chat', 'code')),
  aberta_em     timestamptz NOT NULL DEFAULT now(),
  encerrada_em  timestamptz,
  encerramento  text        CHECK (encerramento IN ('marco', 'zerar', 'abandono', 'erro')),
  -- fita encerrada declara COMO encerrou; fita viva não declara nenhum dos dois.
  CONSTRAINT fita_encerramento_par
    CHECK ((encerrada_em IS NULL) = (encerramento IS NULL))
);

CREATE INDEX fita_viva_idx ON sessao.fita (persona, aberta_em DESC)
  WHERE encerrada_em IS NULL;

-- ---------------------------------------------------------------- giro
-- Um giro é um turno servido. `chapeu` é o vigente NO giro: é o dado que permite
-- medir carga de chapéu depois, e sem ele a camada C não tem baseline (spec fase 9).
CREATE TABLE sessao.giro (
  fita_id  text        NOT NULL REFERENCES sessao.fita(id) ON DELETE CASCADE,
  seq      integer     NOT NULL CHECK (seq > 0),
  chapeu   text,
  em       timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (fita_id, seq)
);

-- ---------------------------------------------------------------- pacote
-- 1:1 com a fita: o pacote é a materialização da abertura, e abertura acontece uma vez.
-- `montador_sha` é o SHA do clone do montador — por arq:0058 um clone só data o pacote
-- inteiro, então é um campo, não um por peça.
CREATE TABLE sessao.pacote (
  fita_id      text        PRIMARY KEY REFERENCES sessao.fita(id) ON DELETE CASCADE,
  montado_em   timestamptz NOT NULL DEFAULT now(),
  montador_sha text,
  tokens       integer     CHECK (tokens >= 0)
);

-- ---------------------------------------------------------------- peça servida
-- Envelope uniforme da spec §6.2 menos o que deriva do catálogo. `dono` NÃO é campo:
-- deriva de `peca` no catálogo, e campo derivável declarado é segunda fonte.
-- `frescor` inclui 'indisponivel' de propósito: substrato fora do ar se declara
-- indisponível, nunca como peça vazia.
CREATE TABLE sessao.peca_servida (
  fita_id text     NOT NULL REFERENCES sessao.pacote(fita_id) ON DELETE CASCADE,
  peca    text     NOT NULL,
  ordem   smallint NOT NULL,
  ref     text     NOT NULL,
  sha     text,
  regime  text     NOT NULL CHECK (regime IN ('valor', 'indice', 'ponteiro')),
  tokens  integer  CHECK (tokens >= 0),
  frescor text     NOT NULL CHECK (frescor IN ('fresco', 'defasado', 'indisponivel')),
  PRIMARY KEY (fita_id, peca)
);

CREATE INDEX peca_servida_peca_idx ON sessao.peca_servida (peca, frescor);

-- ---------------------------------------------------------------- item de mesa
-- Régua de mesa (spec §2): item tem ATO e ALVO, e esvazia por execução do ato.
-- `ato` e `alvo` são NOT NULL porque a admissão é isto — sem ato não é mesa, é outra peça.
-- Decisão fechada NÃO entra aqui: é a peça `antirreabertura`, que não tem ato e nunca esvazia.
CREATE TABLE sessao.mesa_item (
  id                 bigint      GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  cadeira            text        NOT NULL,
  chapeu             text        NOT NULL,
  ato                text        NOT NULL CHECK (length(btrim(ato)) > 0),
  alvo               text        NOT NULL CHECK (length(btrim(alvo)) > 0),
  texto              text,
  plantado_em        timestamptz NOT NULL DEFAULT now(),
  plantado_por_fita  text        REFERENCES sessao.fita(id) ON DELETE SET NULL,
  esvaziado_em       timestamptz,
  esvaziado_por_fita text        REFERENCES sessao.fita(id) ON DELETE SET NULL,
  CONSTRAINT mesa_item_esvaziamento_par
    CHECK ((esvaziado_em IS NULL) = (esvaziado_por_fita IS NULL))
);

-- O índice que a abertura usa: pendente de uma cadeira, por chapéu. Parcial porque item
-- esvaziado não entra em pacote nenhum e não deve pesar na leitura do caminho crítico.
CREATE INDEX mesa_item_pendente_idx ON sessao.mesa_item (cadeira, chapeu, plantado_em)
  WHERE esvaziado_em IS NULL;

-- ---------------------------------------------------------------- mesa legada
-- Destino do que JÁ ESTÁ ESCRITO no Valkey (spec §10, pendência de claudinho-TI).
-- O texto de hoje é prosa por chapéu, não item com ato: não há conversão por máquina,
-- e forçá-la fabricaria `ato` que ninguém escreveu. Fica aqui, legível, até a cadeira
-- dona reescrever o que ainda tiver ato pendente. A tabela some quando esvaziar.
--
-- A PK é a CHAVE DE ORIGEM, não (cadeira, chapeu), porque a mesa está partida em duas
-- por alias: `mem:ti:construcao` e `mem:claudinho-ti:construcao` existem as duas e
-- DIVERGEM (medido em 16/08 nas cinco cadeiras com par). Deduplicar na captura escolheria
-- por nós qual metade é a verdadeira; quem escolhe é a cadeira dona, lendo as duas.
CREATE TABLE sessao.mesa_legado (
  chave_origem   text        PRIMARY KEY,
  cadeira        text        NOT NULL,
  chapeu         text        NOT NULL,
  texto          text        NOT NULL,
  bytes          integer     NOT NULL,
  ttl_restante_s integer,
  capturado_em   timestamptz NOT NULL DEFAULT now(),
  triado_em      timestamptz
);

CREATE INDEX mesa_legado_pendente_idx ON sessao.mesa_legado (cadeira, chapeu)
  WHERE triado_em IS NULL;

-- ---------------------------------------------------------------- entrada de caderno
-- PROJEÇÃO, não fonte. O caderno é fonte editada pela cadeira e continua versionado em
-- `platafirma-harness@caderno/<cadeira>/<slug>.md` por arq:0042 — é de lá que saem diff e
-- revisão, que são a razão de o caderno não ser mesa. Esta tabela existe para o índice de
-- abertura sair por SQL junto do resto, e é regenerável do git a qualquer momento.
-- Enquanto o projetor da fase 5 não existir, fica vazia: vazia e declarada, não esquecida.
CREATE TABLE sessao.caderno_entrada (
  cadeira      text        NOT NULL,
  chapeu       text        NOT NULL,
  texto        text        NOT NULL,
  bytes        integer     NOT NULL,
  blob_sha     text        NOT NULL,
  escrita_em   timestamptz NOT NULL,
  projetado_em timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (cadeira, chapeu)
);
