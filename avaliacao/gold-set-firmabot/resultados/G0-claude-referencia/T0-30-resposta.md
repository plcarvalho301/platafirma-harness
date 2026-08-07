## Nível de garantia de autenticação

**Definição geral (derivada de [3]):** é o grau de confiança que um provedor de serviço tem de que o usuário autenticado numa sessão é de fato o dono legítimo da conta. Esse grau varia conforme a força do mecanismo usado — por exemplo, autenticar só com senha estática dá menos garantia do que autenticar também com um código de uso único gerado no celular do usuário, porque é mais difícil um impostor ter acesso ao segundo fator. Quando uma aplicação exige elevar essa garantia para liberar uma operação mais sensível, o mecanismo usado para isso é o *step-up authentication*.

Importante: a fonte [3] (*Solving Identity Management in Modern Applications*, cap. 12, seção "Step-Up Authentication") é explícita em dizer que os nomes e a numeração dos níveis ali ("nível um", "nível dois") são **exemplo arbitrário de ilustração** do autor, não uma escala normativa — isso está transcrito da fonte, não é uma taxonomia oficial.

**Como termo técnico formal (NIST):** a sigla AAL (*Authentication Assurance Level*) é conceito próprio do NIST SP 800-63B. O trecho recuperado dessa obra [1] confirma a existência do conceito — o Preface diz textualmente: *"This document, SP 800-63B, provides requirements to credential service providers (CSPs) for remote user authentication at each of three authentication assurance levels (AALs)"* — mas o breadcrumb desse trecho é "List of Figures/Preface", e o conteúdo que chegou não inclui a seção que de fato define e caracteriza AAL1, AAL2 e AAL3. Ou seja: **confirmo, transcrito da fonte, que existem três AALs definidos no SP 800-63B, mas as fontes que chegaram não cobrem o conteúdo de cada nível** — não tenho de onde tirar as características técnicas de cada AAL sem especular.

O companheiro [2] (SP 800-63-4, volume geral) também só trouxe List of Figures/Preface, sem detalhar AAL.

Se quiser, posso responder com a caracterização técnica de AAL1/AAL2/AAL3 (número de fatores exigidos, resistência a phishing, etc.) como **leitura minha sem fonte no que chegou** — mas nesse caso preciso que você autorize essa marcação explicitamente, já que não está lastreada em nenhuma das fontes recebidas neste turno.
