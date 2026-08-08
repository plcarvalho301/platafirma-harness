# Propostas rodada 2 — claudinho-conhecimento

## registro-de-decisao
rotulo: Registro de decisão
natureza: modelo
estatuto: doutrinario
definicao: Uma equipe encontra no sistema uma regra esquisita e ninguém sabe por que ela está ali: quem decidiu já saiu, e o que sobrou foi a regra sem o motivo. O registro de decisão é o documento curto e datado que se escreve na hora da escolha, guardando quatro coisas — o que se decidiu, o que estava acontecendo que obrigou a decidir, o que mais se cogitou, e por que se preferiu esta saída.
  Guardar o motivo é o que permite reabrir a decisão depois sem chutar. Quem chega anos mais tarde consegue ver se as circunstâncias que justificaram a escolha ainda valem e, não valendo, mudar sabendo o que está trocando. Sem o motivo escrito sobram duas saídas ruins: obedecer sem entender, ou desfazer sem saber o que se perde junto.
obras-ancora: 69bcfac2-af6c-4f52-b60c-f23470aaa10b, 1cfaaec6-f92e-429a-a647-2062bbbcc489, 70f81706-ef82-4655-83aa-bade4319dab4
caso-falseador: Um registro sem contexto nem alternativas que ainda assim permitisse a um recém-chegado reavaliar a decisão nas condições em que foi tomada.
pai-proposto:
substitui:

## contexto-delimitado
rotulo: Contexto delimitado
natureza: modelo
estatuto: doutrinario
definicao: A mesma palavra significa coisas diferentes em partes diferentes de uma organização, e isso não é confusão a ser corrigida: para o time de vendas, "cliente" é quem pode comprar; para o financeiro, é quem tem contrato ativo. O contexto delimitado é a fronteira declarada dentro da qual cada palavra tem um significado só.
  Declarar a fronteira decide o que fazer quando duas definições divergem. Dentro da mesma fronteira, divergência é defeito e alguém tem que ceder. Entre fronteiras diferentes, não há defeito nenhum — o que se constrói é a tradução de um lado para o outro, e tentar unificar destrói informação dos dois lados.
obras-ancora: 3cd24cc4-ad43-4bb0-b492-e9254689faa0, 778bfb3f-ba6e-42bd-b3c5-5fc193fea4f0, 937af706-a6f2-4a8a-98e8-a3c660bfac0a
caso-falseador: Dois modelos com termos homônimos de réguas incompatíveis convivendo no mesmo contexto sem produzir inconsistência.
pai-proposto:
substitui:

## criterio-de-identidade
rotulo: Critério de identidade
natureza: modelo
estatuto: doutrinario
definicao: Duas fichas com o mesmo nome: é a mesma pessoa ou são duas? A resposta não sai do bom senso, sai de uma regra escolhida antes — mesmo CPF, digamos. Essa regra é o critério de identidade: o que decide quando dois registros falam do mesmo indivíduo, e quanto esse indivíduo pode mudar continuando a ser ele.
  A regra vem sempre da categoria mais funda a que a coisa pertence: pessoa, nunca "cliente". Daí uma consequência prática que pega muito modelo de dados: as categorias que alguém pode largar sem deixar de existir — cliente, paciente, fornecedor — não podem ficar acima das que nunca se larga — pessoa, empresa. Invertido, o modelo passa a exigir que alguém deixe de ser gente ao cancelar o contrato.
obras-ancora: 9ae06d4e-883b-40a1-a1cb-8f195f1cab59, 0e8da498-1e6b-4565-a74a-49e6d92bfcd3
caso-falseador: Uma classe sem critério de identidade próprio cujas instâncias ainda assim pudessem ser contadas e re-identificadas de modo determinado.
pai-proposto:
substitui:

## custo-da-expressividade
rotulo: Custo da expressividade
natureza: fenomeno
estatuto: natural
definicao: Quanto mais coisas uma linguagem formal deixa você afirmar, mais caro fica para o computador calcular o que essas afirmações implicam. Passado certo ponto, a conta não fecha em tempo útil: a máquina roda por horas, ou não termina.
  Por isso as linguagens usadas para escrever ontologia vêm em versões deliberadamente aparadas, cada uma abrindo mão de um tipo de afirmação em troca de resposta rápida e garantida. Escolher uma dessas versões é pagar o preço na frente: o que ela não deixa dizer fica proibido de escrever, e o que se ganha em troca é a certeza de que toda pergunta terá resposta em tempo previsível.
obras-ancora: d9e308e6-34b6-4c78-9a9f-7aae88349d29, 02d24cf3-de18-45de-88a1-1bd5e247211d
caso-falseador: Um construtor que aumentasse estritamente o poder expressivo da linguagem sem alterar a complexidade do raciocínio em caso algum.
pai-proposto:
substitui:

## vocabulario-controlado
rotulo: Vocabulário controlado
natureza: modelo
estatuto: doutrinario
definicao: Quem procura por "demissão", quem procura por "desligamento" e quem procura por "rescisão" deveria achar as mesmas coisas. O vocabulário controlado é a lista fechada de termos que garante isso: cada assunto tem um termo oficial, os sinônimos remetem a ele em vez de virarem entradas próprias, e palavras iguais com sentidos diferentes ganham um qualificador para não se misturarem.
  O trabalho é decidir, para cada palavra que aparece, uma de três coisas: vira termo oficial, vira apelido que aponta para um termo já existente, ou fica de fora. As ligações entre termos também são poucas de propósito — o mesmo que, mais amplo que, mais estreito que, relacionado a. Permitir mais tipos de ligação deixa a lista impossível de manter coerente conforme ela cresce.
obras-ancora: acef84ce-9ddc-4b46-af9b-c5fe4d2596ed, c86ee1f8-6e5b-4982-975a-685190a7d75d, 6b74e179-f3ea-47bf-9d90-1443bb701dc5
caso-falseador: Indexação em linguagem livre, sem controle de sinônimos e homógrafos, produzindo recuperação tão consistente quanto a do vocabulário.
pai-proposto:
substitui:

## descricao-multinivel
rotulo: Descrição multinível
natureza: processo
estatuto: instituido
definicao: Duzentas caixas de documentos de um mesmo órgão não se descrevem caixa por caixa, cada uma do zero. Descreve-se primeiro o conjunto inteiro — quem produziu, em que período, para quê —, depois cada série dentro dele, depois cada dossiê, e assim por diante, do maior para o menor.
  A regra que faz isso funcionar é registrar cada informação uma vez só, no nível mais alto em que ela é verdadeira, e nunca repeti-la abaixo. Sem isso acontece um dos dois estragos: ou a mesma informação é copiada milhares de vezes e passa a divergir na primeira correção, ou o documento isolado chega a quem consulta sem o contexto que explica o que ele é.
obras-ancora: 8a6d157a-8531-4167-a15a-55614b3b8469, fae2391b-bc6b-4f69-8c58-1660d924f6e0, aa385a7e-b92e-4f20-a693-665356ab8187
caso-falseador: Um conjunto documental cuja recuperação e prova de contexto nada perdessem com descrição plana e redundante.
pai-proposto:
substitui:

## documento-de-arquivo
rotulo: Documento de arquivo
natureza: modelo
estatuto: instituido
definicao: Um contrato assinado e um livro sobre contratos são coisas diferentes, e a diferença não está no papel. Documento de arquivo é o que foi produzido ou recebido no meio de uma atividade — o contrato, o ofício, a folha de ponto —, e o que o torna prova é justamente o vínculo com essa atividade: quem fez, quando, no curso de quê, junto de quais outros documentos.
  Daí uma consequência que costuma surpreender: tirar o documento do conjunto onde ele nasceu destrói parte do seu valor. Um livro continua o mesmo livro em qualquer estante, porque nele o que vale é o conteúdo. Um documento de arquivo solto do processo perde a capacidade de provar, mesmo com todas as palavras ainda legíveis.
