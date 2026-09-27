-- 0093_ferramental_infra_migrar_deploy.sql — golden record pos card #3145 (infra, migrar,
-- deploy apagado, sessao reidrata do banco).
--
-- Pratica vigente (decisao 10 do card): migracao seed, padrao 0076/0085 — upsert por slug,
-- fonte = cabecalho do proprio bin/<verbo> na bancada desta fita. NAO mexe em
-- ferramental_ato/ferramental_acesso/ferramental_ambiente/ferramental_consumo (mecanismo de
-- bin/_acervo/registrar, sem DDL nesta linhagem de migracao ainda — fora do escopo aqui).
--
-- O que muda:
--   1. verbos apagados nesta fita (bin/deploy, bin/fabrica-repo, bin/jaiminho,
--      bin/jaiminho-eng, bin/_sessao/longjob-como-verbo-proprio [nunca foi verbo proprio,
--      deletado por seguranca], bin/conta-abertura, bin/ops-log-prune, bin/quarentena-prune):
--      DELETE das linhas em ferramental_instancia (se houver) e ferramental_verbo, por slug.
--      A capacidade 'mudanca' (so 'deploy' a usava) fica: nao e verbo-linha, decisao 10 nao
--      pede remocao de capacidade, e reclassificar espinha e merito de dados/arquiteto.
--   2. infra, migrar, metrica (capacidade nova), sessao (capacidade nova), seg, acervo:
--      upsert capacidade + verbo (slug, capacidade_id, sot, descricao) pelo cabecalho atual.
--
-- Idempotente (ON CONFLICT). NAO faz DROP de tabela/coluna.

begin;

-- ── 1. verbos apagados nesta fita — remove instancia dependente primeiro (FK), depois o verbo ──
delete from acervo.ferramental_instancia
 where verbo_id in (
   select id from acervo.ferramental_verbo
    where slug in ('deploy', 'fabrica-repo', 'jaiminho', 'jaiminho-eng', 'longjob',
                    'conta-abertura', 'ops-log-prune', 'quarentena-prune'));

delete from acervo.ferramental_verbo
 where slug in ('deploy', 'fabrica-repo', 'jaiminho', 'jaiminho-eng', 'longjob',
                'conta-abertura', 'ops-log-prune', 'quarentena-prune');

-- ── 2. capacidade: as duas novas desta fita ('infra' e 'politica' e 'conhecimento' ja existem
--      desde a 0076 seed; 'infra/promocao-de-mudanca' idem, ja usada por outro verbo da casa) ──
insert into acervo.ferramental_capacidade (slug, rotulo) values
  ('metrica', 'métrica'),
  ('sessao', 'sessão'),
  ('infra/promocao-de-mudanca', 'infra / promoção de mudança')
on conflict (slug) do nothing;

-- ── 3. verbo: upsert pelo cabecalho atual de cada bin/<verbo> nesta bancada (cabecalhos finais) ──
insert into acervo.ferramental_verbo (slug, capacidade_id, sot, descricao)
select v.slug, c.id, v.sot, v.descricao
  from (values
    ('infra',   'infra',                      'bin/infra',
     'estado e operação da infraestrutura local: contêiner, unit, timer, stack (compose) e a agenda do cron'),
    ('migrar',  'infra/promocao-de-mudanca',   'bin/migrar',
     'aplica uma migracao SQL versionada num Postgres da stack, por stdin'),
    ('metrica', 'metrica',                     'bin/metrica',
     'agrega o ops log em eventos de uso do harness: giro, erro, help, acerto, cadeia, lote'),
    ('sessao',  'sessao',                      'bin/sessao',
     'o dia de trabalho do agente: autoriza, cunha e torna a fita resolvivel pela porta'),
    ('seg',     'politica',                    'bin/seg',
     'opera o toolkit de seguranca da PlataFirma: avalia, deriva regua e despacha ferramenta'),
    ('acervo',  'conhecimento',                'bin/acervo',
     'opera o acervo da plataforma (casa, obra, registro)')
  ) as v(slug, cap_slug, sot, descricao)
  join acervo.ferramental_capacidade c on c.slug = v.cap_slug
on conflict (slug) do update
   set capacidade_id = excluded.capacidade_id,
       sot           = excluded.sot,
       descricao     = excluded.descricao;

commit;
