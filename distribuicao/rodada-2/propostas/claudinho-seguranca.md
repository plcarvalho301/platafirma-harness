# Propostas de conceito — claudinho-seguranca (rodada 2)

Balde B primeiro. 9 conceitos em B, 16 em A.

---

## delegado-confuso
balde: B
rotulo: Delegado confuso
natureza: fenomeno
estatuto: doutrinario
definicao: Um intermediário autorizado a agir em nome de terceiros exerce a autoridade que ele próprio detém a pedido de quem não a detém, e o alvo não distingue as duas origens porque só vê a credencial do intermediário. A correção é vincular cada ato à parte pretendida — destinatário declarado na credencial, consentimento por ato, e proibição de repassar adiante a credencial recebida.
obras-ancora: 53623fd3-8767-48ae-9734-c31fe4c944a3, 6834144d-a0aa-4ed9-a3b4-163821f7ef44, d2f456aa-560c-4b52-b316-3f021aa027bf
caso-falseador: Um intermediário que valida destinatário e obtém consentimento por ato, e ainda assim é usado para exercer autoridade que o solicitante não tem — mostraria que o vínculo ao destinatário não é o mecanismo que decide.
pai-proposto:
substitui:

## janela-de-exposicao
balde: B
rotulo: Janela de exposição
natureza: fenomeno
estatuto: doutrinario
definicao: Entre o momento em que um defeito conhecido passa a ser explorável e o momento em que a correção está em produção, o risco corre. Todo controle de processo interposto nesse intervalo — teste, aprovação, janela de mudança — reduz o risco de a correção quebrar a operação e aumenta o risco de o defeito ser explorado; a decisão não é entre seguro e inseguro, é a escolha de qual dos dois riscos se prefere pagar.
obras-ancora: 176f8130-6c77-4357-bcfe-7327cf27f028, 8db0629c-213e-44d0-981d-0d8a28fc6523, 942fc75b-d7f1-487b-9007-20aee0f3ea53
caso-falseador: Um defeito conhecido cuja correção existe e cuja demora em aplicar não altera a probabilidade de exploração — a janela seria irrelevante e o único risco seria o da mudança.
pai-proposto:
substitui:

## transparencia-de-composicao
balde: B
rotulo: Transparência de composição
natureza: disposicao
estatuto: doutrinario
definicao: Propriedade de um artefato entregue cuja árvore de constituintes — fornecedor, nome, versão, identificador e relação de dependência, inclusive as transitivas — é declarada pelo produtor em forma legível por máquina, de modo que quem apenas opera o artefato responda "isto contém o componente X na versão Y?" sem consultar o produtor. O que a declaração não alcança é declarado como tal, em vez de omitido.
obras-ancora: 356094cd-262c-4f71-96d2-3d08d64b7d51, 05346de7-dbd7-4dff-a671-fb7f1b9347d7, 32198e7c-9015-4f37-bb60-af093cc883d7
caso-falseador: Uma vulnerabilidade nova em componente de terceiro cujo alcance o operador determina tão rápido e tão bem sem a declaração quanto com ela.
pai-proposto:
substitui:

## padrao-como-politica
balde: B
rotulo: Padrão como decisão de política
natureza: fenomeno
estatuto: doutrinario
definicao: Em sistema configurável, o valor pré-selecionado é o que vigora para a maioria dos afetados, porque a maioria não intervém. Logo a escolha do valor de fábrica é a política efetiva do sistema, e oferecer a opção contrária não a corrige — só transfere ao afetado o ônus de descobrir e exercer a opção.
obras-ancora: d346fdb2-d5fa-4516-a09d-3f6b42879b85, 2fdb66e9-7619-4b1d-bde3-5c8645c8cf98, ac644f13-98c5-4a69-aed5-7cf535b2afd3
caso-falseador: População em que a taxa de alteração do valor de fábrica se aproxima de 100%, tornando o default irrelevante para o resultado agregado.
pai-proposto:
substitui:

## dano-de-privacidade-sem-incidente
balde: B
rotulo: Dano de privacidade sem incidente de segurança
natureza: fenomeno
estatuto: doutrinario
definicao: O prejuízo ao indivíduo pode nascer de operação plenamente autorizada e conforme os controles de confidencialidade — agregação de fontes lícitas, identificação a partir de dado indireto, uso para finalidade diversa, exclusão do próprio titular da decisão que o afeta. Logo a ausência de acesso não autorizado não é evidência de ausência de dano, e o inventário de ameaças de segurança não enumera estas.
obras-ancora: ded222ae-1d8e-41e8-81d0-24f3120233ae, 3ac98f67-b89b-444f-8a23-b5222c0ebf9f, c610bf79-cb67-437a-8e95-b19002ad5843
caso-falseador: Um dano ao titular apontado por esta régua que, examinado, sempre se reduza a uma falha de confidencialidade, integridade ou disponibilidade — a régua seria redundante com a de segurança.
pai-proposto:
substitui:

## base-legal-de-tratamento
balde: B
rotulo: Base legal de tratamento
natureza: modelo
estatuto: instituido
definicao: A licitude de uma operação sobre dado pessoal não deriva da utilidade dela nem do cuidado técnico com que é feita: deriva de o agente enquadrá-la, antes de operar, em uma das hipóteses taxativas previstas para a categoria do dado. As hipóteses não são intercambiáveis depois do fato, e a que serve para um dado comum pode não servir para um dado sensível.
obras-ancora: bf28004e-9a60-4d74-8427-c7f4de6951ed, fcc6e4c0-540e-4c7c-8164-4a8ce802d620, d1d43914-fe4a-40ae-90b1-8aef3f36250a, 584148dc-1402-4852-b676-7c1a4ae85967
caso-falseador: Tratamento reconhecido como lícito por ser demonstradamente benéfico e bem protegido, sem enquadramento em hipótese alguma.
pai-proposto:
substitui:

## avaliacao-de-conformidade
balde: B
rotulo: Avaliação de conformidade
natureza: processo
estatuto: instituido
definicao: Regime em que três papéis são separados por desenho — o fornecedor declara e produz evidência, um laboratório acreditado ensaia contra requisito escrito de antemão, e uma autoridade emite ou nega a validação. O que o selo cobre é o objeto na configuração ensaiada contra aquele conjunto de requisitos, e nada além disso; a garantia não se estende ao produto que embute o objeto nem a versões posteriores.
obras-ancora: 6f6c4e3a-1d35-4871-bafe-c4f5c4f4768f, 4ff459f2-1084-46d4-9e5f-72407c57b395, a24ab830-046b-4a72-b47c-f9faee40d9d1
caso-falseador: Regime em que o próprio fornecedor ensaia e emite o selo e cujo resultado seja indistinguível, em taxa de erro, do regime com laboratório e autoridade separados.
pai-proposto:
substitui:

## requisito-verificavel
balde: B
rotulo: Requisito verificável
natureza: modelo
estatuto: doutrinario
definicao: Um enunciado prescritivo só governa quando vem acompanhado de (a) um procedimento de verificação que produz veredito binário sobre um objeto concreto e (b) um procedimento de correção do objeto que reprovou. Sem os dois, o enunciado é intenção declarada: não distingue quem cumpre de quem não cumpre, e por isso não se audita nem se delega.
obras-ancora: ba8bde5d-b9d8-4500-b996-2222f5d721ed, 4ff459f2-1084-46d4-9e5f-72407c57b395, c8e53981-7b8c-4faa-bab4-3b5d42db3dcd
caso-falseador: Enunciado sem procedimento de verificação nem de correção que, aplicado por avaliadores independentes, produza o mesmo veredito sobre o mesmo objeto.
pai-proposto:
substitui:

## vida-util-do-sigilo
balde: B
rotulo: Vida útil do sigilo
natureza: fenomeno
estatuto: doutrinario
definicao: Toda informação protegida tem um prazo pelo qual precisa permanecer inacessível ao adversário. Somado ao tempo de migrar a proteção, esse prazo se compara ao tempo estimado até a quebra do mecanismo em uso: se a soma o excede, o dado já está comprometido no instante em que é transmitido ou armazenado, ainda que a proteção de hoje seja íntegra e o adversário só o abra depois.
obras-ancora: 50337d04-5bf5-406d-9847-14fd742c5762, f7f3152d-5f2a-44f2-af64-a1f629d2031b, 345317ba-f37f-4806-8d54-796a33ecfbaa
caso-falseador: Classe de dado cujo prazo de sigilo exceda o tempo até a quebra do mecanismo e cuja exposição futura não produza dano — a soma dos prazos não decidiria nada.
pai-proposto:
substitui:

---

