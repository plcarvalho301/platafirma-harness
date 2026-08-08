## relevancia-graduada
rotulo: Relevância graduada
natureza: modelo
estatuto: doutrinario
definicao: Relevância tratada como grau, não como binário: cada documento contribui ganho proporcional ao seu grau, acumulado ao longo do ranking com desconto por posição e normalizado pelo ranking ideal. Decide contra métrica binária (precisão@k) e contra métrica de primeiro acerto (MRR), que não distinguem o altamente relevante do marginal.
obras-ancora: a06bee67-eae0-48d1-a962-459e307d9e2e, 9841c613-c9d6-4dda-b283-775f25224789
caso-falseador: cenário em que juízos graduados são reprodutíveis entre juízes e, ainda assim, a ordenação de sistemas pela métrica graduada nunca diverge da ordenação pela binária — o grau não acrescentaria poder de decisão.
pai-proposto:
substitui:

## recuperacao-densa
rotulo: Recuperação densa
natureza: modelo
estatuto: doutrinario
definicao: Recuperação em que consulta e documento são codificados independentemente em vetores densos, e a relevância é uma operação barata sobre vetores — o que permite pré-computar o índice e buscar por vizinhança. Decide contra o codificador cruzado, que lê o par junto e por isso não indexa: ganha expressividade, perde a pré-computação.
obras-ancora: 02b2fdcb-bed3-490f-a0dd-2b59653140bb, 79ceb118-2e56-415c-81c4-9194f1f5cdd0, d699cba8-10c9-42d8-b71f-4a7c1ea317f6
caso-falseador: sistema que codifica consulta e documento conjuntamente e mesmo assim serve busca sobre índice pré-computado sem aproximação — quebraria o vínculo entre independência de codificação e pré-computação.
pai-proposto: recuperacao-semantica
substitui:

## interacao-tardia
rotulo: Interação tardia
natureza: modelo
estatuto: doutrinario
definicao: Consulta com mais de um conceito, comprimida em vetor único, colapsa num ponto médio que não corresponde a documento nenhum — o casamento fino se perde na média. A interação tardia responde a isso: cada lado vira múltiplos vetores no nível do token, a codificação segue independente (o índice segue pré-computável) e o casamento é adiado para o escore, como soma de máximas similaridades. Compra a granularidade que o vetor único borra, ao preço de uma ordem de grandeza a mais de índice.
obras-ancora: 8488499a-032f-45e9-aa57-cc00062bf04a, 0abce3d7-d52a-4857-98e1-55f740854336
caso-falseador: modelo de vetor único que iguale a qualidade do casamento termo-a-termo fino sem o custo adicional de índice — o trade-off que define a variante desapareceria.
pai-proposto: recuperacao-densa
substitui:

## ranqueamento-multiestagio
rotulo: Ranqueamento multiestágio
natureza: modelo
estatuto: doutrinario
definicao: Pipeline de recuperação em que estágios sucessivos trocam volume de candidatos por custo de escore: um primeiro estágio barato e de alto recall gera o pool, estágios caros e precisos reordenam. O recall do primeiro estágio é teto do resultado — estágio tardio não recupera o que não entrou no pool.
obras-ancora: d699cba8-10c9-42d8-b71f-4a7c1ea317f6, 845f6353-b837-42e1-b04b-5b684776cf02, 5060852e-4f9e-40fc-8712-61c567e4651a
caso-falseador: pipeline em que aumentar a precisão dos estágios tardios compense, no resultado final, relevância ausente do pool do primeiro estágio.
pai-proposto:
substitui:

## workflow-vs-agente
rotulo: Workflow vs. agente
natureza: modelo
estatuto: doutrinario
definicao: A previsibilidade dos subpassos decide a topologia de execução: quando as subtarefas são conhecidas a priori, fluxo fixo composto (mais barato, auditável, otimizável por etapa); quando dependem do que se observa no caminho, loop aberto com orçamento. Régua de decisão, não taxonomia de sistemas.
obras-ancora: 119f1289-e99c-410d-9320-29bf3cd1ea06, c517ca62-5d1d-4ac8-840a-8dc0bfecfb2a
caso-falseador: tarefa de subpassos imprevisíveis resolvida consistentemente melhor por fluxo fixo do que por loop, a custo comparável.
pai-proposto:
substitui:

## isolamento-de-contexto-por-delegacao
rotulo: Isolamento de contexto por delegação
natureza: processo
estatuto: doutrinario
definicao: Delegação a subagente cuja função é separar orçamentos de contexto: a exploração queima tokens na janela do subagente e só o destilado volta ao orquestrador, que preserva a própria janela para síntese. Decide contra a delegação por especialização — aqui o motivo é a contabilidade de contexto, não a competência.
obras-ancora: f56aba50-8ded-412a-b3e0-3394de24c711, 21a3489b-bad2-406c-92fd-99c697250220, 42804aeb-ad42-40cc-b55b-febc38f7f037
caso-falseador: delegação de exploração pesada em que o retorno do subagente consome no orquestrador tanto quanto a exploração consumiria — o isolamento não pagaria o custo de coordenação.
pai-proposto: orquestracao-multi-agente
substitui:

## transporte-de-estado-entre-sessoes
rotulo: Transporte de estado entre sessões
natureza: processo
estatuto: doutrinario
definicao: Trabalho que excede uma janela de contexto se divide em sessões sem memória compartilhada; artefatos duráveis fora da janela (nota, lista de tarefas, log, arquivo), escritos por uma sessão e lidos pela seguinte, carregam o estado. O que não foi inscrito em artefato não existe para a sessão seguinte — inclusive o que a compactação descartou.
obras-ancora: 4ee66aba-abb1-4f3b-a2ff-c4d0b0c4b773, 392edecc-5cd3-4e7a-a23e-63f584558171, 08c18181-e019-4593-a37d-35ee7515aedd
caso-falseador: sessão sucessora recuperando consistentemente estado que nenhuma sessão anterior inscreveu em artefato acessível.
pai-proposto:
substitui:

## degradacao-diferencial-sob-compressao
rotulo: Degradação diferencial sob compressão
natureza: fenomeno
estatuto: natural
definicao: A perda de capacidade causada por compressão de modelo (quantização, esparsificação) não é uniforme: concentra-se em capacidades compostas de múltiplos turnos — uso de ferramenta, fluxo de trabalho agêntico — e pode ser invisível em benchmark de turno único. O efeito da compressão se mede na capacidade-alvo, não no benchmark genérico.
obras-ancora: 54b45e4b-4d81-4de7-ab48-cef80dec8679, 7b2be448-a27f-4e93-a47e-be74221e3183
caso-falseador: compressões variadas, em modelos variados, degradando benchmark de turno único e capacidade agêntica multi-turno nas mesmas proporções.
pai-proposto:
substitui:

## confundimento-de-ambiente-em-avaliacao
rotulo: Confundimento de ambiente em avaliação
natureza: fenomeno
estatuto: natural
definicao: Parte da variação de um escore de avaliação de sistema com modelo é atribuível ao ambiente de execução — serving, latência, concorrência, harness — e não ao modelo. Um escore único não separa as duas fontes; atribuir delta ao modelo exige controlar ou medir o ambiente. Decide quando um delta autoriza conclusão sobre o modelo.
obras-ancora: 2c83db6a-7c2c-4d3a-8aa6-78a9f5f1019f, 4dbdb24e-b0dc-476b-a6e3-6ea77993d5bc
caso-falseador: escores de avaliação agêntica estáveis sob variação deliberada e ampla de infraestrutura — a variância de ambiente seria desprezível e o escore único bastaria.
pai-proposto:
substitui:

## mediacao-do-loop-agentico
rotulo: Mediação do loop agêntico
natureza: modelo
estatuto: doutrinario
definicao: Desenho do ponto em que a ação do agente é liberada: aprovação humana por ação, revisão automática por política, ou execução livre dentro de fronteira de isolamento previamente definida. A régua troca custo de mediação (fadiga de aprovação, latência, configuração) por raio de dano da ação não revisada — e prevê que mediação por ação degrada a própria vigilância que a justifica.
obras-ancora: 680b1e1d-ae7c-4570-a18a-9da45b30d568, a3c90b5b-b359-4216-b6a3-a36c06ad22a9, 21a3489b-bad2-406c-92fd-99c697250220
caso-falseador: aprovação humana por ação mantendo vigilância efetiva constante ao longo de sessões longas — a fadiga de aprovação não existiria e o trade-off colapsaria.
pai-proposto:
substitui:
