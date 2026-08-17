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
