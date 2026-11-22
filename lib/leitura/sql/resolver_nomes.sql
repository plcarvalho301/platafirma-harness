-- resolver_nomes — que fichas cada termo nomeia, e por que passo.
-- Fonte: platafirma-casa@referencias/instancias/verbo/busca.md, seção «resolver_nomes».
-- Roda no retrato do leitor (lib/leitura/retrato.py), pelo papel analise_leitura, com o parâmetro ligado.
-- $1 text[]  o termo inteiro e os cortes, na ordem em que o verbo os gerou
WITH pedido AS (
  SELECT ord, casa.normalizar(cru) AS norm
    FROM unnest($1::text[]) WITH ORDINALITY AS t(cru, ord)
),
nomes(passo, norm, ficha) AS (
  SELECT 1, n.termo_norm, f.uuid                             -- tabela de nomes, só o que vale
    FROM casa.nome n JOIN casa.ficha f ON f.chave_humana = n.chave
   WHERE n.terminou IS NULL
  UNION ALL
  SELECT passo, norm, ficha FROM casa_leitura.nome_da_ficha  -- rótulo, variantes e slug
),
achadas AS (            -- cada ficha uma vez por termo, com o primeiro passo que a achou
  SELECT DISTINCT ON (q.ord, n.ficha) q.ord, n.passo, n.ficha
    FROM pedido q JOIN nomes n ON n.norm = q.norm
   WHERE q.norm <> ''
   ORDER BY q.ord, n.ficha, n.passo
)
SELECT q.ord, q.norm, a.passo,
       f.chave_humana AS chave,
       c.slug         AS classe,
       (c.slug = 'shape') AS e_classe,
       coalesce(s.rotulo, dic.rotulo) AS rotulo,
       coalesce(s.definicao, dic.definicao, ref.resumo) AS definicao
  FROM pedido q
  LEFT JOIN achadas a ON a.ord = q.ord
  LEFT JOIN casa.ficha f        ON f.uuid = a.ficha
  LEFT JOIN casa.shape c        ON c.uuid = f.classe
  LEFT JOIN casa.shape s        ON s.uuid = f.uuid
  LEFT JOIN casa.dicionario dic ON dic.uuid = f.uuid
  LEFT JOIN casa.referencia ref ON ref.ficha = f.uuid
 ORDER BY q.ord, a.passo, f.chave_humana;
