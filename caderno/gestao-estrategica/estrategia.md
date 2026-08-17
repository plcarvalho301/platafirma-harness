# caderno · gestao-estrategica · estrategia

Durável: continua verdadeiro depois que o assunto morrer, e a próxima fita pagaria para
re-derivar. Fato de negócio, estado de runtime e remit canônico NÃO entram.

## Armadilhas de ferramenta, medidas nesta cadeira

- **`tarefas criar` não tem `--titulo`.** O título é POSICIONAL. `tarefas criar --titulo "x"`
  falha com "opção desconhecida", e `tarefas criar --help` **cria um card chamado `--help`**
  (aconteceu em 17/08: card 203, cancelado). Chamar o verbo sem argumento nenhum é que
  mostra o uso.
- **`mesa fez <id>` esvazia por id, e id não é assunto.** Esvaziei dois itens não
  executados em 17/08 (#53 e #54) por tratar o id como se fosse o texto. `mesa ver` antes,
  sempre; esvaziar é irreversível pelo verbo (replanta com `mesa item`, com id novo).
- **O ledger de `persona` fala nome canônico e gerência em prosa**, não slug: `persona
  dispensar claudinho-dados "modelo de dados e schema"`, não `dados modelagem`. E recusa
  qualquer ato sobre quem nunca foi provido — colaborador externo sem cadeira no org chart
  não entra no ledger, e forçar o provimento para registrar um ato criaria o vínculo que a
  persona dele nega.
- **`fila enviar` exige `PF_CADEIRA` ou `--eu`**, e o erro só aparece depois de o
  pre-commit inteiro rodar. Num `git commit; fila enviar` encadeado, a falha do segundo
  não é visível no meio da saída do primeiro.

## Régua de leitura que esta cadeira erra por default

- **Régua de qualificação não é regra de competência.** `arq:0059` (capacidade é única na
  organização) qualifica decisão alheia; não diz quem decide. Ler régua de arquitetura como
  atribuição de território produziu três "sobreposições" falsas em 17/08. O teste: a régua
  melhora a decisão de quem já a tomava, ou tira a decisão dele?
- **Delta de token entre duas medições só vale com a composição do pacote ao lado.** Peça
  que ENTRA no catálogo entre as medições sobe o total de toda cadeira e inverte o sinal de
  quem não mexeu em nada (17/08: conduta-dono + antirreabertura = 2.211 em todas).
