-- 0091_acervo_stack_release_instancia.sql — acervo.stack sem a pasta de trabalho da conta.
-- Card #3010 (producao sem bancada), desenho §4. NAO se aplica sozinha: entra por
-- `migrar aplicar rag` na fase de host, DEPOIS da primeira promocao das familias para
-- /opt/platafirma (frente release: promover antes de reescrever o registro) e do bootstrap
-- de /srv/platafirma/casa.
--
-- Escrita contra as 12 linhas MEDIDAS em 15/09/2026 (SELECT so-leitura em rag-extractor-pg):
-- acervo-api, chat, conhecimento, core, harness-controle, harness-sessao, jaiminho, motor,
-- rag, rastreador, rastreador-tela e searxng. Todas apontavam a pasta de trabalho da conta.
--
-- O contrato e o de bin/deploy (main), campo a campo:
--   compose  so a BASE, na release da propria familia:
--              /opt/platafirma/current/<curto>/<caminho-do-compose>
--            (string; lista JSON quando ha mais de um arquivo, na ordem do -f). A sobreposicao
--            da instancia, /srv/platafirma/casa/deploy/<stack>/compose.override.yaml, NAO entra
--            aqui: o deploy a acrescenta sozinho por ultimo, e `rel_na_familia` recusa (exit 3)
--            qualquer absoluto fora da release — foi o defeito que travava as 12 stacks.
--   projeto  a tabela nao tem coluna `projeto`: o deploy le o `name:` do primeiro compose, e o
--            caminho relativo na familia e o mesmo de antes, entao o projeto e os volumes nomeados
--            ficam os de sempre (platafirma-core, plataforma-wiki, edm, motor, ...).
--   rotas    ingress do tunel, config da instancia: /srv/platafirma/casa/deploy/core/cloudflared.yml
--            (absoluto porque chat, rastreador e rastreador-tela apontam o do core).
--   gate     o compose do core na release: /opt/platafirma/current/core/docker-compose.yml.
--   segredos o cofre da stack, /srv/platafirma/casa/segredos/<stack>/ (um arquivo por variavel; o
--            deploy materializa o --env-file em tmpfs); o cofre matrix em segredos/matrix/, a
--            credencial do tunel em segredos/core/cloudflared/, e o env do ops-server em
--            segredos/ops/systemd.env (medido IGUAL ao arquivo da conta que o core declarava).
--            Nome e caminho, nunca valor.
--   reversao `via` MEDIDA preservada: promover em core, motor, rag, conhecimento, harness-controle,
--            rastreador e rastreador-tela; up em acervo-api, chat, harness-sessao, jaiminho e
--            searxng. `release promover <familia>` recria (--force-recreate --build) toda stack
--            via promover da familia; virar as cinco para promover e decisao de operacao, nao
--            correcao de caminho, e fica fora desta migracao.
--
-- Upsert COMPLETO e nao UPDATE de coluna: em banco novo o seed 0076c e exemplo e nao grava
-- stack nenhuma — esta migracao e quem as cria. Em banco existente, corrige. Serializacao de
-- bin/_acervo/stack (json.dumps::jsonb; compose-lista como JSON, nao repr).
-- Idempotente: on conflict (slug) do update; ligacoes on conflict do nothing. Transacional: um
-- aceite que falha aborta tudo (o `migrar` roda psql -1 com ON_ERROR_STOP).
--
-- Ensaio no banco real SEM gravar (o dono, antes do `migrar aplicar rag`): troca o commit final
-- por rollback e le a prova que a propria migracao imprime.
--   sed 's/^commit;$/rollback;/' /opt/platafirma/current/harness/sessao/migracao/0091_acervo_stack_release_instancia.sql \
--     | DOCKER_HOST=unix:///run/user/1001/docker.sock docker exec -i rag-extractor-pg \
--         psql -U rag -d rag_extractor -v ON_ERROR_STOP=1 -P pager=off -f -
--   Esperado: 12 linhas no SELECT de prova, nenhum ERROR, ROLLBACK no fim; `acervo stack ver --json`
--   depois continua mostrando as linhas antigas. Teste: testes/test_migracao_0091.sh (Postgres
--   descartavel em /tmp, carrega as linhas medidas, aplica duas vezes e roda o bin/deploy nelas).
begin;

