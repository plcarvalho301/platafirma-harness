-- 0077_drop_colunas_projecao_trecho.sql
-- Card #2917 — Rerefactor P1.5 passo 3: remocao das 3 colunas-projecao de acervo.trecho.
--
-- CONTEXTO:
-- Fecho da migracao do modelo #2313 (§6), dentro do epico #283 (fase D, onda rerefactor).
-- O passo 2 (#2896) ligou o runtime + gabarito a acervo.secao/secao_id.
-- As 3 colunas-projecao de acervo.trecho (section_id, anchor_id, hierarquia) viraram lixo.
--
-- ORDEM DO §6:
-- Primeiro TODOS param de ler e gravar (leitores em bench/* e bin/motor; escrita em store/escrita_nova.py).
-- So DEPOIS a coluna cai (DROP e irreversivel).
--
-- FRONTEIRA §7:
-- Esta migracao DDL e destrutiva/irreversivel -> claudinho-TI aplica apos confirmacao dos passos 1 e 2.
-- NAO aplicar automaticamente.

BEGIN;

ALTER TABLE acervo.trecho
    DROP COLUMN IF EXISTS section_id,
    DROP COLUMN IF EXISTS anchor_id,
    DROP COLUMN IF EXISTS hierarquia;

COMMIT;
