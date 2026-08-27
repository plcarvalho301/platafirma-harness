# Recorte — Jaiminho: conta única por provider, dev até o merge request

- **Card:** #2899 · **Cadeira:** claudinho-TI (construção) · **Data:** 2026-08-27 · **Versão:** v1
- **Base:** ordem do dono (fita 27/08/2026) + `recorte-seguranca-modelo-externo-v1` (#2488) +
  dec 0068 (conector por provider) + ADR 0074 (referência fóssil se expurga do estado vivo).

## Modelo (decisão do dono)

- Acesso é modelado **por provider**: cada provider = uma conta = um `sub` (dec 0068, #2488).
  Jaiminho é o provider Antigravity/`agy`.
- Jaiminho tem **uma** conta que faz **tudo que as cadeiras fazem, exceto publicar em
  produção**. Trabalha em branch e abre merge request. Ponto.
- Corolário: não há duas contas por provider. O split `jaiminho` (papel
  `pesquisador-externo`, read-only) **/** `jaiminho-fabrica` (papel `fornecedor`, executa
  card) é **fóssil** sob este modelo — dois sujeitos para um provider.

## O envelope "dev até o MR" já está desenhado — está só preso ao sujeito errado

O alcance que o dono descreve não é novo: é literalmente o papel `fornecedor` do PAP.

- `fornecedor-le-repo` libera `run_command` de git (`add`/`commit`/`push`/`branch`/`merge`/
  `rebase`/`checkout`/`switch`/`worktree`/`stash`/`tag`/`remote`/`clone`…) + `python3`/`uv`/
  `pytest`/`rg`/`fd`/`ls`. É desenvolvimento em branch.
- `fornecedor-sem-estado-do-host` **nega** `docker*`/`systemctl*`/`psql*`/`deploy*`/`infra*`/
  `*.env*`/`seg *`/`acesso *`. É, quase inteiro, o limite **"não publicar em produção"**.
- `fornecedor-nao-toca-identidade` nega o domínio de identidade.

O problema: esse envelope está amarrado ao sujeito **`jaiminho-fabrica`**, que **nunca
atuou** — zero linha de auditoria (medido no PAP, sujeitos.yaml). Enquanto o `jaiminho` real
(o que atua) carrega o papel `pesquisador-externo`, que tem a negativa dura
`externo-nao-executa-comando`. Colapsar os dois é dar ao sujeito que atua o envelope que já
foi desenhado para o que nunca atuou.

## Onde o Jaiminho está sem braço (o gap, quatro itens)

1. **Não executa nada.** `externo-nao-executa-comando` nega todo `run_command`/shell para o
   papel do sujeito ativo. É o item que se sente como "sem braço": ele lê acervo, wiki e o
   espelho do repo, mas não roda um teste nem cria um branch. Correção: colapso de papel
   (seção PAP).
2. **Não tem workspace.** O container não tem clone nenhum dos repos. O home é volume, e o
   uid 1003 não atravessa `/home/claudinho` (750) — não alcança os clones das cadeiras. Sem
   clone na casa dele, não há o que ramificar. Correção: `git clone` dos `platafirma-*` no
   volume da conta (constrói TI), com origem autenticada pela credencial dele.
3. **Não tem como empurrar nem abrir MR.** A fábrica (Claude Code) empurra com a credencial
   do **dono**, via ops-server, com identidade `claudinho` — Jaiminho é conta separada e não
   herda isso. Precisa de credencial **própria**, escopada: push de branch + abrir MR, **sem
   push/merge no branch default e sem deploy**. É o limite "publicar" materializado no
   próprio token — o segundo cadeado, além do PAP. Constrói: dono (é credencial).
4. **Toolchain incompleto.** O Dockerfile dele tem git/python3/rg/fd/jq/sqlite; **falta**
   `gh` (abrir MR pela linha), `uv` (build e teste no padrão da casa) e node/npm (se pegar
   linha de front-end). Referência medida no host: `gh`, `uv`, `node`, `npm` todos presentes
   — é a linha de base que a imagem dele tem de alcançar. Constrói: TI (Dockerfile + ponte).

## O limite "publicar em produção", nomeado

Dois cadeados, e os dois ficam:

- **PAP:** `docker*`, `systemctl*`, `psql*`, `deploy*`, `infra*`, `*.env*`, domínio de
  identidade — negados (herdado de `fornecedor-sem-estado-do-host`).
- **Credencial:** o token de git dele empurra branch e abre MR, mas o branch default é
  protegido contra push/merge por ele, e ele não tem credencial de deploy. Publicar =
  merge no default + deploy; nenhum dos dois está na mão dele.

## Divisão de execução (fronteira)

| Item | Cadeira | Estado |
|------|---------|--------|
| **REGRA do PAP** — colapso de papel, derrubar `externo-nao-executa-comando` | **claudinho-seguranca** | diff pronto abaixo (insumo) |
| **CONSTRUÇÃO** — Dockerfile (`gh`/`uv`/node), ponte MCP, clones, verbo | **claudinho-TI** | minha mão, adiante neste card |
| **Expurgo operacional** do split (composes, verbo, docs) | **claudinho-TI** | no mesmo merge, após teardown |
| **Conta de SO** | — | **feito**: `jaiminho` uid 1003 existe, subuid/subgid alocados (#2286) |
| **Credencial de push/MR escopada** | **mão do dono** | pendente |
| **Teardown dos containers `agy` do arm antigo** | **mão do dono** (root/rootless 1003) | pendente |

O item 1 do #2488 (conta de SO própria, que travava por root) está **feito** para o
`jaiminho`. O que falta de root agora é a credencial de push e o teardown do arm — não a
conta.

## PAP — forma do colapso (para claudinho-seguranca)

Um só sujeito ativo por provider, um só papel de trabalho. Esboço, a regra é da cadeira dela:

- **Fundir** o alcance de `fornecedor` no papel do sujeito `jaiminho` (ou renomear o papel
  para algo como `colaborador-dev` que una: lê acervo/wiki/repo **e** executa git/build em
  branch), preservando as leituras já concedidas (`jaiminho-le-acervo-inteiro`,
  `jaiminho-le-repo`, `jaiminho-le-wiki-conceito`, `jaiminho-usa-area-de-transferencia`).
- **Derrubar** `externo-nao-executa-comando` (a negativa que hoje tira o braço).
- **Manter** `fornecedor-sem-estado-do-host` e `fornecedor-nao-toca-identidade` como o
  limite "publicar/host" — renomeados para o papel unificado.
- **Remover** o sujeito `jaiminho-fabrica` e suas entradas por `sub`/username em
  sujeitos.yaml (nunca atuou; sub suposto em PAP é pior que ausente).
- **Nota de `run_command`:** o próprio PAP já avisa que allowlist de prefixo de string é
  mitigação, não controle. Se o alcance é "quase tudo menos publicar", a regra limpa é
  **permitir `run_command` amplo e negar por alvo** (`docker`/`systemctl`/`psql`/`deploy`/
  `infra`/`.env`), em vez de allowlist de git subcomando a subcomando. Decisão da cadeira de
  segurança.

## Passos de mão do dono

1. **Credencial de push escopada** para a conta `jaiminho`: deploy token ou PAT que empurra
   branch e abre MR nos `platafirma-*`, com o branch default protegido contra push/merge por
   ele. É o que faz "exceto publicar" valer no lado do Git, não só no PAP.
2. **Teardown** dos containers `jaiminho` e `jaiminho-fabrica` do motor `agy` (no daemon
   rootless da conta 1003), substituídos pela imagem única de conta plena. O `jaiminho-server`
   (MCP read-only de acervo/wiki, up 45h) **permanece** — é outra coisa.

## Expurgo — inventário do fóssil (ADR 0074, no merge)

Referências ao split que resolvem como vigentes no estado vivo e saem no mesmo ato:

| Arquivo | Fóssil | Ação |
|---|---|---|
| `platafirma-harness/jaiminho-fabrica/` (LEIA.md) | tombstone do compose do arm | remover **após** teardown (é guard-rail até lá) |
| `politica-acesso/sujeitos.yaml` | sujeito `jaiminho-fabrica` + entradas por sub/username | remover (colapso) |
| `politica-acesso/politica.yaml` | papel `fornecedor` isolado + `externo-nao-executa-comando` | fundir/derrubar (colapso) |
| `politica-acesso/test_matriz_sujeito_fonte.py`, `test_wiki_universal_e_verbo.py` | casos do split | reescrever para o sujeito único |
| `bin/jaiminho-fabrica` | verbo da segunda conta | remover |
| `bin/chat`, `chat/comum/cadeiras.py` | roteamento de participante `jaiminho-fabrica` | ajustar (matéria de claudinho-IA) |
| `sessao/migracao/0076_acervo_ferramental_seed.sql` | seed do verbo fóssil | migração de expurgo |
| `deploy-harness/migrar-agy-para-jaiminho.sh` **e** `bin/migrar-agy-para-jaiminho.sh` | **duas cópias divergentes** do mesmo script; migração moot sob o novo modelo | remover ambas |
| `migracao-2286/` (jaiminho-fabrica) | fonte do arm | remover no teardown |

## Medido (27/08/2026)

- Os containers `jaiminho` **e** `jaiminho-fabrica` estão de pé no daemon rootless da conta
  1003 — `Up 6 days (healthy)` os dois. O arm antigo está **vivo**; o teardown é trabalho
  real, não limpeza de resto.
- Alcançados **desta sessão** (`claudinho`, uid 1001) pelo socket
  `/run/user/1003/docker.sock`, que carrega ACL para o grupo das cadeiras (`srw-rw---T+`).
  Logo `docker -H unix:///run/user/1003/docker.sock` inspeciona o arm 1003 daqui; parar e
  remover container é a mão do teardown, coordenada — não ato incidental.
