-- 0076b_ferramental_campos_abertos.sql — migração ADITIVA, nível 1-2.
-- Estende o golden record de ferramental (0076) sem tocar DDL nem seed que já
-- subiram. Cada campo/tabela aqui tem DONO e NATUREZA próprios (declaração por
-- humano vs reconciliação por fonte) — anotados por campo. Nenhum depende de
-- stacks.json (que morre depois que o seed vira SoT), nem do nível 3.
--
-- Sobe VAZIO. Estrutura é de TI; conteúdo pinga de cada dono no seu tempo.
-- Régua: coluna tolera NULL; migração NÃO espera consenso de dono. (acervo.conceito
-- cresceu assim: outros_rotulos não esperou origem.)
--
-- Idempotente. NÃO faz DROP.

begin;

-- ── em_vez_de: anti-padrão → verbo canônico (nível 2) ───────────────────────
-- DONO: cada dono de verbo (distribuído). NATUREZA: híbrida —
--   parte RECONCILIÁVEL (fonte-máquina: log de run_command em var/log/ops/ propõe
--   pares "invocação crua que replica verbo"), parte DECLARADA (dono confirma).
-- PROPÓSITO: matar a "Coisa 1" do card #2410 — run_command fazendo o que já é verbo.
--   Ex.: verbo 'acervo'.em_vez_de = 'psql direto no schema acervo'.
-- NÃO é "Coisa 2" (grep vs rg): isso é higiene de ofício, mora no caderno do
--   chapéu / ficha do verbo, NÃO no golden record. Ver decisão do (c): comando de
--   sistema não entra na espinha.
alter table acervo.ferramental_verbo
  add column if not exists em_vez_de text;

-- ── capacidade_usa_comando: comando sensível usado por capacidade ────────────
-- Tabela de LIGAÇÃO (M:N), NÃO quarto nível da espinha. Precedente: obra_trata_de
--   (conceito↔obra é ligação, não nível dentro de conceito). A espinha
--   capacidade→verbo→instância fica INTOCADA; isto pendura ao lado.
-- DONO da RÉGUA (o que é sensível, e a faixa): claudinho-seguranca (Leonardo),
--   seg:0010. DONO do FATO (quem chama o quê): reconciliação por varredura dos
--   scripts (fonte-máquina), que eu rodo; humano só revisa.
-- A coluna 'faixa' NÃO é adjetivo livre: referencia a classificação por VETOR da
--   análise de Leonardo (risco-superficie-conta-segregada.md, fa83386):
--     1 = escape real (docker c/ socket alcançável, daemon próprio, nsenter/unshare/chroot/mount)
--     2 = amplia raio de segredo (curl/wget/nc/ssh/gpg/openssl…) — controle é custódia, não negação
--     3 = NÃO é risco pela régua (gcc/make/python3/su/passwd inertes) — registrado p/ NÃO tratar como controle
--   O CHECK impede a tabela de contradizer a análise (faixa fora de 1-3 é erro).
--   Faixa 1 é o que o manifesto de build do #2436 nega por AUSÊNCIA nas cadeiras
--   que não a declaram; faixa 2/3 nunca entram como negação.
create table if not exists acervo.ferramental_capacidade_usa_comando (
    id            bigint generated always as identity primary key,
    capacidade_id bigint not null references acervo.ferramental_capacidade(id),
    comando       text   not null,                 -- nome do binário (docker, curl, nsenter…)
    faixa         smallint not null,               -- vetor de escape, régua seg:0010 / análise fa83386
    nota          text,                            -- por quê / qual invocação (declaração do dono)
    unique (capacidade_id, comando),
    constraint faixa_valida check (faixa in (1,2,3))
);
create index if not exists ix_cap_usa_comando_cap
  on acervo.ferramental_capacidade_usa_comando(capacidade_id);
create index if not exists ix_cap_usa_comando_faixa
  on acervo.ferramental_capacidade_usa_comando(faixa);

commit;
