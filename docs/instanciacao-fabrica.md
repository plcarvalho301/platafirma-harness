# Instanciar a fábrica no Claude Code

A fábrica é a única cadeira que roda no Claude Code; as outras rodam em
claude.ai. Skill não alcança o Code, então o veículo da identidade é arquivo de
configuração de **conta**, nunca de repositório alvo.

## Onde abrir a sessão — no posto, sempre

`~/platafirma-posto`, na conta `megafone`. Não há segundo procedimento, e o
número de repositórios que o card toca não escolhe nada: o clone que o runtime
executa é o de `/home/claudinho/AI`, alcançado pelo connector `claudinho-mcp`,
e é o único que existe. Sete cards em três repositórios são sete caminhos na
mesma sessão.

```
cd ~/platafirma-posto && git pull && bash ./sincroniza.sh
claude
```

`git pull` sozinho não sincroniza: ele traz o script; os arquivos de arranque
vêm por `gh api` quando o script roda. Sessão viva não relê `~/.claude/` —
sincronizou, reabre.

Aceite do arranque: `head -1 ~/.claude/CLAUDE.md` sai
`# Arranque — conta que roda o Claude Code da PlataFirma`.

**Não se clona repositório no posto.** Segundo working tree do mesmo repositório
é como o que está no ar passa a divergir do canônico sem aviso — foi assim que a
entrega do `docs.platafirma.org` ficou em produção e fora do git (#213, 18/08).
Canônico do procedimento, com bootstrap e armadilhas: `Operar:acesso-por-code`
na wiki, e `platafirma-posto/CLAUDE.md`.

O que isso implica, e é preciso saber antes de despachar:

- `Bash`, `Write` e `Edit` nativos não alcançam o host: escrita é `write_file` do
  `ops`, e mudança cirúrgica vai por `run_command` com `python3 - <<'PY'` —
  heredoc com código dentro corrompe em aspas e escape;
- git é `run_command` em `~/AI/<repo>`, e `AGENTS.md` da raiz de cada repo segue
  sendo o roteiro daquele repo;
- job acima de 600 s vai por `longjob`: `run_command` mata o grupo de processos
  no timeout, e build ou indexação passa disso.

**Exceção, e é a única:** máquina emprestada, ou sessão que não autentica pela
conta claude.ai (API key, token de longa duração, provedor de terceiro). Aí não
há posto, e o veículo é o clone do `platafirma-harness` como cliente, com os dois
tokens em variável de ambiente: `docs/estacao-emprestada.md`.

Duas consequências do canal, que valem no posto e na estação, e mordem quem
espera o comportamento do Code nativo:

- commit sai com a identidade de quem o `ops` executa (`claudinho`), não com a da
  conta que roda a fábrica; push é `run_command` com `git -C ~/AI/<repo> push`, e
  usa a credencial do dono;
- auditoria de tudo que a fábrica executa fica em `~/AI/var/log/ops/`.

Nada a configurar em nenhum dos dois: os conectores vêm da conta claude.ai e
valem em qualquer diretório — `claude mcp list` mostra os servidores com o
prefixo `claude.ai` fora de qualquer clone. A persona vem do pacote de conta.

Reexecutar `platafirma-harness/agente/instala.sh` só em conta nova, ou quando o
pacote de conta estiver atrasado.

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

Instalador: `platafirma-harness/agente/instala.sh` — symlink onde o destino
enxerga a fonte, cópia onde não enxerga. Ele liga `tarefas` a partir de
`~/AI/platafirma-harness/bin/tarefas`; sem o clone do harness a conta fica sem
verbo de rastreador, e o instalador diz isso em voz alta. O token continua sendo
o da conta (leitura e comentário; fechar card é aceite de claudinho-TI).

A fábrica roda na conta `megafone`, e lá a instalação é por **cópia**, não por
symlink: `/home/claudinho` é 750 com grupo vazio, então symlink apontando para a
fonte não é legível de fora e o Code cai no default sem reclamar.

Quem faz a cópia é o `sincroniza.sh` do posto, por `gh api` — não `cp`, não
`sudo cat`, e sem precisar de root na máquina:

```
cd ~/platafirma-posto && git pull && bash ./sincroniza.sh
```

Ele traz `agente/CLAUDE.md` e `agente/settings.json` deste repositório para
`~/.claude/`. Persona não entra: desde 16/08/2026 ela sai por `monta_sessao`,
como a de toda cadeira. É cópia, e cópia envelhece — nada no host detecta o
atraso, porque o `claudinho` não alcança a home da `megafone`.

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
  `platafirma-harness` executa por `claudinho-mcp` contra
  `~/AI/platafirma-harness`.
