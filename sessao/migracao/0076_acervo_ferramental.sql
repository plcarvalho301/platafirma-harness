-- 0076_acervo_ferramental.sql
-- Fatia física (TI) da minuta 0012 / ADR 0076: golden record de ferramental
-- como schema relacional de 3 níveis, simétrico a acervo.conceito.
--
-- capacidade (1:1) → verbo (1:N) → instância.
--   - capacidade↔verbo: bijeção, chumbada por UNIQUE em verbo.capacidade_id.
--   - verbo→instância: 1:N (verbo_id NÃO unique).
-- Fonte da régua: platafirma-arquitetura/macro-global/decisions/
--   0076-catalogo-de-ferramental-golden-record-relacional.md
-- Fonte do desenho lógico: card #2430 (posição de dados).
--
-- Idempotente: roda mais de uma vez sem quebrar. NÃO faz DROP — migração aditiva.
-- Atributos "abertos" (nível 1-2 arquiteto, nível 3 TI) entram por ALTER em
-- migração posterior, quando a régua de cada campo estiver lavrada. Aqui só o
-- esqueleto de identidade que a spec cravou.

begin;

-- Nível 1 — capacidade: o que a firma sabe fazer. Golden record de espinha.
create table if not exists acervo.ferramental_capacidade (
    id        bigint generated always as identity primary key,
    slug      text not null unique,          -- vocabulário controlado, não texto livre
    rotulo    text,                           -- nome de exibição
    descricao text                            -- o que a capacidade É, uma frase
);

-- Nível 2 — verbo: o realizador canônico. 1:1 com capacidade.
create table if not exists acervo.ferramental_verbo (
    id            bigint generated always as identity primary key,
    slug          text not null unique,       -- nome do executável (bin/<verbo>)
    capacidade_id bigint not null unique      -- UNIQUE => chumba o 1:1 nos dois sentidos
                  references acervo.ferramental_capacidade(id),
    sot           text                        -- system of record: bin/<verbo>
);

-- Nível 3 — instância: o realizador concreto. 1:N com verbo.
-- NÃO é linha de capacidade nem cidadão de 1ª classe da espinha.
create table if not exists acervo.ferramental_instancia (
    id       bigint generated always as identity primary key,
    slug     text not null unique,
    verbo_id bigint not null                  -- lado N: SEM unique
             references acervo.ferramental_verbo(id),
    sot      text                             -- registro/stacks.json p/ serviço, etc.
);

create index if not exists ix_ferramental_verbo_capacidade
    on acervo.ferramental_verbo(capacidade_id);
create index if not exists ix_ferramental_instancia_verbo
    on acervo.ferramental_instancia(verbo_id);

commit;
