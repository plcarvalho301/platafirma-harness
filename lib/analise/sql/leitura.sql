-- analise_leitura — a role com que o verbo analise lê um Postgres da casa (#4185).
-- O mesmo arquivo vale para todo banco de registro/bancos.json:
--   release migrar aplicar <banco>   com este arquivo no stdin.
-- Idempotente. Lê tudo o que o banco guarda (pg_read_all_data, por cima de RLS) e não
-- escreve nada: nenhum privilégio de escrita e transação só de leitura por padrão.
-- Não tem senha: entra só pelo socket local do contêiner (docker exec), como a sonda de saúde.
-- Rollback: REVOKE pg_read_all_data FROM analise_leitura; DROP ROLE analise_leitura;
SET LOCAL lock_timeout = '5s';
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'analise_leitura') THEN
    CREATE ROLE analise_leitura;
  END IF;
END $$;
ALTER ROLE analise_leitura LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION
  BYPASSRLS INHERIT CONNECTION LIMIT 4 PASSWORD NULL;
ALTER ROLE analise_leitura SET default_transaction_read_only = on;
ALTER ROLE analise_leitura SET statement_timeout = '120s';
ALTER ROLE analise_leitura SET lock_timeout = '2s';
ALTER ROLE analise_leitura SET idle_in_transaction_session_timeout = '30s';
ALTER ROLE analise_leitura SET work_mem = '16MB';
ALTER ROLE analise_leitura SET temp_file_limit = '512MB';
ALTER ROLE analise_leitura SET max_parallel_workers_per_gather = 0;
GRANT pg_read_all_data TO analise_leitura;
DO $$ BEGIN
  EXECUTE format('GRANT CONNECT ON DATABASE %I TO analise_leitura', current_database());
END $$;
COMMENT ON ROLE analise_leitura IS 'Leitura do verbo analise: lê todo o banco, não escreve, sem senha, só socket local. #4185.';
DO $$
DECLARE r pg_roles;
BEGIN
  SELECT * INTO r FROM pg_roles WHERE rolname = 'analise_leitura';
  IF r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication OR NOT r.rolcanlogin THEN
    RAISE EXCEPTION 'analise_leitura: atributo privilegiado';
  END IF;
  IF NOT pg_has_role('analise_leitura', 'pg_read_all_data', 'USAGE') THEN
    RAISE EXCEPTION 'analise_leitura: sem pg_read_all_data';
  END IF;
  IF EXISTS (
    SELECT FROM pg_auth_members m JOIN pg_roles g ON g.oid = m.roleid
     WHERE m.member = r.oid AND g.rolname <> 'pg_read_all_data'
  ) THEN
    RAISE EXCEPTION 'analise_leitura: herda papel além de pg_read_all_data';
  END IF;
  RAISE NOTICE 'analise_leitura aceite em %: lê tudo, não escreve, sem senha', current_database();
END $$;
