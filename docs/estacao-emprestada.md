# Abrir a PlataFirma de uma estação emprestada

Rodar a PlataFirma de qualquer lugar, sem que nada dela rode fora da máquina do dono.

A estação emprestada é **cliente**: hospeda o Claude Code e o clone deste repositório,
e nada mais. Todo trabalho executa na máquina do dono, por tool call contra os MCPs
(`ops.platafirma.org`, `mcp.platafirma.org`). O clone existe para carregar a
configuração — MCPs, permissões, skills, personas e manifestos — não para rodar código.

## Procedimento

1. Clonar o repositório e entrar nele.

```
git clone https://github.com/plcarvalho301/platafirma-harness.git
cd platafirma-harness
```

2. Exportar os dois tokens no shell da sessão. Eles não moram no repositório: o
   `.mcp.json` referencia as variáveis e o Claude Code as expande em tempo de conexão.

```
export PF_OPS_TOKEN='<token do ops-mcp>'
export PF_WIKI_TOKEN='<token do mcp da wiki>'
```

3. Abrir o Claude Code **de dentro do diretório do clone** e aceitar dois diálogos: o de
   confiança da pasta e o de aprovação dos servidores do `.mcp.json`.

```
claude
```

4. Conferir que os dois servidores conectaram, e abrir a cadeira.

```
/mcp
```

```
monta_sessao(cadeira="<cadeira>")
```

## O que a configuração do repositório garante

`.mcp.json` declara os dois servidores remotos por HTTP, com o token vindo de variável
de ambiente. `.claude/settings.json` nega `Bash`, `Write`, `Edit` e `NotebookEdit` — as
quatro ferramentas que executariam ou escreveriam **na estação emprestada**. Leitura
local (`Read`, `Grep`, `Glob`) segue liberada: ler o clone é ler texto que já está no
disco.

Regra de precedência do Claude Code: `deny` vence `allow` em qualquer nível, e vale em
todos os modos de permissão. Consequência prática e desejada: da estação emprestada não
se commita, não se edita arquivo e não se roda comando local. Escrita e execução passam
por `platafirma-ops` — isto é, pela máquina do dono, com auditoria em
`~/AI/var/log/ops/`.

## Duas coisas que costumam surpreender

**O clone não aprova os próprios servidores.** `enableAllProjectMcpServers` e
`enabledMcpjsonServers` versionados no repositório são ignorados numa pasta que você
ainda não marcou como confiável — os servidores ficam em `Pending approval` até você
rodar `claude` na pasta e aceitar. É por isso que o passo 3 é interativo e não há como
versionar a aprovação.

**Logado com conta claude.ai, os conectores da conta já vêm juntos.** Nesse caso o
`.mcp.json` é redundância útil, não pré-requisito: ele mantém o repositório
autossuficiente quando a sessão autentica por API key, por token de longa duração ou
por provedor de terceiro — situações em que os conectores da conta não são carregados.

## Fronteira

Autorização por identidade (Keycloak) não está neste procedimento. Enquanto ela não
existe, o que separa quem entra é a posse dos dois tokens, e eles valem shell na
máquina do dono. Estação emprestada é estação de terceiro: exportar token em shell que
não é seu deixa rastro no histórico do shell dela.
