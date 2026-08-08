# Propostas de conceitos — claudinho-arquiteto (rodada 2)

## problema-perverso
rotulo: Problema perverso
natureza: fenomeno
estatuto: doutrinario
definicao: A formulação do problema não é dada, é escolhida — e cada formulação já embute uma classe de solução; não há teste objetivo de correção nem critério de parada, e o trabalho encerra por esgotamento de recurso ou decisão, não por "resolver". Decide contra o problema domado, que tem enunciado estável e teste de solução fixado ex ante.
obras-ancora: c70e4339-4aff-4607-ac0e-abf2a95142e0, dc3404fc-d73f-4ead-83e4-1812a83ae109
caso-falseador: Um problema social ou de projeto cujo enunciado permaneceu estável e cuja solução foi verificada contra teste fixado antes do trabalho e aceito por todos os atores.
pai-proposto:
substitui:

## estruturacao-de-problema
rotulo: Estruturação de problema
natureza: processo
estatuto: doutrinario
definicao: Produzir o enunciado do problema como artefato de trabalho — quem percebe, o que deseja, onde há conflito entre atores — antes de qualquer otimização; a escolha do enunciado predetermina o espaço de soluções, e a saída é uma formulação que sustenta acordo, não um ótimo. Decide contra a otimização (que exige enunciado dado) e contra product discovery (cujo objeto é a necessidade do usuário de um produto, não o enunciado disputado entre atores).
obras-ancora: ad68ae5e-2f64-4ba4-bf2d-74735f723fb7, acd7590d-e3f9-4282-a023-5c8c0f698bd4, a640b765-42e6-4463-bd4f-5f4a28ad2d9a
caso-falseador: Enunciados distintos do mesmo caso conduzindo sistematicamente ao mesmo espaço de soluções — a escolha do enunciado não faria trabalho.
pai-proposto:
substitui:

## mecanismo-de-coordenacao
rotulo: Mecanismo de coordenação
natureza: modelo
estatuto: doutrinario
definicao: Trabalho dividido exige um modo declarado de coordenação (ajuste mútuo, supervisão direta, padronização; colaboração, X-as-a-Service, facilitação), e a estrutura viável deriva do modo dominante — redesenhar caixas sem trocar o modo não muda a organização. Decide contra a lei de Conway, cujo objeto é o efeito da comunicação sobre a forma do artefato, não o modo pelo qual o trabalho se coordena.
obras-ancora: 49689a0b-bdb6-4707-8f51-b7d742642eaa, 2216a203-568e-485b-b822-094fc3552cb5
caso-falseador: Organização que troca o mecanismo de coordenação dominante e permanece viável sem nenhum rearranjo estrutural.
pai-proposto:
substitui:

## fronteira-por-custo-de-transacao
rotulo: Fronteira por custo de transação
natureza: modelo
estatuto: doutrinario
definicao: A fronteira — da firma ou do módulo — se traça comparando o custo de coordenar dentro com o custo de transacionar fora através de uma interface; quando os custos relativos mudam, a fronteira economicamente sustentável se move, e a fronteira modular bem posta cria opção de substituição com valor próprio. Decide contra fronteiras traçadas por semântica de domínio ou por carga cognitiva: aqui o operador é o custo comparado.
obras-ancora: be47cca3-dbb6-4024-8ea2-d781cda1dcf7, fdda4108-8a68-4599-b2ae-9dcdc8ce4738
caso-falseador: Fronteira que permanece estável enquanto os custos relativos se invertem, sem outra força nomeável que a sustente.
pai-proposto:
substitui:

