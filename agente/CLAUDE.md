# Arranque — conta que roda o Claude Code da PlataFirma

Substitui: a persona de `claudinha-fabrica`, que morava aqui buildada (2026-08-16).

**Identidade não mora mais neste arquivo.** Ela vem de `monta_sessao`, como em
toda superfície — inclusive a persona da fábrica, que é peça
(`platafirma-harness/personas/persona-fabrica.md`) e chega pelo pacote.

## As duas linhas

```
1. Slug dado na abertura ("abre como TI", "sou produto hoje"), nas formas
   canônicas: monta_sessao(cadeira="<slug>").
2. Sem slug: monta_sessao(cadeira="fabrica").
```

O default é a fábrica porque é o que esta conta faz na maior parte do tempo, e
sessão sem cadeira nenhuma não é opção. Slug dado vence o default sempre; nada
mais nesta conta declara identidade.

**`PF_CADEIRA` não serve aqui, e isto foi medido.** Na estação emprestada o
`Bash` está negado, e `run_command` executa no ops-server — ambiente do serviço,
não do terminal em que o Code abriu. Variável exportada no shell da sessão é
ilegível de dentro dela. O que atravessa é o slug dito na abertura.

Arranque canônico das quatro superfícies, e a tabela de injeção de cada uma:
`platafirma-harness/conduta/arranque.md`. Aqui não se copia o texto de lá.

Pacote não chegou: declare que não chegou, não escreva em repo, wiki nem fila, e
responda só o que não depende de remit. Não improvise cadeira.

## A conduta do dono, por import

A linha abaixo é um `@import` do Code: ele lê o arquivo NO ENDEREÇO PUBLICADO a cada
abertura e de novo depois de compactar. Não é cópia — muda na fonte, chega pela
release, e este arquivo não se toca. Está aqui porque o Code apaga retorno antigo de
tool quando a fita cresce, e a conduta chegava só como retorno de `monta_sessao`
(medido em 19 e 20/09/2026, #3091). A persona da cadeira volta pelo hook
`porta-sessao.py` no `SessionStart` de compactação; o resto do pacote, por
`monta_sessao` com o mesmo `sessao_id`.

@/srv/platafirma/casa/var/abertura-publicada/current/abertura/dono.md

## O que é da conta, e não da cadeira

**Dois sistemas de arquivos na mesma sessão, e confundi-los é o erro caro:**

- **local** — o clone na máquina onde o Code abriu. `Bash`, `Write` e `Edit`
  nativos valem aqui e só aqui.
- **host da plataforma** — uid `claudinho`: release em `/opt/platafirma`, instância
  em `/srv/platafirma/casa`. Nunca alcançável por Bash nativo, em máquina nenhuma.
  Só pelo connector `claudinho-mcp`. É onde vivem contêineres, units, banco e os
  verbos.

O connector vem da conta e vale em qualquer diretório e em qualquer máquina.
Não há ambiente a exportar.

Instalação e atualização: `platafirma-harness/agente/instala.sh` (na máquina do
dono: `~/.claude/CLAUDE.md` vira symlink para
`/opt/platafirma/current/harness/agente/CLAUDE.md`, `settings.json` é cópia). Editar o
arquivo instalado não dura — muda na fonte e chega pela release.

Fora do host não se instala nada em `~/.claude/`: a porta de entrada humana é o
`platafirma-posto`, que carrega o arranque (`AGENTS.md`), as permissões e o hook por
projeto e chega por `git pull` (20/09/2026). O hook de lá é cópia byte a byte de
`agente/hooks/porta-sessao.py`: mudou aqui, copia lá no mesmo ato.
