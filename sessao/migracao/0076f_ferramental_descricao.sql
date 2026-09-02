-- 0076f_ferramental_descricao.sql — coluna aditiva `descricao` no nível 2 (verbo).
-- Molde 0076b: ADITIVA, sobe tolerando NULL, materializada do cabeçalho do próprio
-- script (`# <verbo> — <descrição>`), a mesma linha que `conferir` já parseia.
-- DONO: cada dono de verbo. NATUREZA: reconciliável (fonte = cabeçalho do bin).
-- Idempotente. NÃO faz DROP. Fecha o B1 da minuta 0021 (decisão do dono, 02/09/2026).

alter table acervo.ferramental_verbo add column if not exists descricao text;
