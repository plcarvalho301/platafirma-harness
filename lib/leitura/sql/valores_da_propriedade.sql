-- valores_da_propriedade — os valores que existem para a propriedade quando o total é zero.
-- Fonte: platafirma-casa@referencias/instancias/verbo/busca.md, seção «valores_da_propriedade».
-- $1 text    a fonte da propriedade: dado, shape ou dicionario
-- $2 uuid[]  as restrições da propriedade nas classes do plano, na fonte dado
-- $3 text    a coluna, nas fontes shape e dicionario, da lista fixa do leitor
-- $4 uuid[]  as classes do plano
SELECT valor, count(*) AS fichas FROM (
  SELECT coalesce(d.valor_de_dicionario, d.valor #>> '{}') AS valor
    FROM casa.dado d
   WHERE $1::text = 'dado' AND d.terminou IS NULL AND d.restricao = ANY ($2::uuid[])
  UNION ALL
  SELECT coalesce(fa.chave_humana, to_jsonb(s) ->> NULLIF($3, ''))          -- coluna de casa.shape
    FROM casa.shape s
    JOIN casa.ficha f       ON f.uuid = s.uuid AND f.classe = ANY ($4::uuid[])
    LEFT JOIN casa.ficha fa ON fa.uuid::text = to_jsonb(s) ->> NULLIF($3, '')
   WHERE $1::text = 'shape'
  UNION ALL
  SELECT coalesce(fa.chave_humana, to_jsonb(c) ->> NULLIF($3, ''))          -- coluna de casa.dicionario
    FROM casa.dicionario c
    JOIN casa.ficha f       ON f.uuid = c.uuid AND f.classe = ANY ($4::uuid[])
    LEFT JOIN casa.ficha fa ON fa.uuid::text = to_jsonb(c) ->> NULLIF($3, '')
   WHERE $1::text = 'dicionario'
) v
 WHERE valor IS NOT NULL
 GROUP BY valor
 ORDER BY valor
 LIMIT 50;
