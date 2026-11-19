-- 0102 — Remoção definitiva das tabelas de caderno do schema sessao (#4377).
--
-- Os cadernos de todas as cadeiras foram despejados na família negocio.mensagem
-- do banco de eventos (peça despejo-caderno, #4355/#4377) e os leitores ativos
-- de sessao.caderno_* foram retirados antes da aplicação desta migração.
--
-- Ordem filhas-antes-da-mãe: caderno_aresta_uso, caderno_evento, caderno_legado,
-- caderno_entrada, seguida da função sessao.caderno_nada_se_apaga().
-- Não toca em sessao.mesa_item nem em sessao.mesa_legado.
--
-- Aplicação: `release migrar aplicar sessao` com este arquivo no stdin. Idempotente.

DROP TABLE IF EXISTS sessao.caderno_aresta_uso;
DROP TABLE IF EXISTS sessao.caderno_evento;
DROP TABLE IF EXISTS sessao.caderno_legado;
DROP TABLE IF EXISTS sessao.caderno_entrada;
DROP FUNCTION IF EXISTS sessao.caderno_nada_se_apaga();

DO $$
DECLARE
  n_tabelas integer;
  n_funcoes integer;
BEGIN
  SELECT count(*) INTO n_tabelas
    FROM information_schema.tables
   WHERE table_schema = 'sessao'
     AND table_name LIKE 'caderno_%';
  IF n_tabelas <> 0 THEN
    RAISE EXCEPTION '0102: ainda restam % tabela(s) caderno_%% em sessao', n_tabelas;
  END IF;

  SELECT count(*) INTO n_funcoes
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
   WHERE n.nspname = 'sessao'
     AND p.proname = 'caderno_nada_se_apaga';
  IF n_funcoes <> 0 THEN
    RAISE EXCEPTION '0102: função sessao.caderno_nada_se_apaga() ainda existe';
  END IF;
END $$;
