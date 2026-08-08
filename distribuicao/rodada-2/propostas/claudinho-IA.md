## relevancia-graduada
rotulo: Relevância graduada
natureza: modelo
estatuto: doutrinario
definicao: Nem todo acerto vale igual: num resultado de busca, o documento que responde a pergunta inteira vale mais que o que tangencia o assunto. A relevância graduada mede um sistema de busca tratando isso como grau — cada resultado entra com um valor conforme quanto responde, e esse valor pesa menos quanto mais embaixo ele aparece na lista.

A soma desses valores, dividida pela soma da melhor ordem possível, dá uma nota entre 0 e 1. Contar apenas acerto e erro esconde duas coisas que essa nota mostra: quem põe o resultado excelente em quinto perde para quem o põe em primeiro, e quem enche as primeiras posições de resultados apenas aceitáveis não empata com quem acertou em cheio.
obras-ancora: a06bee67-eae0-48d1-a962-459e307d9e2e, 9841c613-c9d6-4dda-b283-775f25224789
caso-falseador: cenário em que juízos graduados são reprodutíveis entre juízes e, ainda assim, a ordenação de sistemas pela métrica graduada nunca diverge da ordenação pela binária — o grau não acrescentaria poder de decisão.
pai-proposto:
substitui:

## recuperacao-densa
rotulo: Recuperação densa
natureza: modelo
estatuto: doutrinario
definicao: Busca por significado em vez de por palavra: a pergunta e cada documento viram uma lista de números que funciona como coordenada, e devolve-se o que caiu perto da pergunta. Como cada documento é convertido sozinho, sem saber que pergunta virá, dá para converter tudo de antemão e guardar — na hora da busca só se procura o vizinho mais próximo, o que é rápido mesmo com milhões de itens.

O preço é a comparação grosseira, feita entre dois pontos já fechados. Existe a alternativa de ler pergunta e documento juntos, que casa muito melhor e é inviável como busca, porque exigiria reler o acervo inteiro a cada pergunta. Por isso a leitura conjunta costuma entrar depois, sobre os poucos candidatos que a busca por vizinhança trouxe.
obras-ancora: 02b2fdcb-bed3-490f-a0dd-2b59653140bb, 79ceb118-2e56-415c-81c4-9194f1f5cdd0, d699cba8-10c9-42d8-b71f-4a7c1ea317f6
caso-falseador: sistema que codifica consulta e documento conjuntamente e mesmo assim serve busca sobre índice pré-computado sem aproximação — quebraria o vínculo entre independência de codificação e pré-computação.
pai-proposto: recuperacao-semantica
substitui:

## interacao-tardia
rotulo: Interação tardia
natureza: modelo
estatuto: doutrinario
definicao: Uma pergunta com dois assuntos — "multa de trânsito em veículo de aluguel" — vira um ponto só quando é comprimida em uma lista de números, e esse ponto cai na média entre os dois assuntos, um lugar onde não existe documento nenhum. A interação tardia evita a média: cada palavra da pergunta e cada palavra do documento vira o seu próprio ponto, e o encontro entre os dois é deixado para o fim.

Cada palavra da pergunta procura a palavra do documento mais próxima dela, e o documento fica com a soma desses melhores encontros. Assim "multa" casa com "multa" e "aluguel" com "locação" ao mesmo tempo, sem um borrar o outro; os pontos do documento continuam calculados de antemão, então a busca segue rápida. O custo é espaço: guardar um ponto por palavra ocupa cerca de dez vezes mais que guardar um por documento.
obras-ancora: 8488499a-032f-45e9-aa57-cc00062bf04a, 0abce3d7-d52a-4857-98e1-55f740854336
caso-falseador: modelo de vetor único que iguale a qualidade do casamento termo-a-termo fino sem o custo adicional de índice — o trade-off que define a variante desapareceria.
pai-proposto: recuperacao-densa
substitui:

## ranqueamento-multiestagio
rotulo: Ranqueamento multiestágio
natureza: modelo
estatuto: doutrinario
definicao: Busca feita em etapas, como peneira: a primeira passa por todo o acervo e é barata e grosseira, separando algumas centenas de candidatos; só sobre esses roda a etapa cara, que ordena com cuidado. O custo alto é pago por poucos itens em vez de por milhões.

A consequência decide projeto: o que a primeira etapa não pescou está perdido. Nenhuma etapa seguinte inventa um documento que não recebeu — melhorar o reordenador não conserta o que ficou fora da peneira. Por isso a primeira etapa se ajusta para não deixar escapar, e não para acertar em cheio; acertar em cheio é serviço da última.
obras-ancora: d699cba8-10c9-42d8-b71f-4a7c1ea317f6, 845f6353-b837-42e1-b04b-5b684776cf02, 5060852e-4f9e-40fc-8712-61c567e4651a
caso-falseador: pipeline em que aumentar a precisão dos estágios tardios compense, no resultado final, relevância ausente do pool do primeiro estágio.
pai-proposto:
substitui:

## quando-cabe-um-agente
rotulo: Quando cabe um agente
natureza: modelo
estatuto: doutrinario
definicao: Antes de montar um sistema com IA, uma pergunta decide a forma dele: dá para escrever de antemão os passos que ele vai dar? Se dá — ler a nota fiscal, conferir contra a tabela, emitir o aviso —, o certo é um roteiro fixo, em que cada passo é um pedaço testável e barato. Se não dá, porque o passo seguinte depende do que aparecer no anterior, entra o agente, que decide o próximo passo a cada volta.

O agente custa mais por tarefa, erra de formas que o roteiro não erra e é mais difícil de investigar, porque cada execução segue um caminho diferente. Em troca, aguenta o caso que ninguém mapeou. Escolher agente onde o roteiro daria conta é pagar essa conta sem precisar.
obras-ancora: 119f1289-e99c-410d-9320-29bf3cd1ea06, c517ca62-5d1d-4ac8-840a-8dc0bfecfb2a
caso-falseador: tarefa de subpassos imprevisíveis resolvida consistentemente melhor por fluxo fixo do que por loop, a custo comparável.
pai-proposto:
substitui:

## isolamento-de-contexto-por-delegacao
rotulo: Isolamento de contexto por delegação
natureza: processo
estatuto: doutrinario
definicao: Todo modelo tem um limite de quanto texto cabe numa conversa, e uma investigação longa — abrir vinte arquivos para responder uma pergunta — enche esse limite com material que não é a resposta. A saída é entregar a investigação a uma segunda instância, que gasta o próprio limite lendo tudo e devolve só o que achou.

O motivo é contabilidade, não competência: quem recebe a tarefa não precisa saber mais que quem delegou, precisa ter espaço próprio para queimar. A conta só fecha se o que volta for muito menor do que foi lido. Quando quase tudo que se leu importa na resposta, dividir custa mais do que rende, porque o material acaba voltando inteiro.
obras-ancora: f56aba50-8ded-412a-b3e0-3394de24c711, 21a3489b-bad2-406c-92fd-99c697250220, 42804aeb-ad42-40cc-b55b-febc38f7f037
caso-falseador: delegação de exploração pesada em que o retorno do subagente consome no orquestrador tanto quanto a exploração consumiria — o isolamento não pagaria o custo de coordenação.
pai-proposto: orquestracao-multi-agente
substitui:

## transporte-de-estado-entre-sessoes
rotulo: Transporte de estado entre sessões
natureza: processo
estatuto: doutrinario
definicao: Um trabalho que não cabe numa conversa só precisa continuar em outra, e a seguinte começa sem lembrar nada da anterior. É uma obra tocada por turnos em que nenhum turno conversa com o próximo: chega adiante apenas o que ficou escrito em lugar durável — lista de pendências, diário de bordo, o próprio código já salvo.

A regra prática é dura: o que não foi escrito não existe para quem vem depois. Isso inclui o que se perdeu quando a conversa foi resumida para caber. Decisão tomada e não anotada volta a ser tomada, às vezes ao contrário da primeira vez — por isso escrever o estado é parte da tarefa, e não relatório dela.
obras-ancora: 4ee66aba-abb1-4f3b-a2ff-c4d0b0c4b773, 392edecc-5cd3-4e7a-a23e-63f584558171, 08c18181-e019-4593-a37d-35ee7515aedd
caso-falseador: sessão sucessora recuperando consistentemente estado que nenhuma sessão anterior inscreveu em artefato acessível.
pai-proposto:
substitui:

## degradacao-diferencial-sob-compressao
rotulo: Degradação diferencial sob compressão
natureza: fenomeno
estatuto: natural
definicao: Modelos são encolhidos para caber em máquina menor, por exemplo guardando cada número com menos casas. O encolhimento tem preço, e o preço não se distribui por igual: responder uma pergunta isolada quase não piora, enquanto tarefa de muitos passos encadeados — chamar uma ferramenta, ler o retorno, decidir o passo seguinte — piora bastante.

O erro comum é medir a versão encolhida por um teste de pergunta única, ver empate com a original e concluir que o encolhimento saiu de graça. Saiu de graça naquilo que foi medido. O efeito aparece na tarefa longa, e cada modelo degrada de um jeito próprio, o que impede transportar a medida de um para outro.
obras-ancora: 54b45e4b-4d81-4de7-ab48-cef80dec8679, 7b2be448-a27f-4e93-a47e-be74221e3183
caso-falseador: compressões variadas, em modelos variados, degradando benchmark de turno único e capacidade agêntica multi-turno nas mesmas proporções.
pai-proposto:
substitui:

## confundimento-de-ambiente-em-avaliacao
rotulo: Confundimento de ambiente em avaliação
natureza: fenomeno
estatuto: natural
definicao: Quando se testa de ponta a ponta um sistema que usa IA, o número que sai não mede só o modelo. Mede também a máquina, a rede, a fila do servidor e a versão do programa que orquestra tudo — e essas coisas variam sozinhas, a ponto de o mesmo teste dar resultado diferente conforme a hora do dia.

Daí a consequência: diferença entre dois testes não autoriza, sozinha, a frase "o modelo piorou". Para dizer isso é preciso ter rodado os dois no mesmo ambiente, ou ter medido antes quanto o ambiente sozinho faz o número oscilar. Sem isso, culpar o modelo é palpite — e é o palpite mais fácil, porque o modelo é a única peça que se anuncia.
obras-ancora: 2c83db6a-7c2c-4d3a-8aa6-78a9f5f1019f, 4dbdb24e-b0dc-476b-a6e3-6ea77993d5bc
caso-falseador: escores de avaliação agêntica estáveis sob variação deliberada e ampla de infraestrutura — a variância de ambiente seria desprezível e o escore único bastaria.
pai-proposto:
substitui:

## mediacao-do-loop-agentico
rotulo: Mediação do loop agêntico
natureza: modelo
estatuto: doutrinario
definicao: Um programa que executa ações sozinho — mexer em arquivo, rodar comando, chamar serviço — precisa de algum ponto em que alguém, ou alguma coisa, diga "pode". Há três formas: pedir aprovação humana a cada ação; deixar uma regra automática revisar cada ação e barrar o que sai do combinado; ou dar liberdade dentro de uma cerca fechada de antemão, em que só existe o que ele tem direito de tocar.

A escolha troca incômodo por estrago possível, e traz uma armadilha. Pedir aprovação a cada passo parece a opção mais segura, mas na décima janela a pessoa aprova sem ler: a frequência do pedido destrói a vigilância que o justificava. Quem escolhe essa forma tem que contar com aprovação distraída, não com atenção constante.
obras-ancora: 680b1e1d-ae7c-4570-a18a-9da45b30d568, a3c90b5b-b359-4216-b6a3-a36c06ad22a9, 21a3489b-bad2-406c-92fd-99c697250220
caso-falseador: aprovação humana por ação mantendo vigilância efetiva constante ao longo de sessões longas — a fadiga de aprovação não existiria e o trade-off colapsaria.
pai-proposto:
substitui:
