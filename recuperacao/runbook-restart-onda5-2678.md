# Runbook — restart da Onda 5 (#2678): ativar o código de identidade mergeado

**O que este restart põe no ar:** rechaveio do PEP por `sub` (#137), `sid`/`jti` na
auditoria (#139), unificação das funções de identidade (#2287) e as duas guardas de
reentrância no `_audit` (ops-server #2700, jaiminho-server b9d0163). Tudo já mergeado;
o código velho segue no ar até este restart.

**Onde cada serviço lê o código:**
- `ops-mcp` (systemd user, `.venv-ops`, porta 8010) roda DIRETO do repo
  (`WorkingDirectory=.../platafirma-harness/ops-server`) → `restart` já pega o código novo.
- `jaiminho-server` (contêiner, imagem `platafirma/jaiminho-server:local`) tem o `server.py`
  BAKED na imagem → precisa **rebuild**, não só restart. `identidade.py` vem por bind e já
  entra no restart. A imagem viva é de 21/08, anterior à guarda → rebuild é obrigatório.

## Pré-voo — JÁ FEITO nesta sessão (25/08), só conferir
- `sujeitos.yaml` dual-keyed por `sub` para os 3 que chamam tool (commit `f2f5e3c`):
  megafone `b6986be0…`, jaiminho `cc897004…`, jaiminho-fabrica `e57eadb1…`. Sem isso o
  PEP pós-restart (chaveia por `sub`) negaria todos por atributo ausente — o lockout.
- Rede de segurança: token estático `OPS_AUTH_TOKEN` vale até **2026-09-30** e resolve
  para `claudinho`/operador. É a mão que volta se o OIDC travar.

## Passos (terminal do host, ~2 min)

    # 0. repo no head e limpo (deve mostrar f2f5e3c ou mais novo)
    cd ~/AI/platafirma-harness && git pull --ff-only && git log --oneline -1

    # 1. ops-mcp — restart pega o código do repo
    systemctl --user restart ops-mcp
    sleep 2 && curl -fsS http://127.0.0.1:8010/health && echo " ops OK"

    # 2. jaiminho-server — REBUILD (server.py baked) + recreate; stack isolada, sem depends_on
    docker compose -f ~/AI/platafirma-harness/jaiminho/docker-compose.yml up -d --build jaiminho-server

## Verificação — o restart valeu?

    # #137 + #139 no ar: sujeito vira o SUB (nao "megafone"), e sid/jti deixam de ser "-"
    tail -5 ~/AI/var/log/ops/ops-$(date +%F).jsonl | jq '{sujeito,sub,sid,jti,tool}'

    # jaiminho rebuildado hoje
    docker inspect platafirma/jaiminho-server:local -f 'built={{.Created}}'

    # guarda de reentrancia (#2700/b9d0163): Bearer malformado da 401 e o servico SEGUE de pe,
    # nao 5xx/queda. Rode 3x seguidas e confirme que continua respondendo.
    for i in 1 2 3; do curl -s -o /dev/null -w '%{http_code}\n' \
      -H 'Authorization: Bearer nao.eh.jwt' http://127.0.0.1:8010/mcp; done
    docker ps --format '{{.Names}} {{.Status}}' | grep -E 'jaiminho-server'

Sinais de sucesso: `sid`/`jti` preenchidos; `sujeito` = UUID de sub; jaiminho `built` de hoje;
malformado dá 401 e o serviço não cai; `restarts=0`.

## Rollback (se travar auth)
1. **Imediato, sem reverter nada:** chamar o ops-mcp com o token estático —
   `Authorization: Bearer $OPS_AUTH_TOKEN` resolve para `claudinho`/operador (vale até 30/09).
   O acesso não some; só o caminho OIDC é que estaria em questão.
2. **Reverter código:** `git revert --no-edit <sha> && systemctl --user restart ops-mcp`
   (e o rebuild do jaiminho, se o problema for lá). Para desfazer a unificação inteira,
   voltar a `fc4f28d` (anterior a esta onda de restart) e reiniciar.
3. **NÃO** editar `sujeitos.yaml` no susto: o dual-key já cobre os dois mundos (username e
   sub), então o arquivo não é a causa. O destravador é o token estático, não o yaml.

## Cuidado aprendido hoje
- Recreate de contêiner por `depends_on` arrasta vizinho: no `platafirma-core`, `up -d` de um
  gate recriou o keycloak junto. A stack do jaiminho é isolada (só `jaiminho-server`), então
  o passo 2 não tem esse risco — mas em `platafirma-core` use `--no-deps`.
