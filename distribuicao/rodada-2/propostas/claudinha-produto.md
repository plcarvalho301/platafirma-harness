# Propostas de conceito — claudinha-produto (rodada 2)

## affordance
rotulo: Affordance
natureza: disposicao
estatuto: natural
definicao: Um objeto sinaliza, pela própria forma, o que dá para fazer com ele: uma maçaneta vertical pede puxar, uma placa lisa pede empurrar. Affordance é essa relação entre o que o objeto permite e o que quem usa consegue fazer.
  O que produz veredito é que permitir e sinalizar são coisas separadas. A ação pode existir sem aparecer — a porta abre, mas nada indica para que lado — ou aparecer sem existir, como a maçaneta que convida a puxar numa porta trancada. Julgar uma tela é comparar as duas listas: o que ela deixa fazer e o que ela avisa que deixa.
obras-ancora: 282e3564-800f-48e7-9a59-d3a4127fda17, e4eb5dc4-70e2-4239-99eb-b52786ccbf6f
caso-falseador: Usuários novatos operando corretamente, de forma sistemática e sem instrução externa, ações que o artefato em nada sinaliza.
pai-proposto:
substitui:

## avaliacao-heuristica
rotulo: Avaliação heurística
natureza: processo
estatuto: doutrinario
definicao: Antes de chamar qualquer usuário, uma pessoa percorre a tela sozinha conferindo-a contra uma lista curta e fixa de perguntas: o sistema mostra em que estado está? dá para desfazer o que foi feito? usa as palavras de quem usa ou as do banco de dados? avisa antes de deixar errar? Avaliação heurística é essa inspeção contra lista.
  O ganho é que a reprovação sai com nome. Não é "não gostei desta tela", é "esta tela esconde o estado do sistema, aqui" — e quem construiu pode discordar do veredito, não do critério. O limite é igualmente claro: a lista pega violação de princípio, não pega o que só aparece quando gente de verdade tenta cumprir a tarefa.
obras-ancora: 34b52e04-32e3-467b-9b5d-bbb557f32c1f, 30f215b8-ced5-45f6-8102-1f42270ac289, 6c39dde2-5020-4688-b848-9e33119a6906
caso-falseador: Problemas graves de uso, encontrados depois em teste com usuário, que nenhuma inspeção contra a lista tinha como capturar — como padrão, não como exceção.
pai-proposto:
substitui:

## design-centrado-no-humano
rotulo: Design centrado no humano
natureza: processo
estatuto: instituido
definicao: Um sistema pode cumprir tudo que foi especificado e mesmo assim ser abandonado por quem deveria usá-lo, porque as pessoas, as tarefas e o lugar reais nunca foram olhados de perto. O design centrado no humano é o conjunto de exigências que fecha essa porta: entender antes quem usa, o que faz e onde; envolver essas pessoas durante o trabalho, não só no fim; submeter cada versão à avaliação de usuários, inclusive na hora de aceitar o produto pronto; e repetir o ciclo enquanto ainda houver dúvida sobre o uso.
  O que separa isso de "conversamos com uns usuários" é o registro: cada uma das quatro exigências deixa evidência datada, e quem confere é a evidência, não a boa intenção de quem fez. Vale igual para formulário de papel e atendimento de balcão — não é regra de aplicativo.
obras-ancora: 010e40c5-9911-4bb3-bf23-e771eea8bb70, 79e6c38d-168a-4e71-a301-a45f22f8f91f, be3803d2-2f8d-4c9f-89c2-9b4523edbc7e
caso-falseador: Processos que satisfazem as quatro condições produzindo sistemas rejeitados pelos usuários na mesma taxa que processos que as ignoram.
pai-proposto:
substitui:

## gap-desenho-realidade
rotulo: Gap desenho-realidade
natureza: fenomeno
estatuto: doutrinario
definicao: Todo sistema novo carrega uma imagem de como o mundo é: que dados existem, quem faz o quê, que equipamento tem na ponta, o que as pessoas ali valorizam. Quando essa imagem está longe do lugar onde o sistema vai ser instalado, ele fracassa mesmo bem construído — e a distância se mede uma dimensão de cada vez: informação, tecnologia, processos de trabalho, objetivos e valores, pessoal, gestão, demais recursos.
  Um telecentro projetado supondo energia estável, técnico morando perto e gente querendo internet, instalado onde falta as três coisas, já tem distância grande em quatro dimensões: o prognóstico é ruim antes da primeira linha de código. E só duas coisas mudam o prognóstico — aproximar o desenho da realidade, ou mexer na realidade para perto do desenho.
obras-ancora: 055bb041-99b4-438e-9ef3-c47b9f57f3bb, 01b7a7f5-a172-40cf-a714-a1bcaa7e0887, 69a02423-aeff-488e-8484-95d13428f821
caso-falseador: Projetos com gaps grandes e não reduzidos em várias dimensões sucedendo na mesma taxa que projetos com gaps pequenos.
pai-proposto:
substitui:

## entrevista-por-comportamento-passado
rotulo: Entrevista por comportamento passado
natureza: processo
estatuto: doutrinario
definicao: Perguntar "você usaria isso?" rende resposta educada e inútil: quase todo mundo diz que sim, e quase ninguém usa. Numa conversa de descoberta conta o que a pessoa já fez — a última vez que enfrentou o problema, o que ela fez naquele dia, quanto tempo ou dinheiro gastou — e o que ela se compromete a fazer agora: marcar a próxima conversa, apresentar um colega, pagar adiantado.
  Por isso a própria ideia entra tarde na conversa, ou não entra. Mencionada cedo, ela vira o assunto: o interlocutor passa a opinar sobre a ideia, em vez de contar a própria vida — que é a única coisa que ele sabe melhor do que quem pergunta.
obras-ancora: eabfd878-771f-40d2-b32a-1ceb7868fad2, 567e3b24-9241-46de-a441-4ecc61f6246f, 39b473eb-0c70-4a66-a371-d9258970541b
caso-falseador: Opinião direta do entrevistado sobre a ideia predizendo o comportamento real de compra ou uso melhor que o relato de comportamento passado.
pai-proposto:
substitui:

## esquema-de-organizacao
rotulo: Esquema de organização
natureza: modelo
estatuto: doutrinario
definicao: Toda lista grande é arrumada por algum critério, e os critérios são de dois tipos. O exato — alfabético, por data, por lugar — põe cada item num só lugar e não deixa dúvida, mas só serve para quem já sabe o nome do que procura. O ambíguo — por assunto, por tarefa, por público — depende de julgamento, dois curadores arrumam diferente, e é o único que serve para quem sabe o problema e não sabe o nome.
  A escolha decide quem consegue encontrar. Num catálogo em ordem alfabética de título, quem quer "alguma coisa sobre contratar melhor" não acha nada; por assunto, acha, ao custo de o mesmo item caber em dois lugares. Coleção grande costuma precisar dos dois, e a decisão é qual deles é a porta de entrada.
obras-ancora: 7417496f-a949-4862-8398-f252caf58ae9, 30f215b8-ced5-45f6-8102-1f42270ac289
caso-falseador: Usuários que não sabem nomear o que procuram encontrando, em esquema exato, na mesma taxa que em esquema ambíguo bem construído.
pai-proposto:
substitui:

## fatiamento-por-jornada
rotulo: Fatiamento por jornada completa
natureza: processo
estatuto: doutrinario
definicao: Uma entrega parcial só vale se alguém conseguir chegar ao fim de alguma coisa com ela. Fatiar por jornada é recortar a próxima entrega como o menor pedaço que permite a uma pessoa começar uma tarefa e terminá-la — do momento em que ela precisa até o momento em que ela tem o que queria, ou desistiu por um caminho previsto.
  O recorte oposto é por camada: primeiro o banco de dados, depois a tela, depois o envio. Cada pedaço fica pronto e ninguém consegue fazer nada com nenhum, então não há o que testar com usuário nem o que pôr no ar. Por isso o aceite se escreve como o caminho inteiro, antes de construir: se ninguém completa nada, não é fatia.
