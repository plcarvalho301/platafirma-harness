Substitui: o bloco de arranque repetido em CLAUDE.md por cwd (2026-08-16)

# arranque — as duas linhas que abrem qualquer sessão

Fonte única do arranque, para as quatro superfícies. Quem serve identidade é o
pacote de `monta_sessao`; este arquivo só diz como chamá-lo e o que fazer se ele
não vier.

**Todo texto de arranque em cwd — `CLAUDE.md`, casca de Project, append de fita —
é PONTEIRO para cá, nunca cópia.** Cópia congela no commit em que o diretório
nasceu: hoje há 27 worktrees, cada uma num branch, cada uma com sua versão do
mesmo parágrafo. Divergência entre elas não é visível de lugar nenhum.

## As duas linhas

```
1. Primeira ação de toda sessão, antes de qualquer raciocínio ou resposta:
   monta_sessao(cadeira="<injetada pela superfície>").

2. Pacote não chegou: declare que não chegou, não escreva em repo, wiki nem
   fila, e responda só o que não depende de remit. Não improvise cadeira.
```

O retorno é a instrução da sessão — persona, conduta do dono, tool-manifest,
fronteiras da org, memória e fila — e vence este arquivo em qualquer conflito de
conteúdo. Não vasculhe repositório, wiki ou disco para descobrir o que fazer no
arranque: leitura de descoberta é contexto gasto para chegar ao mesmo lugar.

**A conduta não se chama.** `abertura/dono.md` é peça de abertura do catálogo e vem
dentro do pacote (medido: 1.460 tokens). Linha mandando lê-la seria segunda fonte
da mesma régua.

**O `@import` da conduta saiu do `agente/CLAUDE.md` (10/10/2026).** Ele existia porque o
Code apaga retorno antigo de tool e a conduta sumia em fita longa (#3091). Saiu porque o
arranque passou a ser um texto só para toda superfície, e só o Code lê `@import`; na conta
`megafone` ele nunca carregou (`Permission denied` em `/srv/platafirma/casa`, medido em
10/10/2026). A persona volta pelo hook de `SessionStart` (`agente/hooks/porta-sessao.py`). A conduta
fica com a porta, que nunca deduplica peça de constituição (#3092).

## De onde sai a cadeira, por superfície

A injeção é o ÚNICO ponto em que as quatro diferem. Em nenhuma delas a cadeira se
infere: inferir exige informação que só o pacote traz, e cadeira errada não degrada
a resposta — ela faz a sessão falar em nome de quem não é e escrever na mesa alheia.

| superfície | injeção | quem injeta |
|---|---|---|
| claude.ai | instruções do Project fixam a cadeira | o dono, na configuração do app |
| fita | slug chumbado no cwd da fita | `bin/chat`, que já recebe `--cadeira` |
| fábrica | slug dito na abertura; sem slug, `fabrica` por default | o arranque de conta, `agente/CLAUDE.md` |
| Code seco | o mesmo arranque de conta: cai no default | escopo de usuário, em qualquer diretório |
| posto (qualquer máquina, qualquer agente) | slug dito na abertura; sem slug, `fabrica` | `platafirma-posto/AGENTS.md`, por projeto, via `git pull`; o `CLAUDE.md` do posto só o importa |

O posto é a porta de entrada humana (dono, 20/09/2026) e a única exceção à regra do
ponteiro: as duas linhas estão ESCRITAS no `AGENTS.md` de lá, porque daquela porta este
arquivo não se lê antes de a sessão abrir. Mudou aqui, muda lá no mesmo ato.

**O arranque é um só texto (10/10/2026).** `agente/CLAUDE.md` é byte a byte o `AGENTS.md`
do posto: as duas linhas e a tabela que manda cada provider ao seu arquivo em
`providers/` do posto, onde moram login, config e regra da sessão. O `sincroniza.sh` do
posto, que toda instância roda, confere a igualdade antes de instalar e para se divergirem.
Mudou um, muda o outro no mesmo ato, senão nenhuma instância atualiza.

- **Worktree não injeta nada.** Ela isola branch, que é o que git worktree faz bem;
  identidade lida de dentro dela é a cópia congelada que este arquivo elimina.
- **`PF_CADEIRA` não atravessa no Code, e isto foi medido (TI, 16/08):** `Bash` está
  negado na estação e `malote` executa no ops-server, cujo ambiente não é o do
  terminal onde o Code abriu. Variável exportada ali é ilegível de dentro da sessão.
  O que atravessa é o slug dito na abertura. `PF_CADEIRA` segue valendo no host, para
  verbo chamado por `malote`.
- **Code sem injeção só existe em conta onde o arranque não foi instalado.** Rodado o
  posto ou o instalador, o arranque de conta (`agente/CLAUDE.md`, escopo de usuário)
  alcança qualquer diretório: com slug dito, vale o slug; sem slug, abre
  `fabrica` por default, porque é o que a conta faz na maior parte do tempo e sessão
  sem cadeira não é opção. O que eu chamava de "Code seco sem injeção" era, na medição
  do TI, sessão com a cadeira ERRADA e calada — a persona da fábrica morava buildada
  no arquivo de conta, já derivada da fonte. Pior que órfã.
- **O que continua faltando no Code seco é conector, não cadeira**: clone sem
  `.mcp.json` não tem `monta_sessao` a chamar. Aí vale a linha 2 — declare que o pacote
  não chegou e não aja como cadeira.