obras-ancora: e6cb866c-f0ba-442d-8b0e-d4764b114346, 0d9fc4f8-c022-44e3-9979-d66e0ccbdbc0
caso-falseador: Documento que preservasse valor probatório pleno depois de removido do conjunto e do contexto em que foi produzido.
pai-proposto:
substitui:

## conhecimento-tacito
rotulo: Conhecimento tácito
natureza: disposicao
estatuto: doutrinario
definicao: Um servidor com trinta anos de casa sabe qual pedido vai emperrar só de bater o olho, e não consegue explicar como sabe. Isso é conhecimento tácito: o que a pessoa usa para agir bem sem conseguir enunciar por inteiro, porque aprendeu fazendo, errando e vendo alguém mais velho fazer.
  A consequência para quem monta formação é dura: parte do que se quer passar adiante não cabe em manual. Escrever ajuda e sempre perde alguma coisa no caminho; o resto só atravessa por convivência, acompanhamento e prática ao lado de quem já sabe. Tratar tudo como escrevível é a origem do treinamento que todo mundo faz e ninguém aprende.
obras-ancora: 3a0967a6-b9eb-4759-b9c1-3fe17ea59f91, c45238d2-88ea-406c-8d2e-e8e4f86dab41
caso-falseador: Uma competência plenamente adquirível por leitura de manual, sem prática, com desempenho igual ao do praticante.
pai-proposto:
substitui:

## pratica-de-recuperacao
rotulo: Prática de recuperação
natureza: processo
estatuto: doutrinario
definicao: Reler a apostila dá a sensação de estar aprendendo e é uma das formas mais fracas de estudar. Aprende-se mais fechando o material e tentando lembrar: o esforço de puxar da memória, mesmo errando, é o que fixa. Reconhecer um trecho já visto engana, porque parece domínio e não é.
  Duas consequências para o desenho de um exercício. A primeira: ele tem que ter a forma em que a pessoa vai precisar se sair depois — se o trabalho é redigir um parecer, o exercício é redigir, não marcar a alternativa certa. A segunda: repetir espalhado no tempo, voltando quando já se começou a esquecer, custa mais no momento e rende mais no fim do que estudar tudo de uma vez.
obras-ancora: 9ac96d9b-f77f-4bce-9bd6-6ce78f65dded, 09bb00ad-cf1a-4412-875a-1f087c4fef07
caso-falseador: Aprendizes que releem sem se testar retendo e transferindo, sistematicamente, tanto quanto os que praticam recuperação.
pai-proposto:
substitui:

## evento-como-entidade
rotulo: Evento como entidade
natureza: modelo
estatuto: doutrinario
definicao: Numa ficha de livro é comum existir um campo "data de catalogação". Funciona até alguém perguntar quem catalogou, se houve uma segunda catalogação e o que ela mudou em relação à primeira — perguntas que um campo de data não responde. Tratar o evento como entidade é dar ficha própria ao acontecimento: a catalogação vira um registro com responsável, início, fim e etapas, em vez de ser um campo do livro.
  O que decide entre os dois é o tipo de pergunta que se pretende responder. Bastando saber quando aconteceu, o campo de data resolve e criar ficha só encarece. Sendo preciso saber quem participou, separar o acontecimento em etapas, ou amarrar um acontecimento a outro que veio antes, o campo não sustenta e o evento precisa existir por conta própria.
obras-ancora: 89fa2571-7887-4225-bf27-67971febac65, 8d32d598-b87c-4d8b-aa5b-bb3f6dcdb691
caso-falseador: Um domínio em que todo requisito sobre atos — agentes, tempo, partes — fosse expressável por atributos das entidades permanentes sem perda.
pai-proposto:
substitui:
