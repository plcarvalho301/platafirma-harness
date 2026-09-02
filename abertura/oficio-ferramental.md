# oficio-ferramental — núcleo

Verbos do núcleo comum de abertura — o que toda cadeira usa, independente de chapéu.
`acervo listar ferramental --oficio` serve as fichas destes filtrando o golden record
por esta lista. Uma linha por slug de verbo canônico (a coluna `verbo` do golden
record); o que vier depois do slug na mesma linha é marcador `chave:valor` — `lote:2`
retém a tool atrás de `PF_TOOLS_LOTE2` até seguranca bater a régua acao/tipo (spec
cápsula §3.6). É a única fonte de quem é lote 2: a porta não tem lista própria.
Recorte por chapéu NÃO mora aqui — vai no `ferramental.md` de cada chapéu.

Fonte da verdade do que cada verbo É: `acervo listar ferramental`. Aqui é só o
whitelist do núcleo; o conteúdo é gerado disto, não editado à mão (mesmo princípio
da lista (b) do chapéu).

```
fila
minuta
monta-sessao
chat  lote:2
mesa
tarefas
acervo
motor
infra  lote:2
deploy  lote:2
conferir
acesso  lote:2
descansar
descobrir
persona
seg
sinal
situacao
```

Fora do núcleo, de propósito: `ollama` (inferência-local) e `matrix` (mensagem-externa)
— capacidades reais no golden record, mas não são abertura de toda cadeira.

Alias `encerrar` -> `descansar` (capacidade `encerramento`): registrado no golden
record em 24/08 (dados). `acervo ferramenta encerrar` resolve para `descansar`. Por
ora o alias mora em `em_vez_de` (eixo de anti-padrao) por falta de eixo de alias-de-
verbo proprio no schema -- a saida ainda rotula "anti-padrao". Eixo proprio proposto
ao dono (DDL, TI); quando entrar, o alias migra e o rotulo corrige.
