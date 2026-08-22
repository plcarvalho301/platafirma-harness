Substitui: tool-manifest-geral (arq:0071/0073); mora em abertura/oficio.md

# tool-manifest — núcleo

Índice de abertura, comum a toda cadeira. Uma linha por ato: **o que existe**, não
como se chama cada flag.

- Opção de um verbo: chamá-lo **sem argumento**.
- Contrato, armadilha e o porquê de cada um: ficha do verbo, por ato (lote B).
- Norma de card, execução inteira e teste de admissão da fila:
  `platafirma-arquitetura/docs/administrativo.md`, por ato.

> **Verbo novo em `bin/`, mesmo commit:** linha aqui antes do push. Ferramenta não
> indexada é ferramenta inexistente.
> **Entrega vai a git ou wiki no mesmo turno.** O dono não tem shell no host: arquivo
> parado em `~/AI` é rascunho. Publica, e só então relata, com link inteiro e colável.

```
fila status|ler|enviar        caixa: quantas novas · so o novo, confirma na entrega · recado
minuta ler|escrever|circular|formalizar   deliberacao entre cadeiras; formalizar e o unico fecho
monta-sessao <cadeira>        abertura da cadeira (a tool monta_sessao e a via boa)
chat despachar|versao         giro na sala; quem chama e a recepcao, nao a cadeira
mesa ver|item|fez|fita        memoria de trabalho por chapeu: item TEM ato e alvo
mesa legado|anota|limpa       prosa do substrato velho, e a triagem dela
mesa caderno [chapeu]         indice na abertura; corpo so por ato
encerrar fita|varredura       fecha por marco fechado, nao por hora do dia
tarefas ler|listar|criar|comentar|mover|fechar|apagar|assinar|sub|api   cards; `mover` anda o
                              fluxo, `fechar` fecha, `apagar` some (ordem do dono), `assinar` e sign-off
acervo escada                 UNICA fonte de numero do acervo; nunca SQL na mao
acervo | seg | motor          sem argumento, cada um lista os proprios sub-atos
motor rag buscar|medir|ajuste
infra estado|saude|logs|restart|exclusivo|cache|backup · sinal
deploy <stack> [up -d|rotas|acessos|segredos]       stack obrigatoria, sem default
conferir servico|verbo|skill|repo|peca|sessao|procedencia|superficie|arranque|commit|chapeu
                              `conferir` sem argumento: o que cada classe julga
acesso listar|conceder|revogar|decidir|politica|desligar|orfaos
git -C ~/AI/<repo> status --short   |   add -A ; commit -m "..." ; push
longjob run <nome> <cmd...>   todo comando acima de 2 min
deploy-harness/instalar       instrumenta ambiente novo
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
  a equalização é pelo MEIO — as três servem `platafirma-ops` e `platafirma-wiki`.
  Texto de cadeira não se reescreve para caber em superfície mais pobre.
- **Todo verbo declara `capacidade:` e `dono:`** no cabeçalho, e a conta é um verbo
  por capacidade (`arq:0037`). `conferir verbo` mede.

Clones de trabalho: `platafirma-{core,conhecimento,arquitetura,harness,motor,posto}`
e `modulo-osint`, todos em `~/AI`.
