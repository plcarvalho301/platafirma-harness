-- 0076c_acervo_stack.sql — entidade stack-de-deploy + ligação M:N com instância.
-- OK de claudinho-dados (Olga), fila 20260824T132320 + correção de nome 132440.
-- Schema conceitual é dela (entra no corpo do arq:0076); DDL/migração/seed são de TI.
--
-- Nomes cravados por ela:
--   acervo.stack                  — NÃO ferramental_stack (stack não é ferramenta,
--                                   é onde ferramenta roda) NEM deploy_stack
--                                   (redundante no namespace acervo). "acervo.stack diz tudo".
--   acervo.instancia_roda_em_stack — ligação M:N (ela pertence à fronteira entre os eixos).
--
-- Eixo ORTOGONAL à espinha: a espinha responde "o que a firma sabe fazer";
-- stack responde "o que sobe junto num compose". Cruzar (JOIN) é o valor; fundir seria erro.
-- Por isso entidade nova AO LADO de _capacidade/_verbo/_instancia, não coluna nelas.
--
-- M:N confirmado no dado (Olga mediu, dono supôs 1:N): rastreador roda em 2 stacks;
-- core hospeda vários serviços. Os dois lados plurais.
--
-- Idempotente. NÃO faz DROP. Migra os campos REAIS do stacks.json (medidos @host).

begin;

-- ── Entidade: stack de deploy (unidade de compose) ──────────────────────────
-- Identidade própria (ciclo de vida e dono independentes de instância que roda nela:
-- harness-sessao é stack e não hospeda nenhuma das 4 instâncias — Olga). Campos
-- operacionais: DONO do CONTEÚDO é TI (compose/reversao/segredos são operação de
-- deploy); Olga modela o campo, não o conteúdo.
create table if not exists acervo.stack (
    id       bigint generated always as identity primary key,
    slug     text not null unique,        -- core, motor, rag, jaiminho, …
    papel    text,                        -- descrição da unidade de deploy
    critico  boolean,                     -- stacks.json.critico
    repo     text,                        -- repo de origem
    compose  text,                        -- caminho do docker-compose.yml
    rotas    jsonb,                       -- stacks.json.rotas (forma livre)
    segredos jsonb,                       -- paths de segredo (operação, dono TI)
    reversao jsonb,                       -- via/quem/janela_min/estado (operação, dono TI)
    gate     jsonb,                       -- stacks.json.gate
    profiles jsonb,                       -- stacks.json.profiles
    nota     text                         -- stacks.json._nota
);

-- ── Ligação M:N: instância roda em stack ────────────────────────────────────
-- PK composta, FK dos dois lados, nenhum UNIQUE simples (Olga). Mesma forma de
-- _capacidade_usa_comando. Instância SEM linha aqui = órfã de stack (ollama hoje);
-- o gate acusa, não se apaga o fato.
create table if not exists acervo.instancia_roda_em_stack (
    instancia_id bigint not null references acervo.ferramental_instancia(id),
    stack_id     bigint not null references acervo.stack(id),
    primary key (instancia_id, stack_id)
);
create index if not exists ix_roda_em_stack_stack
  on acervo.instancia_roda_em_stack(stack_id);

commit;
