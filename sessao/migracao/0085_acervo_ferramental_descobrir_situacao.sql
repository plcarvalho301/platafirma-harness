-- 0085_acervo_ferramental_descobrir_situacao.sql — Indexação dos verbos de leitura no golden record (arq:0085 §2, cards #2952 e #2953).
-- Idempotente por slug (ON CONFLICT DO NOTHING).

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

-- ── Nível 3: instância (homônima ao verbo) ──────────────────────────────────
insert into acervo.ferramental_instancia (slug, verbo_id, especie)
select i.slug, v.id, i.especie from (values
  ('descobrir', 'descobrir', 'core'),
  ('situacao', 'situacao', 'core')
) as i(slug, verbo, especie)
join acervo.ferramental_verbo v on v.slug = i.verbo
on conflict (slug) do nothing;

commit;
