# caderno — chapéu harness

O que continua verdadeiro depois que o assunto morre, e que a próxima fita pagaria
para re-derivar. Não entra: fato de negócio (card/commit/wiki), estado de runtime,
decisão de outra cadeira, o que vale para toda cadeira.

## A régua de entrada da abertura é IMPEDIMENTO, e ela é escassa

Camada A carrega o que, sem ato, deixa o estado como está. Hoje só a mesa passa.
Coação ("sou forçado a ler isto?") decide se a **peça** entra; impedimento decide
se o **item** entra na mesa — são níveis distintos, e trocar um pelo outro é o
erro que já produziu duas reincidências no mesmo ponto (fila na abertura).

Corolário que custa caro para redescobrir: **saliência não é ato.** Uma régua que
proíbe abrir a caixa não neutraliza um envelope injetado na janela — a proibição
passa a competir com o item mais concreto do pacote. Contagem nua tem o mesmo
defeito em forma diminuída, e foi por ela que o defeito voltou.

## Peça servida ≠ peça contada

O que o servidor acrescenta ao pacote depois do montador não entra em
`pacote.tokens` — viaja na janela sem teto e sem dono, e nenhuma conferência de
forma o pega. Medido em 17/08: as peças somavam exatos 7.188, o número declarado,
enquanto o envelope da fila carregava 871 tokens fora da conta.

Verificação que funciona: somar os `tokens` das peças e comparar com
`pacote.tokens`. Bateu exato, o que sobra na janela está fora da contabilidade.

## Prova de mudança em código de abertura, quando não há gate

A suíte de `controle/tests` não roda em CI e está vermelha; não segura mudança
nenhuma (#216). Enquanto for assim, a prova de uma mudança no montador ou no
server é manual e tem quatro passos, nesta ordem:

1. `py_compile` no arquivo tocado.
2. Rodar `bin/monta-sessao <cadeira> --json --sem-atualizar` nas quatro classes:
   uma cadeira comum, TI, dados e **fábrica** — a fábrica é o único caminho
   `fora_do_quadro` e tem podas próprias que nenhuma outra exercita.
3. Boot-check do módulo com o env real (`. ~/.config/ops/env`) antes de reiniciar
   o serviço. Compilar não é subir: o import roda no boot, não no compile.
4. Só então `systemctl --user restart ops-mcp`, e confirmar pela **tool**, não pelo
   verbo — é a superfície do dono que precisa provar, e ela é a que estou usando.

## Remover comportamento sem remover o mecanismo é convite a reincidência

Ao tirar uma peça do pacote, o helper que a produzia vai junto. Mecanismo vivo e
não chamado é o que permite que a mesma decisão volte como "só a contagem" seis
meses depois — e a peça de antirreabertura não alcança código, só decisão.

## Onde o montador esconde ramo

`de_abertura()` tem um ramo `fora_do_quadro` que poda e substitui peças por nome
(`org` vira mapa de alias, e havia um caso nominal de `fila-status`). Mudança no
catálogo que não olhe esse ramo passa verde nas cadeiras comuns e quebra só na
fábrica.

## Falha declarada precisa de dois papéis, não de um

Quem levanta e quem declara são camadas diferentes, e colapsá-las estraga as duas.
A peça que fala com a fonte **levanta** — é o disjuntor que precisa da exceção para
contar falha. A camada que monta o retorno **declara** — é o consumidor que precisa
de `causa` legível em vez de stack. Adaptador que já devolve envelope de falha deixa
o disjuntor cego; envelope que propaga exceção devolve ao modelo o erro que ele não
sabe corrigir.

## O valor honesto do instrumento desligado tem de ser um CAMPO

Componente sem coleção de teste não pode servir o rótulo bom. Para isso valer, o
"ainda não tenho régua" mora num campo do componente (`tem_gold`), nunca num
comentário nem no julgamento de quem lê: campo troca de valor no commit que liga o
instrumento, comentário não. Vale além do RAG — é a forma de qualquer peça que
gradua resultado antes de ter com que graduar.

## Campo de contrato pode ser derivado, e é assim que se evita a segunda verdade

Quando o contrato publicado pede um escalar e o dado real é uma lista, a saída é
manter o escalar como **propriedade calculada** da lista, não como campo redigido em
paralelo. Dois campos que descrevem o mesmo fato divergem no primeiro caminho que
atualiza um só, e o teste que pegaria isso é o que ninguém escreve.

## Suíte de fonte externa em dois níveis, e o skip declarado

Contrato com cliente falso roda sempre e julga o que a peça PRODUZ. Conformidade
contra a fonte real julga se ela bate com o verbo humano sobre o mesmo estado, e é
pulada **com motivo impresso** quando a fonte não responde. Pular declarando é o
oposto de mascarar: o motivo aparece na saída e vira sintoma, enquanto `xfail`
apaga a diferença entre "não medi" e "medi e passou".

## Carimbo que cobre uma metade da fonte é pior que carimbo ausente

Fonte com dois substratos precisa de carimbo que some os dois. Carimbo que lê só um
deles fica CONSTANTE quando o outro é o que muda — e constante é indistinguível de
"nada mudou". Com o carimbo dentro da chave de cache, isso serve estado velho para
sempre, sem sintoma. Metade que não responde declara `?`: não saber é informação, e
fingir que não mudou não é.

## Gabarito de gold não se carimba com uma segunda leitura

A versão que congela o gold é a da busca que gerou os casos, não a de uma chamada
posterior ao carimbo. As duas divergem por desenho quando o carimbo é por recorte
(por stream, por caixa, por partição) e a segunda chamada vem sem o recorte. Gold com
versão falsa faz duas coleções diferentes parecerem a mesma — e é exatamente a
comparação que o gold existe para tornar possível.

## Teste que mede a bancada passa por motivo errado

Dois modos, e os dois se corrigem por injeção: depender da AUSÊNCIA de uma biblioteca
para simular substrato caído (volta a falhar no dia em que alguém a instala), e ler
variável de ambiente que o construtor usa como default (mede quem rodou, não a peça).
O sintoma é o mesmo nos dois: verde que não prova nada e vermelho que não acusa nada.

## Suíte vermelha por gabarito velho não é suíte vermelha por defeito

Quando a política muda por ato, o teste que a codificava reprova sem que o mecanismo
tenha mudado. Antes de tratar como risco, achar o commit que mudou a regra: se o
mecanismo (fail-closed, negativa total, trilha) segue intacto, o que envelheceu foi o
gabarito. A emenda mantém a régua e troca o PAR que a exercita — apagar o teste
perderia a régua junto com o exemplo.
