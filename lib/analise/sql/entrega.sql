-- entrega — a entrega de uma base ou de um resultado do analise a outro sujeito (#4184).
-- Aplicação: release migrar aplicar rag, com este arquivo no stdin, antes do verbo que a lê.
-- Idempotente. O sujeito «*» entrega a todo sujeito que a política de acesso deixa entrar.
-- Rollback: DROP TABLE analise.entrega; os objetos voltam a ser lidos só por quem os gerou.
SET LOCAL lock_timeout = '5s';
CREATE TABLE IF NOT EXISTS analise.entrega (
    objeto_id text NOT NULL,
    sujeito text NOT NULL,
    entregue_por text NOT NULL,
    entregue_em timestamptz NOT NULL DEFAULT clock_timestamp(),
    PRIMARY KEY (objeto_id, sujeito)
);
ALTER TABLE analise.entrega OWNER TO analise_publicacao;
REVOKE ALL ON analise.entrega FROM PUBLIC;
COMMENT ON TABLE analise.entrega IS 'Entregas de base e resultado a outro sujeito do analise. #4184.';
COMMENT ON COLUMN analise.entrega.objeto_id IS 'Base ou resultado entregue. #4184.';
COMMENT ON COLUMN analise.entrega.sujeito IS 'Sujeito que passa a ler o objeto; «*» é todo sujeito autorizado. #4184.';
COMMENT ON COLUMN analise.entrega.entregue_por IS 'Sujeito que gerou o objeto e o entregou. #4184.';
COMMENT ON COLUMN analise.entrega.entregue_em IS 'Instante da entrega. #4184.';
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_tables WHERE schemaname='analise' AND tablename='entrega') THEN
    RAISE EXCEPTION 'entrega: tabela ausente';
  END IF;
  IF has_table_privilege('public','analise.entrega','SELECT') THEN
    RAISE EXCEPTION 'entrega: tabela aberta a PUBLIC';
  END IF;
  IF NOT has_table_privilege('analise_publicacao','analise.entrega','INSERT') THEN
    RAISE EXCEPTION 'entrega: a role de publicação não grava';
  END IF;
  RAISE NOTICE 'entrega aceite: tabela privada, gravada só pela role de publicação';
END $$;