obras-ancora: a8cf6e26-abfe-40cf-9838-167e1f00460f, 17af4452-44d9-46ab-b187-72b2349b7b3c
caso-falseador: Releases fatiados por camada técnica entregando valor verificável por usuário na mesma taxa que fatias de jornada completa.
pai-proposto:
substitui:

## resultado-sobre-entrega
rotulo: Resultado sobre entrega
natureza: modelo
estatuto: doutrinario
definicao: Entregar uma funcionalidade não é a mesma coisa que conseguir algo com ela. O resultado é a mudança de comportamento de gente de verdade — o cliente que passa a concluir a compra, o atendente que passa a resolver no primeiro contato — e é essa mudança que liga o que se constrói ao que a organização queria.
  Na prática a pergunta muda: sai "o que vamos construir neste trimestre?" e entra "quem vai passar a fazer o que de diferente, e como saberemos?". A pergunta nova admite resposta que não é software — mudar um texto, um preço, uma regra, um treinamento — e deixa visível a entrega que ficou pronta no prazo sem mudar o comportamento de ninguém, que pelo critério antigo passava por sucesso.
obras-ancora: c441aacc-2f04-4eed-b836-d5975a74d5c9, 52c6dbe4-41f1-445c-8c82-e2978b5b2c1a
caso-falseador: Entregas sem qualquer mudança de comportamento mensurável produzindo sistematicamente o resultado de negócio pretendido.
pai-proposto:
substitui:

## riscos-de-produto
rotulo: Riscos de produto
natureza: modelo
estatuto: doutrinario
definicao: Uma ideia de produto pode morrer por quatro motivos diferentes, e a evidência que afasta um não diz nada sobre os outros três: as pessoas não querem (valor); querem e não conseguem usar (usabilidade); dá vontade e não dá para construir no prazo e no custo (viabilidade técnica); serve ao usuário e não fecha para quem banca, por causa de jurídico, suporte, canal de venda ou orçamento (viabilidade de negócio).
  O erro comum é parar no primeiro: entrevistas entusiasmadas viram autorização para construir, e a coisa morre depois na usabilidade ou no jurídico. Por isso o critério é evidência coletada contra os quatro, e não a convicção de quem decide — que costuma ser mais firme justamente onde ninguém olhou.
obras-ancora: df1b01d4-a2c9-4350-8a1d-488538ab00e1, 39b473eb-0c70-4a66-a371-d9258970541b
caso-falseador: Produtos construídos sem evidência contra um dos quatro riscos falhando na mesma taxa dos que a coletaram.
pai-proposto: product-discovery
substitui:

## teste-de-usabilidade-informal
rotulo: Teste de usabilidade informal
natureza: processo
estatuto: doutrinario
definicao: Uma manhã por mês, três pessoas de fora tentam usar o que a equipe fez, falando em voz alta o que estão pensando, enquanto quem construiu assiste. É barato e não precisa de laboratório nem de recrutamento caprichado: problema grave aparece para quase qualquer pessoa que nunca viu aquela tela.
  O sucesso não é achar todos os problemas — é achar, a cada rodada, os poucos mais graves e sair da sala com o compromisso de consertá-los antes da próxima. Testar com trinta pessoas e conseguir consertar dois problemas rende menos que testar com três e consertar dois todo mês. Por isso a conversa depois do teste termina numa lista curta e combinada, não num relatório.
obras-ancora: c5e911b6-337a-4870-b241-51527584d899, 6cb845f0-7b24-4618-9531-39442e41588b
caso-falseador: Rodadas recorrentes de três participantes deixando sistematicamente de revelar os problemas mais graves que amostras grandes revelam.
pai-proposto:
substitui:
