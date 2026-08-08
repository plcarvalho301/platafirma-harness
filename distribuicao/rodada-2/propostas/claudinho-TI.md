# Propostas de conceitos — claudinho-TI (rodada 2)

## desempenho-de-entrega
rotulo: Desempenho de entrega de software
natureza: modelo
estatuto: doutrinario
definicao: Quatro medidas dizem se uma equipe entrega software bem: quanto tempo uma mudança leva do código pronto até o ar, com que frequência se publica, que fração das publicações quebra algo, e quanto tempo leva para consertar quando quebra. As duas primeiras medem velocidade; as duas últimas, estabilidade — e uma década de pesquisa mostra que as melhores equipes são boas nas quatro ao mesmo tempo: velocidade não se compra com quebra, nem estabilidade com lentidão. A medida olha o resultado do processo inteiro, não o esforço de cada etapa — medir esforço local premia gente ocupada, não software entregue.
obras-ancora: ac6ffd6c-935f-4f68-b22e-7585f87bdf1b, d87cf7a6-2e2c-4df6-a468-bad132a2cdc9, d4d60417-3306-4bbd-87fd-71f68fa83225, c88796df-1090-46c0-abb1-e2df40135ef5
caso-falseador: Um conjunto de equipes que, medido pelas quatro chaves, sustente por anos vazão de elite com estabilidade baixa (ou o inverso) mostraria que os pares não movem juntos e a régua estaria errada.
pai-proposto:
substitui:

## esteira-de-implantacao
rotulo: Esteira de implantação
natureza: processo
estatuto: doutrinario
definicao: Caminho automatizado que toda mudança de código percorre até estar pronta para publicação: testes rápidos primeiro, depois o pacote versionado, depois testes de aceitação num ambiente igual ao de produção. Cada etapa pode reprovar e devolver a mudança; o que atravessa tudo está pronto para o ar. O ponto é ser o caminho único: existindo um atalho manual por fora, a garantia da esteira vale zero, porque ninguém sabe o que entrou sem passar por ela.
obras-ancora: d1700fc7-f115-485a-84ab-7a5de5065ff7, ac6ffd6c-935f-4f68-b22e-7585f87bdf1b
caso-falseador: Uma organização em que mudanças rotineiramente entram em produção por caminho manual paralelo sem perda de desempenho de entrega falsearia a exigência do caminho único.
pai-proposto:
substitui:

## registro-de-decisao-arquitetural
rotulo: Registro de decisão arquitetural
natureza: modelo
estatuto: doutrinario
definicao: Documento de uma página que fixa uma decisão técnica importante: qual era a situação, o que se decidiu e o que isso custa daqui para frente. Escreve-se no momento da decisão e não se edita depois — mudou a decisão, escreve-se um registro novo que declara substituir o antigo, e o antigo fica. O que ele protege é o porquê: sem o registro, quem chega meses depois vê só a escolha, desfaz sem conhecer o motivo e paga o problema que a escolha original evitava.
obras-ancora: 69bcfac2-af6c-4f52-b60c-f23470aaa10b, d4ca606e-d882-474a-8425-638a9a1ab144, ea6739f1-d054-48b1-8558-2fde8c25429e
caso-falseador: Um repositório de decisões editadas em lugar de substituídas que ainda assim preserve, verificavelmente, a recuperação do racional original falsearia a exigência de imutabilidade.
pai-proposto:
substitui:

## servico-de-ti
rotulo: Serviço de TI
natureza: modelo
estatuto: doutrinario
definicao: Aquilo que uma área de TI entrega e que o cliente reconhece como valor por si — o e-mail que funciona, o sistema no ar — sem carregar o custo e o risco de fazer funcionar. O que existe por baixo (servidor, banco, rede) habilita a entrega mas não vale nada sozinho para o cliente: é componente, não serviço. Confundir os dois infla o catálogo com itens que ninguém contrataria, gera cobrança que o cliente não reconhece e impede priorizar o portfólio, porque tudo virou serviço.
obras-ancora: eb62b2c7-4bac-444a-8f80-2720248da7f9, 0934a1d3-3449-4deb-8280-8499200c960b, 1e06d3ee-cdf2-439a-a8a3-8599df02e926, 3034a632-9b42-4fe0-94f9-37079aa060e2
caso-falseador: Um cliente que contrate e valore diretamente um item que a régua classifica como mero componente (sem serviço acima) mostraria que o corte valor-para-cliente não separa os casos.
pai-proposto:
substitui:

## orcamento-de-erro
rotulo: Orçamento de erro
natureza: modelo
estatuto: doutrinario
definicao: A quantidade de falha que um serviço tem permissão de acumular num período, derivada da meta de confiabilidade prometida: prometeu 99,9% de sucesso no mês, o 0,1% restante é o orçamento — cerca de 43 minutos de indisponibilidade que podem ser gastos. As decisões do dia a dia saem do ritmo de gasto, não do incidente isolado: queimando rápido, congela-se mudança e prioriza-se estabilidade; sobrando orçamento, há espaço para arriscar. O alerta certo dispara quando o ritmo projetado esgota o orçamento antes do fim do período — cedo o bastante para agir, não depois da promessa quebrada.
obras-ancora: 6287cfc2-2638-4665-8d7f-0fa1425886f8, 2d8ad6b2-344f-42bf-b982-c04051129efa
caso-falseador: Um serviço governado por orçamento de erro em que alertas por queima projetada sistematicamente cheguem depois da violação do SLO (sem margem de ação) falsearia o mecanismo preditivo da régua.
pai-proposto:
substitui:

## falha-sistemica
rotulo: Falha sistêmica
natureza: fenomeno
estatuto: natural
definicao: Em sistema grande e cheio de proteções, o desastre nunca vem de um erro só: vem de várias falhas pequenas, cada uma inofensiva sozinha, que se alinham e atravessam as defesas juntas. Por isso a pergunta "qual foi a causa raiz?" engana — apontar uma causa única é escolha de quem analisa depois, não fato do acidente. A análise que ensina algo procura as condições que já estavam armadas antes, e o que segurou o sistema nas tantas vezes em que não caiu.
obras-ancora: 6894f2ba-d36a-4422-ab20-4c26a629dee2, 6287cfc2-2638-4665-8d7f-0fa1425886f8
caso-falseador: Um acidente grave em sistema com defesas em camadas plenamente explicado por uma única falha isolada, sem condição latente concorrente, falsearia a exigência de conjunção.
pai-proposto:
substitui:

## refatoracao-segura
rotulo: Refatoração segura
natureza: processo
estatuto: doutrinario
definicao: Mudar a estrutura interna do código sem mudar o que ele faz, em passos pequenos, rodando os testes a cada passo — o teste verde confirma que o comportamento sobreviveu à mudança. Código sem teste exige um passo anterior: primeiro criar o teste que fotografa o comportamento atual, mesmo com defeitos, e só então mexer. Mexer em estrutura sem verificação a cada passo não é refatorar, é editar no escuro — e é assim que a limpeza bem-intencionada quebra o que funcionava.
obras-ancora: 909016ea-adef-4401-8893-6dda164599d5, 78fa1de3-e516-4f3d-b883-ba1f5851b24e, f497a2e3-f236-4ef1-ac97-4b2a35d388b1
caso-falseador: Uma reestruturação ampla feita sem teste intermediário que preservasse comportamento de forma verificável com custo igual ou menor falsearia a exigência dos passos verificados.
pai-proposto:
substitui:

## fabrica-de-software
rotulo: Fábrica de software (modelo de contratação)
natureza: modelo
estatuto: instituido
definicao: Modelo de contratação de desenvolvimento em que o cliente especifica, o fornecedor produz e o pagamento sai de uma métrica sobre o artefato — tanto por ponto de função, uma unidade que estima o tamanho do que foi construído. É o arranjo dominante na administração pública federal brasileira. O mecanismo que o define: a métrica de pagamento passa a governar a produção — o fornecedor otimiza o que o contrato mede, não o que o software resolve em uso — e a fronteira contratual entre especificar e construir se ergue antes de qualquer linha de código.
obras-ancora: 27880d0e-c12c-4b74-a22b-2924e1d266bb, f445a084-f568-4cf9-9a02-4adcc20abe5c
caso-falseador: Um contrato de fábrica remunerado por métrica de artefato cujo comportamento de produção comprovadamente otimizasse resultado em uso, e não a métrica, falsearia o mecanismo de captura pelo indicador.
pai-proposto:
substitui:

## implantabilidade-independente
rotulo: Implantabilidade independente
natureza: disposicao
estatuto: doutrinario
definicao: Propriedade de uma parte do sistema que pode ir ao ar sozinha: muda-se ali, publica-se ali, e nada mais precisa ser publicado junto. Para isso a fronteira precisa de um contrato explícito e estável — o que ela aceita e o que devolve — e cada mudança tem que continuar honrando o que os vizinhos já usam. Partes que dividem o mesmo banco de dados ou que só sobem em bloco coordenado não têm essa propriedade, ainda que se chamem serviços ou microsserviços.
obras-ancora: 8780a2a8-018b-408a-898a-21d3b93cb86c, c2d7efe8-2057-48d6-803a-b4cd5f99dbef, d1700fc7-f115-485a-84ab-7a5de5065ff7
caso-falseador: Um sistema de serviços com contratos estáveis e retrocompatíveis que ainda assim exigisse liberação coordenada rotineira falsearia a suficiência do contrato estável para a independência.
pai-proposto:
substitui:

## ordenacao-causal
rotulo: Ordenação causal de eventos
natureza: fenomeno
estatuto: natural
definicao: Em um sistema espalhado por várias máquinas, não há relógio comum confiável. A única ordem real entre acontecimentos é a que a causalidade dá: A veio antes de B se os dois ocorreram em sequência na mesma máquina, ou se A enviou uma mensagem que B recebeu. Acontecimentos sem esse elo são simultâneos de verdade — não existe resposta para qual veio primeiro. Qualquer ordem total que o sistema exiba entre eles foi imposta por uma regra de desempate, e tratar essa convenção como fato é fonte clássica de erro em sistema distribuído.
obras-ancora: ef949ef2-da4d-49a2-a760-4a8d5af605fa, 73eaf549-b429-4d23-853a-c5eaf22b54d2
caso-falseador: Um mecanismo que determinasse ordem total verdadeira entre eventos concorrentes sem convenção de desempate e sem canal de comunicação entre eles falsearia a parcialidade da ordem observável.
pai-proposto:
substitui:
