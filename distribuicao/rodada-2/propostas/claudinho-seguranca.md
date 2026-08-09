# Propostas de conceito — claudinho-seguranca (rodada 2)

Balde B primeiro. 9 conceitos em B, 16 em A.

---

## autoridade-do-intermediario
balde: B
rotulo: Autoridade do intermediário
natureza: fenomeno
estatuto: doutrinario
definicao: Um programa que atende várias pessoas costuma ter mais poder do que qualquer uma delas: o sistema de folha pode ler o salário de todo mundo, e cada funcionário só pode ler o seu. Quando alguém faz um pedido a esse programa, quem aparece do outro lado é o programa, com o poder dele — não a pessoa, com o poder dela. É o problema que a literatura chama de delegado confuso. A correção não é confiar menos no intermediário, é amarrar cada pedido a quem o originou: a credencial declara para qual destino foi emitida e é recusada em qualquer outro, o consentimento é dado por ato e não uma vez para sempre, e a credencial recebida de um lado nunca é repassada adiante para o outro.
obras-ancora: 53623fd3-8767-48ae-9734-c31fe4c944a3, 6834144d-a0aa-4ed9-a3b4-163821f7ef44, d2f456aa-560c-4b52-b316-3f021aa027bf
caso-falseador: Um intermediário que valida destinatário e obtém consentimento por ato, e ainda assim é usado para exercer autoridade que o solicitante não tem — mostraria que o vínculo ao destinatário não é o mecanismo que decide.
pai-proposto:
substitui:

## janela-de-exposicao
balde: B
rotulo: Janela de exposição
natureza: fenomeno
estatuto: doutrinario
definicao: Entre o dia em que uma falha vira conhecida e o dia em que a correção está no ar, o sistema fica aberto — e quem ataca sabe disso, porque a falha foi anunciada em público junto com o remendo. Tudo que se coloca dentro desse intervalo para reduzir o risco de quebrar a operação — testar em homologação, esperar a janela de manutenção do fim de semana, colher aprovação — é pago em tempo de exposição. Não existe escolha entre seguro e inseguro: existe escolher qual dos dois riscos se prefere correr, o de a correção derrubar o serviço ou o de alguém entrar antes de ela chegar.
obras-ancora: 176f8130-6c77-4357-bcfe-7327cf27f028, 8db0629c-213e-44d0-981d-0d8a28fc6523, 942fc75b-d7f1-487b-9007-20aee0f3ea53
caso-falseador: Um defeito conhecido cuja correção existe e cuja demora em aplicar não altera a probabilidade de exploração — a janela seria irrelevante e o único risco seria o da mudança.
pai-proposto:
substitui:

## transparencia-de-composicao
balde: B
rotulo: Transparência de composição
natureza: disposicao
estatuto: doutrinario
definicao: Um software é montado com centenas de pedaços escritos por outras pessoas, e cada pedaço traz outros dentro. Transparência de composição é o produtor entregar, junto com o produto, a lista do que tem lá dentro — fornecedor, nome, versão e quem depende de quem — num formato que um programa consiga ler. No mundo do software essa lista tem nome próprio: SBOM. Ela existe para a pergunta que aparece de madrugada: saiu uma falha grave numa biblioteca, a gente usa? Sem a lista, a resposta depende de perguntar ao fornecedor e esperar. Com ela, quem só opera responde sozinho, em minutos. O que o produtor não conseguiu mapear entra declarado como desconhecido — buraco anunciado se procura, buraco omitido vira surpresa.
obras-ancora: 356094cd-262c-4f71-96d2-3d08d64b7d51, 05346de7-dbd7-4dff-a671-fb7f1b9347d7, 32198e7c-9015-4f37-bb60-af093cc883d7
caso-falseador: Uma vulnerabilidade nova em componente de terceiro cujo alcance o operador determina tão rápido e tão bem sem a declaração quanto com ela.
pai-proposto:
substitui:

