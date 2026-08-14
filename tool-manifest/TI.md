# tool-manifest — claudinho-TI

Substitui: ~/AI/tool_manifest.md (03/08/2026)

Ambiente: Linux Mint 22.3, usuário `claudinho` (uid 1001), **sem sudo** — pacote
de sistema é pedido ao dono, em duas linhas separadas (`apt update` e
`apt install`, nunca com `&&`: update não-zero por repo de terceiro faz o
install sumir em silêncio). `~/AI/bin` e `~/.local/bin` já estão no PATH do
subprocesso; binário próprio é chamável pelo nome. `cwd` default: `~/AI`.
Segredos (`OPS_AUTH_TOKEN`, `TUNNEL_TOKEN`) não descem para o subprocesso.

Verificação: cada linha declara **como** — `[exec]` binário executado ·
`[func]` importado e usado em trabalho real · `[inst]` presente, sem prova.
Tudo abaixo é `[exec]` em 05/08/2026 salvo onde marcado.

> **Regra de ouro:** existindo verbo para o que vou fazer, chamo o verbo.
> Reimplementar cliente REST, montar `docker exec` na mão ou repetir credencial
> em script de sessão é o erro que este manifesto existe para cortar.


Formato: necessidade : chamada. Opção detalhada sai de `<comando>` sem argumento.

## Conectores

**platafirma-ops** (`ops.platafirma.org`) — a caixa do claudinho (uid 1001).
- `run_command` · `read_file` · `write_file` — shell e arquivos sob `~/AI`.
- `monta_sessao` — contexto de abertura de uma cadeira numa chamada. Sob
  demanda, não gate de entrada.

**PlataFirma Wiki** (`mcp.platafirma.org`) — conhecimento canônico, acervo, repos.
- `platafirma_index` uma vez por sessão sobre a PlataFirma · `search_pages` /
  `get_page` / `edit_page` / `query_cargo` · `repo_tree` / `repo_read` /
  `repo_grep` / `repo_sync` · `rag_search` / `rag_facets` para **critério** de
  engenharia (fato da PlataFirma nunca sai do RAG).

## Geral — toda cadeira

Em `tool-manifest/TODA-CADEIRA.md`, comum a todas as cadeiras. Não se replica aqui.

## Por domínio — ponteiro, não manual

```
falar com o Jaiminho            : jaiminho perguntar "<texto>"   | continuar, estado, login, logs
                                  colaborador externo no container proprio; Antigravity CLI
                                  com a assinatura do dono, sem API paga. O que ele alcanca
                                  e decisao do PEP, nunca flag do verbo
pôr arquivo na fila do acervo   : platafirma-conhecimento/rag/scripts/acervo-drop
                                  degrau 0, fora do PATH; dono declarado: claudinho-TI
entrada por arquivo / planilha  : acervo ingerir <raiz> | --planilha [x.ods]  [--apply]
inferência local                : curl 127.0.0.1:11434/... · nvitop · nvcc (CUDA 13.2)

segredo em repo                 : gitleaks · trufflehog · detect-secrets
código                          : semgrep · bandit · pip-audit
imagem e SBOM                   : trivy · grype · syft · dive · dockle · hadolint
identidade e política           : seg keycloak -- · jwt · oauth2c · step · opa
TLS e host                      : testssl.sh · sslyze · ssh-audit · lynis · seg oscap avaliar

cifrar, assinar, copiar         : age · sops · minisign · cosign · restic · rsync
```

Ferramental de segurança: usar é permitido, decidir sobre ele não — a cadeira é
claudinho-seguranca. `~/AI/.venv` (ontologia) e `~/AI/.venv-harness` (eval) são
de outras cadeiras: ler, não escrever.

## Armadilhas medidas

- **`infra compose` nao existe mais.** Promover release saiu para `deploy <stack>`
  (capacidade `mudanca`). O antigo tinha `-f` fixo no core e ignorava o `cwd`:
  chamado de outro repo, promovia o control-plane inteiro. No `deploy` a stack e
  argumento obrigatorio, lido de `registro/stacks.json`; nao ha default nem "todas",
  e `down` em stack critica exige `PF_SIM=1`.
- **Restart do ops-mcp mata a chamada em curso.** `infra restart ops-mcp` despacha
  destacado por isso; `systemctl --user restart ops-mcp` direto, não. Todo outro
  alvo é síncrono e conferido: `infra restart` ramifica por `e_conteiner`
  (contêiner → `docker restart`, unit → `systemctl --user restart`) e sai 2 em
  alvo desconhecido, sem imprimir despacho. `--nao-esperar` força o destacado.
- **Unit alterada no disco exige `systemctl --user daemon-reload` ANTES do
  restart** — `infra restart` não recarrega. Sem isso o systemd executa a versão
  em memória: em 10/08 o `WorkingDirectory` velho já não existia e o ops-mcp
  entrou em `200/CHDIR`, 105 tentativas, conector fora para todas as cadeiras.
  Loop de restart ainda queima o `StartLimit`: depois do conserto, `reset-failed`
  antes do restart legítimo.
- **`~/.config/systemd/user/ops-mcp.service` é root-owned**: mudança de
  comportamento do ops-mcp é no código, nunca na unit.
- **Comando longo direto no `run_command`** morre no timeout e leva o process
  group junto. Acima de 2 minutos é `longjob`.
- **`~/AI/{archi_base,i-have-adhd,ollama-orchestrator}`** dão "dubious
  ownership" no git: são de outro dono, não são repo de trabalho. Ignorar.

## Pendências declaradas

- `shellcheck` · `shfmt` · `ruff` · `pytest` ausentes; instaláveis sem
  privilégio, presos à decisão de branching.
- `restic` presente e **sem repositório configurado**; `deploy/backup-cofre.timer`
  existe no repo e não está `enabled` no user.
- `ops-server` roda fora do compose; migração prevista para a janela 4b.