insert into acervo.stack (slug,papel,critico,repo,compose,rotas,segredos,reversao,gate,profiles,nota) values
  ('core','control-plane: IAM, borda, politica de seguranca',true,'platafirma-core','/opt/platafirma/current/core/docker-compose.yml','"/srv/platafirma/casa/deploy/core/cloudflared.yml"'::jsonb,'["/srv/platafirma/casa/segredos/core/", "/srv/platafirma/casa/segredos/core/cloudflared/01452d04-7dd9-40ea-be5a-f8bcaa7bed8f.json", "/srv/platafirma/casa/segredos/ops/systemd.env"]'::jsonb,'{"via": "promover", "nota": "Critica: derruba a borda e o IAM junto. Reverter e recriar, nao ''down''. Sessao aberta de todo mundo cai.", "quem": "claudinho-TI", "estado": "identidade-db, keycloak-db e mdm-rh-db em volume: NAO voltam com o codigo. Migracao de realm feita para frente e irreversivel por aqui.", "janela_min": 1, "provado_em": "2026-08-21 — ida e volta pelo verbo (59bbdd6 -> f674555 -> 59bbdd6), 21s e 29s, keycloak, identidade-db, mdm-rh-db e landing recriados; cloudflared e o tunel voltaram sozinhos."}'::jsonb,null,null,null),
  ('motor','motor: malha de mensageria (msg)',true,'platafirma-motor','/opt/platafirma/current/motor/docker-compose.yml',null,'["/srv/platafirma/casa/segredos/motor/"]'::jsonb,'{"via": "promover", "nota": "Critica: msg para enquanto recria. Consumidor com stream aberto reconecta sozinho.", "quem": "claudinho-TI", "estado": "motor-pg em volume; motor-msg-mem e cache allkeys-lru e pode ser perdido sem dano.", "janela_min": 1, "provado_em": "2026-08-21 — ida e volta pelo verbo (b92c528 -> b0225d8 -> b92c528), 8s cada, os quatro conteineres recriados. msg parou e voltou dentro da janela."}'::jsonb,null,null,null),
  ('rag','recuperacao: extrator, indice e API do acervo',false,'platafirma-conhecimento','["/opt/platafirma/current/conhecimento/rag/docker-compose.yml", "/opt/platafirma/current/conhecimento/rag/docker-compose.gpu.yml"]',null,'["/srv/platafirma/casa/segredos/rag/"]'::jsonb,'{"via": "promover", "nota": "Overlay de GPU e perfil `serving` entram na volta; sem --profile o rag-api fica fora e o verbo nao acusa.", "quem": "claudinho-TI", "estado": "indice vetorial em volume: nao volta com o codigo, e reindexar custa horas de GPU.", "janela_min": 1, "provado_em": "2026-08-21 — ida e volta pelo verbo (f84def9 -> bda62dd -> f84def9), 26s e 25s, minio/pg/api recriados. Acervo conferido DEPOIS: 1639 arquivos e 4.150.556.269 bytes, identico ao de antes. Backup completo na pasta de trabalho da conta (backups/minio-obras-20260821T071055, estado de 21/08/2026) (md5 de amostra confere) existia antes do ensaio."}'::jsonb,null,'["serving"]'::jsonb,null),
  ('acervo-api','API do acervo',false,'platafirma-conhecimento','/opt/platafirma/current/conhecimento/acervo-api/docker-compose.yml',null,'["/srv/platafirma/casa/segredos/acervo-api/"]'::jsonb,'{"via": "up", "nota": "Base na release (/opt/platafirma/current/conhecimento), sobreposicao em /srv/platafirma/casa/deploy/acervo-api/. Via `up`, medida em 15/09/2026 e preservada: `release promover platafirma-conhecimento` NAO recria esta stack. A volta e `release reverter platafirma-conhecimento <rev anterior>` seguida de `deploy acervo-api up -d --build`. Ate 15/09/2026 apontava o clone de trabalho; o ensaio de 21/08 usou `git checkout <ref> -- acervo-api/` nele, sem trocar branch.", "quem": "claudinho-TI", "estado": "le o Postgres do acervo, que nao e desta stack: nada a perder aqui.", "janela_min": 1, "provado_em": "2026-08-21 — ida e volta executada e MEDIDA: acervo-api/ voltado a 5f9a26a, rebuild, container Recreated e /health 200 em 4s; volta a f84def9, Recreated, /health 200 em 3s. Janela real ~7s, nao os ~5 min estimados. Clone limpo depois."}'::jsonb,null,null,null),
  ('conhecimento','wiki e MCP de conhecimento',true,'platafirma-conhecimento','["/opt/platafirma/current/conhecimento/docker-compose.yml", "/opt/platafirma/current/conhecimento/docker-compose.override.yml"]',null,'["/srv/platafirma/casa/segredos/conhecimento/"]'::jsonb,'{"via": "promover", "nota": "Critica. O override do LocalSettings.php e bind de arquivo unico: promover troca o inode e e por isso que a volta tambem tem de ser `promover`, nunca `restart`.", "quem": "claudinho-TI", "estado": "dbdata (MariaDB da wiki) e images em volume: conteudo NAO volta com o codigo. Edicao feita depois do commit ruim permanece, e e isso que se quer.", "janela_min": 1, "provado_em": "2026-08-21 — ida e volta pelo verbo (f84def9 -> bda62dd -> f84def9), 25s cada, wiki-db e mediawiki recriados, /health do wiki-mcp 200 no fim. dbdata intacto."}'::jsonb,null,null,null),
  ('harness-controle','plano de controle do harness: agregador e tela',false,'platafirma-harness','/opt/platafirma/current/harness/controle/compose.yaml',null,'[]'::jsonb,'{"via": "promover", "nota": "O AGREGADOR e unit systemd --user, fora deste compose: reverter a tela nao reverte o agregador.", "quem": "claudinho-TI", "estado": "sem volume: a volta e integral.", "janela_min": 5, "provado_em": "2026-08-21 — ida e volta executada pelo verbo (6fd9997 -> 9825a5a -> 6fd9997), conteiner recriado nos tres passos"}'::jsonb,null,null,'reparticao por direcao: a TELA e conteiner, servida por este compose (front vem da imagem, arq:0056); o AGREGADOR e unit systemd --user em controle/systemd/ no repo, porque os verbos do host nao sobrevivem a containerizacao.'),
  ('jaiminho','corpo do colaborador externo Jaiminho: fala com a API do Google e com o ops-server pelo client proprio no realm',false,'platafirma-harness','/opt/platafirma/current/harness/jaiminho/docker-compose.yml',null,'["/srv/platafirma/casa/segredos/jaiminho/"]'::jsonb,'{"via": "up", "nota": "Base na release (/opt/platafirma/current/harness), sobreposicao em /srv/platafirma/casa/deploy/jaiminho/. Via `up`, medida em 15/09/2026 e preservada: `release promover platafirma-harness` NAO recria esta stack (recriar sem cuidado desloga o braco). A volta e `release reverter platafirma-harness <rev anterior>` seguida de `deploy jaiminho up -d --build jaiminho-server`. Ate 15/09/2026 apontava o clone de trabalho. Ver residuo do #2286 (mesa #221): quem serve a 8023 e o daemon uid 1001.", "quem": "claudinho-TI", "estado": "volume `casa` guarda o login do agy: recriar sem cuidado desloga o braco.", "janela_min": 2, "provado_em": "2026-08-21 — ida e volta por checkout de caminho (jaiminho/ em 57de907 e de volta a c1bd0b5), 63s e 64s, jaiminho-server recriado e /health 200 na 8023. Volume `casa` intacto: o braco nao deslogou."}'::jsonb,null,null,'rede bridge propria, sem alcance ao loopback do host — o Valkey da malha e inalcancavel de dentro (medido em 14/08/2026). Sem rota no tunel: nao e superficie publica.'),
  ('chat','superficie de conversa: homeserver Matrix, banco proprio e Application Service',false,'platafirma-harness','/opt/platafirma/current/harness/chat/docker-compose.yml','"/srv/platafirma/casa/deploy/core/cloudflared.yml"'::jsonb,'["/srv/platafirma/casa/segredos/chat/", "/srv/platafirma/casa/segredos/matrix/oidc-client-secret", "/srv/platafirma/casa/segredos/matrix/signing.key", "/srv/platafirma/casa/segredos/matrix/segredos.yaml", "/srv/platafirma/casa/segredos/matrix/registration.yaml"]'::jsonb,'{"via": "up", "nota": "Base na release (/opt/platafirma/current/harness), sobreposicao em /srv/platafirma/casa/deploy/chat/. Via `up`, medida em 15/09/2026 e preservada: `release promover platafirma-harness` NAO recria esta stack. A volta e `release reverter platafirma-harness <rev anterior>` seguida de `deploy chat up -d`. Ate 15/09/2026 apontava o clone de trabalho. signing.key fora do git — perde-la invalida o homeserver, e nenhuma volta de codigo a recupera.", "quem": "claudinho-TI", "estado": "banco do Synapse em volume: mensagem nao volta, e nem deve.", "janela_min": 1, "provado_em": "2026-08-21 — ida e volta por checkout de caminho (chat/ em 1f985b5 e de volta a c1bd0b5), 18s cada, chat-recepcao recriado. chat-pg e chat-synapse NAO foram recriados: o commit so tocava a recepcao, e reversao parcial e o caso real."}'::jsonb,null,null,'O Synapse fica em duas redes: `interna` (internal, com banco e AS — e por ela que a Admin API responde, e so por ela) e a do conhecimento, que e onde o cloudflared vive. Em rootless o container nao alcanca o loopback do host, entao estar na rede do cloudflared e a unica forma de a borda chegar no homeserver. O ingress mora no core, e por isso `rotas` aponta para fora deste repo.'),
  ('rastreador','rastreador de trabalho: API e banco proprio do boneco',false,'platafirma-rastreador','/opt/platafirma/current/rastreador/docker-compose.yml','"/srv/platafirma/casa/deploy/core/cloudflared.yml"'::jsonb,'["/srv/platafirma/casa/segredos/rastreador/"]'::jsonb,'{"via": "promover", "nota": "Superficie publica: a volta que muda contrato de API quebra a tela, que e de claudinha-produto. Avisar antes.", "quem": "claudinho-TI", "estado": "rastreador-db em volume: card criado depois do commit ruim SOBREVIVE a volta. Migracao de schema aplicada nao desfaz sozinha.", "janela_min": 1, "provado_em": "2026-08-21 — ida e volta pelo proprio verbo (0a14392 -> 2d8e414 -> 0a14392): rastreador-db e rastreador-api Recreated nos dois passos, /health 200 em 10s cada, e o card #184 lido antes e depois byte a byte igual (o volume nao se mexeu). Janela real ~20s."}'::jsonb,'"/opt/platafirma/current/core/docker-compose.yml"'::jsonb,null,'Boneco do card #465, API-only por arq:0056 — o comentario 335 recortou a tela, que volta no #468. Desde o card #3010 a base sobe da release e a sobreposicao da instancia (ate 15/09/2026 apontava o clone de trabalho, como acervo-api, chat e jaiminho). DESDE O #469 a stack tem superficie publica: tarefas.platafirma.org entra no `oauth2-proxy-rastreador`, que vive na stack CORE e alcanca esta API pela rede `pf-borda-rastreador`. Por isso `rotas` e `gate` apontam os dois para fora deste repo — mesma razao do `chat`, cujo ingress tambem mora no core. Reverter continua sendo `deploy rastreador down` mais apagar o volume.'),
  ('rastreador-tela','superficie de tela do rastreador: a tela servida por si, sem o back',false,'platafirma-ui','/opt/platafirma/current/ui/app/rastreador/docker-compose.yml','"/srv/platafirma/casa/deploy/core/cloudflared.yml"'::jsonb,'[]'::jsonb,'{"via": "promover", "nota": "Deploy desta stack e de claudinha-produto desde o #197. claudinho-TI reverte so em incidente, e avisa. NAO ensaiada em 21/08 por fronteira de cadeira: deploy desta stack e de claudinha-produto. FORA DO ESCOPO do #184 por ordem do dono em 21/08/2026: o card cobre as stacks de claudinho-TI, e o deploy desta e de claudinha-produto. Ensaio, quando houver, e dela.", "quem": "claudinha-produto", "estado": "sem volume e sem segredo: a volta e integral.", "janela_min": 5, "provado_em": "FORA DE ESCOPO por ordem do dono, 21/08/2026 — o deploy desta stack e de claudinha-produto desde o #197, e ensaio de reversao acompanha o dono do deploy. A declaracao (via, janela, quem, o que nao volta) segue valendo e nao precisa de ensaio meu."}'::jsonb,'"/opt/platafirma/current/core/docker-compose.yml"'::jsonb,null,'Segunda saida de release da platafirma-ui (arq:0057 emendando arq:0042): a biblioteca sai como imagem versionada, cada superficie de tela sai como SERVICO proprio. Alcancada pelo `oauth2-proxy-rastreador`, que vive na stack CORE, pela rede `pf-borda-rastreador` — por isso `rotas` e `gate` apontam para fora deste repo, mesma razao do `rastreador` e do `chat`. `segredos: []` DECLARA que a stack nao exige nenhum, e e aceite do #187, nao omissao: front que monta segredo de outra camada e o que o instrumento passa a reprovar. Deploy desta stack e de claudinha-produto a partir do fechamento do #187 (card #197).'),
  ('harness-sessao','substrato das entidades operacionais de sessao: fita, giro, pacote, peca servida, mesa',false,'platafirma-harness','/opt/platafirma/current/harness/sessao/compose.yaml',null,'["/srv/platafirma/casa/segredos/harness-sessao/"]'::jsonb,'{"via": "up", "nota": "Base na release (/opt/platafirma/current/harness), sobreposicao em /srv/platafirma/casa/deploy/harness-sessao/. Via `up`, medida em 15/09/2026 e preservada: `release promover platafirma-harness` NAO recria esta stack (promover recria com --force-recreate e derrubaria o banco da fita em curso). A volta e `release reverter platafirma-harness <rev anterior>` seguida de `deploy harness-sessao up -d`. Ate 15/09/2026 apontava o clone de trabalho. Volta de DDL ja aplicada exige migracao para frente, nunca `down -v`. ENSAIO TENTADO E RECUSADO em 21/08: sessao-db e imagem postgres pura, sem build — `up -d --build` nao recria nada quando o conteudo nao muda, e o ensaio passaria verde sem ter revertido (prova falsa). Ensaio valido exige --force-recreate, que derruba o banco da fita em curso; fica para janela sem sessao viva.", "quem": "claudinho-TI", "estado": "sessao-db em volume: fita, giro e mesa NAO voltam com o codigo. DDL em sessao/init/ so roda em volume novo.", "janela_min": 5, "provado_em": null}'::jsonb,null,null,'Desde o card #3010 a base sobe da release e a sobreposicao da instancia (ate 15/09/2026 apontava o clone de trabalho, como chat e jaiminho). Instancia propria, e nao servico do `harness-controle`, porque ali o ciclo de vida e o da TELA — `deploy harness-controle down` levaria a memoria de trabalho junto. Fase 6 do card #189; DDL em sessao/init/, versionada.'),
  ('searxng','metabusca FOSS soberana para o verbo pesquisar (loopback)',false,'platafirma-core','/opt/platafirma/current/core/deploy/searxng/docker-compose.yml',null,'["/srv/platafirma/casa/segredos/searxng/"]'::jsonb,'{"via": "up", "quem": "claudinho-TI", "janela_min": 1, "estado": "sem volume proprio; cache no motor-cache (DB 3) e descartavel.", "nota": "Base na release (/opt/platafirma/current/core/deploy/searxng), segredo em /srv/platafirma/casa/segredos/searxng/. Via `up`, medida em 15/09/2026 e preservada: `release promover platafirma-core` NAO recria esta stack. A volta e `release reverter platafirma-core <rev anterior>` seguida de `deploy searxng up -d`. Ate 15/09/2026 apontava o clone de trabalho. Stateless: sem volume e sem banco proprio. Unico estado e o cache no motor-cache (DB 3), allkeys-lru, descartavel sem dano.", "provado_em": null}'::jsonb,null,null,'Loopback-only (127.0.0.1:8888), consumidor e o verbo `pesquisar` (spec_pesquisa-web 3.1), nao humano: sem rota no tunel e sem oauth2-proxy. Cache/limiter no Valkey da malha (servico `cache`, rede motor_malha), DB 3 reservado por TI; limiter:false. settings.yml versionado em deploy/searxng/ do platafirma-core, e chega pela release; curadoria de categorias/engines e politica do dono. Subida 04/09/2026: JSON ok e cache no DB3; 18 engines_ok agregando as 4 categorias (ciencia 5, codigo 7, social 3, geral 1). `geral` fraco por anti-bot dos buscadores web — curadoria do dono.')