## acesso-delegado
balde: A
rotulo: Acesso delegado
natureza: modelo
estatuto: doutrinario
definicao: Arranjo em que um terceiro obtém acesso limitado a um recurso em nome do dono sem receber a credencial do dono: uma autoridade separada media a aprovação e emite ao terceiro uma autorização própria, restrita em alcance e em prazo, revogável sem tocar na credencial original.
obras-ancora: d2f456aa-560c-4b52-b316-3f021aa027bf, 26489992-4238-4238-b989-1a68dcb507a9, 53623fd3-8767-48ae-9734-c31fe4c944a3
caso-falseador: Arranjo que entrega ao terceiro a credencial do dono e ainda assim permite revogar só aquele terceiro, sem afetar os demais acessos do dono.
pai-proposto: autorizacao
substitui:

## token-portador
balde: A
rotulo: Token portador
natureza: modelo
estatuto: doutrinario
definicao: Credencial cuja simples apresentação basta para o uso: quem a detém exerce tudo o que qualquer outro detentor exerceria, sem provar posse de chave associada. Toda a proteção colapsa no sigilo do armazenamento e do transporte, e o contraste é a credencial de prova de posse, que exige demonstrar controle de uma chave a cada uso.
obras-ancora: d2f456aa-560c-4b52-b316-3f021aa027bf, 26a4deeb-bc53-4515-a2de-f3bbaaa82ec6, 6834144d-a0aa-4ed9-a3b4-163821f7ef44
caso-falseador: Credencial apresentável cuja captura por terceiro não lhe confira o mesmo poder que confere ao titular, sem que haja prova de posse envolvida.
pai-proposto:
substitui:

## prova-de-identidade
balde: A
rotulo: Prova de identidade
natureza: processo
estatuto: doutrinario
definicao: Ato anterior ao cadastro em que se coleta evidência sobre uma identidade do mundo real, se valida a autenticidade dessa evidência e se verifica que o requerente é a pessoa a quem ela se refere. Distingue-se da autenticação: aqui se estabelece o vínculo pela primeira vez; lá se reconhece um vínculo já estabelecido.
obras-ancora: 32d348ee-d5e3-4976-8fbc-7b39990d4093, 4acba478-4a57-4757-bf62-b6d3a8a25e87, 2aa19800-fbfa-4696-849c-30f294e9555d
caso-falseador: Cadastro cuja robustez de autenticação posterior compense integralmente a ausência de vínculo verificado com pessoa real.
pai-proposto:
substitui:

## modulo-criptografico
balde: A
rotulo: Módulo criptográfico
natureza: modelo
estatuto: instituido
definicao: Conjunto de hardware, software ou firmware delimitado por uma fronteira declarada, dentro da qual residem as funções criptográficas aprovadas e os parâmetros críticos de segurança, e cujas interfaces, papéis, serviços, autotestes e proteções físicas são especificados por nível. A garantia se aplica ao que está dentro da fronteira, não ao produto que o contém.
obras-ancora: 179a4f48-3857-496c-a595-652da85a3bd6, e6820da1-9d67-4222-922b-6952adfce2d1, aa8e9400-4191-47ab-841c-1abb2d9fc391
caso-falseador: Implementação criptográfica sem fronteira delimitável cujas garantias de nível ainda assim se apliquem de forma verificável.
pai-proposto:
substitui:

## criptoperiodo
balde: A
rotulo: Criptoperíodo
natureza: modelo
estatuto: doutrinario
definicao: Intervalo durante o qual uma chave permanece autorizada para uso legítimo. É limitado para reduzir o material disponível à criptanálise, conter o alcance do comprometimento de uma única chave e não ultrapassar a vida útil estimada do algoritmo — e é ele, não a conveniência operacional, que fixa a cadência de rotação.
obras-ancora: e0b892df-8ff4-4980-a2e3-cf34dc4b1652, 345317ba-f37f-4806-8d54-796a33ecfbaa, 942fc75b-d7f1-487b-9007-20aee0f3ea53
caso-falseador: Chave cujo uso indefinido não aumente nem o material de criptanálise disponível nem o alcance do dano em caso de comprometimento.
pai-proposto:
substitui:

## credenciamento-de-seguranca
balde: A
rotulo: Credenciamento de segurança
natureza: processo
estatuto: instituido
definicao: Habilitação prévia e formal — de pessoa, órgão ou entidade privada — para tratar informação classificada em determinado grau, concedida por autoridade competente mediante requisitos verificados de idoneidade, qualificação técnica e designação de responsável nomeado. Sem a habilitação vigente não há tratamento lícito, ainda que haja necessidade e meio técnico.
obras-ancora: 54830b16-c29b-46ad-b593-cb433223d68a, 1f737904-a895-45ca-b0d3-dc3525812760, a4e8fd93-e0ea-4421-94e0-4ea2394f55d3
caso-falseador: Acesso lícito a informação classificada concedido a quem tem necessidade funcional comprovada mas não foi habilitado.
pai-proposto:
substitui:

## necessidade-de-conhecer
balde: A
rotulo: Necessidade de conhecer
natureza: modelo
estatuto: instituido
definicao: Dois requisitos independentes governam o acesso a informação restrita: a habilitação, que fixa o teto do grau acessível, e a necessidade inerente ao exercício concreto de cargo, função ou atividade, que fixa o que dentro desse teto de fato se acessa. Ter o grau não confere acesso; a necessidade sem o grau tampouco.
obras-ancora: a4e8fd93-e0ea-4421-94e0-4ea2394f55d3, 6be72be3-f054-4a17-9eee-e6153752b168, 54830b16-c29b-46ad-b593-cb433223d68a
caso-falseador: Qualquer dos dois eixos decidindo sozinho e isso ser tido por correto — pessoa credenciada em grau superior recebendo documento daquele grau sem função que o demande, ou pessoa cuja função exige o documento recebendo acesso sem credencial no grau. Se um dos casos for decidido pelo mínimo necessário à tarefa, a régua da conjunção não delimita nada.
pai-proposto:
substitui:

## politica-de-seguranca-institucional
balde: A
rotulo: Política de segurança institucional
natureza: modelo
estatuto: instituido
definicao: Instrumento formal aprovado pela autoridade máxima da organização que fixa diretrizes, nomeia os papéis responsáveis — gestor, comitê, equipe de tratamento de incidentes — e obriga a organização inteira. Medida declarada obrigatória de que se abre mão exige motivação registrada em análise de risco, e é esse registro que a distingue de declaração de intenção.
obras-ancora: 84b18391-a10b-4675-93ab-9e998eb22872, 512719fb-b958-4624-bcf9-934035a6e165, 0e153a8f-3a33-41e6-9b7a-c9d92ef8218d
caso-falseador: Conjunto de diretrizes sem aprovação da autoridade máxima e sem papéis nomeados que produza obrigação exigível na organização.
pai-proposto:
substitui:

## linha-de-base-de-controles
balde: A
rotulo: Linha de base de controles
natureza: modelo
estatuto: doutrinario
definicao: Conjunto de controles pré-selecionado para uma classe de sistema, que vigora por padrão sem escolha item a item. A adequação ao caso concreto se faz por ações de ajuste declaradas, e cada exceção exige motivo registrado, revisão e plano de eliminação — de modo que o desvio permaneça rastreável e a linha continue servindo de referência de auditoria.
obras-ancora: decf5337-c365-4b51-9a5d-1ce052bd266b, 514d9c80-98e9-402f-be23-350542b3537d, be8ef329-d1ea-4927-8f79-b1d9f2088ad7, 5d4a5862-9b1c-42d0-a8f7-b10ac3b98ea7
caso-falseador: Organização que selecione controles item a item desde o zero e cujos desvios permaneçam igualmente rastreáveis e auditáveis.
pai-proposto:
substitui:

## controlador-e-operador
balde: A
rotulo: Controlador e operador
natureza: modelo
estatuto: instituido
definicao: Responde pelo tratamento quem determina a finalidade e os meios, não quem executa. Executar em nome de outro sob instrução documentada não transfere a responsabilidade; usar o dado para finalidade própria, fora da instrução, converte o executor em responsável por aquele tratamento.
obras-ancora: c0ff6f00-34a2-48a8-a991-1a3b7cda0dc7, 655219ad-ded9-4df7-99dc-e9a67451b73e, d1d43914-fe4a-40ae-90b1-8aef3f36250a
caso-falseador: Executor que trate dado para finalidade própria, fora de qualquer instrução, e continue respondendo apenas como executor.
pai-proposto:
substitui:

## comunicacao-de-incidente-ao-titular
balde: A
rotulo: Comunicação de incidente ao titular
natureza: processo
estatuto: instituido
definicao: Dever de comunicar à autoridade e às pessoas afetadas o incidente com dado pessoal que possa acarretar-lhes risco ou dano relevante, em prazo fixado e com conteúdo mínimo: natureza dos dados, titulares envolvidos, riscos, medidas de proteção existentes e medidas de reversão. O gatilho é o risco à pessoa, não a gravidade técnica do evento nem o sucesso da contenção.
obras-ancora: ac2f61ae-427b-42d5-a9f9-d24773318324, dac57d8b-c3aa-482b-b7e0-1e227f2ce49f, 2fdb66e9-7619-4b1d-bde3-5c8645c8cf98
caso-falseador: Incidente contido em minutos, sem exfiltração comprovada, que exponha dado sensível de milhares de pessoas e cuja não comunicação seja tida por correta.
pai-proposto:
substitui:

## avaliacao-de-impacto-a-privacidade
balde: A
rotulo: Avaliação de impacto à privacidade
natureza: processo
estatuto: instituido
definicao: Exame prévio de um tratamento novo ou alterado que descreve a operação, identifica os riscos que ela gera para os titulares e registra as medidas de mitigação adotadas. É obrigatório em hipóteses tipificadas — decisão automatizada com efeito jurídico, larga escala de dado sensível — e sua função é produzir o registro da decisão antes da operação, não depois.
obras-ancora: c0ff6f00-34a2-48a8-a991-1a3b7cda0dc7, bf28004e-9a60-4d74-8427-c7f4de6951ed, 2fdb66e9-7619-4b1d-bde3-5c8645c8cf98
caso-falseador: Tratamento de alto risco cujo exame conduzido depois da entrada em operação cumpra a mesma função que o exame prévio.
pai-proposto:
substitui:

## exercicio-de-plano
balde: A
rotulo: Exercício de plano
natureza: processo
estatuto: doutrinario
definicao: Simulação conduzida por cenário em que as pessoas com papel num plano discutem ou executam as ações que tomariam, para validar a viabilidade do plano. O objeto medido é o plano e o preparo de quem o executa — a saída útil é a lacuna descoberta —, e não a operabilidade do sistema, que é objeto de teste.
obras-ancora: 47cb0edc-b902-4a40-9d67-924b3b6402ed, e59a6f00-6f0e-49a9-b1fa-8aa1119f8bf9
caso-falseador: Plano validado por teste de componente sem que ninguém com papel nele tenha sido confrontado com um cenário, e que funcione na primeira crise real.
pai-proposto:
substitui:

## exercicio-adversarial
balde: A
rotulo: Exercício adversarial
natureza: processo
estatuto: doutrinario
definicao: Exercício em que uma equipe age como adversário contra defensores que podem não saber do exercício, para medir a capacidade de detectar, escalar e responder. Distingue-se do teste de intrusão pelo objeto medido: lá se estabelece se a falha existe e é explorável; aqui se estabelece o que a defesa percebeu e o que fez a respeito.
obras-ancora: 7584cebf-a903-4562-bba6-e6a362f0c060, 824055cc-577f-4496-8ae2-5006553bf8bd
caso-falseador: Exercício avisado à defesa cujo resultado sobre detecção e resposta seja indistinguível do não avisado.
pai-proposto:
substitui:

## regras-de-engajamento
balde: A
rotulo: Regras de engajamento
natureza: modelo
estatuto: doutrinario
definicao: Autorização escrita, anterior à atividade intrusiva, que delimita alvos incluídos e explicitamente excluídos, período, técnicas permitidas e proibidas, e quem aprova o desvio. É ela que separa o teste do ataque: fora do que ela cobre, a mesma ação técnica deixa de ser autorizada.
obras-ancora: 5370abf1-d240-4a8c-99bf-aa255b66ae81, 7584cebf-a903-4562-bba6-e6a362f0c060
caso-falseador: Atividade intrusiva sem delimitação escrita prévia cuja licitude seja aferível depois do fato apenas pela intenção de quem a conduziu.
pai-proposto:
substitui:

## negar-por-padrao
balde: A
rotulo: Negar por padrão
natureza: modelo
estatuto: doutrinario
definicao: Postura em que o sistema recusa tudo o que não estiver explicitamente permitido, de modo que a lista mantida é a de exceções autorizadas e o esquecimento produz recusa em vez de permissão. Distingue-se de menor privilégio: lá se decide o tamanho da permissão concedida; aqui se decide o que acontece quando não há decisão nenhuma.
obras-ancora: decf5337-c365-4b51-9a5d-1ce052bd266b, 307b8ba5-1af8-41b6-932d-ce5cafd40953, be8ef329-d1ea-4927-8f79-b1d9f2088ad7
caso-falseador: Configuração cuja lista mantida seja a de proibições explícitas e que ainda assim recuse o caso não previsto.
pai-proposto:
substitui: negar-por-padrao