## valor-de-fabrica
balde: B
rotulo: Valor de fábrica
natureza: fenomeno
estatuto: doutrinario
definicao: Quase ninguém abre as configurações. O valor que já vem marcado é o que vale para a maioria esmagadora das pessoas, e por isso ele não é detalhe técnico: é a política real do sistema. Um aplicativo que nasce com o perfil aberto e oferece o botão de fechar tem, na prática, perfil aberto. Daí a consequência incômoda para quem projeta: oferecer a opção contrária não corrige nada, apenas transfere ao usuário o trabalho de descobrir que ela existe. Quem escolhe o valor inicial está decidindo pelos outros, e o honesto é tratar isso como decisão, não como herança do fornecedor.
obras-ancora: d346fdb2-d5fa-4516-a09d-3f6b42879b85, 2fdb66e9-7619-4b1d-bde3-5c8645c8cf98, ac644f13-98c5-4a69-aed5-7cf535b2afd3
caso-falseador: População em que a taxa de alteração do valor de fábrica se aproxima de 100%, tornando o default irrelevante para o resultado agregado.
pai-proposto:
substitui:

## dano-sem-vazamento
balde: B
rotulo: Dano sem vazamento
natureza: fenomeno
estatuto: doutrinario
definicao: Nem todo prejuízo a uma pessoa vem de alguém invadindo alguma coisa. Cruzar três cadastros públicos e descobrir quem mora com quem; deduzir uma gravidez pelo histórico de compras; usar para reajustar um seguro o dado que foi coletado para marcar consulta. Em todos esses casos ninguém arrombou nada, todo mundo tinha acesso legítimo, e a pessoa saiu pior. Por isso não houve incidente de segurança não responde a houve dano. A lista de ameaças que serve para proteger sistema — invasão, adulteração, indisponibilidade — não enumera essas, e quem olha só por ela conclui que está tudo bem.
obras-ancora: ded222ae-1d8e-41e8-81d0-24f3120233ae, 3ac98f67-b89b-444f-8a23-b5222c0ebf9f, c610bf79-cb67-437a-8e95-b19002ad5843
caso-falseador: Um dano ao titular apontado por esta régua que, examinado, sempre se reduza a uma falha de confidencialidade, integridade ou disponibilidade — a régua seria redundante com a de segurança.
pai-proposto:
substitui:

## base-legal-de-tratamento
balde: B
rotulo: Base legal de tratamento
natureza: modelo
estatuto: instituido
definicao: Usar dado de pessoas exige uma permissão prevista em lei, escolhida antes de começar. Não basta o uso ser útil nem o dado estar bem guardado: a lei lista as situações em que se pode tratar dado pessoal — cumprir obrigação legal, executar contrato, consentimento, entre outras — e o uso precisa caber em uma delas. Duas consequências práticas. A permissão não se troca depois que o problema aparece, porque foi ela que justificou coletar aquele dado daquele jeito. E a lista muda conforme o dado: o que autoriza tratar um endereço não autoriza tratar um diagnóstico médico, que a lei protege à parte.
obras-ancora: bf28004e-9a60-4d74-8427-c7f4de6951ed, fcc6e4c0-540e-4c7c-8164-4a8ce802d620, d1d43914-fe4a-40ae-90b1-8aef3f36250a, 584148dc-1402-4852-b676-7c1a4ae85967
caso-falseador: Tratamento reconhecido como lícito por ser demonstradamente benéfico e bem protegido, sem enquadramento em hipótese alguma.
pai-proposto:
substitui:

## avaliacao-de-conformidade
balde: B
rotulo: Avaliação de conformidade
natureza: processo
estatuto: instituido
definicao: Três papéis separados de propósito: quem fabrica declara o que o produto faz, um laboratório credenciado testa contra requisitos escritos de antemão, e uma autoridade decide se emite o certificado. A separação é o mecanismo — se quem fabrica também testasse e certificasse, o selo não diria nada que a propaganda já não dissesse. O que costuma se perder na leitura é o alcance. O selo cobre aquele objeto, naquela configuração testada, contra aquela lista de requisitos. Um cofre certificado dentro de um sistema não certifica o sistema, e a versão seguinte do produto não herda o certificado da anterior.
obras-ancora: 6f6c4e3a-1d35-4871-bafe-c4f5c4f4768f, 4ff459f2-1084-46d4-9e5f-72407c57b395, a24ab830-046b-4a72-b47c-f9faee40d9d1
caso-falseador: Regime em que o próprio fornecedor ensaia e emite o selo e cujo resultado seja indistinguível, em taxa de erro, do regime com laboratório e autoridade separados.
pai-proposto:
substitui:

## requisito-verificavel
balde: B
rotulo: Requisito verificável
natureza: modelo
estatuto: doutrinario
definicao: Um requisito só governa se vier com duas coisas junto: como conferir se um caso concreto cumpre, e o que fazer quando não cumpre. O servidor deve ser seguro não separa quem cumpre de quem não cumpre — duas pessoas competentes olham a mesma máquina e discordam. O acesso remoto deve recusar senha e aceitar só chave, confira com tal comando, corrija em tal arquivo decide sozinho. Sem os dois procedimentos o texto é intenção declarada: não se audita, porque não há veredito; e não se delega, porque quem recebe a tarefa precisa adivinhar o que o autor queria.
obras-ancora: ba8bde5d-b9d8-4500-b996-2222f5d721ed, 4ff459f2-1084-46d4-9e5f-72407c57b395, c8e53981-7b8c-4faa-bab4-3b5d42db3dcd
caso-falseador: Enunciado sem procedimento de verificação nem de correção que, aplicado por avaliadores independentes, produza o mesmo veredito sobre o mesmo objeto.
pai-proposto:
substitui:

## vida-util-do-sigilo
balde: B
rotulo: Vida útil do sigilo
natureza: fenomeno
estatuto: doutrinario
definicao: Todo segredo tem prazo. Uma senha precisa durar até a próxima troca; um plano de defesa precisa durar trinta anos. Some a esse prazo o tempo que a organização levaria para trocar a proteção que usa hoje e compare com o tempo estimado até essa proteção ser quebrada. Se a soma passa, o dado já está perdido no momento em que trafega — ainda que a proteção esteja intacta e a quebra só aconteça daqui a uma década. É esse cálculo que explica adversários guardarem hoje tráfego cifrado que não conseguem abrir. Não precisam abrir agora; precisam que o conteúdo ainda importe quando abrirem.
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
definicao: Você quer que um aplicativo de notas fiscais leia seu e-mail, mas não quer entregar sua senha — com ela, o aplicativo lê tudo, para sempre, e você só corta trocando a senha. Acesso delegado é o arranjo que resolve isso: um terceiro serviço confirma com você o que será permitido e entrega ao aplicativo uma autorização própria, limitada ao que você aprovou e com prazo. O ganho está na revogação. Cancelar aquela autorização derruba aquele aplicativo e não afeta mais nada que você tenha autorizado, porque cada um recebeu a sua — impossível quando todos usam a mesma senha.
obras-ancora: d2f456aa-560c-4b52-b316-3f021aa027bf, 26489992-4238-4238-b989-1a68dcb507a9, 53623fd3-8767-48ae-9734-c31fe4c944a3
caso-falseador: Arranjo que entrega ao terceiro a credencial do dono e ainda assim permite revogar só aquele terceiro, sem afetar os demais acessos do dono.
pai-proposto: autorizacao
substitui:

## token-portador
balde: A
rotulo: Token portador
natureza: modelo
estatuto: doutrinario
definicao: Uma credencial de portador funciona como dinheiro em espécie: quem está com ela, gasta. O sistema que a recebe não pergunta se quem apresentou é o dono, porque não tem como perguntar — a posse é a prova. Isso torna tudo dependente do sigilo. Se ela aparece num registro de log, num histórico de navegação ou numa mensagem de erro, quem leu passa a poder o que o dono podia, até ela expirar. O arranjo alternativo exige que a cada uso o portador demonstre ter uma chave secreta que não trafega junto: mais caro de implementar, e imune ao roubo por cópia.
obras-ancora: d2f456aa-560c-4b52-b316-3f021aa027bf, 26a4deeb-bc53-4515-a2de-f3bbaaa82ec6, 6834144d-a0aa-4ed9-a3b4-163821f7ef44
caso-falseador: Credencial apresentável cuja captura por terceiro não lhe confira o mesmo poder que confere ao titular, sem que haja prova de posse envolvida.
pai-proposto:
substitui:

