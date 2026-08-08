# Instanciar a fábrica no Claude Code

A fábrica é a única cadeira que roda no Claude Code; as outras rodam em
claude.ai. Skill não alcança o Code, então o veículo da identidade é arquivo de
configuração de **conta**, nunca de repositório alvo.

## Onde abrir a sessão — decide o card, não o hábito

O card diz quantos repositórios ele toca, e isso escolhe o procedimento.

**Card de um repositório só** — clone do repo do card. `Bash`, `Write` e `Edit`
nativos valem, o `AGENTS.md` da raiz é o roteiro, e o push da branch sai do
próprio clone.

```
git clone <repositório do card>
cd <repositório do card>
claude
```

**Card que toca mais de um repositório** — estação emprestada, isto é, o clone
do `platafirma-harness`. É o caso do card cujo escopo cruza repos e do card que
toca o próprio harness.

```
cd <clone do platafirma-harness>
git pull --ff-only
claude
```

Por que a estação resolve multi-repo: o `.claude/settings.json` do harness nega
`Bash`, `Write`, `Edit` e `NotebookEdit` **na estação**, então toda escrita e
execução passam por `platafirma-ops`, na máquina do dono, contra as árvores em
`~/AI/`. Dois repositórios viram dois caminhos na mesma sessão, não duas
sessões. Procedimento completo e o que a configuração garante:
`docs/estacao-emprestada.md`.

O que muda nesse modo, e é preciso saber antes de despachar:

- commit sai com a identidade de quem o `ops` executa (`claudinho`), não com a
  da conta que roda a fábrica;
- edição é `write_file` do `ops`; `Edit` e `str_replace` não alcançam arquivo do
  host a partir do container;
- push da branch é `run_command` com `git -C ~/AI/<repo> push`, e usa a
  credencial do dono — não a da fábrica;
- auditoria fica em `~/AI/var/log/ops/`.

Sem configurar ambiente nos dois casos. Os conectores vêm da conta claude.ai e
valem em qualquer diretório — `claude mcp list` mostra os servidores com o
prefixo `claude.ai` fora de qualquer clone. A persona vem do pacote de conta, já
instalado. Nada a exportar, nada a aprovar.

Configurar só em dois casos:

- **Sessão que não autentica pela conta claude.ai** (API key, token de longa
  duração, provedor de terceiro): aí os conectores não vêm juntos, e o caminho é
  o clone do harness com os dois tokens em variável de ambiente —
  `docs/estacao-emprestada.md`.
- **Conta nova, ou pacote de conta desatualizado**: reexecutar
  `platafirma-core/deploy/agente/instala.sh`.

Régua de veículo: **Code é a fábrica; cadeira que conversa é claude.ai.**

## Onde a identidade mora

Escopo de usuário, na conta que roda a fábrica:

```
~/.claude/CLAUDE.md       persona da fábrica (build) e recorte vigente
~/.claude/settings.json   perfil de permissão
~/.claude/vikunja.env     credencial do rastreador (0600), da conta
~/.local/bin/tarefas      verbo do rastreador — symlink para o harness
```

Fonte canônica da persona: `platafirma-harness/personas/persona-fabrica.md`. O
arquivo instalado é build dessa fonte; reexecutar o instalador atualiza.

Instalador: `platafirma-core/deploy/agente/instala.sh` — symlink onde o destino
enxerga a fonte, cópia onde não enxerga. Ele liga `tarefas` a partir de
`~/AI/platafirma-harness/bin/tarefas`; sem o clone do harness a conta fica sem
verbo de rastreador, e o instalador diz isso em voz alta. O token continua sendo
o da conta (leitura e comentário; fechar card é aceite de claudinho-TI).

A fábrica roda na conta `megafone`, e lá a instalação é por **cópia**:
`/home/claudinho` é 750 com grupo vazio, então symlink apontando para a fonte
não é legível de fora e o Code cai no default sem reclamar. O `cp` como
`megafone` também não serve — quem lê a origem tem que ser root, e quem escreve
o destino tem que ser megafone:

```
sudo cat /home/claudinho/AI/platafirma-core/deploy/agente/CLAUDE.md > /home/megafone/.claude/CLAUDE.md
sudo cat /home/claudinho/AI/platafirma-core/deploy/agente/settings.json > /home/megafone/.claude/settings.json
head -3 /home/megafone/.claude/CLAUDE.md
```

Sessão do Code já aberta não recarrega o pacote — vale a partir da próxima.

## O que o repositório alvo carrega

`AGENTS.md` com o roteiro do repo, que vale para qualquer agente. Texto de
persona e `.mcp.json` não entram: um por repo alvo é uma cópia por repo alvo, e
a que envelhecer diferente é a que vai ser obedecida.

## Régua de instanciação

- A identidade vem de arquivo instalado, não de chamada no arranque, porque
  chamada que não acontece deixa a sessão sem persona e sem sinal, enquanto
  arquivo divergente aparece em `diff`.
- `monta_sessao(cadeira="fabrica")` é chamada de dentro da sessão — fila,
  manifesto e org do momento. Serve também de verificação: o que ela devolve é
  a fonte, e a diferença contra o instalado é deriva de build.
- Conexão de MCP se resolve na conta, não no repo alvo, porque o alvo do card
  muda e a conta não.
- A fábrica não edita o clone do harness em nenhum modo. Card que toque
  `platafirma-harness` executa por `platafirma-ops` contra
  `~/AI/platafirma-harness`.
