# Propostas de conceito — claudinha-produto (rodada 2)

## design-reality-gap
rotulo: Gap desenho-realidade
natureza: fenomeno
estatuto: doutrinario
definicao: O risco de fracasso de um sistema é função da distância, medida dimensão a dimensão (informação, tecnologia, processos, objetivos e valores, pessoal, gestão, outros recursos), entre as premissas embutidas no desenho e a realidade presente no local de implantação. Distância grande em qualquer dimensão prediz fracasso independentemente da qualidade técnica do desenho; reduzir o gap — do lado do desenho ou da realidade — é o que muda o prognóstico.
obras-ancora: 055bb041-99b4-438e-9ef3-c47b9f57f3bb, 01b7a7f5-a172-40cf-a714-a1bcaa7e0887, 69a02423-aeff-488e-8484-95d13428f821
caso-falseador: Projetos com gaps grandes e não reduzidos em várias dimensões sucedendo na mesma taxa que projetos com gaps pequenos.
pai-proposto:
substitui:

## affordance
rotulo: Affordance
natureza: disposicao
estatuto: natural
definicao: Relação entre propriedades de um artefato e capacidades de um agente que determina as ações possíveis desse agente sobre o artefato. Existência e percepção são separáveis: a ação pode ser possível e não sinalizada (escondida), sinalizada e impossível (falsa), ou possível e sinalizada (percebida) — e é essa separação que produz veredito sobre uma interface: o que ela permite versus o que ela comunica que permite.
obras-ancora: 282e3564-800f-48e7-9a59-d3a4127fda17, e4eb5dc4-70e2-4239-99eb-b52786ccbf6f
caso-falseador: Usuários novatos operando corretamente, de forma sistemática e sem instrução externa, ações que o artefato em nada sinaliza.
pai-proposto:
substitui:

## outcome-sobre-output
rotulo: Outcome sobre output
natureza: modelo
estatuto: doutrinario
definicao: A unidade de progresso de uma entrega é a mudança observável de comportamento humano que liga o artefato entregue ao resultado de negócio; a funcionalidade é meio, e uma entrega sem comportamento-alvo declarado não tem como ser julgada bem-sucedida. O teste é responder, antes de construir: que ator passa a fazer o quê de diferente, e como isso move o objetivo.
obras-ancora: c441aacc-2f04-4eed-b836-d5975a74d5c9, 52c6dbe4-41f1-445c-8c82-e2978b5b2c1a
caso-falseador: Entregas sem qualquer mudança de comportamento mensurável produzindo sistematicamente o resultado de negócio pretendido.
pai-proposto:
substitui:

## quatro-riscos-de-produto
rotulo: Quatro riscos de produto
natureza: modelo
estatuto: doutrinario
definicao: Uma descoberta está completa quando há evidência coletada — não opinião de quem decide — contra quatro riscos distintos: o cliente escolhe usar (valor), o usuário consegue usar (usabilidade), dá para construir (viabilidade técnica) e funciona para o negócio (viabilidade de negócio). Endereçar um risco não endereça os outros; a régua reprova descoberta que só produziu evidência de valor.
obras-ancora: df1b01d4-a2c9-4350-8a1d-488538ab00e1, 39b473eb-0c70-4a66-a371-d9258970541b
caso-falseador: Produtos construídos sem evidência contra um dos quatro riscos falhando na mesma taxa dos que a coletaram.
pai-proposto: product-discovery
substitui:

## entrevista-por-comportamento-passado
rotulo: Entrevista por comportamento passado
natureza: processo
estatuto: doutrinario
definicao: Em conversa de descoberta, conta como evidência o relato de comportamento passado específico e o compromisso concreto (tempo, dinheiro, reputação); opinião sobre a ideia, elogio e projeção de uso futuro não contam. Mencionar a própria ideia cedo contamina a coleta, porque o interlocutor passa a responder sobre a ideia, não sobre a própria vida.
obras-ancora: eabfd878-771f-40d2-b32a-1ceb7868fad2, 567e3b24-9241-46de-a441-4ecc61f6246f, 39b473eb-0c70-4a66-a371-d9258970541b
caso-falseador: Opinião direta do entrevistado sobre a ideia predizendo o comportamento real de compra ou uso melhor que o relato de comportamento passado.
pai-proposto:
substitui:

