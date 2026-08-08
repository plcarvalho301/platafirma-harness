# Propostas de conceitos — claudinho-TI (rodada 2)

## desempenho-de-entrega
rotulo: Desempenho de entrega de software
natureza: modelo
estatuto: doutrinario
definicao: Medição do processo de entrega por quatro resultados pareados — tempo de ciclo da mudança, frequência de implantação, taxa de falha de mudança e tempo de recuperação — em que vazão e estabilidade são lidas juntas e movem juntas. A medida afere resultado global do processo, não produção local de artefato, e sua melhora não se compra com a piora do par.
obras-ancora: ac6ffd6c-935f-4f68-b22e-7585f87bdf1b, d87cf7a6-2e2c-4df6-a468-bad132a2cdc9, d4d60417-3306-4bbd-87fd-71f68fa83225, c88796df-1090-46c0-abb1-e2df40135ef5
caso-falseador: Um conjunto de equipes que, medido pelas quatro chaves, sustente por anos vazão de elite com estabilidade baixa (ou o inverso) mostraria que os pares não movem juntos e a régua estaria errada.
pai-proposto:
substitui:

## esteira-de-implantacao
rotulo: Esteira de implantação
natureza: processo
estatuto: doutrinario
definicao: Caminho único e automatizado que leva toda mudança de commit a artefato liberável, atravessando estágios eliminatórios (verificação rápida, artefato versionado, aceitação em ambiente similar a produção). Nenhuma mudança chega ao ar por fora dela, e cada estágio pode rejeitar o candidato.
obras-ancora: d1700fc7-f115-485a-84ab-7a5de5065ff7, ac6ffd6c-935f-4f68-b22e-7585f87bdf1b
caso-falseador: Uma organização em que mudanças rotineiramente entram em produção por caminho manual paralelo sem perda de desempenho de entrega falsearia a exigência do caminho único.
pai-proposto:
substitui:

## registro-de-decisao-arquitetural
rotulo: Registro de decisão arquitetural
natureza: modelo
estatuto: doutrinario
definicao: Documento curto e imutável que fixa uma decisão de construção com contexto, decisão em voz afirmativa e consequências, portando estado próprio (proposta, aceita, substituída). Preserva o porquê contra mudança de contexto e muda por substituição encadeada, nunca por edição do registro original.
obras-ancora: 69bcfac2-af6c-4f52-b60c-f23470aaa10b, d4ca606e-d882-474a-8425-638a9a1ab144, ea6739f1-d054-48b1-8558-2fde8c25429e
caso-falseador: Um repositório de decisões editadas em lugar de substituídas que ainda assim preserve, verificavelmente, a recuperação do racional original falsearia a exigência de imutabilidade.
pai-proposto:
substitui:

## servico-de-ti
rotulo: Serviço de TI
natureza: modelo
estatuto: doutrinario
definicao: Meio de entregar valor a um cliente sem que ele carregue os custos e riscos específicos da entrega. Cria valor para o cliente por si; o que habilita ou compõe a entrega sem valer sozinho para o cliente é componente de serviço, construído sobre itens de configuração. Confundir os dois infla o catálogo com itens que ninguém contrata, gera cobrança que o cliente não reconhece e torna o portfólio impriorizável, porque tudo virou serviço.
obras-ancora: eb62b2c7-4bac-444a-8f80-2720248da7f9, 0934a1d3-3449-4deb-8280-8499200c960b, 1e06d3ee-cdf2-439a-a8a3-8599df02e926, 3034a632-9b42-4fe0-94f9-37079aa060e2
caso-falseador: Um cliente que contrate e valore diretamente um item que a régua classifica como mero componente (sem serviço acima) mostraria que o corte valor-para-cliente não separa os casos.
pai-proposto:
substitui:

## orcamento-de-erro
rotulo: Orçamento de erro
natureza: modelo
estatuto: doutrinario
definicao: Conversão de um alvo de confiabilidade (SLO) na quantidade de indisponibilidade que o negócio aceita gastar num período. A decisão operacional (alertar, congelar mudança, priorizar confiabilidade sobre feature) é tomada pela taxa projetada de queima do orçamento, não pelo evento pontual de falha.
obras-ancora: 6287cfc2-2638-4665-8d7f-0fa1425886f8, 2d8ad6b2-344f-42bf-b982-c04051129efa
caso-falseador: Um serviço governado por orçamento de erro em que alertas por queima projetada sistematicamente cheguem depois da violação do SLO (sem margem de ação) falsearia o mecanismo preditivo da régua.
pai-proposto:
substitui:

## falha-sistemica
rotulo: Falha sistêmica
natureza: fenomeno
estatuto: natural
definicao: Em sistema complexo defendido em camadas, a catástrofe exige a conjunção de múltiplas falhas pequenas atravessando defesas simultaneamente; falha de ponto único não basta. "Causa raiz" única é atribuição retrospectiva do analista, não propriedade do evento — a análise correta busca as condições latentes concorrentes, não um culpado singular.
obras-ancora: 6894f2ba-d36a-4422-ab20-4c26a629dee2, 6287cfc2-2638-4665-8d7f-0fa1425886f8
caso-falseador: Um acidente grave em sistema com defesas em camadas plenamente explicado por uma única falha isolada, sem condição latente concorrente, falsearia a exigência de conjunção.
pai-proposto:
substitui:

## refatoracao-segura
rotulo: Refatoração segura
natureza: processo
estatuto: doutrinario
definicao: Mudança de estrutura interna que preserva comportamento observável, executada em passos pequenos verificados por teste a cada passo. Código sem teste (legado) exige primeiro criar o ponto de verificação — costura e teste de caracterização — antes de qualquer mudança; intervenção estrutural sem verificação a cada passo não é refatoração, é edição arriscada.
obras-ancora: 909016ea-adef-4401-8893-6dda164599d5, 78fa1de3-e516-4f3d-b883-ba1f5851b24e, f497a2e3-f236-4ef1-ac97-4b2a35d388b1
caso-falseador: Uma reestruturação ampla feita sem teste intermediário que preservasse comportamento de forma verificável com custo igual ou menor falsearia a exigência dos passos verificados.
pai-proposto:
substitui:

## fabrica-de-software
rotulo: Fábrica de software (modelo de contratação)
natureza: modelo
estatuto: instituido
definicao: Arranjo contratual que separa quem especifica (cliente) de quem produz (fornecedor) e remunera a produção por artefato medido (ponto de função, UST). A métrica de pagamento passa a governar o comportamento de produção: otimiza-se o que o contrato mede, não o resultado do software em uso. A fronteira contratual e a métrica de remuneração precedem e condicionam o processo de construção.
obras-ancora: 27880d0e-c12c-4b74-a22b-2924e1d266bb, f445a084-f568-4cf9-9a02-4adcc20abe5c
caso-falseador: Um contrato de fábrica remunerado por métrica de artefato cujo comportamento de produção comprovadamente otimizasse resultado em uso, e não a métrica, falsearia o mecanismo de captura pelo indicador.
pai-proposto:
substitui:

## implantabilidade-independente
rotulo: Implantabilidade independente
natureza: disposicao
estatuto: doutrinario
definicao: Propriedade de uma fronteira de construção pela qual uma mudança dentro dela pode ser implantada e liberada sem implantar nenhuma outra parte do sistema. Exige contrato explícito e estável na fronteira, com evolução retrocompatível; fronteiras que compartilham banco ou exigem liberação coordenada não a possuem, qualquer que seja o nome que carreguem.
obras-ancora: 8780a2a8-018b-408a-898a-21d3b93cb86c, c2d7efe8-2057-48d6-803a-b4cd5f99dbef, d1700fc7-f115-485a-84ab-7a5de5065ff7
caso-falseador: Um sistema de serviços com contratos estáveis e retrocompatíveis que ainda assim exigisse liberação coordenada rotineira falsearia a suficiência do contrato estável para a independência.
pai-proposto:
substitui:

## ordenacao-causal
rotulo: Ordenação causal de eventos
natureza: fenomeno
estatuto: natural
definicao: Em sistema distribuído, a única ordem observável entre eventos é a relação aconteceu-antes — parcial, definida por sequência local e troca de mensagem. Eventos não conectados por essa relação são concorrentes; qualquer ordem total entre eles é imposta por convenção (relógio lógico, timestamp), não observada. Uma afirmação de ordem é causal se deriva da relação parcial; é convencional se exige desempate arbitrário.
obras-ancora: ef949ef2-da4d-49a2-a760-4a8d5af605fa, 73eaf549-b429-4d23-853a-c5eaf22b54d2
caso-falseador: Um mecanismo que determinasse ordem total verdadeira entre eventos concorrentes sem convenção de desempate e sem canal de comunicação entre eles falsearia a parcialidade da ordem observável.
pai-proposto:
substitui:
