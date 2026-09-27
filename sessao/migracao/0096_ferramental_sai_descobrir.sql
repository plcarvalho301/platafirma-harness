-- 0096_ferramental_sai_descobrir.sql — o verbo `descobrir` sai do golden record.
--
-- Ordem do dono, 27/09/2026 14:42 (incidente, carta 20260927T144250-seguranca): o verbo
-- morreu ha tempos e seguia no ar, pedindo `acervo:*` que nenhuma regra concede e induzindo
-- diagnostico errado. O sucessor responde: `acervo listar obra obra --sobre <termo>` e
-- `motor rag buscar` (spec acervo §8). Cai a trava do #3145 («nao apagar antes da busca por
-- assunto»).
--
-- Remove as linhas do verbo em todas as tabelas do ferramental que o citam (as quatro por
-- slug em `verbo` e a instancia por FK), depois o verbo. A capacidade 'descoberta' fica,
-- como 'mudanca' ficou na 0093: outras cinco tabelas a referenciam, e podar espinha de
-- capacidade e merito de dados.
--
-- Idempotente: DELETE de linha ausente nao falha.

begin;

delete from acervo.ferramental_instancia
 where verbo_id in (select id from acervo.ferramental_verbo where slug = 'descobrir');

delete from acervo.ferramental_ato      where verbo = 'descobrir';
delete from acervo.ferramental_acesso   where verbo = 'descobrir';
delete from acervo.ferramental_consumo  where verbo = 'descobrir';
delete from acervo.ferramental_ambiente where verbo = 'descobrir';

delete from acervo.ferramental_verbo where slug = 'descobrir';

commit;
