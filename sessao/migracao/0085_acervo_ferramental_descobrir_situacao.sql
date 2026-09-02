-- 0085_acervo_ferramental_descobrir_situacao.sql — Indexação dos verbos de leitura no golden record (arq:0085 §2, cards #2952 e #2953).
-- Idempotente por slug (ON CONFLICT DO NOTHING).
-- Correção 02/09 (dados): o bloco de Nível 3 (instância) foi removido — usava a coluna
-- inexistente `especie` (o correto é `sot`) e, além disso, verbo-núcleo sem shim NÃO tem
-- instância (só keycloak/matrix/rastreador têm). A versão original abortava a transação
-- inteira no 3º INSERT (ON_ERROR_STOP) e nunca populava capacidade nem verbo.

begin;

-- ── Nível 1: capacidade ────────────────────────────────────────────────────
insert into acervo.ferramental_capacidade (slug, rotulo) values
  ('descoberta', 'descoberta'),
  ('situacao', 'situação')
on conflict (slug) do nothing;

-- ── Nível 2: verbo (1:1 com capacidade) ────────────────────────────────────
insert into acervo.ferramental_verbo (slug, capacidade_id, sot)
select v.slug, c.id, v.sot from (values
  ('descobrir', 'descoberta', 'bin/descobrir'),
  ('situacao', 'situacao', 'bin/situacao')
) as v(slug, cap, sot)
join acervo.ferramental_capacidade c on c.slug = v.cap
on conflict (slug) do nothing;

-- Nível 3 (instância) omitido de propósito: verbo-núcleo de leitura não tem shim.

commit;