## prova-de-identidade
balde: A
rotulo: Prova de identidade
natureza: processo
estatuto: doutrinario
definicao: Antes de existir login, alguém precisa estabelecer que aquela conta corresponde a uma pessoa real, e a essa pessoa. É o que o banco faz na abertura da conta: recebe documentos, confere junto a quem os emitiu se são autênticos, e verifica se quem está ali é a pessoa retratada neles. Não se confunde com o login de todo dia. Ali se reconhece um vínculo que já existe; aqui ele é criado. Um sistema pode ter senha forte e segundo fator impecáveis e ainda assim estar dando acesso a quem se cadastrou com o documento dos outros — são problemas diferentes, resolvidos em momentos diferentes.
obras-ancora: 32d348ee-d5e3-4976-8fbc-7b39990d4093, 4acba478-4a57-4757-bf62-b6d3a8a25e87, 2aa19800-fbfa-4696-849c-30f294e9555d
caso-falseador: Cadastro cuja robustez de autenticação posterior compense integralmente a ausência de vínculo verificado com pessoa real.
pai-proposto:
substitui:

## modulo-criptografico
balde: A
rotulo: Módulo criptográfico
natureza: modelo
estatuto: instituido
definicao: É a caixa onde as operações com chaves acontecem, com uma fronteira desenhada e declarada: um cartão, um chip, uma biblioteca, um equipamento de rede. Dentro dela ficam as chaves e as funções que as usam; fora circula só o resultado. Os padrões definem níveis crescentes de exigência para essa caixa, incluindo o que ela deve fazer ao ser aberta à força — apagar as chaves. A distinção que importa na hora de comprar: a garantia vale para o que está dentro da fronteira. Um equipamento com módulo certificado embutido não é um equipamento certificado. O certificado descreve a caixa, não a casa.
obras-ancora: 179a4f48-3857-496c-a595-652da85a3bd6, e6820da1-9d67-4222-922b-6952adfce2d1, aa8e9400-4191-47ab-841c-1abb2d9fc391
caso-falseador: Implementação criptográfica sem fronteira delimitável cujas garantias de nível ainda assim se apliquem de forma verificável.
pai-proposto:
substitui:

## criptoperiodo
balde: A
rotulo: Criptoperíodo
natureza: modelo
estatuto: doutrinario
definicao: Toda chave tem prazo de validade, curto por três razões concretas. Quanto mais tempo a mesma chave cifra coisas, mais material acumulado alguém tem para tentar quebrá-la. Quanto mais tempo ela vale, maior o estrago se vazar — tudo que protegeu, do começo ao fim. E nenhuma chave deve durar mais que o algoritmo que a usa, que envelhece por conta própria. É esse prazo que manda na rotação. Trocar chave dá trabalho e costuma ser adiado pela agenda da operação; adiar é decidir correr o risco, não evitá-lo.
obras-ancora: e0b892df-8ff4-4980-a2e3-cf34dc4b1652, 345317ba-f37f-4806-8d54-796a33ecfbaa, 942fc75b-d7f1-487b-9007-20aee0f3ea53
caso-falseador: Chave cujo uso indefinido não aumente nem o material de criptanálise disponível nem o alcance do dano em caso de comprometimento.
pai-proposto:
substitui:

## credenciamento-de-seguranca
balde: A
rotulo: Credenciamento de segurança
natureza: processo
estatuto: instituido
definicao: Verificar a confiabilidade de uma pessoa custa caro e demora: antecedentes, vínculos, entrevista. Ninguém refaz isso cada vez que ela vai abrir um documento — e quem não faz nenhuma vez acaba liberando por conhecimento pessoal, confio nele, trabalhamos juntos. A saída é tirar a apuração do momento do acesso: ela vira ato próprio, feito antes por quem tem autoridade para tanto, com prazo. Na porta, a pergunta deixa de ser se a pessoa é confiável e passa a ser até que nível ela foi habilitada. O rigor da apuração é proporcional ao nível pretendido, escolhido antes de começar — não se apura o máximo possível, e é isso que faz o arranjo caber no orçamento. O que vem junto e costuma ser esquecido: o resultado envelhece entre o dia em que foi apurado e o dia em que é usado. Por isso todo arranjo desse tipo carrega validade, revalidação e cancelamento por fato novo — sem eles, o que se apresenta na porta é uma foto antiga usada como se fosse a pessoa de hoje.
obras-ancora: 54830b16-c29b-46ad-b593-cb433223d68a, 1f737904-a895-45ca-b0d3-dc3525812760, a4e8fd93-e0ea-4421-94e0-4ea2394f55d3
caso-falseador: Regime em que a confiabilidade é apurada no próprio ato de acesso, caso a caso, com custo e resultado equivalentes aos da apuração prévia — a habilitação antecipada não estaria comprando nada. Ou habilitação cujo valor não se degrade com o tempo decorrido desde a apuração, tornando prazo e revalidação supérfluos.
pai-proposto:
substitui:

## necessidade-de-conhecer
balde: A
rotulo: Necessidade de conhecer
natureza: modelo
estatuto: instituido
definicao: Dois requisitos independentes decidem quem vê um documento sigiloso, e é preciso passar nos dois. A habilitação prévia fixa o teto — até que grau aquela pessoa pode ir. A necessidade decorrente do que ela de fato faz no cargo fixa o que, dentro do teto, ela vê. Por isso um diretor habilitado no grau mais alto não tem direito a ler tudo daquele grau: falta a segunda condição, e ela não é dispensada por hierarquia. O inverso também vale — precisar muito não substitui a habilitação que não se tem. Cada requisito é concedido por autoridade diferente, e é essa separação que impede que um deles saia por conveniência.
obras-ancora: a4e8fd93-e0ea-4421-94e0-4ea2394f55d3, 6be72be3-f054-4a17-9eee-e6153752b168, 54830b16-c29b-46ad-b593-cb433223d68a
caso-falseador: Qualquer dos dois eixos decidindo sozinho e isso ser tido por correto — pessoa credenciada em grau superior recebendo documento daquele grau sem função que o demande, ou pessoa cuja função exige o documento recebendo acesso sem credencial no grau. Se um dos casos for decidido pelo mínimo necessário à tarefa, a régua da conjunção não delimita nada.
pai-proposto:
substitui:

## politica-de-seguranca-institucional
balde: A
rotulo: Política de segurança institucional
natureza: modelo
estatuto: instituido
definicao: Documento aprovado pelo dirigente máximo que diz o que a organização faz em segurança da informação e nomeia quem responde por cada parte: o gestor, o comitê, a equipe que atende incidentes. Vale para a organização inteira, inclusive para quem não gostou. O que separa isso de uma carta de intenções é o tratamento da exceção. Quando se decide não implementar uma medida declarada obrigatória, a justificativa e a análise de risco ficam registradas. Sem esse registro não há política — há um texto que todos contornam sem deixar rastro, e ninguém consegue dizer depois quem decidiu contornar.
obras-ancora: 84b18391-a10b-4675-93ab-9e998eb22872, 512719fb-b958-4624-bcf9-934035a6e165, 0e153a8f-3a33-41e6-9b7a-c9d92ef8218d
caso-falseador: Conjunto de diretrizes sem aprovação da autoridade máxima e sem papéis nomeados que produza obrigação exigível na organização.
pai-proposto:
substitui:

## linha-de-base-de-controles
balde: A
rotulo: Linha de base de controles
natureza: modelo
estatuto: doutrinario
definicao: Em vez de cada equipe escolher controle por controle, parte-se de um conjunto pronto para aquele tipo de sistema — servidor web, banco de dados, estação de trabalho — que passa a valer por padrão. O ajuste ao caso concreto se faz por decisões declaradas sobre essa base, e cada item de que se abre mão exige motivo escrito, revisão e plano para voltar a cumprir. O valor está em inverter o esforço. Sem a base, quem audita precisa reconstruir o que deveria estar configurado em cada máquina. Com ela, compara com a referência e discute a lista curta de desvios, que já vem com o motivo ao lado.
obras-ancora: decf5337-c365-4b51-9a5d-1ce052bd266b, 514d9c80-98e9-402f-be23-350542b3537d, be8ef329-d1ea-4927-8f79-b1d9f2088ad7, 5d4a5862-9b1c-42d0-a8f7-b10ac3b98ea7
caso-falseador: Organização que selecione controles item a item desde o zero e cujos desvios permaneçam igualmente rastreáveis e auditáveis.
pai-proposto:
substitui:

## controlador-e-operador
balde: A
rotulo: Controlador e operador
natureza: modelo
estatuto: instituido
definicao: Responde pelo tratamento de dados quem decide para que servem e como serão usados, não quem opera os sistemas. A empresa que contrata um serviço de disparo de e-mail responde pela campanha; o fornecedor executa o contratado e responde por seguir a instrução. A regra tem uma virada importante. Se o fornecedor usa aqueles dados para finalidade própria — treinar um produto dele, montar uma base para vender — deixa de ser executor naquele ponto e passa a responder como quem decidiu. A responsabilidade acompanha quem escolheu a finalidade, e escolher sem contrato não isenta ninguém.
obras-ancora: c0ff6f00-34a2-48a8-a991-1a3b7cda0dc7, 655219ad-ded9-4df7-99dc-e9a67451b73e, d1d43914-fe4a-40ae-90b1-8aef3f36250a
caso-falseador: Executor que trate dado para finalidade própria, fora de qualquer instrução, e continue respondendo apenas como executor.
pai-proposto:
substitui:

## comunicacao-de-incidente-ao-titular
balde: A
rotulo: Comunicação de incidente ao titular
natureza: processo
estatuto: instituido
definicao: Incidente com dado pessoal que possa trazer risco relevante às pessoas tem que ser avisado. A organização comunica a autoridade e as pessoas atingidas, em prazo definido, dizendo quais dados foram afetados, quem foi afetado, quais os riscos, o que os protegia e o que está sendo feito. O gatilho é o risco para a pessoa, não o tamanho técnico do estrago. Um incidente contido em dez minutos, sem prova de cópia, que expôs dados de saúde de mil pacientes, dispara o dever; uma invasão espetacular em servidor sem dado pessoal não dispara. É quem foi avisado que decide o que fazer com o aviso — trocar senha, vigiar a fatura —, e por isso segurar a informação é dano somado ao dano.
obras-ancora: ac2f61ae-427b-42d5-a9f9-d24773318324, dac57d8b-c3aa-482b-b7e0-1e227f2ce49f, 2fdb66e9-7619-4b1d-bde3-5c8645c8cf98
caso-falseador: Incidente contido em minutos, sem exfiltração comprovada, que exponha dado sensível de milhares de pessoas e cuja não comunicação seja tida por correta.
pai-proposto:
substitui:

## avaliacao-de-impacto-a-privacidade
balde: A
rotulo: Avaliação de impacto à privacidade
natureza: processo
estatuto: instituido
definicao: Exame feito antes de ligar um tratamento novo, ou de mudar um que já roda, que descreve a operação, lista os riscos que ela cria para as pessoas e registra o que foi feito para reduzi-los. Em algumas situações a lei o exige: decisão automatizada com efeito jurídico sobre alguém, uso em larga escala de dado sensível. A palavra que carrega o peso é antes. Com o sistema no ar, mudar o desenho custa caro e a conclusão tende a acompanhar o que já foi construído. O documento serve para que a decisão exista por escrito enquanto ainda dá para decidir diferente.
obras-ancora: c0ff6f00-34a2-48a8-a991-1a3b7cda0dc7, bf28004e-9a60-4d74-8427-c7f4de6951ed, 2fdb66e9-7619-4b1d-bde3-5c8645c8cf98
caso-falseador: Tratamento de alto risco cujo exame conduzido depois da entrada em operação cumpra a mesma função que o exame prévio.
pai-proposto:
substitui:

## exercicio-de-plano
balde: A
rotulo: Exercício de plano
natureza: processo
estatuto: doutrinario
definicao: Reunir quem tem papel num plano — de crise, de recuperação, de continuidade — e apresentar um cenário: pegou fogo no datacenter às três da manhã de domingo, o que cada um faz? Pode ser conversa em volta da mesa ou pode chegar a executar as ações de verdade. O que se mede é o plano e o preparo de quem o executa, não o equipamento. A saída útil é a lacuna descoberta: o telefone do fornecedor que mudou, o passo que dependia de alguém que saiu, a decisão que ninguém sabe de quem é. Testar se o servidor reserva liga é outra coisa, e não substitui esta.
obras-ancora: 47cb0edc-b902-4a40-9d67-924b3b6402ed, e59a6f00-6f0e-49a9-b1fa-8aa1119f8bf9
caso-falseador: Plano validado por teste de componente sem que ninguém com papel nele tenha sido confrontado com um cenário, e que funcione na primeira crise real.
pai-proposto:
substitui:

## exercicio-adversarial
balde: A
rotulo: Exercício adversarial
natureza: processo
estatuto: doutrinario
definicao: Um grupo é contratado para agir como o inimigo — invadir, enganar funcionários, entrar no prédio — enquanto quem defende segue a rotina, muitas vezes sem saber que há exercício em curso. O que se mede é a defesa, não o alvo. Um teste de invasão comum responde se a falha existe e dá para explorar. Aqui a pergunta é outra: alguém percebeu, em quanto tempo, avisou quem, e o que fez depois. O resultado mais comum e mais desconfortável é a invasão ter dado certo por um caminho já conhecido e o alerta ter aparecido sem que ninguém olhasse.
obras-ancora: 7584cebf-a903-4562-bba6-e6a362f0c060, 824055cc-577f-4496-8ae2-5006553bf8bd
caso-falseador: Exercício avisado à defesa cujo resultado sobre detecção e resposta seja indistinguível do não avisado.
pai-proposto:
substitui:

## regras-de-engajamento
balde: A
rotulo: Regras de engajamento
natureza: modelo
estatuto: doutrinario
definicao: Documento assinado antes de qualquer teste que mexa em sistema de verdade. Ele fixa o que pode ser atacado, o que fica expressamente de fora, em que período, com quais técnicas, o que é proibido — derrubar serviço, tocar em dado real de cliente — e quem autoriza sair do combinado. É ele que separa o teste do crime. A mesma ação técnica, sem esse papel, é acesso não autorizado, e a boa intenção de quem executou não serve de defesa. Vale também para dentro de casa: sem escopo escrito, alguém varre uma faixa de rede que era de outra empresa e a conversa seguinte é com o jurídico.
obras-ancora: 5370abf1-d240-4a8c-99bf-aa255b66ae81, 7584cebf-a903-4562-bba6-e6a362f0c060
caso-falseador: Atividade intrusiva sem delimitação escrita prévia cuja licitude seja aferível depois do fato apenas pela intenção de quem a conduziu.
pai-proposto:
substitui:

## negar-por-padrao
balde: A
rotulo: Negar por padrão
natureza: modelo
estatuto: doutrinario
definicao: O sistema recusa tudo que não estiver expressamente liberado. A lista que alguém mantém é a das exceções autorizadas, e o caso que ninguém previu cai na recusa — a instalação nova nasce fechada e vai abrindo conforme se justifica. A diferença em relação a conceder pouco é sutil e decide muito. Lá se discute o tamanho da permissão de quem já foi considerado; aqui se decide o que acontece com quem ninguém considerou. Como esquecer é a regra e não a exceção, a postura de recusa transforma o esquecimento em chamado de suporte, e a postura oposta transforma o mesmo esquecimento em porta aberta que ninguém vai procurar.
obras-ancora: decf5337-c365-4b51-9a5d-1ce052bd266b, 307b8ba5-1af8-41b6-932d-ce5cafd40953, be8ef329-d1ea-4927-8f79-b1d9f2088ad7
caso-falseador: Configuração cuja lista mantida seja a de proibições explícitas e que ainda assim recuse o caso não previsto.
pai-proposto:
substitui: negar-por-padrao
