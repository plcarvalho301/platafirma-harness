-- consultar_fichas — consulta por condição, com cabeçalho e página.
-- Fonte: platafirma-casa@referencias/instancias/verbo/busca.md, seção «consultar_fichas».
-- $1 uuid[]  as classes do plano
-- $2 jsonb   predicados de propriedade: [{n, fonte, restricoes, coluna, valor, alvo, sem}]
-- $3 jsonb   alcance dos predicados de ligação: [{n, ficha, passos, posicao}]
-- $4 int     número de predicados de ligação; o de n = 1 ordena a página
-- $5 text    estado pedido, ou vazio para NULL
-- $6 text    ordem da última linha da página anterior (int), ou vazio para NULL
-- $7 text    chave da última linha da página anterior, ou vazio para NULL
-- $8 int     tamanho da página
-- $9 text[]  tipos de evento que contam para a versão, de versao-da-classe.yaml
-- $10 jsonb  faltas de ligação, a um passo: [{propriedade, sentido, alvo}], alvo nulo para qualquer
WITH
prop AS (
  SELECT * FROM jsonb_to_recordset($2::jsonb)
    AS x(n int, fonte text, restricoes uuid[], coluna text, valor jsonb, alvo uuid, sem boolean)
),
alcance AS (
  SELECT * FROM jsonb_to_recordset($3::jsonb)
    AS x(n int, ficha uuid, passos int, posicao int)
),
estado AS (             -- o estado vigente: o último evento de transição de cada ficha das classes do plano
  SELECT DISTINCT ON (e.payload->>'ficha')
         (e.payload->>'ficha')::uuid AS ficha, e.payload->>'para' AS estado
    FROM casa.ficha_evento e
   WHERE e.payload->>'uso' = 'transitar'
     AND EXISTS (SELECT 1 FROM casa.ficha x
                  WHERE x.uuid = (e.payload->>'ficha')::uuid AND x.classe = ANY ($1::uuid[]))
   ORDER BY e.payload->>'ficha', e.ocorrido_em DESC, e.uuid DESC
),
casadas AS (
  SELECT f.uuid, f.chave_humana, f.classe,
         coalesce((SELECT a.posicao FROM alcance a WHERE a.n = 1 AND a.ficha = f.uuid),
                  2147483647) AS ordem
    FROM casa.ficha f
   WHERE f.classe = ANY ($1::uuid[])
     AND NOT EXISTS (       -- nenhum predicado de propriedade fica do lado errado: o «tem» sem valor, o «sem» com valor
           SELECT 1 FROM prop x
            WHERE coalesce(x.sem, false) = (
                  (x.fonte = 'dado' AND EXISTS (
                     SELECT 1 FROM casa.dado d
                      WHERE d.ficha = f.uuid AND d.terminou IS NULL
                        AND d.restricao = ANY (x.restricoes)
                        AND (x.valor IS NULL                  -- só o «sem» chega sem valor: qualquer valor conta
                             OR d.valor_de_dicionario = x.valor #>> '{}'
                             OR d.valor @> x.valor)))
               OR (x.fonte = 'shape' AND EXISTS (
                     SELECT 1 FROM casa.shape s
                      WHERE s.uuid = f.uuid
                        AND CASE WHEN x.valor IS NULL AND x.alvo IS NULL
                                 THEN (to_jsonb(s) -> x.coluna) NOT IN ('null', '[]', '""')
                                 ELSE (to_jsonb(s) -> x.coluna) @> x.valor
                                      OR (to_jsonb(s) ->> x.coluna) = x.alvo::text END))
               OR (x.fonte = 'dicionario' AND EXISTS (
                     SELECT 1 FROM casa.dicionario c
                      WHERE c.uuid = f.uuid
                        AND CASE WHEN x.valor IS NULL AND x.alvo IS NULL
                                 THEN (to_jsonb(c) -> x.coluna) NOT IN ('null', '[]', '""')
                                 ELSE (to_jsonb(c) -> x.coluna) @> x.valor
                                      OR (to_jsonb(c) ->> x.coluna) = x.alvo::text END))))
     AND NOT EXISTS (       -- nenhum predicado de ligação fica sem alcance
           SELECT 1 FROM generate_series(1, $4::int) AS l(n)
            WHERE NOT EXISTS (
                  SELECT 1 FROM alcance a WHERE a.n = l.n AND a.ficha = f.uuid))
     AND NOT EXISTS (       -- nenhuma falta de ligação pedida está presente, a um passo
           SELECT 1 FROM jsonb_to_recordset($10::jsonb) AS s(propriedade uuid, sentido text, alvo uuid)
            WHERE EXISTS (
                  SELECT 1 FROM casa.ligacao g
                   WHERE g.terminou IS NULL AND g.propriedade = s.propriedade
                     AND ((s.sentido = 'saida'   AND g."de" = f.uuid AND (s.alvo IS NULL OR g.para = s.alvo))
                       OR (s.sentido = 'chegada' AND g.para = f.uuid AND (s.alvo IS NULL OR g."de" = s.alvo)))))
     AND (NULLIF($5, '') IS NULL OR EXISTS (
           SELECT 1 FROM estado t
            WHERE t.ficha = f.uuid AND t.estado = NULLIF($5, '')))
),
cabecalho AS (
  SELECT (SELECT count(*) FROM casadas) AS total,
         (SELECT count(*) FROM casadas k
           WHERE NULLIF($7, '') IS NOT NULL
             AND (k.ordem, k.chave_humana) <= (NULLIF($6, '')::int, NULLIF($7, ''))) AS antes,
         (SELECT 'v1:' || encode(sha256(convert_to(
                   coalesce(jsonb_agg(u.chave_humana ORDER BY u.chave_humana COLLATE "C")::text, '[]'),
                   'UTF8')), 'hex')
            FROM casa.ficha u WHERE u.classe = ANY ($1::uuid[])) AS digest,
         (SELECT t.f FROM (     -- a versão: as fontes de versao-da-classe.yaml
              SELECT s.fornada AS f FROM casa.shape s WHERE s.uuid = ANY ($1::uuid[])
              UNION ALL SELECT d.iniciou FROM casa.dado d JOIN casa.ficha x ON x.uuid = d.ficha
                         WHERE x.classe = ANY ($1::uuid[]) AND d.terminou IS NULL
              UNION ALL SELECT l.iniciou FROM casa.ligacao l JOIN casa.ficha x ON x.uuid = l."de"
                         WHERE x.classe = ANY ($1::uuid[]) AND l.terminou IS NULL
              UNION ALL SELECT s.fornada FROM casa.shape s          -- a classe shape: toda classe
                         WHERE EXISTS (SELECT 1 FROM casa.shape c
                                        WHERE c.uuid = ANY ($1::uuid[]) AND c.slug = 'shape')
              UNION ALL SELECT d.fornada FROM casa.dicionario d     -- a classe dicionário: todo dicionário
                         WHERE EXISTS (SELECT 1 FROM casa.shape c
                                        WHERE c.uuid = ANY ($1::uuid[]) AND c.slug = 'dicionario')
              UNION ALL SELECT v.fornada FROM casa.valor v           -- e todo valor
                         WHERE EXISTS (SELECT 1 FROM casa.shape c
                                        WHERE c.uuid = ANY ($1::uuid[]) AND c.slug = 'dicionario')
              UNION ALL SELECT e.uuid FROM casa.ficha_evento e      -- fornada e descarte que citam a classe
                          JOIN casa.tipo_de_evento te ON te.uuid = e.tipo AND te.slug = ANY ($9::text[])
                          JOIN casa.shape c ON c.uuid = ANY ($1::uuid[])
                         WHERE e.payload->>'classe' = c.slug
                            OR e.payload->'relatorio'->>'classe' = c.slug
                            OR coalesce(e.payload->'relatorio'->'gravadas', '[]')
                                 ?| ARRAY(SELECT chave_humana FROM casa.ficha WHERE classe = c.uuid)
                            OR coalesce(e.payload->'relatorio'->'removidas', '[]')
                                 ?| ARRAY(SELECT chave_humana FROM casa.ficha WHERE classe = c.uuid)
           ) t
           JOIN casa.ficha_evento fe ON fe.uuid = t.f   -- a mais recente, pelo critério da configuração
          ORDER BY fe.ocorrido_em DESC, fe.uuid DESC LIMIT 1) AS fornada
),
pagina AS (
  SELECT c.uuid, c.ordem, c.chave_humana AS chave, s.slug AS classe,
         coalesce(sh.rotulo, dc.rotulo,
                  (SELECT d.valor #>> '{}' FROM casa.dado d
                     JOIN casa.restricao r   ON r.id = d.restricao
                     JOIN casa.propriedade p ON p.id = r.propriedade AND p.slug = 'rotulo'
                    WHERE d.ficha = c.uuid AND d.terminou IS NULL LIMIT 1)) AS rotulo,
         t.estado
    FROM casadas c
    JOIN casa.shape s ON s.uuid = c.classe
    LEFT JOIN casa.shape sh      ON sh.uuid = c.uuid
    LEFT JOIN casa.dicionario dc ON dc.uuid = c.uuid
    LEFT JOIN estado t           ON t.ficha = c.uuid
   WHERE NULLIF($7, '') IS NULL OR (c.ordem, c.chave_humana) > (NULLIF($6, '')::int, NULLIF($7, ''))
   ORDER BY c.ordem, c.chave_humana
   LIMIT $8::int
)
SELECT h.total, h.antes, h.digest, h.fornada,
       p.uuid, p.ordem, p.chave, p.classe, p.rotulo, p.estado
  FROM cabecalho h LEFT JOIN pagina p ON true
 ORDER BY p.ordem, p.chave;
