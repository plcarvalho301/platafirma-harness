# Análise de risco: vetores de escape da cadeira-de-trabalho segregada

- **Card:** #2437 (insumo do #2436 — "isolamento por ausência")
- **Cadeira:** claudinho-seguranca · **Data:** 2026-08-26 · **Versão:** v1
- **Base:** recon direto do host + mineração do log de auditoria (`~/AI/var/log/ops/ops-*.jsonl`)

## Objeto e método

A cadeira-de-trabalho é a conta `claudinho` (uid 1001), operada pelo MCP `claudinho-mcp`
cujo verbo central (`run_command`) é bash arbitrário. Hoje ela roda **direto no host**
(`/proc/1/cgroup` = `init.scope`, sem `/.dockerenv`) — sem container.

O #2436 propõe isolar *por ausência*: comando não-declarado não existe no ambiente, em vez
de ser barrado por política. Esta análise enumera os vetores de escape atuais, por vetor,
com o raio de dano (blast radius), e o que a containerização resolve — e o que não resolve.

## O que já contém o dano (não mexer — é o que segura hoje)

- `claudinho` **não é root** e está **só no próprio grupo** (`groups=1001`); **não está no
  grupo `docker`** → não alcança o daemon rootful (`/var/run/docker.sock` é `root:docker`).
- `/etc`, `/home/megafone`, `/etc/cron.d`, `/var/spool/cron`, `/usr/local/bin`: **não graváveis**.
- `~/.ssh` só tem `known_hosts` — **sem chave privada**.
- Segredos da instância (`OPS_AUTH_TOKEN`, `TUNNEL_TOKEN`) **não descem** para o env do comando.
- Docker é **rootless** → um escape mapeia para `claudinho`, não para root no host.
- `pkexec` é v124 (polkit 124-2ubuntu1) → **pwnkit / CVE-2021-4034 já corrigido**.

## Vetores de escape (por vetor)

| # | Vetor | Blast radius | Severidade |
|---|-------|-------------|------------|
| V1 | **Execução arbitrária** — `run_command` + interpretadores (`python3`/`perl`/`node`) | qualquer coisa sob `claudinho` | é o vetor-mãe; o #2436 ataca na raiz |
| V2 | **Docker rootless → stack de produção** — o socket rootless controla `keycloak`, `oauth2-proxy`, `identidade-db`, `jaiminho`: `exec`, `inspect` (lê env/segredos), `stop`, recreate | **produção inteira + segredos dos containers**, sem virar root no host | **ALTO** (maior raio real) |
| V3 | **Egresso irrestrito + transporte** — `curl`/`wget`/`nc`/`socat` e saída livre (`http=200` p/ internet) | download de payload, reverse shell, exfiltração | **ALTO** |
| V4 | **Toolchain de compilação** — `gcc`/`cc`/`make` | compilar exploit / módulo | presente, **nunca usado** |
| V5 | **Namespace/mount** — `nsenter`/`unshare`/`chroot`/`mount` | pouco sem cap root hoje; `nsenter` entra em ns de container rootless | presente, **nunca usado** |
| V6 | **pkexec** (setuid-root) | pwnkit já corrigido (v124); risco latente do próximo CVE polkit | presente, **nunca usado** |
| V7 | **sudo NOPASSWD (cruft de desktop)** — 4 comandos root do Linux Mint (`mintdrivers-*`, `mint-refresh-cache`, `mintUpdate/dpkg_lock_check.sh`) | root NOPASSWD; inúteis num servidor | **MÉDIO** |
| V8 | **Persistência** — `~/.config/systemd/user` gravável + `crontab` do usuário | sobrevive a restart, escopo `claudinho` | BAIXO-MÉDIO |
| V9 | **Movimento lateral** — `ssh`/`scp` | latente (sem chave privada hoje) | presente, **nunca usado** |

## Superfície vs. uso real (o dado que o "por ausência" precisa)

Mineração do log de auditoria — o que a cadeira **de fato** invoca: `docker`, `git`,
`python3`, os verbos `bin/` (`tarefas`, `acesso`, `seg`…), coreutils (`ls`/`cat`/`grep`/`sed`),
`rg`/`fd`/`jq`, `curl`, `psql`. ~uma dúzia de ferramentas.

**Presente e nunca invocado:** `gcc`/`cc`/`make`, `nsenter`/`unshare`/`chroot`/`mount`,
`pkexec`, `socat`/`nc`, `perl`/`node`, `ssh`/`scp`, `wget`, `su`, `crontab`. Toda essa lista
é superfície de ataque que **só serve ao atacante** — é exatamente o alvo do #2436.

## O que o #2436 resolve — e o que não resolve sozinho

**Some por ausência** com um casco mínimo: V1 (parcial), V4, V5, V6, V9, e V7 (um container
não herda o `sudoers` do host).

**NÃO resolve sozinho — precisa decisão explícita mesmo com container:**
- **V2 (docker):** se a cadeira precisa operar containers, colocar o socket *dentro* do
  container **traz o escape de volta**. Decisão de projeto: a cadeira containerizada **não
  recebe o socket docker**; operação de produção vira **verbo mediado**, não `docker` cru.
- **V3 (egresso):** container não fecha rede. Precisa de **policy de egresso (allowlist)**.
- **V8 (persistência):** **fs efêmero / recriável** mitiga.

## Recomendações priorizadas

**Imediato (não espera o container):**
1. Remover o `sudo` NOPASSWD do Mint (V7) — superfície root sem função num servidor.
2. Fechar o egresso para allowlist (V3) — hoje é internet aberta.
3. Remover do host (ou marcar para ausência no casco) os binários presentes-e-nunca-usados (V4/V5/V6/V9).

**Design do #2436:**
4. Casco mínimo = **só o allowlist medido** (docker mediado, não socket; `git`; `python3`;
   verbos `bin/`; coreutils; `rg`/`fd`/`jq`; `psql` via verbo).
5. **Sem socket docker** no container (V2).
6. **Egresso allowlisted** (V3).
7. **FS efêmero** (V8).

**Medir antes de cortar:**
8. Este allowlist saiu de amostra do audit; validar contra os runbooks antes de remover, para
   o casco não quebrar trabalho real. O "não-declarado não existe" só é seguro depois que o
   declarado está inventariado.
