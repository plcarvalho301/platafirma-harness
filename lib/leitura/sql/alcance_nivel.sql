-- alcance_nivel — um nível da caminhada em largura pelas ligações vigentes.
-- Fonte: platafirma-casa@referencias/instancias/verbo/busca.md, seção «A caminhada pelas ligações».
-- $1 uuid[]  a fronteira: as fichas alcançadas no nível anterior
-- $2 text    a propriedade da ligação (uuid), ou vazio para qualquer
-- $3 text    o sentido: saida, chegada ou qualquer
SELECT DISTINCT ON (v.ficha)
       v.ficha, v.pai, p.slug AS propriedade, v.posicao
  FROM (
    SELECT g."de" AS ficha, g.para AS pai, g.propriedade, g.posicao       -- saída: a ficha aponta a fronteira
      FROM casa.ligacao g
     WHERE $3::text IN ('saida', 'qualquer') AND g.terminou IS NULL
       AND g.para = ANY ($1::uuid[])
       AND (NULLIF($2, '')::uuid IS NULL OR g.propriedade = NULLIF($2, '')::uuid)
    UNION ALL
    SELECT g.para, g."de", g.propriedade, g.posicao                      -- chegada: a fronteira aponta a ficha
      FROM casa.ligacao g
     WHERE $3::text IN ('chegada', 'qualquer') AND g.terminou IS NULL
       AND g.para IS NOT NULL AND g."de" = ANY ($1::uuid[])
       AND (NULLIF($2, '')::uuid IS NULL OR g.propriedade = NULLIF($2, '')::uuid)
  ) v
  JOIN casa.ficha fp      ON fp.uuid = v.pai
  JOIN casa.propriedade p ON p.id = v.propriedade
 ORDER BY v.ficha, fp.chave_humana, p.slug, v.posicao;