on conflict (slug) do update set
  papel = excluded.papel,
  critico = excluded.critico,
  repo = excluded.repo,
  compose = excluded.compose,
  rotas = excluded.rotas,
  segredos = excluded.segredos,
  reversao = excluded.reversao,
  gate = excluded.gate,
  profiles = excluded.profiles,
  nota = excluded.nota;

-- ligacoes MEDIDAS (vindas do 0076c, que deixou de grava-las): keycloak->core;
-- matrix->chat; rastreador->2 stacks.
insert into acervo.instancia_roda_em_stack (instancia_id,stack_id)
  select i.id,s.id from acervo.ferramental_instancia i, acervo.stack s where i.slug='keycloak' and s.slug='core'
union all
  select i.id,s.id from acervo.ferramental_instancia i, acervo.stack s where i.slug='matrix' and s.slug='chat'
union all
  select i.id,s.id from acervo.ferramental_instancia i, acervo.stack s where i.slug='rastreador' and s.slug='rastreador'
union all
  select i.id,s.id from acervo.ferramental_instancia i, acervo.stack s where i.slug='rastreador' and s.slug='rastreador-tela'
on conflict do nothing;

-- Aceites embutidos: o que o bin/deploy recusaria, recusado aqui, sobre a TABELA INTEIRA (linha
-- que ninguem previu tambem conta). Qualquer um aborta a transacao e nada fica gravado.
do $$
declare lista text;
begin
  -- 1. as 12 stacks medidas existem
  select string_agg(e, ', ' order by e) into lista
    from unnest(array['acervo-api','chat','conhecimento','core','harness-controle','harness-sessao',
                      'jaiminho','motor','rag','rastreador','rastreador-tela','searxng']) e
   where not exists (select 1 from acervo.stack s where s.slug = e);
  if lista is not null then
    raise exception 'acervo.stack: faltam as stacks medidas: %', lista;
  end if;

  -- 2. nenhuma linha aponta a pasta de trabalho da conta
  select string_agg(slug, ', ' order by slug) into lista
    from acervo.stack
   where concat_ws(' ', compose, rotas::text, segredos::text, reversao::text, gate::text, nota)
         ~ ('/' || 'AI([/[:space:]"]|$)');
  if lista is not null then
    raise exception 'acervo.stack: ainda apontam a pasta de trabalho da conta: %', lista;
  end if;

  -- 3. compose (rel_na_familia): cada arquivo relativo a raiz da familia ou sob
  --    /opt/platafirma/current/<curto>/ da PROPRIA familia; sem ~, sem .., sem /srv (a sobreposicao
  --    o deploy acrescenta sozinho), e com repo declarado e nao vazio (o deploy sai 3 com repo '').
  select string_agg(s.slug || ' -> ' || coalesce(c.item, '(sem compose)'), '; ' order by s.slug) into lista
    from acervo.stack s
    left join lateral jsonb_array_elements_text(
           case when s.compose is null or s.compose = '' then '[]'::jsonb
                when left(s.compose, 1) = '[' then s.compose::jsonb
                else jsonb_build_array(s.compose) end) c(item) on true
   where coalesce(s.repo, '') = ''
      or c.item is null
      or c.item like '%..%'
      or (c.item ~ '^[~/]'
          and c.item not like '/opt/platafirma/current/' || regexp_replace(s.repo, '^platafirma-', '') || '/%');
  if lista is not null then
    raise exception 'acervo.stack: compose fora do contrato do deploy (base na release da familia): %', lista;
  end if;

  -- 4. rotas, gate e segredos (resolve): string ou lista; relativo vale, absoluto so sob
  --    /srv/platafirma/casa ou /opt/platafirma; ~ e .. nunca.
  select string_agg(x.slug || '.' || x.campo || ' -> ' || x.item, '; ' order by x.slug, x.campo) into lista
    from (select s.slug, k.campo,
                 case when jsonb_typeof(k.v) in ('array', 'string', 'null') then e.item
                      else '(tipo ' || jsonb_typeof(k.v) || ')' end as item
            from acervo.stack s
           cross join lateral (values ('rotas', s.rotas), ('gate', s.gate), ('segredos', s.segredos)) k(campo, v)
           cross join lateral jsonb_array_elements_text(
                   case jsonb_typeof(k.v) when 'array' then k.v
                                          when 'string' then jsonb_build_array(k.v)
                                          when 'null' then '[]'::jsonb
                                          else '["?"]'::jsonb end) e(item)
           where k.v is not null) x
   where x.item like '(tipo %'
      or x.item like '~%'
      or x.item like '%..%'
      or (x.item like '/%'
          and x.item not like '/srv/platafirma/casa/%'
          and x.item not like '/opt/platafirma/%');
  if lista is not null then
    raise exception 'acervo.stack: rotas/gate/segredos fora das raizes de producao: %', lista;
  end if;
end $$;

-- Prova (stdout do `migrar`): o que o deploy vai ler, stack a stack.
select slug, reversao->>'via' as via, compose, rotas::text as rotas, gate::text as gate,
       segredos::text as segredos, profiles::text as profiles
  from acervo.stack order by slug;

commit;
