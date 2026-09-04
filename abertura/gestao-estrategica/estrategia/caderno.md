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
- **`mesa anota <chapéu>` REESCREVE o slot inteiro, não acrescenta.** Em 04/09 apaguei a
  prosa da deriva golden↔rotas-chapeu ao anotar o conceito comunicacao-executiva no mesmo
  slot [rh]; restaurei do texto que a abertura tinha servido. O aviso da ferramenta só sai
  depois da sobrescrita. `mesa ver` antes, reincluir no stdin a prosa que fica; o que tem
  ato pendente vai em `mesa item <chapéu> --ato … --alvo …`, que é o que a abertura serve.
- **O ledger de `persona` fala nome canônico e gerência em prosa**, não slug: `persona
  dispensar dados "modelo de dados e schema"`, não `dados modelagem`. E recusa
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

## Comunicação executiva do dono à alta gestão do órgão

- **Num órgão em guerra aberta entre diretorias, o sponsor apadrinha regra impessoal, não
  peça de guerra.** A tese vai como pergunta que o decisor reconhece sem explicação («de
  quem é esse dado?»), nunca como veredito que aponta uma área — o veredito, mesmo certo,
  vira ataque a quem estará na mesa, e o decisor sabe disso. Medido em 04/09: propus slide
  explícito sobre o vibecoding alheio; o dono cortou com o contexto da guerra, e a própria
  NT já dizia «não é briga entre pessoas: é ausência da régua».
- **O ethos ("somos o expert; a TI é refém, não vilã") passa por caso concreto que termina
  na régua, nunca na diretoria.** Caso que termina numa área é ataque; caso que termina em
  "sem régua, sem dono" é prova de que se conhece o terreno.
- **Receptor sem repertório técnico: conclusão-primeiro só com o andaime mínimo.** A
  pirâmide (Minto) pressupõe que o leitor avalia a conclusão contra um modelo mental que
  já tem; sem modelo, a conclusão é viga com carga prematura — ou ele assina por
  deferência (não sobrevive a controle/auditoria) ou trava. Cura não é bottom-up
  exaustivo (ganho enterrado): é o pré-requisito que sustenta ESTA conclusão, na ordem
  em que ela precisa (sequenciamento-por-pre-requisito), com o "S" do SCQA dimensionado
  ao repertório do público, não ao do apresentador (curse of knowledge — Torres). Teste
  por afirmação: ele consegue dizer POR QUE isso é verdade, ou só que a gente disse?
- **A palavra que o decisor não tem é a que a casa mais usa.** "Domínio" (DDD, 8 obras no
  acervo) é jargão para o diretor; arq:0098 vale para fora ainda mais que para dentro — na
  primeira ocorrência, o nome comum ao lado: domínio (o assunto que tem um dono),
  Proprietário (quem responde pelo dado), ISP (a Política Mestra de Segurança). Medido em
  04/09: entreguei "mapa de domínios" sem tradução no mesmo turno em que escrevi o filtro
  da curse of knowledge. O teste não é "eu sei o que significa": é "ele saberia".
  Corrigido no mesmo dia pelo dono: traduzir NÃO é a cura quando o decisor vai OUVIR a
  palavra no trabalho seguinte — aí a palavra se ensina, num slide, ancorada no
  vocabulário que ele já tem (na casa: temática → iniciativa = domínio → plano de
  produção, com o mapa de domínios = lista de iniciativas com dono). Substituir esconde;
  ensinar habilita. Escolher entre os dois pelo que ele fará com a palavra depois.
- **O que o decisor não é: leitor da NT.** Documento técnico de 15 políticas é anexo que
  ele leva; a fala é o corte (5 slides, dez minutos até o pedido), e o pedido é o que ELE
  faz — pautar, apadrinhar, datas na mão.
