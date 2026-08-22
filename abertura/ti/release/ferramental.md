# ferramental — TI/release (L2)

O que está no ar e desde quando; como se volta atrás.

- `deploy <stack> promover` — promoção controlada de stack.
- `deploy <stack> reverter --executar <ref>` — rollback de stack worktree-deploy.
- `git checkout <ref> -- <dir>/` — rollback de stack clone-based.
- `git tag <marco> <sha>` antes de mudança destrutiva — ponto de retorno verificado.
- `deploy-harness/instalar` — instrumenta ambiente novo.

## Ambiente
- `export PF_CADEIRA=claudinho-TI` antes de `deploy`.
- Merge em main = deploy: não há staging. Entrega só existe em git (`git push origin main`),
  e o branch se confere antes de relatar.

## Armadilhas de uso
- Espelho de repo serve o SHA velho depois do push — `repo_sync` ou ler o clone local.
- Sign-off antes do ar só em superfície EXTERNA em produção: assinatura de TI e segurança.
