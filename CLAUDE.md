# Sessão da PlataFirma a partir deste clone

Esta pasta é **cliente**. Nada da plataforma roda aqui: todo trabalho executa na
máquina do dono, por tool call contra `platafirma-ops` e `platafirma-wiki`. O clone
existe para carregar configuração — não para ser explorado.

## Primeira ação, antes de qualquer outra

```
monta_sessao(cadeira="<cadeira>")
```

Uma chamada devolve persona canônica, o tool-manifest que ela declara, o org canônico
e o estado da fila. **Não vasculhe o diretório para descobrir o que fazer** — nada de
`Glob`/`Grep`/`Read` procurando persona, manifesto ou README no arranque. O que a
sessão precisa saber está no retorno da montagem, e cada leitura de descoberta é
contexto gasto para chegar ao mesmo lugar.

De onde sai a cadeira, nesta ordem:

1. o que o usuário disse nesta conversa ("abre como TI", "sou a fábrica hoje");
2. a variável `PF_CADEIRA`, se exportada no shell da sessão;
3. não havendo nem um nem outro, **pergunte uma vez** — chame `monta_sessao()` sem
   argumento, que o retorno traz a lista de cadeiras válidas, e ofereça a lista.

O prefixo `claudinho-`/`claudinha-` é aceito e descartado; cadeira desconhecida
devolve a lista, nunca erro mudo.

## Depois da montagem

O texto de persona que veio no pacote **é a instrução desta sessão**: remit, o que a
cadeira decide, o que ela não decide e para onde aponta. Ele vence este arquivo em
qualquer conflito de conteúdo — aqui só se descreve o arranque.

Três coisas que não vêm no pacote, de propósito, e como buscar cada uma:

- **corpo das mensagens da fila** — o pacote traz só o envelope; leia o arquivo da
  mensagem que importar, e apague só depois de processar;
- **acervo** — pergunta de critério (prática, padrão, métrica, régua) vai para a busca
  no acervo; pergunta de fato da plataforma vai para wiki, repositório ou rastreador;
- **régua de ferramenta** — está no tool-manifest da cadeira, que veio no pacote.

## Ferramenta: verbo pronto antes de comando cru

`~/AI/bin` tem os verbos de operação, no PATH do `run_command`:

| verbo | para quê |
|---|---|
| `fila` | caixa de mensagens entre cadeiras |
| `tarefas` | rastreador (`tarefas projetos`, e o que o `--help` listar) |
| `infra` | contêiner, unit, timer |
| `monta-sessao` | o mesmo pacote de abertura, em texto, quando não há conector |
| `acervo-status` | tamanho e composição do acervo |

Antes de escrever `curl`, `python` ou `docker` à mão, veja se o verbo existe. Quem
ignorou isso perdeu sessão brigando com autenticação que o verbo já resolve.

## O que esta estação não faz

`Bash`, `Write`, `Edit` e `NotebookEdit` estão negados em `.claude/settings.json`, e
`deny` vence `allow` em qualquer modo. Escrita e execução acontecem **só** por
`platafirma-ops`, na máquina do dono, com auditoria em `~/AI/var/log/ops/`.

Ler o clone segue liberado. Editar o clone, não: mudança em persona, manifesto ou
skill se faz na máquina do dono, pelo caminho da cadeira dona daquele artefato.

## Fila fechada não é fila ausente

Endereço de fila que é **arquivo** em vez de diretório é porteiro deliberado, e o
texto dele diz por onde entrar. `claudinha-fabrica` é o caso vivo: demanda para a
fábrica entra por card no rastreador, nunca por mensagem. Tratar porteiro como "sem
caixa" engole justamente a instrução de roteamento.
