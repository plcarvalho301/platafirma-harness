-- 0076d_ferramental_norma_shim.sql — migração ADITIVA, documental.
-- Grava no próprio golden record a norma que o card do catálogo (24/08/2026) fixou:
-- INSTÂNCIA com nome ≠ o verbo que serve NÃO se chama como verbo na CLI.
--
-- O PROBLEMA que isto documenta:
--   A espinha é capacidade → verbo → instância. O verbo é o nome canônico da CLI
--   (bin/<verbo>); a instância é o realizador concreto (serviço, banco, motor).
--   Quando os nomes coincidem (ollama→ollama) ninguém erra. Quando diferem
--   (rastreador→tarefas, keycloak→acesso) a cadeira alcança pelo nome que ouve o
--   dia inteiro — o da instância — digita `rastreador ...`, recebe `command not
--   found` (exit 127) e perde o turno. Erro mudo, e reincidente por desenho.
--
-- A CORREÇÃO, dirigida por ESTE dado (não por lista fixa):
--   platafirma-harness/bin/_shims-instancia consulta esta tabela e, para cada par
--   (instancia.slug <> verbo.slug), materializa ~/.local/bin/<instancia> que avisa
--   a causa+correção e delega ao verbo. Roda no instala.sh. Instância nova
--   cadastrada aqui ganha o shim na próxima instalação, sem tocar em código.
--
-- Idempotente (comment on é sempre substituição). NÃO faz DROP.

begin;

comment on table acervo.ferramental_instancia is
  'Realizador concreto do verbo (nível 3). NORMA (card catálogo, 24/08/2026): '
  'instância cujo slug difere do verbo que serve NÃO é invocável como verbo na CLI '
  '— o verbo é o slug de ferramental_verbo. bin/_shims-instancia gera um shim '
  'redirecionador para cada par (instancia<>verbo) a partir desta tabela.';

comment on column acervo.ferramental_instancia.slug is
  'Nome da instância (serviço/banco/motor). Se != o slug do verbo, NÃO chamar como '
  'verbo: _shims-instancia gera ~/.local/bin/<slug> que redireciona e avisa.';

commit;
