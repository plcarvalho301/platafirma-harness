-- ligacoes_opostas — quando uma condição com --ligacao devolve total zero,
-- verifica se existem ligações no sentido oposto ou por outra propriedade entre as
-- classes do plano e os mesmos alvos (DT 1370).
-- $1 uuid[]  as classes do plano
-- $2 jsonb   predicados de ligação do plano: [{propriedade_id, sentido, alvos}]
WITH
preds AS (
  SELECT * FROM jsonb_to_recordset($2::jsonb)
    AS x(propriedade_id uuid, sentido text, alvos uuid[])
),
opostas AS (
  SELECT p.slug AS propriedade, 'saida'::text AS sentido, fp.chave_humana AS alvo, f.uuid AS ficha
    FROM preds x
    JOIN casa.ficha f       ON f.classe = ANY ($1::uuid[])
    JOIN casa.ligacao g     ON g.terminou IS NULL AND g."de" = f.uuid AND g.para = ANY (x.alvos)
    JOIN casa.propriedade p ON p.id = g.propriedade
    JOIN casa.ficha fp      ON fp.uuid = g.para
   WHERE NOT (g.propriedade = x.propriedade_id AND x.sentido = 'saida')
  UNION ALL
  SELECT p.slug AS propriedade, 'chegada'::text AS sentido, fd.chave_humana AS alvo, f.uuid AS ficha
    FROM preds x
    JOIN casa.ficha f       ON f.classe = ANY ($1::uuid[])
    JOIN casa.ligacao g     ON g.terminou IS NULL AND g.para = f.uuid AND g."de" = ANY (x.alvos)
    JOIN casa.propriedade p ON p.id = g.propriedade
    JOIN casa.ficha fd      ON fd.uuid = g."de"
   WHERE NOT (g.propriedade = x.propriedade_id AND x.sentido = 'chegada')
)
SELECT propriedade, sentido, alvo, count(DISTINCT ficha) AS fichas
  FROM opostas
 GROUP BY propriedade, sentido, alvo
 ORDER BY fichas DESC, propriedade, sentido, alvo
 LIMIT 20;
