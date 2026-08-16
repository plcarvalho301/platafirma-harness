-- `mesa_item_esvaziamento_par` estava errado e o teste pegou: ele amarrava
-- `esvaziado_por_fita` a `esvaziado_em`, mas fita é OPCIONAL — sessão de mão
-- (claude.ai, terminal) não declara PF_FITA, e o item esvaziado por ela nasce com
-- fita nula. O par verdadeiro é só o de `fita`, que declara encerramento quando encerra.
-- Item pendente continua sendo `esvaziado_em IS NULL`, que é o que o índice parcial lê.
ALTER TABLE sessao.mesa_item DROP CONSTRAINT mesa_item_esvaziamento_par;
