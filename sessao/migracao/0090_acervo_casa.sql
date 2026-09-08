-- 0090_acervo_casa.sql
-- Partição `casa` do acervo: texto declarado da casa (harness, ADR, spec, wiki,
-- cadernos, cabeçalhos de verbo, automações) recuperável por identidade exata
-- (repo@path) e por índice semântico próprio.
--
-- Fonte da régua: platafirma-arquitetura/docs/spec_acervo-casa.md (§1 três entidades
--   irmãs, §2 quatro eixos, §Schema coluna a coluna) e spec_acervo.md (§1 vocabulário
--   de entidade da partição casa). Decisão do dono, fita de 08/09/2026.
--
-- Contexto: #3019 ("Passo 1: partição acervo.casa") estava marcado Entregue mas a
-- partição NÃO existia no banco (conferido por psql, banco rag, 08/09). Esta é a
-- materialização que faltava.
--
-- Idempotente, aditiva, sem DROP. Segue o padrão de 0076_acervo_ferramental.sql:
-- schema `acervo` no banco rag, `especie_id uuid` FK para especie_tipo (o físico
-- vigente de acervo.obra usa especie_id uuid, não `tipo text` — a spec descreve o
-- conceitual; o físico é de dados e espelha obra).
--
-- ORDEM TRAVADA pela spec (§Corte, item 1): as espécies novas entram em especie_tipo
-- ANTES da tabela acervo.casa, senão a FK especie_id fica órfã e a ingestão do passo 2
-- serve vazio sem erro.

begin;

-- ── Pré-passo: espécies de `casa` que faltam em especie_tipo ──────────────────
-- As 6 espécies documentais próprias da casa. Régua arq:0059 (tipo único; duplicado
-- funde, ambíguo parte): conferido que nenhuma já existe (só adr, spec, minuta de
-- casa existiam). Família padrao-tecnico: são padrões técnicos que a casa declara
-- sobre si mesma. `on conflict (slug) do nothing` garante idempotência.
insert into acervo.especie_tipo (id, slug, familia_id, forma_canonica) values
  (gen_random_uuid(), 'pagina',             'b3310ea1-8e32-4512-b979-0cd4121c8611', 'Página'),
  (gen_random_uuid(), 'caderno',            'b3310ea1-8e32-4512-b979-0cd4121c8611', 'Caderno'),
  (gen_random_uuid(), 'chapeu',             'b3310ea1-8e32-4512-b979-0cd4121c8611', 'Chapéu'),
  (gen_random_uuid(), 'persona',            'b3310ea1-8e32-4512-b979-0cd4121c8611', 'Persona'),
  (gen_random_uuid(), 'cabecalho-de-verbo', 'b3310ea1-8e32-4512-b979-0cd4121c8611', 'Cabeçalho de verbo'),
  (gen_random_uuid(), 'automacao',          'b3310ea1-8e32-4512-b979-0cd4121c8611', 'Automação')
on conflict (slug) do nothing;

-- ── Enums dos eixos (spec §2) ────────────────────────────────────────────────
-- natureza: golden · derivado · documentacao (derivado NÃO indexa — §4.3)
-- ciclo:    minuta · publicado · superado (superado = aposentar-e-criar por sha)
-- Criados por DO-block para idempotência (CREATE TYPE não tem IF NOT EXISTS).
do $$ begin
  create type acervo.casa_natureza as enum ('golden','derivado','documentacao');
exception when duplicate_object then null; end $$;

do $$ begin
  create type acervo.casa_ciclo as enum ('minuta','publicado','superado');
exception when duplicate_object then null; end $$;

-- classe do referente (spec §Schema, casa_referente.tipo_ref): vocabulário fechado
-- pelo mapa de topologia (§2). N:N nunca pré-filtra o vetor (§4) — só resolve exato
-- e rotula o retorno.
do $$ begin
  create type acervo.casa_tipo_ref as enum (
    'verbo','ferramenta','stack','cadeira','chapeu','gerencia','capacidade',
    'conceito','decisao','contrato','superficie','morada','ato'
  );
exception when duplicate_object then null; end $$;

-- ── acervo.casa — texto declarado da casa ────────────────────────────────────
-- Identidade natural (repo, path). sha distingue fresco de fóssil (§6). SEM coluna
-- de embedding (emenda arq:0105): o vetor vive em motor.vetor por alvo_id.
create table if not exists acervo.casa (
    id          uuid primary key default gen_random_uuid(),
    repo        text not null,                          -- clone de origem
    path        text not null,                          -- caminho no repo
    sha         text not null,                          -- sha do ref publicado ingerido
    dono        text not null,                          -- cadeira dona (slug puro)
    especie_id  uuid not null references acervo.especie_tipo(id),  -- espécie documental
    natureza    acervo.casa_natureza not null,          -- golden/derivado/documentacao
    ciclo       acervo.casa_ciclo not null,             -- minuta/publicado/superado
    titulo      text,                                   -- human-legível, quando há
    corpo       text not null,                          -- texto ingerido (chunkado na ingestão)
    criado_em   timestamptz not null default now(),
    constraint casa_identidade unique (repo, path)
);

create index if not exists ix_casa_especie  on acervo.casa(especie_id);
create index if not exists ix_casa_dono      on acervo.casa(dono);
create index if not exists ix_casa_natureza  on acervo.casa(natureza);

-- ── acervo.casa_referente — ligação N:N doc ↔ entidade da casa ────────────────
-- Um ADR que toca três capacidades = três linhas. Usado pelo resolvedor exato (§4.2)
-- e para rotular o retorno; NUNCA para pré-filtrar o vetor.
create table if not exists acervo.casa_referente (
    casa_id  uuid not null references acervo.casa(id) on delete cascade,
    tipo_ref acervo.casa_tipo_ref not null,            -- classe do referente
    ref      text not null,                             -- slug/id da entidade referida
    primary key (casa_id, tipo_ref, ref)
);

create index if not exists ix_casa_referente_ref on acervo.casa_referente(tipo_ref, ref);

commit;
