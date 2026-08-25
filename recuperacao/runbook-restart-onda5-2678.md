# Runbook — restart da Onda 5 (#2678): ativar o código de identidade mergeado

> **EXECUTAR COMO `claudinho` — NÃO como `megafone`.** Todos os serviços vivem na conta
> `claudinho` (uid 1001): é dela o unit `ops-mcp` (`systemctl --user` só vê o próprio dono)
> e o daemon docker rootless (`/run/user/1001/docker.sock`). Rodando como `megafone` (uid
> 1000), `systemctl --user` não acha o unit e `docker` bate no daemon de SISTEMA — a prod
> não muda e ainda pode nascer um contêiner órfão no lugar errado.
>
> Entre no contexto certo (megafone tem sudo):
>
>     sudo machinectl shell claudinho@        # abre sessão como claudinho e roda tudo lá
>
> ou, sem shell interativo, prefixe com o env do user-manager (senao `systemctl --user`
> da 'Failed to connect to bus: No medium found'):
>
>     sudo -u claudinho env XDG_RUNTIME_DIR=/run/user/1001 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus <comando> E use SEMPRE caminho ABSOLUTO
> `/home/claudinho/AI` — nunca `~/AI`, que como megafone vira `/home/megafone/AI`.

**O que este restart põe no ar:** rechaveio do PEP por `sub` (#137), `sid`/`jti` na
auditoria (#139), unificação das funções de identidade (#2287) e as duas guardas de
reentrância no `_audit` (ops-server #2700, jaiminho-server b9d0163). Já mergeado; o código
velho segue no ar até este restart.

**Onde cada serviço lê o código:**
- `ops-mcp` (systemd user do claudinho, `.venv-ops`, porta 8010) roda DIRETO do repo
  → `restart` já pega o código novo. Ele não se reinicia de dentro de si — daí ser ato de
  terminal.
- `jaiminho-server` (contêiner no daemon do claudinho) tem o `server.py` BAKED na imagem →
  precisa **rebuild**, não só restart. `identidade.py` vem por bind e entra no restart.

## Pré-voo — JÁ FEITO nesta sessão (25/08), só conferir
- `sujeitos.yaml` dual-keyed por `sub` para os 3 que chamam tool (commit `f2f5e3c`):
  megafone `b6986be0…`, jaiminho `cc897004…`, jaiminho-fabrica `e57eadb1…`. Sem isso o
  PEP pós-restart (chaveia por `sub`) negaria todos por atributo ausente — o lockout.
- Rede de segurança: token estático `OPS_AUTH_TOKEN` vale até **2026-09-30** e resolve
  para `claudinho`/operador. É a mão que volta se o OIDC travar.

## Passos (na sessão do claudinho, ~2 min)

    # 0. repo no head e limpo (deve mostrar f2f5e3c ou mais novo)
    cd /home/claudinho/AI/platafirma-harness && git pull --ff-only && git log --oneline -1

    # 1. ops-mcp — restart pega o código do repo
    systemctl --user restart ops-mcp
    sleep 2 && curl -fsS http://127.0.0.1:8010/health && echo " ops OK"

    # 2. jaiminho-server — REBUILD (server.py baked) + recreate; stack isolada, sem depends_on
    docker compose -f /home/claudinho/AI/platafirma-harness/jaiminho/docker-compose.yml up -d --build jaiminho-server

Se preferir não abrir a sessão, os dois como one-liner de fora:

    # `sudo -iu` NAO anexa ao bus do user-manager -> da 'Failed to connect to bus: No medium found'.
    # Setar o env explicitamente (paths medidos: XDG_RUNTIME_DIR=/run/user/1001, bus em /run/user/1001/bus):
    sudo -u claudinho env XDG_RUNTIME_DIR=/run/user/1001 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus systemctl --user restart ops-mcp
    # alternativa (systemd 255): sudo systemctl -M claudinho@ --user restart ops-mcp
    # jaiminho ja rebuildado em 25/08; se precisar refazer, entre com `sudo machinectl shell claudinho@` e rode o compose la dentro.

## Verificação — o restart valeu?

    sudo -iu claudinho bash -lc 'tail -5 /home/claudinho/AI/var/log/ops/ops-$(date +%F).jsonl | jq "{sujeito,sub,sid,jti,tool}"'
    # #137/#139 no ar: sujeito vira o SUB (nao "megafone"), e sid/jti deixam de ser null
    sudo -iu claudinho docker inspect platafirma/jaiminho-server:local -f 'built={{.Created}}'   # de hoje
    # guarda de reentrancia: Bearer malformado da 401 e o servico SEGUE de pe
    for i in 1 2 3; do curl -s -o /dev/null -w '%{http_code}\n' -H 'Authorization: Bearer nao.eh.jwt' http://127.0.0.1:8010/mcp; done

## Rollback (se travar auth)
1. **Imediato, sem reverter nada:** chamar o ops-mcp com o token estático —
   `Authorization: Bearer $OPS_AUTH_TOKEN` resolve para `claudinho`/operador (vale até 30/09).
2. **Reverter código:** `sudo -u claudinho env XDG_RUNTIME_DIR=/run/user/1001 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1001/bus bash -lc 'cd /home/claudinho/AI/platafirma-harness && git revert --no-edit <sha> && systemctl --user restart ops-mcp'` (e rebuild do jaiminho se o problema for lá). Para desfazer a unificação inteira, voltar a `fc4f28d`.
3. **NÃO** editar `sujeitos.yaml` no susto: o dual-key já cobre username e sub. O destravador é o token estático, não o yaml.

## Se você já rodou como megafone (limpeza)
Megafone está no grupo `docker`, então o `--build` pode ter criado um `jaiminho-server` no
daemon de SISTEMA (separado da prod). Conferir e limpar, como megafone:

    docker -H unix:///var/run/docker.sock ps -a | grep jaiminho    # existe algo?
    # se existir e NÃO for a prod (a prod roda no rootless do claudinho, uid 1001):
    docker -H unix:///var/run/docker.sock rm -f jaiminho-server
    docker -H unix:///var/run/docker.sock image rm platafirma/jaiminho-server:local

Remover no daemon de sistema NÃO toca a prod (daemon diferente, uid 1001).

## Cuidado aprendido
- Comando de conta (`systemctl --user`, rootless `docker`) só vale na conta dona. Runbook
  tem de declarar o principal e usar caminho absoluto — `~` mente conforme quem loga.
- Recreate por `depends_on` arrasta vizinho: em `platafirma-core`, `up -d` de um gate
  recriou o keycloak. A stack do jaiminho é isolada, sem esse risco.
