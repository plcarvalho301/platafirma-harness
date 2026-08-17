# tool-manifest — claudinho-TI · DETALHE (por ato)

> Índice de abertura: `tool-manifest/TI.md`. Este arquivo NÃO sobe na abertura — lê-se
> por ato, quando a armadilha, o contrato ou o porquê de um item importa. Espelha o
> padrão de `nucleo-detalhe.md` e `IA-detalhe.md`.

Armadilha de **ferramenta** (a chamada mente, trunca ou falha em silêncio) mora aqui.
Armadilha de **escopo** (o julgamento sai errado embora a chamada tenha funcionado) mora
no chapéu da gerência — o corte é por onde o erro se manifesta, e o teste é: trocada a
tool por outra equivalente, o erro persiste? Persiste → escopo.

Item entra medido, com data. Previsto não entra.

## Deploy e promoção

- **`infra compose` não existe mais.** Promover release é `deploy <stack>`, capacidade
  `mudanca`. A stack é argumento obrigatório, lida de `registro/stacks.json`: não há
  default nem "todas", e `down` em stack crítica exige `PF_SIM=1`.
  *Por quê:* o antigo tinha `-f` fixo no core e ignorava o `cwd` — chamado de outro repo,
  promovia o control-plane inteiro.
- **`deploy promover` recusa clone em branch nomeada** e exige worktree detached, padrão
  `~/AI/deploy/<stack>` com `.env` copiado do clone de trabalho.
- **Push é `git push origin main`, nunca `origin HEAD`.** `HEAD` empurra para o branch em
  que o clone estiver; clone parado em branch de fábrica já mandou entrega para branch que
  ninguém consome, relatada como "no ar" por dois turnos. Confira o branch ANTES de relatar.

## Serviço e unit

- **Restart do ops-mcp mata a chamada em curso.** `infra restart ops-mcp` despacha
  destacado por isso; `systemctl --user restart ops-mcp` direto, não. Todo outro alvo é
  síncrono e conferido: `infra restart` ramifica por `e_conteiner` (contêiner →
  `docker restart`, unit → `systemctl --user restart`) e sai 2 em alvo desconhecido, sem
  imprimir despacho. `--nao-esperar` força o destacado.
- **Unit alterada no disco exige `systemctl --user daemon-reload` ANTES do restart** —
  `infra restart` não recarrega. Medido em 10/08/2026: o `WorkingDirectory` velho já não
  existia, o systemd executou a versão em memória, `200/CHDIR`, 105 tentativas, conector
  fora para todas as cadeiras. Loop de restart queima o `StartLimit`: `reset-failed` antes
  do restart legítimo.
- **`systemctl --user enable` falha com Access denied em unit servida por symlink.**
  Contorno: `ln -sfn <caminho-da-unit> <target>.wants/<nome-da-unit>` e `daemon-reload`.
- **`~/.config/systemd/user/ops-mcp.service` é root-owned**: mudança de comportamento do
  ops-mcp é no código, nunca na unit.

## Execução e canal

- **Comando acima de 2 minutos direto no `run_command`** morre no timeout e leva o process
  group junto — é `longjob`. `longjob` não herda o ambiente da sessão:
  `bash -lc 'export VAR=x PATH=...; <verbo>'`.
- **`&&` no `run_command` some com o erro** — usar `;` ou chamadas separadas. Vale dobrado
  para `apt update` e `apt install`, que vão em linhas separadas.
- **Toda chamada de `run_command` grava linha JSONL** em
  `~/AI/var/log/ops/ops-AAAA-MM-DD.jsonl` com comando, cwd, exit code e duração. Não é
  opcional nem silenciável pelo chamador — é a fonte primária quando o resultado do canal
  é ambíguo, junto com `git reflog`.

## Leitura de repo e wiki

- **Espelho de repo serve o SHA velho depois do push** — `repo_sync`, ou ler o clone local
  por `run_command`.
- **`edit_page` substitui a página inteira** — `get_page` antes, sempre.
- **Faceta válida e despovoada devolve zero sem erro** — `rag_facets` antes de filtrar.
- **`~/AI/{archi_base,i-have-adhd,ollama-orchestrator}`** dão "dubious ownership" no git:
  são de outro dono, não são repo de trabalho. Ignorar.

## Pendências declaradas

- `restic` presente e **sem repositório configurado**; `deploy/backup-cofre.timer` existe
  no repo e não está `enabled` no user.
- `ops-server` roda fora do compose; migração prevista para a janela 4b.
- `shellcheck`, `shfmt`, `ruff` e `pytest` ausentes; instaláveis sem privilégio, presos à
  decisão de branching (#178).