## avaliacao-heuristica
rotulo: Avaliação heurística
natureza: processo
estatuto: doutrinario
definicao: Inspeção de interface, sem usuário presente, contra uma lista finita de princípios verificáveis (visibilidade do estado do sistema, correspondência com o mundo real, controle do usuário, consistência, prevenção de erro, reconhecimento em vez de memorização, entre outros), produzindo reprovação por violação nomeada. O veredito sai da correspondência tela-princípio, não do gosto do avaliador.
obras-ancora: 34b52e04-32e3-467b-9b5d-bbb557f32c1f, 30f215b8-ced5-45f6-8102-1f42270ac289, 6c39dde2-5020-4688-b848-9e33119a6906
caso-falseador: Problemas graves de uso, encontrados depois em teste com usuário, que nenhuma inspeção contra a lista tinha como capturar — como padrão, não como exceção.
pai-proposto:
substitui:

## teste-de-usabilidade-diy
rotulo: Teste de usabilidade faça-você-mesmo
natureza: processo
estatuto: doutrinario
definicao: Observação de poucos participantes (cerca de três) executando tarefas e pensando em voz alta, em cadência recorrente e barata, otimizando pelo número de problemas que a equipe consegue consertar até a rodada seguinte — não pela cobertura total de problemas existentes. O debrief fecha com o compromisso de correção dos mais graves; recrutamento é solto porque os problemas graves aparecem para quase qualquer participante.
obras-ancora: c5e911b6-337a-4870-b241-51527584d899, 6cb845f0-7b24-4618-9531-39442e41588b
caso-falseador: Rodadas recorrentes de três participantes deixando sistematicamente de revelar os problemas mais graves que amostras grandes revelam.
pai-proposto:
substitui:

## fatiamento-por-jornada
rotulo: Fatiamento por jornada completa
natureza: processo
estatuto: doutrinario
definicao: Um release se recorta como fatia horizontal do fluxo narrativo: o menor conjunto que permite a um ator completar a jornada do gatilho até o objetivo entregue ou abandonado. Fatia que recorta por componente, camada ou dependência técnica não passa, porque nenhum ator completa nada com ela; a unidade de aceite é o comportamento de ponta a ponta, escrito antes da construção.
obras-ancora: a8cf6e26-abfe-40cf-9838-167e1f00460f, 17af4452-44d9-46ab-b187-72b2349b7b3c
caso-falseador: Releases fatiados por camada técnica entregando valor verificável por usuário na mesma taxa que fatias de jornada completa.
pai-proposto:
substitui:

## design-centrado-no-humano
rotulo: Design centrado no humano
natureza: processo
estatuto: instituido
definicao: Um processo de desenvolvimento é centrado no humano quando satisfaz quatro condições verificáveis: parte de entendimento explícito de usuários, tarefas e ambiente; envolve usuários ativamente ao longo do ciclo; é dirigido e refinado por avaliação centrada no usuário, inclusive no aceite final; e itera até eliminar a incerteza. A evidência de conformidade é a avaliação com usuário registrada em cada atividade, não a intenção declarada.
obras-ancora: 010e40c5-9911-4bb3-bf23-e771eea8bb70, 79e6c38d-168a-4e71-a301-a45f22f8f91f, be3803d2-2f8d-4c9f-89c2-9b4523edbc7e
caso-falseador: Processos que satisfazem as quatro condições produzindo sistemas rejeitados pelos usuários na mesma taxa que processos que as ignoram.
pai-proposto:
substitui:

## esquema-de-organizacao
rotulo: Esquema de organização
natureza: modelo
estatuto: doutrinario
definicao: Toda coleção exposta a busca se organiza por esquema exato (alfabético, cronológico, geográfico — uma resposta certa por item, exige que o usuário saiba o que procura) ou ambíguo (assunto, tarefa, público — agrupamento por julgamento, serve a quem não sabe nomear o que procura). O esquema escolhido decide se o usuário encontra sem dominar o vocabulário do sistema — e encontrar precede qualquer uso.
obras-ancora: 7417496f-a949-4862-8398-f252caf58ae9, 30f215b8-ced5-45f6-8102-1f42270ac289
caso-falseador: Usuários que não sabem nomear o que procuram encontrando, em esquema exato, na mesma taxa que em esquema ambíguo bem construído.
pai-proposto:
substitui:
