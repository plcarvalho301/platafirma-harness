# Catálogo de verbos da PlataFirma

Tudo que é executável pelo nome no host da plataforma, agrupado pela capacidade
de negócio que serve (`docs/arquitetura-negocio-operacao.md`, `arq:0037`).

Espelho de leitura humana: `Operar:catalogo-de-verbos` na wiki.

## Mandato: um verbo por capacidade de negócio

`arq:0037` é a régua e vale como mandato do dono: **capacidade instanciada no
harness tem um verbo, e o verbo serve uma capacidade.** Verbo que executa atos de
duas capacidades se parte; dois verbos para a mesma capacidade se resolvem de um
dos dois modos declarados na ADR — consolidar num só, ou partir a capacidade em
filhas, cada uma com o seu verbo.

Cabeçalho e origem única não substituem isto. São como o verbo se declara e de
onde ele vem; o mandato é **quantos** podem existir.

Conta atual, reproduzida por `conferir verbo` a partir do próprio PATH:

| Capacidade | Verbo | Conforme |
|---|---|---|
| `acesso` | `acesso` | sim |
| `conhecimento` | `acervo` | sim |
| `decisao` | `minuta` | sim |
| `encerramento` | `descansar` (alias: `encerrar`) | sim |
| `expediente` | `monta-sessao` | sim |
| `incidente` | `sinal` | sim |
| `infra` | `infra` | sim |
| `memoria` | `mesa` | sim |
| `mensagem` | `jaiminho` | sim |
| `motor` | `motor` | sim |
| `mudanca` | `deploy` | sim |
| `organizacao` | `persona` | sim |
| `politica` | `seg` | sim |
| `trabalho` | `tarefas` | sim |
| `verificacao` | `conferir` (alias: `conferir-servido`) | sim |
| órfã | `longjob` e `ops-log-prune` | **não** |

`conferir verbo` sai 1 enquanto houver capacidade com verbo demais ou verbo sem
capacidade declarada. Hoje a única divergência é a dupla órfã: `longjob` e
`ops-log-prune` não têm capacidade no mapa, e o recorte cabe à mesa de
arquitetura.

`fila` é alias de `fila_streams.py` e não conta na régua — a capacidade
`mensagem` é servida pelo verbo `jaiminho`, que fala com o colaborador externo.
Partida a capacidade em filhas, cada verbo vai para a sua.

## Contrato de cabeçalho

Todo verbo da plataforma carrega, nas primeiras linhas do arquivo:

```
# <nome> — <uma linha de propósito, em verbo ativo>
# capacidade: <uma das do mapa da mesa>
# dono: <cadeira>
```

Regras verificáveis, na ordem em que `conferir verbo` as aplica:

1. Cabeçalho presente e com as três linhas. Sem cabeçalho, o verbo não entra no
   PATH.
2. Chamada sem argumento imprime o uso e sai com código 2.
3. Ato de mutação exige alvo explícito; ausência de alvo recusa, nunca opera
   sobre tudo.
4. Ausência se declara. Verbo que não olhou um lugar não afirma que ele está
   vazio.
5. Origem única: o arquivo mora no repo dono e chega ao host por symlink. Cópia
   não é forma válida de instalação.

Forma extensa do BizBOK e contração valem as duas: `gestao-de-motores` e `motor`
são o mesmo termo para a conferência.

## Verbos da plataforma

Todos com origem **harness** — symlink para `platafirma-harness/bin`, versionado.
Medido por `conferir verbo` e `conferir procedencia` em 14/08/2026.

| Verbo | Capacidade | Dono | Propósito |
|---|---|---|---|
| `acervo` | `conhecimento` | claudinho-dados | opera o acervo: ingestão ponta a ponta, escada, obra, bancada e extrato |
| `acesso` | `acesso` | claudinho-seguranca | opera o controle de acesso: concede, revoga, consulta e decide |
| `conferir` | `verificacao` | claudinho-TI | compara o declarado com o servido, por classe de alvo |
| `deploy` | `mudanca` | claudinho-TI | promove ao ar o que está declarado no compose de uma stack |
| `descansar` | `encerramento` | claudinho-IA | fim de fita: confere a memória e mede os fatos voláteis |
| `infra` | `infra` | claudinho-TI | estado e operação da infraestrutura local (contêiner, unit, timer) |
| `jaiminho` | `mensagem` | claudinho-TI | fala com o colaborador externo Jaiminho, no container próprio dele |
| `longjob` | órfã | claudinho-TI | dispara trabalho longo como unit transiente do systemd --user |
| `mesa` | `memoria` | claudinho-IA | memória de trabalho da cadeira entre fitas, por chapéu; `caderno` abre a durável |
| `minuta` | `decisao` | claudinha-gestao-estrategica | despachante do protocolo de deliberação entre cadeiras — escrever, circular, ler, formalizar |
| `monta-sessao` | `expediente` | claudinho-IA | contexto de abertura de uma cadeira, numa volta |
| `motor` | `motor` | claudinho-IA | gestão de motores de decisão: o que um motor serve e mede |
| `ops-log-prune` | órfã | claudinho-TI | poda o registro de operação por retenção declarada |
| `persona` | `organizacao` | claudinha-gestao-estrategica | escrita compartimentada das personas da PlataFirma |
| `seg` | `politica` | claudinho-seguranca | despachante do toolkit de segurança: avalia, deriva régua e repassa ferramenta |
| `sinal` | `incidente` | claudinho-TI | coleta o estado de saúde dos serviços e escreve o arquivo de sinal |
| `tarefas` | `trabalho` | claudinho-TI | cliente do rastreador de tarefas da PlataFirma |

Aliases, que não contam na régua de `arq:0037`: `encerrar` (de `descansar`),
`conferir-servido` (de `conferir`) e `fila` (de `fila_streams.py`).

## Ferramenta de terceiro

Instalada, não construída aqui. Não é espinha da plataforma e não segue o
contrato de cabeçalho.

```
age · age-keygen · cosign · ctop · dive · dockle · fd · gitleaks · grype
hadolint · hurl · jwt · lnav · lynis · minisign · nvcc · oauth2c · opa
osv-scanner · restic · rg · sops · step · syft · testssl.sh · trivy
trufflehog · uv · uvx · yq
```

## Capacidades sem verbo

Do mapa de capacidades, seguem sem instância executável:

- `solicitacao` — pedido do humano ao sistema. Não há superfície pela qual o
  operador humano descubra o que a máquina faz sem perguntar a uma persona.
- `comunicacao` — anúncio por difusão retida. Desenhado em `arq:0036`, sem verbo;
  hoje vaza pela fila.
- `canal` — design system em git, sem verbo que o distribua aos canais.
- `ativo` — item de configuração e seu estado declarado; `config` proposto, não
  construído.

## Pendências

- **Duas capacidades órfãs no PATH**: `longjob` e `ops-log-prune` declaram
  `capacidade: orfa`, e é a única divergência que faz `conferir verbo` sair 1.
- **Cabeçalho de `acervo` defasado**: declara `dono: claudinho-conhecimento`, cadeira
  renomeada para `claudinho-dados` em 12/08/2026. A tabela acima traz o dono atual;
  corrigir o arquivo é do dono da matéria.
- **`oscap-casco`, `oscap-casco-falhas`, `ssg-deriva`, `kcadm` e `openssl-pqc`
  saíram do PATH**, absorvidos pelo despachante `seg` (`arq:0040`). Não há mais
  verbo por cópia nem por origem `core`: `conferir procedencia` reprova se voltar.
