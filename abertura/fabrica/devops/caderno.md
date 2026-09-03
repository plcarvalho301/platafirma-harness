# caderno — fabrica / devops

Durável: continua verdadeiro depois que o assunto morrer, e re-derivar custaria caro.

## Teste que nasce verde não prova nada até o mutante derrubá-lo

Teste escrito DEPOIS da correção nasce verde por construção: passa tanto com o furo
fechado quanto com ele aberto, se a asserção não morde o ponto exato. Entregar assim é
entregar a aparência da trava, e a regressão volta com a suíte inteira verde.

A régua: antes de abrir o MR, **reponha o furo** e rode. O teste novo tem de ficar
VERMELHO. Só então ele vale como trava. Reponha e restaure no mesmo giro, com backup do
arquivo — a janela em que a árvore está mutada é o único risco, e ela dura segundos.

Medido no #2945 (reancorar voto por `sessao_id`, 09/2026): 6 casos novos, todos verdes.
Repondo os dois furos — o fallback temporal cego e o `sessao_id` que não era repassado —
**5 dos 6 vermelharam**. O sexto era verde vazio e teria ido no MR como trava que não
trava. Sem o mutante, ninguém veria a diferença entre os dois grupos.

Corolário do mesmo princípio, e o caso que engana mais: **falha anterior se PROVA, não se
alega**. Suíte que já vem vermelha tenta o atalho "essas falhas não são minhas". A prova
é o contrafactual: `git stash` das mudanças, rodar em HEAD, ver as mesmas falhas com os
mesmos nomes, `git stash pop`. No #2945 eram 6 (`test_sidecar` 2, `test_carga_acervo` 2,
`test_nomes` 1, `test_planilha` 1) — e só depois de medidas em HEAD é que couberam no
corpo do MR como dívida de outra frente.

O que os dois casos têm em comum: um resultado de teste é uma afirmação sobre uma
DIFERENÇA (com o bug vs sem, com minha mudança vs sem), e diferença não se lê num estado
só. Rodar uma vez e reportar a cor é opinião; rodar os dois lados é medida.

## Apontamento de linha se declara no MR, não se resolve calado

Despacho de outra cadeira fecha o desenho, mas quem executa é quem encosta no código — e
às vezes a letra do desenho, aplicada ao pé, produz regressão que o desenho não pediu.
Quando isso aparece, não são dois caminhos (obedecer cegamente ou reabrir o desenho): é
um terceiro. Implemente a leitura que preserva o comportamento, **isole a decisão num
bloco próprio do corpo do MR**, com o motivo medido e o custo de reverter ("é uma linha").
A cadeira que desenhou decide na revisão, com o código na frente, em vez de decidir no
abstrato antes.

No #2945 a §2 mandava não descer ao fallback quando `sessao_id` não casasse. Ao pé da
letra, isso matava também a busca por `ordem_id` — porque a mesma mudança fazia `_votar`
herdar `PF_SESSAO`, e voto por `ordem_id` passaria a chegar com `sessao_id` preenchido sem
ninguém pedir. Cortar só o degrau CEGO e declarar o desvio custou um parágrafo; descobrir
a regressão depois do deploy teria custado o ciclo inteiro.
