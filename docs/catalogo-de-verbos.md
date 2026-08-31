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

A conta viva (capacidade ↔ verbo, conforme sim/não) não mora aqui: é o golden record
`acervo.ferramental` no Postgres (arq:0076), reproduzido do próprio PATH por
`conferir verbo`. Esta seção fixa a *régua*; a *contagem* pergunta-se ao verbo.

`conferir verbo` sai 1 enquanto houver capacidade com verbo demais ou verbo sem
capacidade declarada. Hoje a única divergência é a dupla órfã: `longjob` e
`ops-log-prune` não têm capacidade no mapa, e o recorte cabe à mesa de
arquitetura.

`fila` é alias de `fila_streams.py` e não conta na régua — a capacidade
`mensagem` é servida pelo verbo `jaiminho`, que fala com o colaborador externo.
Partida a capacidade em filhas, cada verbo vai para a sua.

## Instância e anti-padrão — o que empurra ao verbo certo

O golden record tem três níveis: **capacidade → verbo → instância**. O verbo é o
nome canônico da CLI (`bin/<verbo>`); a instância é o realizador concreto (o
serviço, o banco, o motor). Dois erros recorrentes nascem daí, e cada um tem um
mecanismo de defesa próprio — pela natureza do erro, não por gosto.

**Erro 1 — chamar a INSTÂNCIA como se fosse verbo.** A cadeira alcança o board
pelo nome que ouve o dia inteiro (`rastreador`) e digita `rastreador ...`, quando
o verbo é `tarefas`. `keycloak ...` no lugar de `acesso`, idem. O nome existe como
conceito, então é interceptável.

- **Defesa: symlink gerado do acervo.** `bin/_shims-instancia` lê
  `acervo.ferramental_instancia`, e para cada par cujo nome da instância difere do
  verbo, materializa `~/.local/bin/<instancia>` que avisa a causa e delega ao
  verbo. Roda no `instala.sh`. Instância nova cadastrada no golden record ganha o
  shim na próxima instalação, sem editar código.
- Prova: `rastreador listar` hoje avisa e serve `tarefas listar`.

**Erro 2 — usar COMANDO CRU no lugar do verbo.** `psql` direto no schema,
`docker compose` fora do fluxo, `curl` na API do rastreador — quando um verbo já
faz isso com carimbo e invariante. Aqui **não há symlink possível**: `psql`,
`docker` e `curl` são comandos legítimos em mil outros usos; sequestrá-los
quebraria o host. O nome não é interceptável.

- **Defesa: consulta ao acervo.** A coluna `acervo.ferramental_verbo.em_vez_de`
  guarda o anti-padrão em prosa (ex.: verbo `acervo`, `em_vez_de = "psql direto no
  schema acervo"`). `acervo ferramenta <nome>` casa um nome contra os três níveis
  E contra `em_vez_de`, e responde qual verbo faz aquilo.
- Prova: `acervo ferramenta psql` lista `acervo`, `conferir`, `motor`, `tarefas` —
  todos os verbos que substituem `psql` cru.

**Resumo da assimetria:** instância tem nome fantasma → symlink o intercepta;
comando cru tem nome real → consulta te reorienta. Os dois lêem a MESMA fonte, o
golden record, e por isso não divergem nem envelhecem por conta própria.

Fonte única de verdade: `acervo.ferramental_*`. A norma está gravada no próprio
banco (`comment on table acervo.ferramental_instancia`, migração `0076d`) e o
mecanismo é consequência do modelo de 3 níveis da **ADR 0076**.

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
| `descobrir` | `descoberta` | claudinho-dados | descobre o que o acervo tem sobre um assunto por varredura multi-eixo (obras, facetas, vínculos) |
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
| `situacao` | `situacao` | claudinho-dados | consulta o estado vivo de serviço de uma obra na escada do acervo |
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
- `recuperacao` — estado da plataforma alcançado por consulta a fonte declarada.
  Capacidade de nível 1 desde `arq:0067`, que também fixa o verbo: **um só**,
  `recuperar`, com a tool homônima. Verbo dono de fonte NÃO ganha sub-ato
  `recuperar` — seis sub-atos seriam seis verbos servindo uma capacidade.
  Decidido e não construído; entra na tabela acima quando `bin/recuperar` existir.

## Pendências

- **Duas capacidades órfãs no PATH**: `longjob` e `ops-log-prune` declaram
  `capacidade: orfa`, e é a única divergência que faz `conferir verbo` sair 1.
- **Cabeçalho de `acervo` defasado**: declara `dono: claudinho-conhecimento`, cadeira
  renomeada para `claudinho-dados` em 12/08/2026. A tabela acima traz o dono atual;
  corrigir o arquivo é do dono da matéria.
- **`oscap-casco`, `oscap-casco-falhas`, `ssg-deriva`, `kcadm` e `openssl-pqc`
  saíram do PATH**, absorvidos pelo despachante `seg` (`arq:0040`). Não há mais
  verbo por cópia nem por origem `core`: `conferir procedencia` reprova se voltar.
