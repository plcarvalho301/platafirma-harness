-- 0076e_ferramental_nivel2_propriedade.sql
-- Averbacao BIZBOK fase 2 (arq:0079) — claudinho-dados, sob arq:0059 (capacidade unica
-- no mapa) + arq:0008 (uma fonte por vocabulario: edita-se a FONTE e repromove).
-- Fecha as 3 reclassificacoes que a fase 1 (arquiteto, 0079-fase1-...sql) deixou apenas
-- SINALIZADAS na coluna descricao (marca "RECLASSIFICAR").
--
-- Regua (docs/arquitetura-negocio-operacao.md, mapa BIZBOK):
--   - memoria, encerramento -> nivel-2 de expediente (expediente/memoria, expediente/encerramento).
--   - inferencia(-local) -> NAO e capacidade, e PROPRIEDADE da ferramenta; motor absorveu
--     na fusao aceita em 2026-08-09. Sai da espinha do golden record.
--
-- O golden record ferramental_capacidade era flat nivel-1. Aqui ganha o eixo de
-- DECOMPOSICAO de negocio (pai_id, self-ref) SEM tocar a bijecao capacidade<->verbo
-- chumbada em 0076/arq:0037: a nivel-2 mantem o proprio verbo (mesa, descansar) e apenas
-- passa a apontar o pai nivel-1. Nao confundir este eixo com a espinha tecnica
-- capacidade -> verbo -> instancia (que continua intocada).
--
-- Idempotente. NAO faz DROP de tabela. Deletes por slug re-rodam sem efeito.

begin;

-- 1. Eixo de decomposicao BIZBOK: nivel-2 aponta o pai nivel-1. NULL = nivel-1.
alter table acervo.ferramental_capacidade
  add column if not exists pai_id bigint references acervo.ferramental_capacidade(id);

comment on column acervo.ferramental_capacidade.pai_id is
  'Decomposicao BIZBOK (arq:0079/0059): NULL=nivel-1; preenchido=nivel-2, filha da capacidade pai. Eixo de negocio, ORTOGONAL a espinha tecnica capacidade->verbo->instancia.';

-- 2. memoria, encerramento -> nivel-2 de expediente. Verbo (mesa, descansar) preservado;
--    a bijecao segue valida porque a capacidade continua existindo, so ganha pai.
update acervo.ferramental_capacidade
   set pai_id     = (select id from acervo.ferramental_capacidade where slug = 'expediente'),
       descricao  = 'Nivel-2 de expediente (BIZBOK arq:0079/0059). Averbado por claudinho-dados.'
 where slug in ('memoria', 'encerramento');

-- 3. inferencia-local -> propriedade: sai da espinha. Medido 26/08: 0 refs em
--    capacidade_roda_em_stack (capacidade_id e exposicao_de) e 0 em
--    ferramental_capacidade_usa_comando. A cadeia e instancia(ollama) -> verbo(ollama)
--    -> capacidade(inferencia-local); ollama, a inferencia local, permanece registrado
--    em registro/stacks.json (fora da espinha). Deleta na ordem das FKs.
delete from acervo.ferramental_instancia
 where verbo_id in (
   select v.id from acervo.ferramental_verbo v
     join acervo.ferramental_capacidade c on c.id = v.capacidade_id
    where c.slug = 'inferencia-local');

delete from acervo.ferramental_verbo
 where capacidade_id in (
   select id from acervo.ferramental_capacidade where slug = 'inferencia-local');

delete from acervo.ferramental_capacidade
 where slug = 'inferencia-local';

commit;
