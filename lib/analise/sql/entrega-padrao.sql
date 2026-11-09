-- entrega-padrao — base e resultado que já existem passam a ser lidos por todo sujeito autorizado (#4184).
-- Aplicação: release migrar aplicar rag, com este arquivo no stdin, depois de entrega.sql.
-- Idempotente. O objeto novo já nasce entregue a todos (lib/analise/publicacao.py), salvo receita com
-- entrega: privada. Rollback: DELETE FROM analise.entrega WHERE sujeito='*' AND entregue_por IN
-- (SELECT sujeito FROM analise.base UNION SELECT sujeito FROM analise.resultado).
SET LOCAL lock_timeout = '5s';
INSERT INTO analise.entrega (objeto_id, sujeito, entregue_por)
SELECT id, '*', sujeito FROM analise.base
UNION ALL
SELECT id, '*', sujeito FROM analise.resultado
ON CONFLICT DO NOTHING;
