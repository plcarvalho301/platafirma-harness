## FERRAMENTAL — ambiente `claudinho`, via platafirma-ops:run_command
Verificado 03/08/2026 por varredura de PATH. Linux Mint 22.3, kernel 7.0.0-28, x86_64.
Substitui: tool_manifest.md (02/08/2026)
 
### Condições de contorno
- **Sem `sudo`.** Pacote de sistema exige o usuário `megafone` — vira pedido ao Pedro,
  em duas linhas separadas (`apt update` e `apt install`, nunca com `&&`: se o update
  sair não-zero por repo de terceiro quebrado, o install some em silêncio).
- **`~/AI/bin` e `~/.local/bin` estão no PATH** desde `platafirma-core@40a2f3e`
  (`_env_subprocesso()` em `ops-server/server.py`). Binário em user-space é encontrável.
- **Segredos não descem para o subprocesso**: `OPS_AUTH_TOKEN` e `TUNNEL_TOKEN` saem do
  env via `ENV_OCULTO`. Valor real em `~/.config/ops/env` (root:claudinho, 0640).
- `~/.config/systemd/user/ops-mcp.service` é **root-owned**: não dá para editar a unit
  nem injetar env por systemd. Mudança de comportamento do ops-mcp é no código, com
  restart destacado (`systemd-run --user`) porque o restart mata a chamada em curso.
- Rede de saída livre (github, pypi). `gh` 2.45.0 autenticado como `plcarvalho301`.
### Processo, CPU, memória
ps · top · htop · pidstat · iostat · mpstat · vmstat · sar · free · uptime
strace · ltrace · gdb · lsof · nice · ionice · timeout
→ `sar` guarda histórico: é a única que responde "como estava há 3 horas".
 
### Disco e I/O
df · du · ncdu · iotop · lsblk · smartctl · inotifywait · tree
 
### Rede
ss · ip · dig · host · tcpdump · nmap · socat · nc · curl · wget
mtr · traceroute · ping · iftop · nethogs · openssl · cloudflared
 
### Log, texto, dados estruturados
journalctl · lnav · jq · yq · rg · fd · ts · sponge · parallel · awk · sed · column · watch
→ `yq` lê compose e YAML sem regex — usar em vez de grep para config.
→ `rg` varre ~/AI inteiro em ~16 ms. `grep -r` está aposentado.
→ `ts` (moreutils) carimba hora em pipe sem timestamp próprio.
→ `lnav` para leitura de log com timeline e SQL.
 
### Contêiner e systemd
docker 29.7.1 (rootless) · docker compose 5.3.1 · ctop · dive · hadolint · dockle
systemctl --user · journalctl · systemd-run · systemd-analyze · loginctl · busctl
→ `ctop`: recurso por contêiner ao vivo. `dive`: camadas de imagem sem subir contêiner.
→ `longjob`: job longo como unidade transiente em `app.slice/platafirma-job-*`, fora do
  cgroup do ops-mcp. Log em `~/AI/var/log/jobs/`. Fonte em
  `platafirma-core/deploy/ops/longjob`; `~/AI/bin/longjob` é symlink.
 
### Python e ambiente
python3 3.12.3 · pip 24.0 · pip3 (=/usr/bin/pip3, são) · pipx · uv 0.12.1 · uvx
node 24.18.1 · npm 11.16.0 · make · gcc
→ `uv` para venv reprodutível.
 
### Scripts próprios em ~/AI/bin
longjob (em git) · ops-log-prune · acervo-get · acervo-pacote · exporta-acervo-xlsx.py
→ **só o `longjob` está versionado.** Os outros quatro são exemplar único no host.
 
### Segredo, sessão, cópia
gpg · ssh · rsync · git · gh · git-lfs · tmux · age · sops · minisign · restic
→ `restic` presente e sem repositório configurado. Cofre tem
  `deploy/backup-cofre.{sh,service,timer}` no repo; a timer não está enabled no user.
 
### De outra cadeira — presente no PATH, escopo do claudinho-seguranca
cosign · gitleaks · trufflehog · grype · trivy · syft · osv-scanner · opa · step
jwt · oauth2c · kcadm · openssl-pqc · hurl · lynis · testssl.sh · oscap · oscap-casco
ssg-deriva · docker-bench-security (~/AI/opt)
→ Fonte da documentação: `PlataFirma:Sec/ferramental` na wiki. Usar é permitido;
  decidir sobre eles, não.
 
### Ausente — fábrica, não incidente
shellcheck · shfmt · ruff · pytest
Instaláveis sem privilégio quando a decisão de branching sair.
(yamllint e pre-commit deixaram de faltar: estão em ~/.local/bin.)
 
### Reinstalar em user-space
`bash ~/AI/platafirma-core/deploy/instala-ferramental.sh`
`bash ~/AI/platafirma-core/deploy/seguranca/instala-ferramental-seguranca.sh`
Ambos idempotentes, sem privilégio.
