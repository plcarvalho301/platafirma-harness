# _release/conferir — sub-ato de `release conferir` (arq:0110 §1: sub-ato mora em bin/_<verbo>/, fora do PATH)

`conferir.py` é a implementação das classes de conferência. As classes do SERVIDO
(verbo, servico, skill, procedencia, superficie, ferramental, front, sessao, chapeu,
pdp, alcance, card) são chamadas por `release conferir <classe>`; as classes de bancada
(repo --staged, commit, arranque --staged) e `existe` seguem em `bin/conferir` até
`spec_lint` existir. Régua: spec_release §4.

## O contrato de 3 estados (card #3142)

`resultado.py`, ao lado deste arquivo, dá o veredito comum: toda classe que o adota
devolve uma LISTA de itens, cada item com um `Veredito` de um destes três estados —

- `conforme` — sem motivo (a fábrica `conforme(desde=None)` nem aceita o parâmetro:
  quem tem algo a dizer além de "bateu" não está conforme).
- `divergente` — motivo obrigatório: bateu, e a diferença tem descrição.
- `indeterminavel` — motivo obrigatório: não deu para olhar (fonte fora do ar, uso
  incompleto, dependência ausente). Não é "OK por omissão": não conseguir olhar
  NUNCA sai `conforme`.

`Veredito.__init__` recusa (`ValueError`) `divergente`/`indeterminavel` sem `motivo`
— o contrato é reforçado em código, não só em convenção.

`desde` é opcional nos três estados: quando a classe sabe "desde quando" aquele
item está naquele jeito (ex.: `started_at` do container, `quando` da promoção), ela
registra. Um detalhe que engana quem só olha o `--json`: `Veredito.dict()` grava
`"desde": "indeterminavel"` (a STRING) quando `desde` está ausente — não confundir
com o `estado` "indeterminavel" do próprio item; são dois campos diferentes que
podem usar a mesma palavra em momentos diferentes.

## A linha-âncora

A primeira linha de toda saída em texto (e a chave `"ancora"` no `--json`) é colável
como referência:

    release conferir <classe> [<alvo>]: N conforme · N divergente · N não consegui olhar — release <sha>

(`resultado.linha_ancora`). `<sha>` é o HEAD curto do harness servido no momento da
medição (`_sha_release()` em `conferir.py`); na classe `verbo` com `--ref <rev>` é a
rev candidata materializada para medir, não o current. Abaixo da âncora, cada item
imprime `<marca> <nome>[ (desde <desde>)]` e, quando houver, o `motivo` numa linha
indentada por baixo.

## Exit codes

`resultado.agrega()` decide o exit pela LISTA inteira, pior caso primeiro:

- `0` — tudo `conforme`.
- `1` — há ao menos um `divergente` (divergente pesa mais que indeterminável: não
  conseguir olhar não pode mascarar uma divergência real).
- `5` — nenhum divergente, e ao menos um `indeterminavel`.

Isto é a fatia de `conferir` dentro da tabela geral de exit de `bin/release`
(0/1/2/3/4/5 — arq:0110 par.4): `2` (uso), `3` (dependência) e `4` (política) saem
ANTES de qualquer item existir — classe desconhecida, `--ref` sem rev válida,
git/docker fora do ar. Só depois que a classe resolveu e produziu itens é que o
exit vem de `agrega()`, restrito a 0/1/5.

## Classes: quem já usa o Veredito comum, e quem ainda não

**Servido** (`release conferir <classe>`):

- `servico`, `verbo`, `skill`, `procedencia`, `superficie` (`--caso conectores` e
  `--caso descricao`), `ferramental`, `front`, `pdp`, `alcance`, `card` — todas via
  `resultado.relatorio()`, o Veredito comum de ponta a ponta.
- `sessao`, `chapeu` — declaradas no docstring deste arquivo (mede tokens do pacote
  de abertura e o `chapeu.md` de camada C, as duas dependentes de um tokenizador
  ainda ausente) mas SEM `def conferir_sessao`/`def conferir_chapeu` nem despacho em
  `main()`: `release conferir sessao` ou `chapeu` cai hoje em "classe desconhecida"
  (exit 2), não no aviso dedicado que `CLASSES_ABERTAS` dá às classes
  conhecidas-sem-implementação (`canal`, `casco`) — ausência que este README declara
  porque o próprio código ainda não a registra lá. Vale notar também que o
  docstring descreve `sessao` como "medição, não veredito" por desenho: mesmo
  implementada, pode não vir a adotar o Veredito de 3 estados.

**Bancada** (`bin/conferir`, fora de `release conferir`):

- `repo` (com `--staged`) e `arranque` (com `--staged`) — Veredito comum.
- `commit` — usa o VOCABULÁRIO do Veredito (estado/desde/motivo) para descrever a
  mensagem de commit em curso, mas por desenho NÃO passa pelo agregador
  `resultado.relatorio()`/`agrega()`: o exit vem de uma lógica própria ("recusas") e
  fica em 0 mesmo com veredito indeterminável — ver o comentário junto de
  `conferir_commit` no fonte. Declarado, não esquecido.
- `existe` — ainda NÃO usa o Veredito comum. Tem seu próprio par
  existe/não-existe (não o vocabulário de 3 estados), com helpers locais
  (`sai()`/`indeterminavel()` dentro da função) e exit 0/1/5 (5 para
  indeterminável, alinhado à régua geral desde o card #3142 passo 7) — mas por
  fora de `resultado.Veredito`. O docstring da própria função ainda diz "2
  indeterminavel", desatualizado frente ao 5 que o código de fato devolve hoje.

## Ver também

Isto é referência técnica do instrumento — o que cada classe mede e como o
resultado se lê. Para "qual classe olhar pra que pergunta" (produção fora do ar?
verbo sem dono? sessão sem paridade?), veja `guia/conferir-e-reportar.md` em
platafirma-casa.
