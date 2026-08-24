-- 0076_acervo_ferramental_seed.sql — INSERT inicial do golden record.
-- Traduz catalogo-global.md (tabela plana arq:0071) -> 3 níveis, aplicando os
-- reparos que a spec de dados (card #2430, D6 do ADR 0076) cravou:
--   - acesso: capacidade renomeada para 'iam'; verbo segue 'acesso' (invocação na mão de todos).
--   - keycloak: instância de 'acesso' (não capacidade). Reparo do objeto-motor: motor é instância nível 3.
--   - rastreador: instância de 'tarefas' (verbo canônico de 'trabalho'), não capacidade.
--   - jaiminho / jaiminho-fabrica: FORA do seed. Pendência do dono (usam a malha de
--     mensageria ou não?). Não entram como verbo de 'mensagem' — eram fóssil.
--   - ollama, matrix: capacidade+verbo próprios (têm capacidade de espinha no md:
--     inferencia-local, mensagem-externa) e a instância homônima pendurada.
--   - terceiros/scripts (habilitador): FORA do seed inicial. São meio, não espinha;
--     entram como inventário de nível 3 quando os atributos operacionais de TI forem povoados.
--
-- Idempotente por slug (ON CONFLICT DO NOTHING). Roda depois da DDL 0076.

begin;

-- ── Nível 1: capacidade ────────────────────────────────────────────────────
insert into acervo.ferramental_capacidade (slug, rotulo) values
  ('conhecimento','conhecimento'),
  ('iam','identidade, autenticação e autorização'),   -- rename: era 'acesso'
  ('verificacao','verificação'),
  ('mudanca','mudança'),
  ('infra','infra'),
  ('decisao','decisão'),
  ('gestao-de-motores','gestão de motores'),
  ('organizacao','organização'),
  ('politica','política'),
  ('incidente','incidente'),
  ('trabalho','trabalho'),
  ('gestao-de-recurso','gestão de recurso'),
  ('memoria','memória'),
  ('expediente','expediente'),
  ('solicitacao','solicitação'),
  ('encerramento','encerramento'),
  ('mensagem','mensagem'),
  ('inferencia-local','inferência local'),
  ('mensagem-externa','mensagem externa')
on conflict (slug) do nothing;

-- ── Nível 2: verbo (1:1 com capacidade) ────────────────────────────────────
insert into acervo.ferramental_verbo (slug, capacidade_id, sot)
select v.slug, c.id, v.sot from (values
  ('acervo','conhecimento','bin/acervo'),
  ('acesso','iam','bin/acesso'),                       -- verbo segue 'acesso'; capacidade é 'iam'
  ('conferir','verificacao','bin/conferir'),
  ('deploy','mudanca','bin/deploy'),
  ('infra','infra','bin/infra'),
  ('minuta','decisao','bin/minuta'),
  ('motor','gestao-de-motores','bin/motor'),
  ('persona','organizacao','bin/persona'),
  ('seg','politica','bin/seg'),
  ('sinal','incidente','bin/sinal'),
  ('tarefas','trabalho','bin/tarefas'),
  ('recurso','gestao-de-recurso','bin/recurso'),
  ('mesa','memoria','bin/mesa'),
  ('monta-sessao','expediente','bin/monta-sessao'),
  ('chat','solicitacao','bin/chat'),
  ('descansar','encerramento','bin/descansar'),
  ('fila','mensagem','bin/fila'),
  ('ollama','inferencia-local','registro/stacks.json'),
  ('matrix','mensagem-externa','registro/stacks.json')
) as v(slug, cap_slug, sot)
join acervo.ferramental_capacidade c on c.slug = v.cap_slug
on conflict (slug) do nothing;

-- ── Nível 3: instância (1:N com verbo) ──────────────────────────────────────
insert into acervo.ferramental_instancia (slug, verbo_id, sot)
select i.slug, vb.id, i.sot from (values
  ('keycloak','acesso','registro/stacks.json'),   -- motor de iam; instância, não capacidade
  ('ollama','ollama','registro/stacks.json'),
  ('matrix','matrix','registro/stacks.json'),
  ('rastreador','tarefas','registro/stacks.json') -- reparo D6: instância de tarefas
) as i(slug, verbo_slug, sot)
join acervo.ferramental_verbo vb on vb.slug = i.verbo_slug
on conflict (slug) do nothing;

commit;
