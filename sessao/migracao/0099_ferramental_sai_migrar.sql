-- 0099_ferramental_sai_migrar.sql — o verbo `migrar` sai do golden record.
--
-- O quê: retira `migrar` (deprecado em 05/10/2026, sucessor `release migrar`) de todas as
-- tabelas do ferramental, no molde da 0096. A capacidade 224 (infra/promocao-de-mudanca)
-- fica só com `release`, o que destrava o UNIQUE em ferramental_verbo.capacidade_id (#3261).
-- Fonte: card #3260 passo 5 e aceite 3; arq:0076 (bijeção capacidade-verbo); ordem do dono
-- de 05/10/2026 no chat da ti, que dispensa a janela da arq:0110 §11 para este verbo.
-- Aplicação: tira linha → da release, depois de promovido o harness sem bin/migrar:
--   release migrar aplicar rag < este arquivo
-- Rollback: reinserir a linha pela 0093 (bloco 3, linha 'migrar') e o bin/migrar pelo
-- release reverter platafirma-harness ao sha anterior.
-- Idempotente: DELETE de linha ausente não falha. Sem BEGIN/COMMIT: o verbo envolve.

delete from acervo.ferramental_instancia
 where verbo_id in (select id from acervo.ferramental_verbo where slug = 'migrar');

delete from acervo.ferramental_ato      where verbo = 'migrar';
delete from acervo.ferramental_acesso   where verbo = 'migrar';
delete from acervo.ferramental_consumo  where verbo = 'migrar';
delete from acervo.ferramental_ambiente where verbo = 'migrar';

delete from acervo.ferramental_verbo where slug = 'migrar';

-- aceite: nenhuma capacidade com mais de um verbo
do $$
begin
  if exists (select 1 from acervo.ferramental_verbo
              where capacidade_id is not null
              group by capacidade_id having count(*) > 1) then
    raise exception 'aceite 0099: capacidade com verbo duplicado';
  end if;
  raise notice '0099 aceite';
end $$;
