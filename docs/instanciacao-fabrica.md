# Instanciar a fábrica no Claude Code

A fábrica é a única cadeira que roda no Claude Code; as outras rodam em
claude.ai. Skill não alcança o Code, então o veículo da identidade é arquivo de
configuração de **conta**, nunca de repositório alvo.

## Onde a identidade mora

Escopo de usuário, na conta que roda a fábrica:

```
~/.claude/CLAUDE.md       persona da fábrica (build) e recorte vigente
~/.claude/settings.json   perfil de permissão
~/.claude/card            acesso ao rastreador
```

Fonte canônica da persona: `platafirma-harness/personas/persona-fabrica.md`. O
arquivo instalado é build dessa fonte; reexecutar o instalador atualiza.

Instalador: `platafirma-core/deploy/agente/instala.sh` — symlink onde o destino
enxerga a fonte, cópia onde não enxerga.

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

## Clone do harness é estação emprestada, sempre

`.claude/settings.json` deste repositório nega `Bash`, `Write`, `Edit` e
`NotebookEdit`. É a configuração de `docs/estacao-emprestada.md` e vale para
todo clone: a fábrica não trabalha a partir do clone do harness — ela clona o
repositório do card. A estação emprestada não instala o pacote de conta.