## cascata-de-objetivos
rotulo: Cascata de objetivos
natureza: modelo
estatuto: doutrinario
definicao: Necessidade de stakeholder se traduz em objetivo corporativo, que se traduz em objetivo de alinhamento, que seleciona e prioriza processos e recursos; a decisão local se justifica pelo rastro até o topo, e objetivo sem rastro não tem lastro. Decide contra OKR: lá o mecanismo é pactuação colaborativa de metas por ciclo, aqui é derivação rastreável entre níveis.
obras-ancora: 94d1793e-30b2-416a-bb79-48579d6e77ff, ccc19c82-6204-4c1c-a8f2-c8a76a093b2c, d47bad12-585f-4acf-924d-4d62395b749c
caso-falseador: Processos selecionados sem rastro entregando sistematicamente os objetivos de topo tão bem quanto os rastreados — o rastro não faria trabalho.
pai-proposto:
substitui:

## fluxo-de-valor
rotulo: Fluxo de valor
natureza: modelo
estatuto: doutrinario
definicao: Sequência de estágios, disparada por um stakeholder, que acumula itens de valor até a proposição de valor final; cada estágio tem critério de entrada e de saída e é habilitado por capacidades. É o "o quê" percebido de ponta a ponta, cruzando funções — decide contra business capability (bloco estável de habilidade, sem sequência) e contra o processo (o "como" de cada etapa).
obras-ancora: 3c66afe9-b83f-4b6b-aafd-b4ea658d446d, 9c23b902-9501-48f3-add0-75bfaeec4978
caso-falseador: Valor entregue a um stakeholder que nenhuma sequência de estágios com critérios de entrada e saída representa sem perder o que importa na entrega.
pai-proposto:
substitui:

## processo-de-negocio
rotulo: Processo de negócio
natureza: modelo
estatuto: doutrinario
definicao: O trabalho é gerido pela travessia — entrada, atividades coordenadas, saída de valor — e não pela função que o executa; o processo é objeto próprio de desenho, medição e melhoria cíclica, redesenhável sem que a capacidade que o sustenta mude. Decide contra automação de processos (execução por sistema, não a unidade de gestão) e contra gestão de projetos (empreendimento temporário, não travessia repetível).
obras-ancora: 9c23b902-9501-48f3-add0-75bfaeec4978, d47bad12-585f-4acf-924d-4d62395b749c
caso-falseador: Organização que melhora sistematicamente suas entregas gerindo apenas funções, sem que nenhuma travessia ponta a ponta seja desenhada ou medida.
pai-proposto:
substitui:

## abertura-por-padrao
rotulo: Abertura por padrão
natureza: modelo
estatuto: instituido
definicao: O regime fixa o acesso ao dado como presunção e a restrição como exceção enquadrada em categoria prévia; o ônus argumentativo é de quem restringe, e o rito de acesso é decidido pelo nível declarado ex ante, não por negociação bilateral caso a caso. Decide contra a classificação da informação (que atribui nível de sensibilidade sem fixar direção da presunção) e contra regimes de base legal, em que a presunção é inversa.
obras-ancora: b340e6db-53c6-4d4c-bb35-8f2dc8ef3d6f, 89cff7b4-3dff-4c88-bd07-3af200efd55d
caso-falseador: Dentro do regime, uma restrição de acesso sem enquadramento em exceção categorizada sustentada como válida.
pai-proposto:
substitui:

## governanca-dados
rotulo: Governança de dados
natureza: modelo
estatuto: doutrinario
definicao: Alocação de autoridade sobre o dado — quem fixa política, quem decide exceção, quem responde pela qualidade — separada da gestão que executa; governar dados é decidir quem decide, em arranjo transversal às funções, e a operação madura desaparece no dia a dia em vez de virar departamento. Decide contra a gestão de dados: a obra entra se seu objeto é a alocação de autoridade e supervisão, não a execução de pipeline.
obras-ancora: 0fde1528-69b7-4742-a517-dc7ae81bed1c, 129fbd44-6695-4885-9078-cd7ab0cf996f
caso-falseador: Organização em que a mesma unidade executa e supervisiona o dado, sem conflito, com resultados de qualidade e conformidade indistinguíveis dos arranjos separados — a separação não faria trabalho.
pai-proposto: governanca
substitui: governanca-dados
