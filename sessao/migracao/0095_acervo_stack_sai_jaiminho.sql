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
-- Idempotente: delete por slug; rodar de novo nao acha nada. Sem instancia dependente
-- medida em 27/09/2026 (`acervo listar topologia jaiminho --completo`: instancias -).

begin;

delete from acervo.stack where slug = 'jaiminho';

commit;
