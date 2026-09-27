-- 0095_acervo_stack_sai_jaiminho.sql — golden record pos card #3117 (expurgo do codigo
-- jaiminho, ordem do dono 27/09/2026).
--
-- A stack `jaiminho` (seed da 0091) aponta compose em
-- /opt/platafirma/current/harness/jaiminho/docker-compose.yml, e esse diretorio ja nao
-- existe no repositorio. Linha de topologia sem compose e ponteiro morto: `release
-- promover` e `infra up` a leriam como stack valida.
--
-- NAO toca a conta de SO `jaiminho` (uid 1003), o client `jaiminho-fabrica` nem os
-- segredos em /srv/platafirma/casa/segredos/jaiminho/: a ordem foi apagar o codigo, e a
-- conta fica.
--
-- Idempotente: delete por slug; rodar de novo nao acha nada. A stack tinha uma linha
-- dependente em acervo.capacidade_roda_em_stack (FK), que sai primeiro. `migrar aplicar`
-- ja abre a transacao: sem begin/commit aqui. Aplicada em rag em 27/09/2026.

delete from acervo.capacidade_roda_em_stack
 where stack_id in (select id from acervo.stack where slug = 'jaiminho');

delete from acervo.stack where slug = 'jaiminho';
