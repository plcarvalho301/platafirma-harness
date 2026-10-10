-- 0100_usuario_leitura_sessao.sql — Usuário de leitura no banco de sessão para o gravador do acervo (card #3375)
--
-- O que faz:
-- Cria a role `sessao_leitor` com LOGIN e concede apenas CONNECT no banco `sessao`,
-- USAGE no schema `sessao` e SELECT na tabela `sessao.sessao`.
--
-- Aplicação: `release migrar aplicar sessao` com este arquivo no stdin. Idempotente.
--
-- Rollback:
--   REVOKE SELECT ON sessao.sessao FROM sessao_leitor;
--   REVOKE USAGE ON SCHEMA sessao FROM sessao_leitor;
--   REVOKE CONNECT ON DATABASE sessao FROM sessao_leitor;
--   DROP ROLE IF EXISTS sessao_leitor;

DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'sessao_leitor') THEN
    CREATE ROLE sessao_leitor WITH LOGIN;
  END IF;
END $$;

GRANT CONNECT ON DATABASE sessao TO sessao_leitor;
GRANT USAGE ON SCHEMA sessao TO sessao_leitor;
GRANT SELECT ON sessao.sessao TO sessao_leitor;

COMMENT ON ROLE sessao_leitor IS
  'Usuário de leitura para conferência de sessao_id na gravação do acervo (card #3375). 0100.';

DO $$
BEGIN
  RAISE NOTICE '0100 aceite: role sessao_leitor criada com SELECT em sessao.sessao; nada do aceite gravado';
END $$;
