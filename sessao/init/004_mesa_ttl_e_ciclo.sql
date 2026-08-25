-- 004 — TTL de mesa (48h, expurgo físico) + numeração exibida com reset semanal.
--
-- POR QUE (fóssil): mesa_item nasceu sem TTL. Item pendente vivia para sempre até
-- `mesa fez`, e `monta_sessao` serve todo pendente em toda abertura. Item de semanas
-- atrás entrava na janela como impedimento atual — foi a referência fóssil medida em
-- 25/08 (SHA velho, "carta enviada 22/08" servidos como se fossem de hoje). Medição:
-- 154 pendentes na org, 125 (81%) com +48h; mediana de execução dos que executam é
-- 0,0-0,4 dia. Depois de 48h a chance de `fez` já colapsou — o que sobra é fóssil.
--
-- EXPURGO É FÍSICO, sem retenção (ordem do dono, 25/08): o log de fita já mora em
-- sessao.fita + ops jsonl. Guardar cadáver de mesa para "medir a política" seria a
-- patologia da própria cadeira IA — medir muito, cortar nada. DELETE, não tombstone.
-- Régua de serviço a humano (resgate, "não some porque o usuário saiu") é de sessão
-- humana; mesa é memória de curto prazo de agente e o durável (card/wiki/repo) que o
-- item aponta reconstrói qualquer coisa que valha. Sem resgate.
--
-- NUMERAÇÃO: o id (PK) segue GENERATED ALWAYS — cresce invisível, mantém FK e medição.
-- O número EXIBIDO passa a ser `num`, contador por (cadeira, ciclo semanal) que reinicia
-- em 1 toda segunda. Assim a mesa vive na faixa #1..~#20 e nunca aproxima card (#4xx) nem
-- issue (#2xxx): a desambiguação vira range, não sorte. `ciclo` = segunda-feira ISO.

BEGIN;

-- 1. Colunas novas, nascendo nulas para o backfill.
ALTER TABLE sessao.mesa_item ADD COLUMN ciclo date;
ALTER TABLE sessao.mesa_item ADD COLUMN num  int;

-- 2. Expurgo do fóssil: pendente com mais de 48h sai de uma vez (decisão do dono:
--    virar a chave, não janela de triagem). Fez'd fica — é a medição do que a mesa moveu.
DELETE FROM sessao.mesa_item
 WHERE esvaziado_em IS NULL
   AND plantado_em < now() - interval '48 hours';

-- 3. Backfill determinístico do que sobrou (survivors ≤48h + histórico fez'd), para
--    satisfazer NOT NULL e dar número sensato ao histórico. ciclo pela data de plantio;
--    num por (cadeira, ciclo) na ordem do id.
UPDATE sessao.mesa_item
   SET ciclo = date_trunc('week', plantado_em)::date;

WITH numerado AS (
  SELECT id, row_number() OVER (PARTITION BY cadeira, ciclo ORDER BY id) AS n
    FROM sessao.mesa_item
)
UPDATE sessao.mesa_item m SET num = numerado.n
  FROM numerado WHERE numerado.id = m.id;

-- 4. Trava: ciclo com default (o verbo não precisa mais mandar), num obrigatório e
--    único por cadeira+ciclo — protege a numeração da corrida de escrita do verbo.
ALTER TABLE sessao.mesa_item ALTER COLUMN ciclo SET DEFAULT date_trunc('week', now())::date;
ALTER TABLE sessao.mesa_item ALTER COLUMN ciclo SET NOT NULL;
ALTER TABLE sessao.mesa_item ALTER COLUMN num   SET NOT NULL;
CREATE UNIQUE INDEX mesa_item_num_uq ON sessao.mesa_item (cadeira, ciclo, num);

COMMIT;
