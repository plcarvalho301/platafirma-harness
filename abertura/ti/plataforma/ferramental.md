# ferramental — TI/plataforma (L2)

Working set do chapéu além do ofício: o que roda, onde roda, o que se reinicia.

- `infra estado|saude|logs|restart|exclusivo|cache|backup` — o serviço no ar; `restart`
  é o ato de retomada de incidente, sempre com ponto de retorno verificado antes.
- `deploy <stack> promover` — promover release de stack (nunca `up -d` cru).
- `longjob run <nome> <cmd...>` — todo comando acima de 2 min; não herda o ambiente,
  `bash -lc 'export VAR=…; <verbo>'`.
- `git -C ~/AI/<repo>` · `systemctl --user` · `docker` (rootless) — host do uid 1001,
  sem sudo.
- `git-filter-repo` — reescrita de história, irreversível: exige clone descartável.

## Ambiente
- `export PF_CADEIRA=claudinho-TI` antes de `infra`, `deploy`, `longjob`.
- Segredos não descem para o subprocesso do ops-mcp.

## Armadilhas de uso
- `deploy <stack> up` de stack grande estoura o timeout do connector e para no meio,
  sem erro — recreate cirúrgico: `docker compose up -d --no-deps <servico>`.
- `&&` no run_command engole o erro — usar `;` ou chamadas separadas.
