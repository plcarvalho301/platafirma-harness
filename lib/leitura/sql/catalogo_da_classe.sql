-- catalogo_da_classe — o que as classes do plano declaram (propriedades, dicionários e estados).
-- Fonte: platafirma-casa@referencias/instancias/verbo/busca.md, seção «catalogo_da_classe».
-- $1 uuid[]  as classes do plano
SELECT s.slug AS classe, p.slug AS propriedade, p.id AS propriedade_id,
       r.id AS restricao, r.tipo_de_valor, r.sentido, r.dicionario,
       (SELECT jsonb_agg(jsonb_build_object('slug', v.slug, 'rotulo', v.rotulo)
                         ORDER BY v.ordem, v.slug)
          FROM casa.valor v WHERE v.dicionario = r.dicionario) AS valores,
       (SELECT jsonb_agg(e.slug ORDER BY e.slug)
          FROM casa.estado e WHERE e.shape = s.uuid) AS estados
  FROM casa.shape s
  JOIN casa.restricao r   ON r.shape = s.uuid AND r.tipo_de_valor <> 'secao'
  JOIN casa.propriedade p ON p.id = r.propriedade
 WHERE s.uuid = ANY ($1::uuid[])
 ORDER BY s.slug, p.slug, r.sentido;
