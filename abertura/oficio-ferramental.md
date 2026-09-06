# oficio-ferramental — núcleo

Verbos do núcleo comum de abertura — o que toda cadeira usa, independente de chapéu.
`acervo listar ferramental --oficio` serve as fichas destes filtrando o golden record
por esta lista. Uma linha por slug de verbo canônico (a coluna `verbo` do golden
record); o que vier depois do slug na mesma linha é marcador `chave:valor`.
Recorte por chapéu NÃO mora aqui — vai no `ferramental.md` de cada chapéu.

`leva:2` foi retirado em 02/09 (retinha acesso/infra/deploy/chat atrás de uma régua
acao/tipo por tool que nunca chegou a ser pedida — `_autoriza` já cobre essas quatro
pelo mesmo PEP genérico que cobre as outras treze e o `run_command`, então a retenção
não protegia nada) e **volta em 05/09 para `repo` e `pr`**, por pedido escrito no
refinamento da #3004: são os verbos que MUDAM repo e forge, e tool de escrita a um
clique do claude.ai é risco de outra ordem que `tarefas ler`. Diferença do caso de
02/09: aqui a régua foi pedida — é a decisão do grão que claudinho-seguranca escreve
na #3006. Enquanto ela não existe, retido é o comportamento certo, não defeito.
Custo declarado: `repo estado` é leitura e fica retido junto, porque o gate é por
SLUG e `repo` agrupa leitura e mudança nos seus atos (#3004, decisão da fábrica).

Fonte da verdade do que cada verbo É: `acervo listar ferramental`. Aqui é só o
whitelist do núcleo; o conteúdo é gerado disto, não editado à mão (mesmo princípio
da lista (b) do chapéu).

```
fila
minuta
monta-sessao
chat
mesa
tarefas
acervo
motor
infra
deploy
conferir
acesso
descansar
descobrir
persona
seg
sinal
situacao
repo leva:2
teste
lint
```

Os três últimos são o braço de repo/teste/lint/PR da #3004 (feature #3003, invariante
`seg:0014`): a verbologia que substitui `run_command "git -C …"` — allowlist de PREFIXO
DE STRING, que o próprio PAP marca como «mitigação, não controle». Entram no núcleo por
uma razão de mecânica, não de escopo: o whitelist daqui é a ÚNICA fonte da projeção de
tools (`acervo listar ferramental --tools`), e verbo que não aparece no `tools/list` não
serve ninguém. Recorte de QUEM usa é do `ferramental.md` do chapéu, não desta lista.

Fora do núcleo, de propósito: `ollama` (inferência-local) e `matrix` (mensagem-externa)
— capacidades reais no golden record, mas não são abertura de toda cadeira.

Alias `encerrar` -> `descansar` (capacidade `encerramento`): registrado no golden
record em 24/08 (dados). `acervo ferramenta encerrar` resolve para `descansar`. Por
ora o alias mora em `em_vez_de` (eixo de anti-padrao) por falta de eixo de alias-de-
verbo proprio no schema -- a saida ainda rotula "anti-padrao". Eixo proprio proposto
ao dono (DDL, TI); quando entrar, o alias migra e o rotulo corrige.
