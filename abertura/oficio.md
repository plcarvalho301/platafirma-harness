Substitui: tool-manifest-geral (arq:0071/0073); mora em abertura/oficio.md

# tool-manifest — núcleo

Regras comuns a toda cadeira. **Os verbos do núcleo chegam como tools** (nome = slug
do verbo, descrição do golden record — `tools/list` é o índice; spec cápsula de
verbos, 02/09/2026). Sem tool para o que precisa → `run_command`, que é fallback.

- Norma de card, execução inteira e teste de admissão da fila:
  `platafirma-arquitetura/docs/administrativo.md`, por ato.

> **Entrega vai a git ou wiki no mesmo turno.** O dono não tem shell no host: arquivo
> parado em `~/AI` é rascunho. Publica, e só então relata, com link inteiro e colável.

O que NÃO é tool, e por isso mora aqui (vai por `run_command`):

```
rastreador|keycloak ...       SHIM de instancia: nome de servico nao e verbo. `_shims-instancia` gera do acervo; redireciona e avisa
git -C ~/AI/<repo> status --short   |   add -A ; commit -m "..." ; push
longjob run <nome> <cmd...>   todo comando acima de 2 min
conta-abertura [cadeira]      tokens do pacote de abertura por cadeira/peca (qwen2.5); --tudo --json --chapeu
deploy-harness/instalar       instrumenta ambiente novo
politica-sync                 publica dados de identidade repo->PDP_DIR (var); morada fora do WT de fabrica (#2956)
uv venv|pip|uvx · python3 (sem shim de pip)
rg · fd · jq · yq · lnav · sar · df -h · du -sh · ncdu
```

## Cinco armadilhas que mordem toda cadeira

- **Espelho de repo serve o SHA velho depois do push** — `repo_sync`, ou ler o clone
  local por `run_command`.
- **`&&` no `run_command` some com o erro** — usar `;` ou chamadas separadas.
- **Faceta válida e despovoada devolve zero sem erro** — `rag_facets` antes de filtrar.
- **`longjob` não herda o ambiente da sessão** — `bash -lc 'export VAR=x PATH=...; <verbo>'`.
- **`edit_page` substitui a página inteira** — `get_page` antes, sempre.

## Três regras que não são de ferramenta

- **Escovação de bit só no miolo do loop**: o que sobe no contexto a cada giro. Fora
  dele, clareza vence contração.
- **O comportamento é o mesmo nas três superfícies** (claude.ai, fita do chat, Code):
  a equalização é pelo MEIO — as três servem `claudinho-mcp` e `platafirma-wiki`.
  Texto de cadeira não se reescreve para caber em superfície mais pobre.
- **Todo verbo declara `capacidade:` e `dono:`** no cabeçalho, e a conta é um verbo
  por capacidade (`arq:0037`). `conferir verbo` mede.

Clones de trabalho: `platafirma-{core,conhecimento,arquitetura,harness,motor,posto}`
e `modulo-osint`, todos em `~/AI`.
